"""
    Network
    =======

    .. Copyright:
        Copyright 2019 Wirepas Ltd under Apache License, Version 2.0
        See file LICENSE for full license details.
"""

import logging
import queue
import time

import wirepas_messaging

from ..api import MQTT
from ..api import StreamObserver
from ..api import Topics
from ..api import decode_topic_message
from ..api import topic_message
from ..tools import ExitSignal


class NetworkDiscovery(StreamObserver):
    """
    NetworkDiscovery

    Tracks the MQTT topics and generates an object representation of the
    devices present in a given network.

    It builds a map of gateways, sinks and devices.

    """

    def __init__(
        self,
        mqtt_settings,
        shared_state=None,
        data_queue=None,
        event_queue=None,
        gateway_id: str = "+",
        sink_id: str = "+",
        network_id: str = "+",
        source_endpoint: str = "+",
        destination_endpoint: str = "+",
        message_subscribe_handlers=None,
        message_publish_handlers=None,
        network_parameters=None,
        **kwargs
    ):
        """ MQTT Observer constructor """

        try:
            self.tx_queue = kwargs["tx_queue"]
        except KeyError:
            kwargs["tx_queue"] = None

        try:
            self.rx_queue = kwargs["rx_queue"]
        except KeyError:
            kwargs["rx_queue"] = None

        super(NetworkDiscovery, self).__init__(**kwargs)

        try:
            self.logger = kwargs["logger"]
        except KeyError:
            self.logger = logging.getLogger(__name__)

        try:
            self.exit_signal = kwargs["exit_signal"]
        except KeyError:
            self.exit_signal = ExitSignal()

        self.response_queue = self.tx_queue
        self.request_queue = self.rx_queue

        self.data_queue = data_queue
        self.event_queue = event_queue

        if network_parameters:
            self.network_parameters = network_parameters
        else:
            self.network_parameters = dict(
                gw_id=str(gateway_id),
                sink_id=str(sink_id),
                network_id=str(network_id),
                src_ep=str(source_endpoint),
                dst_ep=str(destination_endpoint),
            )

        self.mqtt_settings = mqtt_settings
        self.mqtt_topics = Topics()

        if message_subscribe_handlers:
            self.message_subscribe_handlers = message_subscribe_handlers
        else:
            self.message_subscribe_handlers = self.build_subscription()

        if message_publish_handlers:
            self.message_publish_handlers = message_publish_handlers
        else:
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
            exit_signal=self.exit_signal,
            message_subscribe_handlers=self.message_subscribe_handlers,
            message_publish_handlers=self.message_publish_handlers,
            logger=self.logger,
        )

        self.shared_state = shared_state
        self.device_manager = MeshManagement()

    def run(self):
        """
        Executes MQTT loop

        Attributes:
            message_subscribe_handlers (dict): overrides message handlers
            message_publish_handlers (dict): overrides publish handlers

        """
        self.mqtt.serve()

    def notify(self, message, path="response"):
        """ Puts the device on the queue"""
        if self.shared_state:
            self.shared_state["devices"] = self.device_manager

        try:
            if message:
                if "response" in path:
                    self.response_queue.put(message)

                elif "data" in path and self.data_queue:
                    self.data_queue.put(message)

                elif "event" in path and self.event_queue:
                    self.event_queue.put(message)
        except:
            pass

    def build_subscription(self):

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

        message_subscribe_handlers = {
            event_status: self.generate_gateway_status_event_cb(),
            event_received_data: self.generate_gateway_data_event_cb(),
            response_get_configs: self.generate_gateway_response_get_configs_cb(),
            response_set_config: self.generate_gateway_response_set_config_cb(),
            response_send_data: self.generate_gateway_data_response_cb(),
            response_otap_status: self.generate_gateway_otap_status_response_cb(),
            response_otap_load_scratchpad: self.generate_gateway_load_scratchpad_response_cb(),
            response_otap_process_scratchpad: self.generate_gateway_process_scratchpad_response_cb(),
        }

        return message_subscribe_handlers

    # Publishing
    def send_data(self, mqtt_publish: callable, topic: str):
        """ Callback provided by the interface's cb generator
            Args:
                mqtt_publish: callable that handles the message dispatch
                topic: where the message goes to - ignored if from_message
        """
        try:
            message = self.request_queue.get(block=True, timeout=1)
            self.logger.debug("publishing message %s", message)

            if "from_message" in topic:
                topic = message["topic"]

            if "qos" in message:
                qos = message["qos"]
            else:
                qos = 1

            if "retain" in message:
                retain = message["retain"]
            else:
                retain = False

            if "wait_for_publish" in message:
                wait_for_publish = message["wait_for_publish"]
            else:
                wait_for_publish = False

            try:
                message = message["data"].payload
            except AttributeError:
                message = message["data"]

            mqtt_publish(
                message=message,
                retain=retain,
                qos=qos,
                topic=topic,
                wait_for_publish=wait_for_publish,
            )

        except queue.Empty:
            pass

        except AttributeError:
            time.sleep(10)

        try:
            if self.shared_state:
                if self.shared_state["devices"] is not None:
                    self.device_manager = self.shared_state["devices"]
        except KeyError:
            pass

    # Subscribing
    def generate_gateway_status_event_cb(self) -> callable:
        @topic_message
        def on_gateway_status_event_cb(message, topic: list):
            """ Decodes an incoming gateway status event """

            self.logger.info("status event %s", message)
            try:
                message = wirepas_messaging.gateway.api.StatusEvent.from_payload(
                    message
                )

                # updates gateway details
                gateway = self.device_manager.add(message.gw_id)
                gateway.state = message.state

                self.notify(message=message, path="event")
            except:
                pass

        return on_gateway_status_event_cb

    def generate_gateway_data_event_cb(self) -> callable:
        @decode_topic_message
        def on_gateway_data_event_cb(message, topic: list):
            """ Decodes an incoming data event callback """

            self.logger.info("data event: %s", message)
            self.device_manager.add_from_mqtt_topic(
                topic, message.source_address
            )
            self.notify(message=message, path="data")

        return on_gateway_data_event_cb

    def generate_gateway_response_get_configs_cb(self) -> callable:
        @topic_message
        def on_gateway_get_configs_cb(message, topic: list):
            """ Decodes and incoming configuration response """

            self.logger.info("configs response: %s", message)
            message = self.mqtt_topics.constructor(
                "response", "get_configs"
            ).from_payload(message)

            self.device_manager.add_from_mqtt_topic(topic)
            self.device_manager.update(message.gw_id, message.configs)
            self.notify(message, path="response")

        return on_gateway_get_configs_cb

    def generate_gateway_otap_status_response_cb(self) -> callable:
        @topic_message
        def on_gateway_otap_status_cb(message, topic: list):
            """ Decodes an otap status response """
            self.logger.info("otap status response: %s", message)
            message = self.mqtt_topics.constructor(
                "response", "otap_status"
            ).from_payload(message)
            self.notify(message, path="response")

        return on_gateway_otap_status_cb

    def generate_gateway_response_set_config_cb(self) -> callable:
        @topic_message
        def on_gateway_set_config_response_cb(message, topic: list):
            """ Decodes a set config response """
            self.logger.info("set config response: %s", message)
            message = self.mqtt_topics.constructor(
                "response", "set_config"
            ).from_payload(message)
            self.notify(message, path="response")

        return on_gateway_set_config_response_cb

    def generate_gateway_data_response_cb(self) -> callable:
        @topic_message
        def on_gateway_data_response_cb(message, topic: list):
            """ Decodes a data response """
            self.logger.info("send data response: %s", message)
            self.device_manager.add_from_mqtt_topic(topic)
            message = self.mqtt_topics.constructor(
                "response", "send_data"
            ).from_payload(message)

            self.notify(message, path="response")

        return on_gateway_data_response_cb

    def generate_gateway_load_scratchpad_response_cb(self) -> callable:
        @topic_message
        def on_gateway_load_scratchpad_response_cb(message, topic: list):
            """ """
            self.logger.info("load scratchpad response: %s", message)
            message = self.mqtt_topics.constructor(
                "response", "otap_load_scratchpad"
            ).from_payload(message)
            self.notify(message, path="response")

        return on_gateway_load_scratchpad_response_cb

    def generate_gateway_process_scratchpad_response_cb(self) -> callable:
        @topic_message
        def on_gateway_process_scratchpad_cb(message, topic: list):
            """ """
            self.logger.info("process scratchpad response: %s", message)
            message = self.mqtt_topics.constructor(
                "response", "otap_process_scratchpad"
            ).from_payload(message)
            self.notify(message, path="response")

        return on_gateway_process_scratchpad_cb

    def generate_gateway_response_cb(self) -> callable:
        @topic_message
        def on_response_cb(message, topic: list):
            """ generic message handler """
            self.notify(message, path="response")

        return on_response_cb


