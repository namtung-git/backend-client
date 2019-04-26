"""
    MQTT API
    ============

    Contains class to handle MQTT requests

    .. Copyright:
        Wirepas Oy licensed under Apache License, Version 2.0.
        See file LICENSE for full license details.
"""
import os
import ssl
import time
import uuid
import logging
import paho
import json
import paho.mqtt.client as mqtt
import multiprocessing
import google.protobuf.json_format as json_format
from functools import wraps

from .stream import StreamObserver
from ..tools import Settings
from ..tools import ExitSignal
from .. import messages
from ..messages.interface import MessageManager

import wirepas_messaging
import queue


class Topics(object):
    """
    MQTT Topics

    An helper class to manage the API MQTT topics.

    All topics are inside a dictionary,

    requests
    responses
    events

    The first element of the dictionary is the version number.

    """

    def __init__(self, api_version: str = "1"):
        super(Topics, self).__init__()
        if not api_version == "1":
            raise ValueError("Unsupported API version")

        self.api_version = str(api_version)
        self._topics = dict()
        self._build_topics(str(api_version))

        self._default_attributes = dict(
            gw_id="+", sink_id="+", network_id="+", src_ep="+", dst_ep="+"
        )

    def list(self):
        return dict(
            requests=self._topics[self.api_version]["request"].values(),
            events=self._topics[self.api_version]["event"].values(),
            responses=self._topics[self.api_version]["request"].values(),
        )

    def _build_topics(self, api_version: str = "1"):

        self._topics = {
            api_version: dict(request=dict(), response=dict(), event=dict())
        }

        # Requests
        self._topics[api_version]["request"]["get_configs"] = dict(
            path="gw-request/get_configs/{gw_id}",
            constructor=wirepas_messaging.gateway.api.GetConfigsRequest,
        )

        self._topics[api_version]["request"]["set_config"] = dict(
            path="gw-request/set_config/{gw_id}/{sink_id}",
            constructor=wirepas_messaging.gateway.api.SetConfigRequest,
        )

        self._topics[api_version]["request"]["send_data"] = dict(
            path="gw-request/send_data/{gw_id}/{sink_id}",
            constructor=wirepas_messaging.gateway.api.SendDataRequest,
        )

        self._topics[api_version]["request"]["otap_status"] = dict(
            path="gw-request/otap_status/{gw_id}/{sink_id}",
            constructor=wirepas_messaging.gateway.api.GetScratchpadStatusRequest,
        )

        self._topics[api_version]["request"]["otap_load_scratchpad"] = dict(
            path="gw-request/otap_load_scratchpad/{gw_id}/{sink_id}",
            constructor=wirepas_messaging.gateway.api.UploadScratchpadRequest,
        )

        self._topics[api_version]["request"]["otap_process_scratchpad"] = dict(
            path="gw-request/otap_process_scratchpad/{gw_id}/{sink_id}",
            constructor=wirepas_messaging.gateway.api.ProcessScratchpadRequest,
        )

        # Responses
        self._topics[api_version]["response"]["get_configs"] = dict(
            path="gw-response/get_configs/{gw_id}",
            constructor=wirepas_messaging.gateway.api.GetConfigsResponse,
        )

        self._topics[api_version]["response"]["set_config"] = dict(
            path="gw-response/set_config/{gw_id}/{sink_id}",
            constructor=wirepas_messaging.gateway.api.SetConfigResponse,
        )

        self._topics[api_version]["response"]["send_data"] = dict(
            path="gw-response/send_data/{gw_id}/{sink_id}",
            constructor=wirepas_messaging.gateway.api.SendDataResponse,
        )

        self._topics[api_version]["response"]["otap_status"] = dict(
            path="gw-response/otap_status/{gw_id}/{sink_id}",
            constructor=wirepas_messaging.gateway.api.GetScratchpadStatusResponse,
        )

        self._topics[api_version]["response"]["otap_load_scratchpad"] = dict(
            path="gw-response/otap_load_scratchpad/{gw_id}/{sink_id}",
            constructor=wirepas_messaging.gateway.api.UploadScratchpadResponse,
        )

        self._topics[api_version]["response"][
            "otap_process_scratchpad"
        ] = dict(
            path="gw-response/otap_process_scratchpad/{gw_id}/{sink_id}",
            constructor=wirepas_messaging.gateway.api.ProcessScratchpadResponse,
        )

        # Asynchronous events
        self._topics[api_version]["event"]["clear"] = dict(
            path="gw-event/status/{gw_id}",
            constructor=wirepas_messaging.gateway.GenericMessage,
        )

        self._topics[api_version]["event"]["status"] = dict(
            path="gw-event/status/{gw_id}",
            constructor=wirepas_messaging.gateway.api.StatusEvent,
        )

        self._topics[api_version]["event"]["received_data"] = dict(
            path="gw-event/received_data/{gw_id}/{sink_id}/{network_id}/{src_ep}/{dst_ep}",
            constructor=wirepas_messaging.gateway.api.ReceivedDataEvent,
        )

        # Generic fallback
        self._topics[api_version]["event"]["generic"] = dict(
            path="", constructor=wirepas_messaging.gateway.api.Event
        )
        self._topics[api_version]["request"]["generic"] = dict(
            path="", constructor=wirepas_messaging.gateway.api.Request
        )
        self._topics[api_version]["response"]["generic"] = dict(
            path="", constructor=wirepas_messaging.gateway.api.Response
        )

    def request(self, name, kwargs):
        return self.path(topic_type="request", name=name, kwargs=kwargs)

    def response(self, name, kwargs):
        return self.path(topic_type="response", name=name, kwargs=kwargs)

    def event(self, name, kwargs):
        return self.path(topic_type="event", name=name, kwargs=kwargs)

    def request_message(self, name, kwargs):
        message = None
        if kwargs:
            topic_info = self._topics[self.api_version]["request"][name]
            if topic_info["constructor"]:
                path = topic_info["path"].format(**kwargs)
                message = dict(
                    topic=path, data=topic_info["constructor"](**kwargs)
                )
        return message

    def response_message(self, name, kwargs):
        message = None
        if kwargs:
            topic_info = self._topics[self.api_version]["response"][name]
            if topic_info["constructor"]:
                path = topic_info["path"].format(**kwargs)
                message = dict(
                    topic=path, data=topic_info["constructor"](**kwargs)
                )
        return message

    def event_message(self, name, kwargs):
        message = None
        if kwargs:
            topic_info = self._topics[self.api_version]["event"][name]
            if topic_info["constructor"]:
                path = topic_info["path"].format(**kwargs)
                try:
                    message = dict(
                        topic=path, data=topic_info["constructor"](**kwargs)
                    )
                except:
                    message = dict(
                        topic=path, data=topic_info["constructor"]()
                    )
        return message

    def path(self, topic_type: str, name: str, kwargs: dict = None):
        """
        Builds a topic based on its type, name and kwargs

        Args:
            topic_type: request/response/envent
            name: which request/response/event to build
            kwargs: expects a keyword list with:
                        gateway_id
                        sink_id
                        network_id
                        source_endpoint
                        destination_endpoint

        If no kwargs are provided, the gw_id and sink_id are set to '+'.
        """
        topic_type = topic_type.lower()
        name = name.lower()

        if topic_type not in self._topics[self.api_version]:
            return None

        topic = self._topics[self.api_version][topic_type][name]
        if kwargs:
            topic = topic["path"].format(**kwargs)
        else:
            topic = topic["path"].format(**self._default_attributes)

        return topic

    def constructor(self, topic_type: str, name: str):

        topic_type = topic_type.lower()
        name = name.lower()

        if topic_type not in self._topics[self.api_version]:
            return None

        constructor = self._topics[self.api_version][topic_type][name][
            "constructor"
        ]

        if constructor is None:
            constructor = self._topics[self.api_version][topic_type][
                "generic"
            ]["constructor"]

        return constructor


