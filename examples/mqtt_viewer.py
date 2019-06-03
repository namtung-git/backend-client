# Wirepas Oy
#
# See file LICENSE for full license details.

import os
import wirepas_messaging
import wirepas_backend_client
import multiprocessing
import time
import queue
import logging

from wirepas_backend_client.api import MQTT
from wirepas_backend_client.api import MQTTSettings
from wirepas_backend_client.api import Topics
from wirepas_backend_client.api import topic_message, decode_topic_message
from wirepas_backend_client.tools import Settings, ParserHelper, LoggerHelper

from wirepas_backend_client.management import NetworkDiscovery
from wirepas_backend_client.management import MeshManagement
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
        """ MQTT Observer constructor """
        super(MQTTViewer, self).__init__(
            mqtt_settings=mqtt_settings,
            data_queue=data_queue,
            event_queue=event_queue,
            shared_state=None,
            **kwargs
        )
        self.data_queue = self.data_queue
        self.event_queue = self.event_queue
        self.response_queue = self.response_queue

        if "logger" in kwargs:
            self.logger = kwargs["logger"] or logging.getLogger(__name__)

        if network_parameters is None:
            self.network_parameters = dict(
                gw_id="+", sink_id="+", network_id="+", src_ep="+", dst_ep="+"
            )
        else:
            self.network_parameters = network_parameters

        self.mqtt_settings = mqtt_settings
        self.mqtt_topics = Topics()

        self.message_subscribe_handlers = self.build_subscription()

        self.message_publish_handlers = {"from_message": self.send_data}

        self.mqtt = MQTT(
            username=mqtt_settings.username,
            password=mqtt_settings.password,
            hostname=mqtt_settings.hostname,
            port=mqtt_settings.port,
            ca_certs=mqtt_settings.ca_certs,
            userdata=mqtt_settings.userdata,
            transport=mqtt_settings.transport,
            clean_session=mqtt_settings.clean_session,
            reconnect_min_delay=mqtt_settings.reconnect_min_delay,
            reconnect_max_delay=mqtt_settings.reconnect_max_delay,
            allow_untrusted=mqtt_settings.mqtt_allow_untrusted,
            force_unsecure=mqtt_settings.mqtt_force_unsecure,
            heartbeat=mqtt_settings.heartbeat,
            keep_alive=mqtt_settings.keep_alive,
            exit_signal=kwargs["exit_signal"],
            message_subscribe_handlers=self.message_subscribe_handlers,
            message_publish_handlers=self.message_publish_handlers,
            logger=self.logger,
        )

        self.device_manager = MeshManagement()

    def notify(self, message, path="response"):
        """
        Routes the received message to the correct queue based on the path
        parameter.
        """
        if message:
            if "response" in path:
                self.response_queue.put(message)

            elif "data" in path and self.data_queue:
                self.data_queue.put(message)

            elif "event" in path and self.event_queue:
                self.event_queue.put(message)

    def build_subscription(self):
        """
        Build subscription sets up the MQTT object with the callbacks to
        handle each topic of intertest
        """

        # track gateway events
        event_status = self.mqtt_topics.event(
            "status", self.network_parameters
        )
        event_received_data = self.mqtt_topics.event(
            "received_data", self.network_parameters
        )

        response_get_configs = self.mqtt_topics.response(
            "get_configs", self.network_parameters
        )
        response_set_config = self.mqtt_topics.response(
            "set_config", self.network_parameters
        )
        response_send_data = self.mqtt_topics.response(
            "send_data", self.network_parameters
        )
        response_otap_status = self.mqtt_topics.response(
            "otap_status", self.network_parameters
        )
        response_otap_load_scratchpad = self.mqtt_topics.response(
            "otap_load_scratchpad", self.network_parameters
        )
        response_otap_process_scratchpad = self.mqtt_topics.response(
            "otap_process_scratchpad", self.network_parameters
        )

        # the MQTT object will use the cb (value) to handle each topic (key)
        message_subscribe_handlers = {
            event_status: self.generate_gateway_satus_event_cb(),
            event_received_data: self.generate_gateway_data_event_cb(),
            response_get_configs: self.generate_gateway_response_get_configs_cb(),
            response_set_config: self.generate_gateway_response_set_config_cb(),
            response_send_data: self.generate_gateway_data_response_cb(),
            response_otap_status: self.generate_gateway_otap_status_response_cb(),
            response_otap_load_scratchpad: self.generate_gateway_load_scratchpad_response_cb(),
            response_otap_process_scratchpad: self.generate_gateway_process_scratchpad_response_cb(),
        }

        return message_subscribe_handlers

    # Subscribing methods
    def generate_gateway_satus_event_cb(self) -> callable:
        @topic_message
        def on_gateway_satus_event_cb(message, topic: list):
            """ Decodes an incoming gateway status event """
            try:
                self.logger.debug("status event {}".format(message))
                message = wirepas_messaging.gateway.api.StatusEvent.from_payload(
                    message
                )

                # updates gateway details
                gateway = self.device_manager.add(message.gw_id)
                gateway.state = message.state

                self.notify(message=message, path="event")
            except RuntimeError:
                self.logger.exception("Failed decoding from {}".format(topic))

        return on_gateway_satus_event_cb

    def generate_gateway_data_event_cb(self) -> callable:
        @decode_topic_message
        def on_gateway_data_event_cb(message, topic: list):
            """ Decodes an incoming data event callback """
            self.logger.info(message.serialize())
            self.device_manager.add_from_mqtt_topic(
                topic, message.source_address
            )
            self.notify(message=message, path="event")

        return on_gateway_data_event_cb

    def generate_gateway_response_get_configs_cb(self) -> callable:
        @topic_message
        def on_response_cb(message, topic: list):
            """ Decodes and incoming configuration response """

            self.logger.debug("configs response: {}".format(message))
            message = self.mqtt_topics.constructor(
                "response", "get_configs"
            ).from_payload(message)

            self.device_manager.add_from_mqtt_topic(topic)
            self.notify(message, path="response")

        return on_response_cb

    def generate_gateway_otap_status_response_cb(self) -> callable:
        @topic_message
        def on_response_cb(message, topic: list):
            """ Decodes an otap status response """
            self.logger.debug("otap status response: {}".format(message))
            message = self.mqtt_topics.constructor(
                "response", "otap_status"
            ).from_payload(message)
            self.notify(message, path="response")

        return on_response_cb

    def generate_gateway_response_set_config_cb(self) -> callable:
        @topic_message
        def on_response_cb(message, topic: list):
            """ Decodes a set config response """
            self.logger.debug("set config response: {}".format(message))
            message = self.mqtt_topics.constructor(
                "response", "set_config"
            ).from_payload(message)
            self.notify(message, path="response")

        return on_response_cb

    def generate_gateway_data_response_cb(self) -> callable:
        @topic_message
        def on_response_cb(message, topic: list):
            """ Decodes a data response """
            self.logger.debug("set data response: {}".format(message))
            self.notify(message, path="response")

        return on_response_cb

    def generate_gateway_load_scratchpad_response_cb(self) -> callable:
        @topic_message
        def on_response_cb(message, topic: list):
            """ Decodes a set load scratchpad response """
            self.logger.debug("load scratchpad response: {}".format(message))
            self.notify(message, path="response")

        return on_response_cb

    def generate_gateway_process_scratchpad_response_cb(self) -> callable:
        @topic_message
        def on_response_cb(message, topic: list):
            """ Decodes a process scratchpad response """
            self.logger.debug(
                "process scratchpad response: {}".format(message)
            )
            self.notify(message, path="response")

        return on_response_cb


def loop(exit_signal, data_queue, event_queue, response_queue, sleep_for=100):
    """
    Client loop

    This loop goes through each message queue and gathers the shared
    messages.
    """

    @deferred_thread
    def get_item(q, block=True, timeout=1):
        try:
            message = q.get(block=block, timeout=timeout)
            print(message)
        except queue.Empty:
            pass

    get_item(data_queue)
    get_item(event_queue)
    get_item(response_queue)

    while not exit_signal.is_set():
        time.sleep(sleep_for)


def main(parser, logger):
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
            mqtt_settings=parser.settings(MQTTSettings),
        ),
    )

    daemon.set_loop(
        loop,
        dict(
            exit_signal=daemon.exit_signal,
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

    settings = parser.settings(skip_undefined=False)

    log = LoggerHelper(
        module_name="MQTT viewer", args=settings, level=debug_level
    )
    logger = log.setup()

    LoggerHelper(
        module_name="message_decoding", args=settings, level=debug_level
    ).setup()

    main(parser, logger)