class MeshDevice(object):
    """
    MeshDevice

    Lowest representation of a WM device
    """

    __name = "node"

    def __init__(
        self,
        device_id: str,
        network_id: str = None,
        gateway_id: str = None,
        state: int = None,
        role: int = None,
    ):
        super(MeshDevice, self).__init__()
        self._device_id = str(device_id)
        self.__dict__["device_type"] = self.__name
        self.state = state
        self.role = role
        self.gateway_id = gateway_id
        self.network_id = network_id

    def update(self, configuration: dict):
        for k, v in configuration.items():
            if v is not None:
                self.__dict__[k] = v
                if "network_address" in k:
                    self.__dict__["network_id"] = v

    @property
    def device_id(self):
        return self._device_id

    def __str__(self):
        id_str = "Device type: {}\n".format(self.__name)
        id_str = "{}Device attributes: \n".format(id_str)
        for k, v in self.__dict__.items():
            id_str = "{}  {}={}\n".format(id_str, k, v)
        return id_str


class Sink(MeshDevice):
    """
    MeshDevice

    Lowest representation of a WM device
    """

    __name = "sink"

    # add allowed properties to filter out clutter

    def __init__(self, device_id: str, **kwargs):
        super(Sink, self).__init__(device_id=device_id, **kwargs)
        self.node_address = None
        self.app_config_data = None
        self.app_config_diag = None
        self.role = None
        self.firmware_version = None

    def set_app_config(self, **kwargs):
        pass

    def __str__(self):

        id_str = (
            "Sink id: {_device_id}\n"
            "Attached to network: {network_id}\n"
            "Address: {node_address}\n"
            "Appconfig: {app_config_data}\n"
            "Appconfig interval: {app_config_diag}\n"
            "Role: {role}\n"
            "Firmware: {firmware_version}\n"
        ).format(**self.__dict__)

        return id_str


