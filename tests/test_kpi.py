# Wirepas Oy
#
# See file LICENSE for full license details.

import os
import sys
import enum
import queue
import pprint
import struct
import logging
import argparse
import binascii
import datetime
import multiprocessing
import time
import MySQLdb

from functools import wraps

import wirepas_backend_client
from wirepas_backend_client.messages.interface import MessageManager
from wirepas_backend_client.api import topic_message
from wirepas_messaging.gateway.api import GatewayState
from wirepas_backend_client.tools import Settings, ParserHelper, LoggerHelper
from wirepas_backend_client.api import MySQLSettings
from wirepas_backend_client.api import MQTTSettings
from wirepas_backend_client.api import HTTPSettings

__test_name__ = "test_kpi"


# Own version of retrieve_message inorder to have network_id in message.
def retrieve_message_kpi(f):
    """ Decorator to decode incoming proto message """

    @wraps(f)
    def wrapper_retrieve_message_kpi(client, userdata, message, **kwargs):
        """ Receives an MQTT message and retrieves its protobuffer """
        topic = message.topic.split("/")
        source_endpoint = topic[-2]
        destination_endpoint = topic[-1]
        data = MessageManager.map(
            source_endpoint, destination_endpoint
        ).from_bus(message.payload)
        data.network_id = topic[-3]
        f(data)

    return wrapper_retrieve_message_kpi


class MultiMessageMqttObserver(wirepas_backend_client.api.MQTTObserver):
    """ MultiMessageMqttObserver """

    def __init__(self, **kwargs):
        self.gw_status_queue = kwargs.pop("gw_status_queue", None)
        self.storage_queue = kwargs.pop("storage_queue", None)
        super(MultiMessageMqttObserver, self).__init__(**kwargs)
        self.logger = kwargs["logger"]
        self.message_publish_handlers = {"useless-key": self.send_data}
        self.message_subscribe_handlers = {
            "gw-event/received_data/#": self.generate_data_received_cb(),
            "gw-event/status/+": self.generate_gw_status_cb(),
            "gw-response/get_configs/+": self.generate_got_gw_configs_cb(),
        }
        self.mqtt_topics = wirepas_backend_client.api.Topics()

    def run(self):
        # Disable KeyboardInterrupts in mqttl observer process
        try:
            super(MultiMessageMqttObserver, self).run()
        except KeyboardInterrupt:
            pass

    def generate_data_received_cb(self) -> callable:
        """ Returns a callback to process the incoming data """

        @retrieve_message_kpi
        def on_data_received(message):
            """ Retrieves a MQTT data message and sends it to the tx_queue """
            if self.start_signal.is_set():
                self.logger.debug("mqtt data received {}".format(message))
                # In KPI testing all received data packages are directed to
                # storage
                self.storage_queue.put(message)
            else:
                self.logger.debug(
                    "waiting for start signal, received mqtt data ignored"
                )

        return on_data_received

    def generate_gw_status_cb(self) -> callable:
        """ Returns a callback to process gw status events """

        @topic_message
        def on_status_received(message, topic: list):
            """ Retrieves a MQTT gw status event and
                sends gw configuration request to MQTT broker
            """
            if self.start_signal.is_set():
                message = self.mqtt_topics.constructor(
                    "event", "status"
                ).from_payload(message)
                self.logger.debug("mqtt gw status received {}".format(message))
                if message.state == GatewayState.ONLINE:
                    # Gateway is online, ask configuration
                    request = self.mqtt_topics.request_message(
                        "get_configs", dict(gw_id=message.gw_id)
                    )
                    # MQTTObserver's queue naming might be confusing here.
                    # 'rx_queue' == 'send to MQTT broker'
                    self.rx_queue.put(request)
                else:
                    # Gateway is offline, inform to status_queue that
                    # gateway and gateway's all sinks are not running.
                    gw_status_msg = {"gw_id": message.gw_id, "configs": []}
                    self.logger.debug("gw_status_msg={}".format(gw_status_msg))
                    self.gw_status_queue.put(gw_status_msg)
            else:
                self.logger.debug(
                    "waiting for start signal, received mqtt gw status ignored"
                )

        return on_status_received

    def generate_got_gw_configs_cb(self) -> callable:
        """ Returns a callback to process gw responses to get_configs message """

        @topic_message
        def on_response_cb(message, topic: list):
            """ Retrieves a MQTT message and sends it to the tx_queue """
            if self.start_signal.is_set():
                message = self.mqtt_topics.constructor(
                    "response", "get_configs"
                ).from_payload(message)
                self.logger.debug(
                    "mqtt gw configuration received {}".format(message)
                )
                self.gw_status_queue.put(message.__dict__)
            else:
                self.logger.debug(
                    "waiting for start signal, received mqtt gw configuration ignored"
                )

        return on_response_cb

    def send_data(self, mqtt_publish, topic):
        """ Callback provided by the interface's cb generator """
        try:
            message = self.rx_queue.get(block=True, timeout=self.timeout)
            self.logger.debug("publishing message {}".format(message))
            mqtt_publish(message["data"].payload, message["topic"])
        except queue.Empty:
            pass


class MySqlStorage(wirepas_backend_client.api.MySQLObserver):
    def run(self, **kwargs):
        # Disable KeyboardInterrupts in mysql storage process
        try:
            super(MySqlStorage, self).run(**kwargs)
        except KeyboardInterrupt:
            pass


class HttpControl(wirepas_backend_client.api.HTTPObserver):
    def run(self):
        # Disable KeyboardInterrupts in http control process
        try:
            super(HttpControl, self).run()
        except KeyboardInterrupt:
            pass


if __name__ == "__main__":

    parser = ParserHelper.default_args("KPi test arguments")

    try:
        debug_level = os.environ["DEBUG_LEVEL"]
    except KeyError:
        debug_level = "debug"

    log = LoggerHelper(
        module_name=__test_name__, args=parser.arguments, level=debug_level
    )
    logger = log.setup()

    daemon = wirepas_backend_client.management.Daemon(logger=logger)

    gw_status_from_mqtt_broker = daemon._manager.Queue()

    mqtt_name = "mqtt"
    storage_name = "mysql"
    control_name = "http"

    daemon.build(
        storage_name,
        MySqlStorage,
        dict(
            mysql_settings=parser.settings(
                settings_class=MySQLSettings, skip_undefined=False
            )
        ),
    )
    daemon.set_run(
        storage_name, task_kwargs={"parallel": True}, task_as_daemon=False
    )

    daemon.build(
        mqtt_name,
        MultiMessageMqttObserver,
        dict(
            gw_status_queue=gw_status_from_mqtt_broker,
            mqtt_settings=parser.settings(
                settings_class=MQTTSettings, skip_undefined=False
            ),
        ),
        storage=True,
        storage_name=storage_name,
    )

    daemon.build(
        control_name,
        HttpControl,
        dict(
            gw_status_queue=gw_status_from_mqtt_broker,
            http_settings=parser.settings(
                settings_class=HTTPSettings, skip_undefined=False
            ),
        ),
        send_to=mqtt_name,
    )

    daemon.start(set_start_signal=True)

    logger.debug("test_kpi exit!")
