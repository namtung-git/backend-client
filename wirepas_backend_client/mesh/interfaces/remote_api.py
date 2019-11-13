"""
    Remote API

    Wirepas Mesh stack v3.1 onwards provides a way to configure and reconfigure nodes remotely,
    over the Wirepas Mesh network. Parameters such as node address, network address and node
    role can be set or queried. This feature is called the Remote API.

    The Remote API refers to node parameters in the same way the Wirepas Mesh Dual-MCU API
    does. Parameters are called attributes and are separated into MSAP (Management Services)
    and CSAP (Configuration Services).


    .. Copyright:
        Copyright 2019 Wirepas Ltd under Apache License, Version 2.0
        See file LICENSE for full license details.
"""

import struct
import logging
import enum


class ErrorResponseType(enum.Enum):
    """ Error response types """

    AccessDenied = 0xF8
    WriteOnly = 0xF9
    InvalidBroadcastRequest = 0xFA
    InvalidBegin = 0xFB
    OutOfSpace = 0xFC
    InvalidValue = 0xFD
    InvalidLength = 0xFE
    UnknownRequest = 0xFF


class RemoteAPI:
    """
    RemoteAPI

    The Wirepas Mesh Remote API requests and responses are sent as regular data frames in the
    Wirepas Mesh network. *One or more requests* can be combined into a Remote API request
    packet.

    Using the sink node, a request packet is sent to target nodes and the target nodes then send a
    response packet back to the sink. *Only sinks can send Remote API requests* via the dual-MCU
    API. A single-MCU application must make sure it only sends Remote API requests from a sink
    node.

    """

    def __init__(self, logger=None):
        super().__init__()
        self._request = dict(
            source_endpoint=255,
            destination_endpoint=240,
            type=None,
            length=None,
            pdu=None,
            pdu_format="< BB",
        )
        self._response = dict(
            source_endpoint=240,
            destination_endpoint=250,
            type=None,
            length=None,
            pdu=None,
            values=None,
            pdu_format="< BB",
        )

        self.logger = logger or logging.getLogger(__name__)
        self._request["length"] = len(self._request["pdu_format"])
        self._response["length"] = len(self._response["pdu_format"])

    @property
    def request_source_endpoint(self):
        """ Returns the request's source endpoint """
        return self._request["source_endpoint"]

    @property
    def request_destination_endpoint(self):
        """ Returns the request's destination endpoint """
        return self._request["destination_endpoint"]

    @property
    def request_type(self):
        """ Returns the request's type value """
        return self._request["type"]

    @property
    def request_length(self):
        """ Returns the request's length """
        return self._request["length"]

    @property
    def request_pdu(self):
        """ Returns the request's payload """
        return self._request["pdu"]

    @property
    def request_pdu_format(self):
        """ Returns the request's apdu format - how to (un)pack """
        return self._request["pdu_format"]

    @request_source_endpoint.setter
    def request_source_endpoint(self, source_endpoint):
        """ Returns the source's endpoint """
        self._request["source_endpoint"] = source_endpoint

    @request_destination_endpoint.setter
    def request_destination_endpoint(self, destination_endpoint):
        """ Returns the request's destination endpoint """
        self._request["destination_endpoint"] = destination_endpoint

    @request_type.setter
    def request_type(self, request_type):
        """ Sets the request's type field """
        self._request["type"] = request_type

    @request_pdu.setter
    def request_pdu(self, pdu):
        """ Stores the request's payload """
        if pdu is None:
            pdu = bytearray()
        self._request["pdu"] = pdu
        self._request["pdu_format"] += "{}s".format(len(pdu))
        self._request["length"] = struct.calcsize(self._request["pdu_format"])

    @request_pdu_format.setter
    def request_pdu_format(self, pdu_format):
        """ Stores the request's payload format """
        if pdu_format:
            self._request["pdu_format"] = pdu_format
            self._request["length"] = len(self._request["pdu_format"])

    @property
    def response_source_endpoint(self):
        """ Provides the expected source endpoint within the response """
        return self._response["source_endpoint"]

    @property
    def response_destination_endpoint(self):
        """ Provides the expected destination endpoint within the response """
        return self._response["destination_endpoint"]

    @property
    def response_type(self):
        """ Provides the type to expect in the response payload """
        return self._response["type"]

    @property
    def response_pdu(self):
        """ Provides the response payload API response """
        return self._response["pdu"]

    @property
    def response_pdu_format(self):
        """ Provides the response payload format - how to (un)pack it """
        return self._response["pdu_format"]

    @property
    def response_values(self):
        """ Provides the response decoded values """
        return self._response["values"]

    @response_source_endpoint.setter
    def response_source_endpoint(self, source_endpoint):
        """ Sets the response payload API response"""
        self._response["source_endpoint"] = source_endpoint

    @response_destination_endpoint.setter
    def response_destination_endpoint(self, destination_endpoint):
        """ Sets the response destination endpoint """
        self._response["destination_endpoint"] = destination_endpoint

    @response_type.setter
    def response_type(self, response_type):
        """ Sets the response type field """
        self._response["type"] = response_type

    @response_pdu.setter
    def response_pdu(self, pdu):
        """ Sets the response's payload """
        if pdu is None:
            pdu = bytearray()
        self._response["pdu"] = pdu

    @response_values.setter
    def response_values(self, values):
        """ Provides the response decoded values """
        self._response["values"] = values
        self.response_type = values[0]

    def encode(self) -> bytes:
        """ Returns a byte array with the command payload """
        self.logger.debug("Encoding request: %s", self._request)

        if self.request_pdu:
            payload = struct.pack(
                self.request_pdu_format,
                self.request_type,
                self.request_length,
                self.request_pdu,
            )

        else:
            payload = struct.pack(
                self.request_pdu_format, self.request_type, self.request_length
            )

        return payload

    def decode(self) -> dict:
        """ Returns a dictionary with the decoded values """
        self.logger.debug("Decoding response: %s", self._response)

        if self.response_pdu:
            self.response_values = struct.unpack_from(
                self.response_pdu_format, self.response_pdu
            )

        return self

    @staticmethod
    def unpack(fmt, payload):
        """ Returns the values within the payload """
        return struct.unpack(fmt, payload)

    @staticmethod
    def pack(fmt, values, expand=False):
        """ Returns a bytearray with the packed payload """
        if expand:
            return bytearray(struct.pack(fmt, *values))
        return bytearray(struct.pack(fmt, values))

    def __str__(self):
        """ Defines how to print the remote api command """
        identity = f"RemoteAPI:{self.__class__.__name__}"
        if self.request_type and self.response_type:
            identity = (
                f"{identity}({self.request_type:02x},{self.response_type:02x})"
            )
        return identity