class Gateway(MeshDevice):
    """
    MeshDevice

    Lowest representation of a WM device
    """

    __name = "gateway"

    def __init__(self, device_id, network_id=None, **kwargs):
        super(Gateway, self).__init__(
            device_id=device_id, network_id=network_id, **kwargs
        )
        self.gateway_id = device_id
        self.state = None
        self._sinks = dict()
        self._nodes = dict()

    def add(self, devices: list(), device_type):
        attribute = None
        if "sink" in device_type:
            attribute = self._sinks

        if "node" in device_type:
            attribute = self._nodes

        if devices and attribute:
            for device in devices:
                if device.device_id not in attribute:
                    attribute[device.device_id] = device

    def remove(self, device_id):
        if device_id in self._sinks:
            del self._sinks[device_id]

        if device_id in self._nodes:
            del self._nodes[device_id]

    @property
    def sinks(self):
        for sink in self._sinks.values():
            yield sink

    @property
    def nodes(self):
        for node in self._nodes.values():
            yield node

    @sinks.setter
    def sinks(self, value: list):
        for sink in value:
            if sink and sink not in self._sinks:
                self._sinks[sink] = Sink(
                    device_id=sink,
                    network_id=self.network_id,
                    gateway_id=self.device_id,
                )

    @nodes.setter
    def nodes(self, value: list):
        for node in value:
            if node and node not in self._nodes:
                self._nodes[node] = MeshDevice(
                    device_id=node,
                    network_id=self.network_id,
                    gateway_id=self.device_id,
                )

    def update(self, configurations: list):
        for configuration in configurations:
            sink_id = configuration["sink_id"]
            self.sinks = [sink_id]
            self._sinks[sink_id].update(configuration)

    def notify_sinks(self, sink_id, dest, src_ep, dst_ep, qos, payload):
        pass

    def __str__(self):
        id_str = (
            "Gateway id: {gateway_id}\n"
            "  Attached to network: {network_id}\n"
        ).format(gateway_id=self.gateway_id, network_id=self.network_id)
        id_str = "{}  Sinks:{}\n".format(
            id_str, str(list(map(str, self.sinks)))
        )
        id_str = "{}  Nodes:{}\n".format(
            id_str, str(list(map(str, self.nodes)))
        )
        return id_str


