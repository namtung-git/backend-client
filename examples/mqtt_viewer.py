# Copyright 2019 Wirepas Ltd
#
# See file LICENSE for full license details.

import os
import wirepas_backend_client
import time
import queue
import logging

from wirepas_backend_client.api import MQTTSettings
from wirepas_backend_client.tools import ParserHelper, LoggerHelper
from wirepas_backend_client.tools.utils import deferred_thread


class MQTTViewer(wirepas_backend_client.management.NetworkDiscovery):
    """
    NetworkDiscovery

    Tracks the MQTT topics and generates an object representation of the
    devices present in a given network.

    It builds a map of gateways, sinks and devices.

    """

    def __init__(
        self,
        mqtt_settings,
        data_queue=None,
        event_queue=None,
        response_queue=None,
        network_parameters=None,
        **kwargs
    ):
        if "logger" in kwargs:
            self.logger = kwargs["logger"] or logging.getLogger(__name__)

        if network_parameters is None:
            self.network_parameters = dict(
                gw_id="+", sink_id="+", network_id="+", src_ep="+", dst_ep="+"
            )
        else:
            self.network_parameters = network_parameters

        """ MQTT Observer constructor """
        super(MQTTViewer, self).__init__(
            mqtt_settings=mqtt_settings,
            data_queue=data_queue,
            event_queue=event_queue,
            shared_state=None,
            **kwargs
        )


def loop(
    exit_signal, logger, data_queue, event_queue, response_queue, sleep_for=100
):
    """
    Client loop

    This loop goes through each message queue and gathers the shared
    messages.
    """

    @deferred_thread
    def get_data(exit_signal, q, block=True, timeout=60):

        while not exit_signal.is_set():
            try:
                message = q.get(block=block, timeout=timeout)
            except queue.Empty:
                continue
            try:
                logger.info(message.serialize())
            except AttributeError:
                continue

    @deferred_thread
    def consume_queue(exit_signal, q, block=True, timeout=60):

        while not exit_signal.is_set():
            try:
                q.get(block=block, timeout=timeout)
            except queue.Empty:
                continue

    get_data(exit_signal, data_queue)
    consume_queue(exit_signal, event_queue)
    consume_queue(exit_signal, response_queue)

    while not exit_signal.is_set():
        time.sleep(sleep_for)


def main(settings, logger):
    """ Main loop """

    # process management
    daemon = wirepas_backend_client.management.Daemon(logger=logger)

    data_queue = daemon._manager.Queue()
    event_queue = daemon._manager.Queue()
    response_queue = daemon._manager.Queue()

    # create the process queues
    daemon.build(
        "discovery",
        MQTTViewer,
        dict(
            data_queue=data_queue,
            event_queue=event_queue,
            response_queue=response_queue,
            mqtt_settings=settings,
        ),
    )

    daemon.set_loop(
        loop,
        dict(
            exit_signal=daemon.exit_signal,
            logger=logger,
            data_queue=data_queue,
            event_queue=event_queue,
            response_queue=response_queue,
        ),
    )
    daemon.start()


if __name__ == "__main__":

    try:
        debug_level = os.environ["WM_DEBUG_LEVEL"]
    except KeyError:
        debug_level = "info"

    parser = ParserHelper(description="Default arguments")

    parser.add_file_settings()
    parser.add_mqtt()
    parser.add_test()
    parser.add_database()
    parser.add_fluentd()

    settings = parser.settings(settings_class=MQTTSettings)

    if settings.sanity():
        logger = LoggerHelper(
            module_name="MQTT viewer", args=settings, level=debug_level
        ).setup()

        # sets up the message_decoding which is picked up by the
        # message decoders
        LoggerHelper(
            module_name="message_decoding", args=settings, level=debug_level
        ).setup()

        main(settings, logger)
    else:
        print("Please check your connection settings")
