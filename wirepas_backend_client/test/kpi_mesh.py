"""
    TEST KPI
    ========

    Allows executing mesh kpi tests

    .. Copyright:
        Copyright 2019 Wirepas Ltd under Apache License, Version 2.0.
        See file LICENSE for full license details.
"""

import os

from wirepas_messaging.gateway.api import GatewayState
from wirepas_backend_client.api import topic_message, decode_topic_message
from wirepas_backend_client.tools import ParserHelper, LoggerHelper
from wirepas_backend_client.api import MySQLSettings, MySQLObserver
from wirepas_backend_client.api import MQTTSettings, MQTTObserver, Topics
from wirepas_backend_client.api import HTTPSettings, HTTPObserver
from wirepas_backend_client.management import Daemon


__test_name__ = "test_kpi"


class MultiMessageMqttObserver(MQTTObserver):
    """ MultiMessageMqttObserver """

    # pylint: disable=locally-disabled, too-many-instance-attributes

    def __init__(self, **kwargs):
        self.logger = kwargs["logger"]
        self.gw_status_queue = kwargs.pop("gw_status_queue", None)
        self.storage_queue = kwargs.pop("storage_queue", None)
        super(MultiMessageMqttObserver, self).__init__(**kwargs)

        self.network_id = kwargs["mqtt_settings"].network_id
        self.sink_id = kwargs["mqtt_settings"].sink_id
        self.gateway_id = kwargs["mqtt_settings"].gateway_id
        self.source_endpoint = kwargs["mqtt_settings"].source_endpoint
        self.destination_endpoint = kwargs[
            "mqtt_settings"
        ].destination_endpoint

        self.logger.debug(
            "subscription filters: %s/%s/%s/%s/%s",
            self.gateway_id,
            self.sink_id,
            self.network_id,
            self.source_endpoint,
            self.destination_endpoint,
        )

        self.publish_cb = self.send_data
        self.message_subscribe_handlers = {
            "gw-event/received_data/{gw_id}/{sink_id}/{network_id}/#".format(
                gw_id=self.gateway_id,
                sink_id=self.sink_id,
                network_id=self.network_id,
            ): self.generate_data_received_cb(),
            # There seems to be problem, at least with some versions of
            # mosquito MQTT Broker when subscribing "gw-event/status/+/#".
            # The last stored gw status is not received after subscription
            # is performed. It should, just like with "gw-event/status/#".
            # To workaround this problem gw_id filter is not used with
            # gw-event/status. Filter in subscription of get_configs
            # handles cases where gw is online, but in offline case
            # receiver of gw_status_queue must be capable to handle
            # unfiltered gw_ids.
            "gw-event/status/#": self.generate_gw_status_cb(),
            "gw-response/get_configs/{gw_id}/#".format(
                gw_id=self.gateway_id
            ): self.generate_got_gw_configs_cb(),
        }
        self.mqtt_topics = Topics()

    def run(self):
        # Disable KeyboardInterrupts in mqttl observer process
        try:
            super(MultiMessageMqttObserver, self).run()
        except KeyboardInterrupt:
            pass

    def generate_data_received_cb(self) -> callable:
        """ Returns a callback to process the incoming data """

        @decode_topic_message
        def on_data_received(message, topics):
            """ Retrieves a MQTT data message and sends it to the tx_queue """
            if self.start_signal.is_set():
                self.logger.debug("mqtt data received %s", message)
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
            # pylint: disable=locally-disabled, unused-argument
            """ Retrieves a MQTT gw status event and
                sends gw configuration request to MQTT broker
            """
            if self.start_signal.is_set():
                message = self.mqtt_topics.constructor(
                    "event", "status"
                ).from_payload(message)
                self.logger.debug("mqtt gw status received %s", message)
                if message.state == GatewayState.ONLINE:
                    # Gateway is online, ask configuration
                    request = self.mqtt_topics.request_message(
                        "get_configs", **dict(gw_id=message.gw_id)
                    )
                    # MQTTObserver's queue naming might be confusing here.
                    # 'rx_queue' == 'send to MQTT broker'
                    self.rx_queue.put(request)
                else:
                    # Gateway is offline, inform to status_queue that
                    # gateway and gateway's all sinks are not running.
                    gw_status_msg = {"gw_id": message.gw_id, "configs": []}
                    self.logger.debug("gw_status_msg=%s", gw_status_msg)
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
                self.logger.debug("mqtt gw configuration received %s", message)
                self.gw_status_queue.put(message.__dict__)
            else:
                self.logger.debug(
                    "waiting for start signal, received mqtt gw configuration ignored"
                )

        return on_response_cb


class MySqlStorage(MySQLObserver):
    """
    MySqlStorage

    Wrapper around MySQLObserver to allow escaping keyboar interrupts
    """

    def run(self, **kwargs):
        # Disable KeyboardInterrupts in mysql storage process
        try:
            super(MySqlStorage, self).run(**kwargs)
        except KeyboardInterrupt:
            pass


class HttpControl(HTTPObserver):
    """
    HttpControl

    Wrapper around HTTPObserver to allow escaping keyboar interrupts
    """

    def run(self):
        # Disable KeyboardInterrupts in http control process
        try:
            super(HttpControl, self).run()
        except KeyboardInterrupt:
            pass


if __name__ == "__main__":

    PARSER = ParserHelper("KPi test arguments")
    PARSER.add_file_settings()
    PARSER.add_mqtt()
    PARSER.add_test()
    PARSER.add_database()
    PARSER.add_fluentd()
    PARSER.add_http()

    SETTINGS = PARSER.settings()

    DEBUG_LEVEL = "debug"
    try:
        DEBUG_LEVEL = os.environ["WM_DEBUG_LEVEL"]
    except KeyError:
        pass

    LOG = LoggerHelper(
        module_name=__test_name__, args=SETTINGS, level=DEBUG_LEVEL
    )
    LOG.add_stderr("warning")
    LOGGER = LOG.setup()

    MQTT_SETTINGS = MQTTSettings(SETTINGS)
    HTTP_SETTINGS = HTTPSettings(SETTINGS)

    if MQTT_SETTINGS.sanity() and HTTP_SETTINGS.sanity():

        DAEMON = Daemon(logger=LOGGER)

        GW_STATUS_FROM_MQTT_BROKER = DAEMON.create_queue()

        MQTT_NAME = "mqtt"
        STORAGE_NAME = "mysql"
        CONTROL_NAME = "http"

        DAEMON.build(
            STORAGE_NAME,
            MySqlStorage,
            dict(mysql_settings=MySQLSettings(SETTINGS)),
        )
        DAEMON.set_run(
            STORAGE_NAME,
            task_kwargs={"parallel": True, "n_workers": 8},
            task_as_daemon=False,
        )

        DAEMON.build(
            MQTT_NAME,
            MultiMessageMqttObserver,
            dict(
                gw_status_queue=GW_STATUS_FROM_MQTT_BROKER,
                mqtt_settings=MQTTSettings(SETTINGS),
            ),
            storage=True,
            storage_name=STORAGE_NAME,
        )

        DAEMON.build(
            CONTROL_NAME,
            HttpControl,
            dict(
                gw_status_queue=GW_STATUS_FROM_MQTT_BROKER,
                http_settings=HTTPSettings(SETTINGS),
            ),
            send_to=MQTT_NAME,
        )

        DAEMON.start(set_start_signal=True)
    else:
        LOGGER.error("Please check your MQTT and MySQ settings:")
        LOGGER.error("\n%s", MQTT_SETTINGS)
        LOGGER.error("\n%s", HTTP_SETTINGS)

    LOGGER.debug("test_kpi exit!")