class Network(object):
    """
    MeshDevice

    Lowest representation of a WM device
    """

    name = "network"

    def __init__(self, network_id: str, gateways=None, sinks=None, nodes=None):
        super(Network, self).__init__()
        self._network_id = network_id
        self._gateways = dict()

        if gateways:
            for gateway in gateways:
                self.add(gateway=gateway, sinks=sinks, nodes=nodes)

    @property
    def network_id(self):
        return self._network_id

    @property
    def gateways(self):
        yield self._gateways

    @property
    def nodes(self):
        for gateway in self._gateways.values():
            return gateway.nodes

    @property
    def sinks(self):
        for gateway in self._gateways.values():
            return gateway.sinks

    @property
    def devices(self):
        return {str(self._network_id): self._gateways}

    def add(self, gateway: "MeshDevice", sinks: list, nodes: list):
        """ Adds devices in the network """
        gateway_id = str(gateway.device_id)
        self._gateways[gateway_id] = gateway

        if sinks:
            self._gateways[gateway_id].sinks = sinks

        if nodes:
            self._gateways[gateway_id].nodes = nodes

    def update(self, gateway_id, sink_configuration: dict):
        """ updates the inner setting of the gateway device """
        if gateway_id not in self._gateways:
            gateway_device = Gateway(gateway_id)
            self._gateways[gateway_id] = gateway_device
        self._gateways[gateway_id].update([sink_configuration])

    def remove(self, device_id: str):
        for gateway in self._gateways.values():
            gateway.remove(device_id)

        if device_id in self._gateways:
            del self._gateways[device_id]

    def __str__(self):
        """ Provides a string with the summary of its contents """

        id_str = "Network: {}\n".format(self._network_id)

        for gateway_id, gateway in self._gateways.items():
            id_str = "{}  Gateway: {}\n".format(id_str, gateway_id)

            sinks = gateway.sinks
            for sink in sinks:
                id_str = "{}    Sink:{}\n".format(id_str, sink.device_id)

            nodes = gateway.nodes
            for node in nodes:
                id_str = "{}    Node:{}\n".format(id_str, node.device_id)

        return id_str


class MeshManagement(object):
    """
    MeshManagement

    Manages the Wirepas Mesh Layer

    Attributes:
        gateways (dict): a dictionary with all the existing gateways
        networks (dict): a dictionary with all the available networks
    """

    def __init__(self):
        super(MeshManagement, self).__init__()
        self._gateways = (
            dict()
        )  # holds gateways because they might not have a network
        self._networks = dict()

    @property
    def networks(self):
        if not self._networks:
            yield list()
        for network in self._networks.values():
            yield network

    @property
    def gateways(self):
        if not self._gateways:
            yield list()
        for gateway in self._gateways.values():
            yield gateway

    @property
    def sinks(self):
        if not self._networks:
            return list()
        for network in self._networks:  # generator magic
            return self._networks[network].sinks

    @property
    def nodes(self):
        if not self._networks:
            return list()
        for network in self._networks:  # generator magic
            return self._networks[network].nodes

    def add(
        self,
        gw_id: str,
        network_id: str = None,
        sink_id: str = None,
        node_id: str = None,
        **kwargs
    ):
        """
        Creates a device entry in the node management.

        The internal dictionary is organized according to the device type

        Args:
            identifier (str): device id
            device_type (str): type of the device (Gateway, Sink, ..)
            kwargs (dict): arguments to pass on to the class constructor

        Returns:
            the created object
        """

        try:
            gateway_device = self._gateways[gw_id]
        except KeyError:
            gateway_device = Gateway(gw_id, **kwargs)
            self._gateways[gw_id] = gateway_device

        if network_id:
            gateway_device.network_id = network_id

        if network_id is not None:
            if network_id not in self._networks:
                self._networks[network_id] = Network(
                    network_id=network_id,
                    gateways=[gateway_device],
                    sinks=[sink_id],
                    nodes=[node_id],
                    **kwargs
                )
            else:
                self._networks[network_id].add(
                    gateway=gateway_device, sinks=[sink_id], nodes=[node_id]
                )

        return gateway_device

    def update(self, gateway_id, configurations):
        """
        Receives a gateway id and a list of its configurations.

        Args:
            gateway_id (str): the gateway identifier
            configurations (list): list of configuration dictionaries
        """
        self._gateways[gateway_id].update(configurations)

        for configuration in configurations:
            network_id = configuration["network_address"]
            if network_id is not None:
                network_id = str(network_id)
                if network_id not in self._networks:
                    self._networks[network_id] = Network(
                        network_id=network_id,
                        gateways=[self._gateways[gateway_id]],
                    )
                else:
                    self._networks[network_id].update(
                        gateway_id=gateway_id, sink_configuration=configuration
                    )

    def add_from_mqtt_topic(self, topic: list, node_id: list = None):
        """
        Receives a ordered topic list split at the / delimiter and a node id
        if it refers to a data message

        Args:
            topic (str): the MQTT topic
            node_id (str): the identifier of the node who sent the message
        """

        sink_id = None
        gateway_id = None
        network_id = None

        try:
            gateway_id = topic[2]
            sink_id = topic[3]
            network_id = topic[4]
        except IndexError:
            pass

        self.add(
            gw_id=gateway_id,
            network_id=network_id,
            sink_id=sink_id,
            node_id=node_id,
        )

    def remove(self, device_id):
        """ Removes a device or a network interely"""

        if device_id in self._gateways:
            del self._gateways[device_id]

        for network in self._networks.values():
            network.remove(device_id)

    def __str__(self):
        obj = ""

        for _, v in self._networks.items():
            obj = "{}{}\n".format(obj, str(v))

        return obj