class MeshServices(RemoteAPI):
    """MeshServices"""

    def __init__(self):
        super().__init__()
        self._attribute = None
        self._service_class = None

    @property
    def attribute(self):
        """ Returns the attribute id for the command """
        return self._attribute

    @property
    def service_class(self):
        """ Returns the service class of the command (CSAP/MSAP) """
        return self._service_class

    @attribute.setter
    def attribute(self, attribute):
        """ Sets the command's attribute value """

        if self.service_class != attribute.service_class:
            raise ValueError("Unknown attribute for desired mesh service")

        # add id which is H
        self._attribute = attribute
        self.request_pdu = attribute.bytes

    def __str__(self):
        """ Defines how to print the Remote API service command """

        identity = super().__str__()
        if self._service_class is not None:
            identity += f":{self.attribute}"

        return identity


class QueueTime(RemoteAPI):
    """QueueTimeWrite"""

    def __init__(self):
        super().__init__()
        self.request_type = 0x4F
        self.response_type = 0xCF
        self._priority = None
        self._queue_time = None

    @property
    def priority(self):
        """ Returns the message priority class associated with the request """
        return self._priority

    @property
    def time(self):
        """ Returns the amount of time a message is set to stay in the queue """
        return self._queue_time

    @priority.setter
    def priority(self, priority):
        """ Sets the message priority class associated with the request """
        self._priority = priority

    @time.setter
    def time(self, queue_time):
        """ Sets the amount of time a message can stay in the queue """
        if self._priority is None:
            raise ValueError("priority must be set before time")
        self._queue_time = queue_time
        self.request_pdu = self.pack(
            "<BH", [self._priority, self._queue_time], expand=True
        )


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
            self.request_pdu = self.pack("16s", self._feature_lock_key)
        else:
            raise ValueError("Improper BEGIN lock key size")

        self.request_type = 0x02
        self.response_type = 0x82

    @property
    def feature_lock_key(self):
        """ Returns the feature lock key """
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
    """Update"""

    def __init__(self):
        super().__init__()
        self.request_type = 0x05
        self.response_type = 0x85
        self._countdown = 0

    @property
    def countdown(self):
        """ Returns the amount of time for the command to take effect """
        return self._countdown

    @countdown.setter
    def countdown(self, countdown):
        """ Sets the amount of time to wait until the command takes effect """
        self._countdown = countdown
        self.request_pdu = self.pack("<H", self._countdown)


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
        """Retrieves the scratchpad sequence number"""
        return self._sequence

    @sequence.setter
    def sequence(self, value: int):
        """Sets the target scratchpad sequence number"""
        self._sequence = value
        self.request_pdu = self.pack("<B", self._sequence)


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