class MQTTSettings(Settings):
    """MQTTSettings"""

    def __init__(self, settings: Settings) -> "MQTTSettings":

        self.userdata = None
        self.transport = "tcp"
        self.reconnect_min_delay = 10
        self.reconnect_max_delay = 120

        self.heartbeat = 2
        self.keep_alive = 60

        super(MQTTSettings, self).__init__(settings)

        self.username = self.mqtt_username
        self.password = self.mqtt_password
        self.hostname = self.mqtt_hostname
        self.port = self.mqtt_port
        self.clean_session = not self.mqtt_persist_session

        try:
            self.ca_certs = self.mqtt_ca_certs
        except AttributeError:
            self.mqtt_ca_certs = None
            self.ca_certs = None

        self.allow_untrusted = self.mqtt_allow_untrusted
        self.force_unsecure = self.mqtt_force_unsecure

        try:
            self.mqtt_ciphers = self.mqtt_ciphers
        except AttributeError:
            self.mqtt_ciphers = None
            self.ciphers = None

        self.topic = self.mqtt_topic

    def set_defaults(self) -> None:
        """ Sets common settings for the MQTT client connection """

    def to_dict(self):
        return self.__dict__

    def __str__(self):
        return json.dumps(self.__dict__)


def decode_topic_message(f):
    """ Decorator to decode incoming proto message """

    @wraps(f)
    def wrapper_retrieve_message(client, userdata, message, **kwargs):
        """ Receives an MQTT message and retrieves its protobuffer """
        topic = message.topic.split("/")
        source_endpoint = topic[-2]
        destination_endpoint = topic[-1]
        message = MessageManager.map(
            source_endpoint, destination_endpoint
        ).from_bus(message.payload)
        f(message, topic)

    return wrapper_retrieve_message


