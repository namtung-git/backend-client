"""
    Provisioning server
    ===================

    .. Copyright:
        Copyright 2020 Wirepas Ltd under Apache License, Version 2.0.
        See file LICENSE for full license details.
"""

import time
import logging
import queue
import argparse

from wirepas_backend_client.api import (
    MQTTSettings,
    MQTTObserver,
    Topics,
    topic_message,
)
from wirepas_backend_client.tools import (
    ParserHelper,
    LoggerHelper,
    deferred_thread,
)
from wirepas_backend_client.management import Daemon
from .events import (
    ProvisioningEventPacketReceived,
    ProvisioningEventPacketSent,
)
from .sm import ProvisioningStateMachine, ProvisioningStatus
from .message import ProvisioningMessageFactory, ProvisioningMessageException
from .data import ProvisioningData


class ProvParserHelper(ParserHelper):
    def __init__(
        self,
        description="argument parser",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    ):
        super(ProvParserHelper, self).__init__(
            description=description, formatter_class=formatter_class
        )

    def add_provisioning(self):
        """ Commonly used Provisioning arguments """

        self.provisioning.add_argument(
            "--provisioning_config",
            default="./config.yml",
            action="store",
            type=str,
            help="Provisioning config file path ",
        )


class ProvisioningObserver(MQTTObserver):
    """
    ProvisioningObserver

    """

    # Wirepas Provisioning Protocol endpoints :
    #  - Downlink: Source: 255 ; Destination: 246
    #  - Uplink: Source: 246 ; Destination: 255
    PROV_DOWNLINK_EP = "255"
    PROV_UPLINK_EP = "246"

    def __init__(self, response_queue, **kwargs):

        self.response_queue = response_queue
        self.message_subscribe_handlers = {
            "gw-event/received_data/+/+/+/"
            + self.PROV_UPLINK_EP
            + "/"
            + self.PROV_DOWNLINK_EP: self.generate_data_received_cb(),
            "gw-response/send_data/#": self.generate_data_response_cb(),
        }

        self.mqtt_topics = Topics()

        super(ProvisioningObserver, self).__init__(
            message_subscribe_handlers=self.message_subscribe_handlers,
            **kwargs
        )

    def generate_data_response_cb(self) -> callable:
        @topic_message
        def on_gateway_data_response_cb(payload, topic_items):
            """ Decodes a data response """
            message = self.mqtt_topics.constructor(
                "response", "send_data"
            ).from_payload(payload)

            if self.start_signal.is_set():
                self.logger.debug("received send_data response %s", message)
                self.response_queue.put(message)
            else:
                self.logger.debug("Waiting for manager readiness.")

        return on_gateway_data_response_cb


class ProvisioningServer(object):
    def __init__(
        self,
        data_queue,
        request_queue,
        response_queue,
        settings,
        exit_signal=None,
        logger=None,
    ):
        super(ProvisioningServer, self).__init__()

        self.request_queue = request_queue
        self.data_queue = data_queue
        self.response_queue = response_queue
        self.exit_signal = exit_signal
        self.logger = logger or logging.getLogger(__name__)

        self.sessions = {}
        self.send_list = {}

        self.data = ProvisioningData(settings.provisioning_config, logger)

    @deferred_thread
    def _manage_data_queue(self, exit_signal, q, block=True, timeout=60):
        while not exit_signal.is_set():
            try:
                message = q.get(block=block, timeout=timeout)
            except queue.Empty:
                continue
            # Catch EOFError when process is killed with Ctrl+C
            except EOFError:
                break

            try:
                msg_data = ProvisioningMessageFactory.map(message)
            except ProvisioningMessageException as e:
                print(e)
                continue
            ev = ProvisioningEventPacketReceived(msg_data)
            self.logger.debug("Got new packet: %s.", msg_data)

            try:
                self.sessions[msg_data.msg_id].event_q.put(ev)
                self.logger.debug("Found SM with id: %s.", msg_data)
            except KeyError:
                self.logger.info("Create new SM with id: %s.", msg_data)
                self.sessions[msg_data.msg_id] = ProvisioningStateMachine(
                    self,
                    msg_data.msg_id,
                    self.data,
                    exit_signal=self.exit_signal,
                    logger=self.logger,
                )
                self.sessions[msg_data.msg_id].event_q.put(ev)

    @deferred_thread
    def _manage_response_queue(self, exit_signal, q, block=True, timeout=60):
        while not exit_signal.is_set():
            try:
                message = self.response_queue.get(block=block, timeout=timeout)
            except queue.Empty:
                continue
            # Catch EOFError when process is killed with Ctrl+C
            except EOFError:
                break

            self.logger.debug("Got new response: %s.", message.req_id)

            ev = ProvisioningEventPacketSent(message.req_id, message.res)

            try:
                self.send_list[message.req_id].event_q.put(ev)
                del self.send_list[message.req_id]
            except KeyError:
                continue

    def loop(self, sleep_for=0.1):
        """
        Client loop

        """

        self._manage_data_queue(self.exit_signal, self.data_queue)
        self._manage_response_queue(self.exit_signal, self.response_queue)
        while not self.exit_signal.is_set():
            time.sleep(sleep_for)
            for key in list(self.sessions.keys()):
                if self.sessions[key].status is not ProvisioningStatus.ONGOING:
                    self.logger.info(
                        "Provisioning Session %s terminated with result: %s.",
                        self.sessions[key],
                        self.sessions[key].status,
                    )
                    del self.sessions[key]

    def send_packet(self, obj, msg):
        self.logger.debug(
            "Sending packet with req_id: %s.", msg["data"].req_id
        )
        self.logger.debug("%s", msg["data"])
        self.send_list[msg["data"].req_id] = obj
        self.request_queue.put(msg)


def main():
    """ Main loop """

    parser = ProvParserHelper(description="Default arguments")

    parser.add_file_settings()
    parser.add_mqtt()
    parser.add_provisioning()
    parser.add_fluentd()

    settings = parser.settings(settings_class=MQTTSettings)

    if settings.debug_level is None:
        settings.debug_level = "info"

    if settings.sanity():
        logger = LoggerHelper(
            module_name="Provisioning server",
            args=settings,
            level=settings.debug_level,
        ).setup()

        # process management
        daemon = Daemon(logger=logger)

        response_queue = daemon._manager.Queue()

        # create the process queues
        mqtt_process = daemon.build(
            "mqtt",
            ProvisioningObserver,
            dict(
                mqtt_settings=settings,
                logger=logger,
                response_queue=response_queue,
            ),
        )

        srv = ProvisioningServer(
            data_queue=mqtt_process.tx_queue,
            request_queue=mqtt_process.rx_queue,
            response_queue=response_queue,
            settings=settings,
            exit_signal=daemon.exit_signal,
            logger=logger,
        )

        daemon.set_loop(srv.loop)

        daemon.start(True)
    else:
        print("Please check your connection settings.")


if __name__ == "__main__":

    main()