class QueueTimeWrite(QueueTime):
    """QueueTimeWrite"""

    def __init__(self):
        super().__init__()
        self.request_type = 0x4F
        self.response_type = 0xCF


class QueueTimeRead(QueueTime):
    """QueueTimeRead"""

    def __init__(self):
        super().__init__()
        self.request_type = 0x50
        self.response_type = 0xD0


class RemoteAPIError(RemoteAPI):
    """ Error
    """

    def __init__(self, payload=None):
        super().__init__()
        self.request_source_endpoint = None
        self.request_destination_endpoint = None
        self.request_type = None
        self.request_pdu = None
        self.response_pdu = payload

    def encode(self) -> bytes:
        raise TypeError("Only replies are allowed")

    def decode(self):
        """ Generates and returns the appropriate error class """
        super().decode()

        if self.response_type == ErrorResponseType.AccessDenied.value:
            obj = AccessDenied(self.response_pdu)

        elif self.response_type == ErrorResponseType.WriteOnly.value:
            obj = WriteOnly(self.response_pdu)

        elif (
            self.response_type
            == ErrorResponseType.InvalidBroadcastRequest.value
        ):
            obj = InvalidBroadcastRequest(self.response_pdu)

        elif self.response_type == ErrorResponseType.InvalidBegin.value:
            obj = InvalidBegin(self.response_pdu)

        elif self.response_type == ErrorResponseType.OutOfSpace.value:
            obj = OutOfSpace(self.response_pdu)

        elif self.response_type == ErrorResponseType.InvalidValue.value:
            obj = InvalidValue(self.response_pdu)

        elif self.response_type == ErrorResponseType.InvalidLength.value:
            obj = InvalidLength(self.response_pdu)

        elif self.response_type == ErrorResponseType.UnknownRequest.value:
            obj = UnknownRequest(self.response_pdu)

        return obj


class AccessDenied(RemoteAPIError):
    """ErrorAccessDenied"""

    def __init__(self, payload):
        super().__init__(payload)
        self.response_type = ErrorResponseType.AccessDenied.value


class WriteOnly(RemoteAPIError):
    """ErrorAccessDenied"""

    def __init__(self, payload):
        super().__init__(payload)
        self.response_type = ErrorResponseType.WriteOnly.value
        self.response_length = 0x03


class InvalidBroadcastRequest(RemoteAPIError):
    """InvalidBroadcastRequest"""

    def __init__(self, payload):
        super().__init__(payload)
        self.response_type = ErrorResponseType.InvalidBroadcastRequest.value
        self.response_length = 0x03


class InvalidBegin(RemoteAPIError):
    """InvalidBegin"""

    def __init__(self, payload):
        super().__init__(payload)
        self.response_type = ErrorResponseType.InvalidBegin.value
        self.response_length = 0x03


class OutOfSpace(RemoteAPIError):
    """InvalidBegin"""

    def __init__(self, payload):
        super().__init__(payload)
        self.response_type = ErrorResponseType.OutOfSpace.value
        self.response_length = 0x03


class InvalidValue(RemoteAPIError):
    """InvalidValue"""

    def __init__(self, payload):
        super().__init__(payload)
        self.response_type = ErrorResponseType.InvalidValue.value


class InvalidLength(RemoteAPIError):
    """InvalidLength"""

    def __init__(self, payload):
        super().__init__(payload)
        self.response_type = ErrorResponseType.InvalidLength.value


class UnknownRequest(RemoteAPIError):
    """UnknownRequest"""

    def __init__(self, payload):
        super().__init__(payload)
        self.response_type = ErrorResponseType.UnknownRequest.value
