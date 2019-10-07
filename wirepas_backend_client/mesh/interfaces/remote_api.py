"""
         Network address
    •    Network channel
    •    Cipher Key
    •    Authentication Key
    •    Node address
    •    Node role

    .. Copyright:
        Copyright 2019 Wirepas Ltd under Apache License, Version 2.0
        See file LICENSE for full license details.
"""

import struct


class RemoteAPI:
    """
    RemoteAPI

    Wirepas Mesh stack v3.1 onwards provides a way to configure and reconfigure nodes remotely,
    over the Wirepas Mesh network. Parameters such as node address, network address and node
    role can be set or queried. This feature is called the Remote API.

    The Remote API refers to node parameters in the same way the Wirepas Mesh Dual-MCU API
    does. Parameters are called attributes and are separated into MSAP (Management Services)
    and CSAP (Configuration Services).

    Operation
    ---------

    The Wirepas Mesh Remote API requests and responses are sent as regular data frames in the
    Wirepas Mesh network. *One or more requests* can be combined into a Remote API request
    packet.

    Using the sink node, a request packet is sent to target nodes and the target nodes then send a
    response packet back to the sink. *Only sinks can send Remote API requests* via the dual-MCU
    API. A single-MCU application must make sure it only sends Remote API requests from a sink
    node

    """

    def __init__(self):
        super().__init__()
        self._request = dict(
            source_endpoint=255,
            destination_endpoint=240,
            type=None,
            length=None,
            pdu=list(),
            pdu_format="< BB",
        )
        self._response = dict(
            source_endpoint=240,
            destination_endpoint=250,
            type=None,
            length=None,
            pdu=list(),
            pdu_format="< BB",
        )

        self._request["length"] = len(self._request["pdu_format"])
        self._response["length"] = len(self._response["pdu_format"])

    @property
    def request_source_endpoint(self):
        return self._request["source_endpoint"]

    @property
    def request_destination_endpoint(self):
        return self._request["destination_endpoint"]

    @property
    def request_type(self):
        return self._request["type"]

    @property
    def request_length(self):
        return self._request["length"]

    @property
    def request_pdu(self):
        return self._request["pdu"]

    @property
    def request_pdu_format(self):
        return self._request["pdu_format"]

    @request_source_endpoint.setter
    def request_source_endpoint(self, source_endpoint):
        self._request["source_endpoint"] = source_endpoint

    @request_destination_endpoint.setter
    def request_destination_endpoint(self, destination_endpoint):
        self._request["destination_endpoint"] = destination_endpoint

    @request_type.setter
    def request_type(self, request_type):
        self._request["type"] = request_type

    @request_pdu.setter
    def request_pdu(self, pdu):
        self._request["pdu"] = pdu

    @request_pdu_format.setter
    def request_pdu_format(self, pdu_format):
        self._request["pdu_format"] = pdu_format
        self._request["length"] = len(self._request["pdu_format"])

    @property
    def response_source_endpoint(self):
        return self._response["source_endpoint"]

    @property
    def response_destination_endpoint(self):
        return self._response["destination_endpoint"]

    @property
    def response_type(self):
        return self._response["type"]

    @property
    def response_pdu(self):
        return self._response["pdu"]

    @property
    def response_pdu_format(self):
        return self._response["pdu_format"]

    @response_source_endpoint.setter
    def response_source_endpoint(self, source_endpoint):
        self._response["source_endpoint"] = source_endpoint

    @response_destination_endpoint.setter
    def response_destination_endpoint(self, destination_endpoint):
        self._response["destination_endpoint"] = destination_endpoint

    @response_type.setter
    def response_type(self, response_type):
        self._response["type"] = response_type

    @response_pdu.setter
    def response_pdu(self, pdu):
        self._response["pdu"] = pdu

    @response_pdu_format.setter
    def response_pdu_format(self, pdu_format):
        self._response["pdu_format"] = pdu_format
        self._response["length"] = len(self._response["pdu_format"])

    def encode(self) -> bytes:
        """ returns a byte array with the command payload"""
        if self.request_pdu:

            payload = struct.pack(
                self.request_pdu_format,
                self.request_type,
                self.request_length,
                *self.request_pdu,
            )

        else:
            payload = struct.pack(
                self.request_pdu_format, self.request_type, self.request_length
            )

        return payload

    def decode(self, payload: bytes) -> dict:
        """ returns a dictionary with the decoded values"""
        raise NotImplementedError

    def __str__(self):

        identity = f"RemoteAPI:{self.__class__.__name__}({self.request_type:02x},{self.response_type:02x})"

        return identity