def topic_message(f):
    """ Decorator to decode incoming proto message """

    @wraps(f)
    def wrapper_retrieve_message(client, userdata, message, **kwargs):
        """ Receives an MQTT message and retrieves its protobuffer """
        topic = message.topic.split("/")
        f(message.payload, topic)

    return wrapper_retrieve_message


def retrieve_message(f):
    """ Decorator to decode incoming proto message """

    @wraps(f)
    def wrapper_retrieve_message(client, userdata, message, **kwargs):
        """ Receives an MQTT message and retrieves its protobuffer """
        topic = message.topic.split("/")
        source_endpoint = topic[-2]
        destination_endpoint = topic[-1]
        data = MessageManager.map(
            source_endpoint, destination_endpoint
        ).from_bus(message.payload)
        f(data)

    return wrapper_retrieve_message


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


class MQTT(object):
    """
    Generic MQTT handler for backend client sessions
    """

    def __init__(
        self,
        username: str,
        password: str,
        hostname: str,
        port: int,
        ca_certs: str,
        cert_required=None,
        tls_version=None,
        certfile=None,
        keyfile=None,
        cert_reqs=None,
        ciphers=None,
        userdata: object = None,
        transport: str = "tcp",
        clean_session: bool = True,
        reconnect_min_delay: int = 10,
        reconnect_max_delay: int = 120,
        allow_untrusted: bool = False,
        force_unsecure: bool = False,
        exit_signal: object = None,
        heartbeat: int = 100,
        keep_alive: int = 120,
        message_subscribe_handlers: dict = None,
        message_publish_handlers: dict = None,
        mqtt_protocol=None,
        logger: logging.Logger = None,
    ):

        super(MQTT, self).__init__()

        self.logger = logger or logging.getLogger(__name__)

        self.running = False
        self.heartbeat = heartbeat
        self.exit_signal = ExitSignal(exit_signal)
        self.id = "wm-gw-cli:{0}".format(uuid.uuid1(clock_seq=0).urn)

        self.username = username
        self.password = password

        if cert_required is None:
            self.cert_reqs = ssl.CERT_REQUIRED

        if tls_version is None:
            self.tls_version = ssl.PROTOCOL_TLSv1_2

        if mqtt_protocol is None:
            self.mqtt_protocol = mqtt.MQTTv311

        self.ca_certs = ca_certs
        self.certfile = certfile
        self.keyfile = keyfile
        self.ciphers = ciphers

        self.hostname = hostname
        self.port = port

        self.clean_session = clean_session
        self.userdata = userdata
        self.transport = transport

        self.client = mqtt.Client(
            client_id=self.id,
            clean_session=self.clean_session,
            userdata=self.userdata,
            protocol=self.mqtt_protocol,
            transport=self.transport,
        )
        self.client.username_pw_set(self.username, self.password)
        self.client.reconnect_delay_set(
            min_delay=reconnect_min_delay, max_delay=reconnect_max_delay
        )
        self.client.enable_logger(self.logger)

        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.client.on_publish = self.on_publish
        self.client.on_disconnect = self.on_disconnect
        self.client.on_unsubscribe = self.on_unsubscribe

        self.keep_alive = keep_alive
        self.allow_untrusted = allow_untrusted
        self.force_unsecure = force_unsecure

        if message_publish_handlers is None:
            message_publish_handlers = dict()
        else:
            self.message_publish_handlers = message_publish_handlers

        if message_subscribe_handlers is None:
            message_subscribe_handlers = dict()
        else:
            self.message_subscribe_handlers = message_subscribe_handlers

        self.subscription = set()

    def serve(self: "MQTT"):
        """
        Connects and serves for ever.

        The loop periodically checks if the client is alive by looking at the
        exit_signal event.
        """

        self.running = True
        try:
            self.connect()
        except:
            self.exit_signal.set()
            raise
        self.subscribe_messages(self.message_subscribe_handlers)
        self.client.loop_start()

        while not self.exit_signal.is_set():
            self.logger.debug("mqtt loop running")
            if len(self.message_publish_handlers) == 0:
                time.sleep(self.heartbeat)
            else:
                for topic, cb in self.message_publish_handlers.items():
                    cb(topic=topic, mqtt_publish=self.send)

        if not self.exit_signal.is_set():
            self.exit_signal.set()

        self.close()
        self.client.loop_stop()

        return self.running

    def connect(self: "MQTT"):
        """ Establishes a connection and service loop. """

        self.logger.info(
            "connecting to {user}:{password}"
            "@{host}:{port} - {cert}".format(
                user=self.username,
                password=self.password,
                host=self.hostname,
                port=self.port,
                cert=self.ca_certs,
            )
        )

        if self.force_unsecure is False:

            if self.allow_untrusted:
                self.client.tls_insecure_set(self.allow_untrusted)

            elif self.ca_certs:
                self.client.tls_set(
                    ca_certs=self.ca_certs,
                    certfile=self.certfile,
                    keyfile=self.keyfile,
                    cert_reqs=self.cert_reqs,
                    tls_version=self.tls_version,
                    ciphers=self.ciphers,
                )

        self.client.connect(
            self.hostname, port=self.port, keepalive=self.keep_alive
        )

    def close(self: "MQTT") -> None:
        """ Handles disconnect from the pubsub. """
        if self.running:
            self.running = False
            self.on_close()
            self.client.disconnect()

    def subscribe_messages(self, handlers: dict) -> None:
        """
        Register a set of callbacks with topic handlers

        Handlers is a dictionary with contains as key the topic filter
        and as value the callable who should handle such messages.
        """
        if len(handlers) > 0:
            for topic_filter, cb in handlers.items():
                self.client.message_callback_add(topic_filter, cb)
                self.subscription.add(topic_filter)
                self.logger.info("{} -> {}".format(topic_filter, cb))

            self.message_subscribe_handlers = handlers

    def on_close(self: "MQTT") -> None:
        """ Override for handling before closing events, like last will"""
        pass

    def on_connect(
        self: "MQTT",
        client: "paho.mqtt.client",
        userdata: object,
        flags: list,
        rc: int,
    ) -> None:
        """
        Callback that is called when connection to MQTT has succeeded.

        Here, we're subscribing to the incoming topics.

        Args:
           client (object): The MQTT client instance for this callback;
           userdata (object): The private user data;
           flags (list): A list of flags;
           rc (int): The connection result.

        """

        # Check the connection result.
        if rc == mqtt.CONNACK_ACCEPTED:
            self.logger.info(
                "connected to MQTT {0} {1}".format(
                    flags, mqtt.connack_string(rc)
                )
            )

            for topic in self.subscription:
                rc, mid = client.subscribe(topic)

                if rc == mqtt.MQTT_ERR_SUCCESS:
                    self.logger.info(
                        "subscribed to topic: "
                        "{topic} ({mid}, {rc})".format(
                            topic=topic, mid=mid, rc=rc
                        )
                    )

                elif rc == mqtt.MQTT_ERR_SUCCESS:
                    self.logger.error(
                        "failed topic subscription with "
                        "{msg}: {topic} ({mid}, {rc})".format(
                            topic=topic,
                            mid=mid,
                            rc=rc,
                            msg=mqtt.error_string(rc),
                        )
                    )
                    self.client.disconnect()

        else:
            self.logger.error(
                "connection error: {msg} {flags}".format(
                    msg=mqtt.error_string(rc), flags=flags
                )
            )
            self.client.disconnect()

    def on_disconnect(
        self: "MQTT", client: paho.mqtt.client, userdata: object, rc: int
    ):
        """
        Handles a disconnect request.

        If the disconnect reason is unknown the method lets the reconnection
        loop establish the connection to the server once again.

        If the disconnect is due to a call to disconnect, then the

        """
        self.logger.error(
            "disconnect: server is down ({1})".format(
                mqtt.error_string(rc), rc
            )
        )

        if rc == mqtt.MQTT_ERR_SUCCESS and self.running:
            self.running = False
            if not self.exit_signal.is_set():
                self.exit_signal.set()

            if self.subscription is not None:
                for topic in self.subscription:
                    self.client.unsubscribe(topic)

    def on_subscribe(
        self: "MQTT",
        client: paho.mqtt.client,
        userdata: object,
        mid: int,
        granted_qos: int,
    ):
        """
        Callback generated when the broker acknowledges a subscription event
        """
        self.logger.debug(
            "subscribed with mid:{0} / qos: {1}".format(mid, granted_qos)
        )

    def on_unsubscribe(
        self: "MQTT", client: paho.mqtt.client, userdata: object, mid: int
    ):
        """
        Callback generated when the broker acknowledges an unsubscribe event
        """
        self.logger.debug("unsubscribed with mid:{0}".format(mid))

    def on_publish(
        self: "MQTT", client: paho.mqtt.client, userdata: object, mid: int
    ):
        """
        Callback generated when the broker acknowledges a pubished message
        """
        self.logger.debug("sent message {0}".format(mid))

    def on_log(
        self: "MQTT",
        client: paho.mqtt.client,
        userdata: object,
        level: int,
        buf: str,
    ):
        """
        Internal mqtt logging where buf is the message being sent
        """
        self.logger.debug("mqtt-log: {0}".format(buf))

    def on_message(
        self: "MQTT", client: paho.mqtt.client, userdata: object, message: str
    ):
        """
        Generic topic to handle message requests

        Args:
            client (object): MQTT client object;
            userdata (object): the private user data;
            message (object): Incoming message.
        """

        self.logger.debug(
            "{topic}:{payload}:{qos}".format(
                topic=message.topic, payload=message.payload, qos=message.qos
            )
        )

    def _print(
        self: "MQTT", client: paho.mqtt.client, userdata: object, message: str
    ):
        self.logger.debug(
            "Message print > {topic}:{payload}:{qos}".format(
                topic=message.topic, payload=message.payload, qos=message.qos
            )
        )

    def send(
        self,
        message: str,
        topic: str,
        qos: int = 1,
        retain: bool = False,
        wait_for_publish: bool = False,
    ):
        pubinfo = self.client.publish(
            "{0}".format(topic), message, qos=qos, retain=retain
        )

        if pubinfo.rc != mqtt.MQTT_ERR_SUCCESS:
            self.logger.error(
                "publish: {0} ({1})".format(
                    mqtt.error_string(pubinfo.rc), pubinfo.rc
                )
            )
            self.exit_signal.set()

        elif wait_for_publish:
            try:
                self.logger.info("Waiting for publish.")
                pubinfo.wait_for_publish()  # proper way, but it can hang
            except ValueError:
                self.logger.error("Could not validate publish.")
                pass

    def __str__(self):
        return str("{}{}{}", self.username, self.hostname, self.port)
