"""
    MQTT Handlers
    ==============

    Contains class to handle MQTT requests

    .. Copyright:
        Copyright 2019 Wirepas Ltd under Apache License, Version 2.0.
        See file LICENSE for full license details.
"""

import logging
import multiprocessing
import queue

from .connectors import MQTT
from .decorators import retrieve_message
from ..stream import StreamObserver
from ...tools import Settings


class MQTTObserver(StreamObserver):
    """MQTTObserver monitors the MQTT topics for test data"""

    def __init__(
        self,
        mqtt_settings: Settings,
        start_signal: multiprocessing.Event,
        exit_signal: multiprocessing.Event,
        tx_queue: multiprocessing.Queue,
        rx_queue: multiprocessing.Queue,
        allowed_endpoints: set = None,
        message_subscribe_handlers: dict = None,
        message_publish_handlers: dict = None,
        logger=None,
    ) -> "MQTTObserver":
        """ MQTT Observer constructor """
        super(MQTTObserver, self).__init__(
            start_signal=start_signal,
            exit_signal=exit_signal,
            tx_queue=tx_queue,
            rx_queue=rx_queue,
        )

        self.logger = logger or logging.getLogger(__name__)

        if message_subscribe_handlers is None:
            self.message_subscribe_handlers = {"#": self.simple_mqtt_print}
        else:
            self.message_subscribe_handlers = message_subscribe_handlers

        if message_publish_handlers is None:
            self.message_publish_handlers = {
                "publish/example": self.generate_data_send_cb()
            }
        else:
            self.message_publish_handlers = message_publish_handlers

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
            allow_untrusted=mqtt_settings.allow_untrusted,
            force_unsecure=mqtt_settings.force_unsecure,
            heartbeat=mqtt_settings.heartbeat,
            keep_alive=mqtt_settings.keep_alive,
            exit_signal=self.exit_signal,
            message_subscribe_handlers=message_subscribe_handlers,
            message_publish_handlers=self.message_publish_handlers,
            logger=self.logger,
        )

        self.timeout = mqtt_settings.heartbeat

        if allowed_endpoints is None:
            self.allowed_endpoints = set()
        else:
            self.allowed_endpoints = allowed_endpoints

    @staticmethod
    @retrieve_message
    def simple_mqtt_print(message):
        print("MQTT >> {}".format(message))

    def generate_data_received_cb(self) -> callable:
        """ Returns a callback to process the incoming data """

        @retrieve_message
        def on_data_received(message):
            """ Retrieves a MQTT message and sends it to the tx_queue """

            if len(self.allowed_endpoints) == 0 or (
                message.source_endpoint in self.allowed_endpoints
                and message.destination_endpoint in self.allowed_endpoints
            ):

                if self.start_signal.is_set():
                    self.logger.debug("sending message {}".format(message))
                    self.tx_queue.put(message)
                else:
                    self.logger.debug("waiting for manager readiness")

        return on_data_received

    def send_data(self, mqtt_publish, topic):
        """ Callback provided by the interface's cb generator """
        try:
            message = self.rx_queue.get(block=True, timeout=self.timeout)
            self.logger.debug("publishing message {}".format(message))
            mqtt_publish(message.payload, topic)

        except queue.Empty:
            pass

        except AttributeError:
            self.logger.error("Unable to fetch from uninitialized queue")

    def run(
        self, message_subscribe_handlers=None, message_publish_handlers=None
    ):
        """
        Executes MQTT loop

        Attributes:
            message_subscribe_handlers (dict): overrides message handlers
            message_publish_handlers (dict): overrides publish handlers

        """

        if message_subscribe_handlers is not None:
            self.message_subscribe_handlers = message_subscribe_handlers

        if message_publish_handlers is not None:
            self.message_publish_handlers = message_publish_handlers

        self.mqtt.subscribe_messages(self.message_subscribe_handlers)
        self.mqtt.message_publish_handlers = self.message_publish_handlers
        self.mqtt.serve()