class Ping(RemoteAPI):
    """Ping"""

    def __init__(self):
        super().__init__()
        self.request_type = 0x00
        self.response_type = 0x80


class Begin(RemoteAPI):
    """Begin"""

    def __init__(self):
        super().__init__()
        self.request_type = 0x01
        self.response_type = 0x81


class BeginWithLock(RemoteAPI):
    """RemoteAPI"""

    def __init__(self, feature_lock_key):
        super().__init__()
        self._feature_lock_key_size = 16
        if len(feature_lock_key) == 16:
            self._feature_lock_key = feature_lock_key
            self.request_pdu = self._feature_lock_key
        else:
            raise ValueError("Improper BEGIN lock key size")

        self.request_type = 0x02
        self.response_type = 0x82
        self.request_pdu_format += self._feature_lock_key_format()

    def _feature_lock_key_format(self):
        """ Format for packing lock feature key"""
        return "B" * self._feature_lock_key_size

    @property
    def feature_lock_key(self):
        return self._feature_lock_key


class End(RemoteAPI):
    """End"""

    def __init__(self):
        super().__init__()
        self.request_type = 0x03
        self.response_type = 0x83


class Cancel(RemoteAPI):
    """Cancel"""

    def __init__(self):
        super().__init__()
        self.request_type = 0x04
        self.response_type = 0x84


class Update(RemoteAPI):
    """Update
        An Update request starts a countdown, after which the MSAP and CSAP attributes are written
        from a temporary buffer to the actual attributes. The node is then reset, if any of the written
        attributes require a reboot. See Table 6 and Table 7 for a list of attributes that require a reboot.

        Format of the Update request is shown in Figure 13 and the response in Figure 14.

        The countdown time value range is described in Table 5. A special value of 0 is also accepted.
        It cancels a running countdown. If the countdown time is omitted completely, the current
        countdown time is reported, or zero if no countdown is running

    """

    def __init__(self):
        super().__init__()
        self.request_type = 0x05
        self.response_type = 0x85

    def timer(self, value):
        self.request_pdu_format += "H"
        self.countdown = [value]
        self.request_pdu = self.countdown


class MeshServices(RemoteAPI):
    """MeshServices"""

    def __init__(self):
        super().__init__()
        self._attribute = None
        self._service_class = None

    @property
    def attribute(self):
        return self._attribute.identifier

    @property
    def service_class(self):
        return self._service_class

    @attribute.setter
    def attribute(self, attribute):

        if self.service_class != attribute.service_class:
            raise ValueError("Unknown attribute for desired mesh service")
        # add id which is H
        self._attribute = attribute
        self.request_pdu_format += "H"
        self.request_pdu = [attribute.identifier]

        # add attribute value
        self.request_pdu.append(attribute.bytes)
        self.request_pdu_format += "{}s".format(len(self.request_pdu))


class WriteMSAP(MeshServices):
    """WriteMSAP"""

    def __init__(self):
        super().__init__()
        self.request_type = 0x0B
        self.response_type = 0x8B
        self._service_class = "MSAP"


class ReadMSAP(MeshServices):
    """ReadMSAP"""

    def __init__(self):
        super().__init__()
        self.request_type = 0x0C
        self.response_type = 0x8C
        self._service_class = "MSAP"


class ScratchpadStatus(RemoteAPI):
    """ScratchpadStatus"""

    def __init__(self):
        super().__init__()
        self.request_type = 0x19
        self.response_type = 0x99


class ScratchpadUpdate(RemoteAPI):
    """ScratchpadUpdate"""

    def __init__(self):
        super().__init__()
        self.request_type = 0x1A
        self.response_type = 0x9A
        self._sequence = None

    @property
    def sequence(self):
        return self._sequence

    @sequence.setter
    def sequence(self, value: int):
        self._sequence = value
        self.request_pdu = [self._sequence]
        self.request_pdu_format += "B"


class WriteCSAP(MeshServices):
    """WriteCSAP"""

    def __init__(self):
        super().__init__()

        self.request_type = 0x0D
        self.response_type = 0x8D
        self._service_class = "CSAP"


class ReadCSAP(MeshServices):
    """ReadCSAP"""

    def __init__(self):
        super().__init__()

        self.request_type = 0x0E
        self.response_type = 0x8E
        self._service_class = "CSAP"


class QueueTimeWrite(RemoteAPI):
    """QueueTimeWrite"""

    def __init__(self):
        super().__init__()
        self.request_type = 0x4F
        self.response_type = 0xCF


class QueueTimeRead(RemoteAPI):
    """QueueTimeRead"""

    def __init__(self):
        super().__init__()
        self.request_type = 0x50
        self.response_type = 0xD0
