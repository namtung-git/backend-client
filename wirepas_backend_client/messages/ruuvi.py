"""
    Ruuvi
    =====

    Contains helpers to translate network data from Ruuvi devices

    .. Copyright:
        Copyright 2019 Wirepas Ltd. All Rights Reserved.
        See file LICENSE.txt for full license details.
"""
import datetime
import struct

from .generic import GenericMessage
from .types import ApplicationTypes


class RuuviMessage(GenericMessage):
    """
    RuuviMessage

    Represents a message sent by advertiser devices.

    Attributes:
        SOURCE_EP (int): Ruuvi source endpoint
        DESTINATION_EP (int): Ruuvi destination endpoint
        TYPES (dict): APDU's types
        MESSAGE_COUNTER (int): number of decoded messages
    """

    SOURCE_EP = 11
    DESTINATION_EP = 11

    TYPES = {
        1: {"name": "counter", "unit": 1, "format": "< H", "type": "uint16"},
        2: {
            "name": "temperature",
            "unit": 1 / 100.0,
            "format": "< i",
            "type": "int32",
        },
        3: {
            "name": "humidity",
            "unit": 1 / 1024.0,
            "format": "< I",
            "type": "uint32",
        },
        4: {
            "name": "pressure",
            "unit": 1 / 10000.0,
            "format": "< I",
            "type": "uint32",
        },
        5: {"name": "acc_x", "unit": 1e-03, "format": "< i", "type": "int32"},
        6: {"name": "acc_y", "unit": 1e-03, "format": "< i", "type": "int32"},
        7: {"name": "acc_z", "unit": 1e-03, "format": "< i", "type": "int32"},
    }

    MESSAGE_COUNTER = 0

    def __init__(self, *args, **kwargs) -> "RuuviMessage":

        self.data_payload = None
        super(RuuviMessage, self).__init__(*args, **kwargs)
        self.type = ApplicationTypes.Ruuvi
        self.timestamp = self.rx_time_ms_epoch
        self.apdu_content = dict()
        self.decode_time = None
        self.decode()

    def decode(self) -> None:
        """
            Counter:
                0x01 0x02 uint16 - Count from 0, increment every send period

            Temperature:
                0x02 0x04 int32 - unit: 0.01°C

            Humidity:
                0x03 0x04 uint32 - unit: (%RH) in Q24.10

            Pressure:
                0x04 0x04 uint32 - unit: (hPa) in Q24.8


            Payload example:
                01 02
                    b0 43

                02 04
                    61 09 00 00

                03 04
                    ad 3f 00 00

                04 04
                    9f 56 95 00

                05 04
                    00 00 00 00

                06 04
                    00 00 00 00

                07 04
                    00 00 00 00

        """

        self.decode_time = datetime.datetime.utcnow().isoformat("T")

        s_header = struct.Struct("<B B")

        _start = 0
        _end = 0

        try:
            while True:

                # grab header
                _start = _end
                _end = _start + s_header.size

                if _end > self.data_size:
                    break

                tlv_header = s_header.unpack(self.data_payload[_start:_end])

                # switch on type and unpack
                tlv_id = int(tlv_header[0])
                tlv_name = self.TYPES[tlv_id]["name"]
                tlv_field_format = struct.Struct(self.TYPES[tlv_id]["format"])

                _start = _end
                _end = _start + tlv_field_format.size

                tlv_value = tlv_field_format.unpack(
                    self.data_payload[_start:_end]
                )[0]

                self.apdu_content[tlv_name] = (
                    tlv_value * self.TYPES[tlv_id]["unit"]
                )
                self.apdu_content["{}.raw".format(tlv_name)] = tlv_value

        except KeyError:
            raise

        if self.data_payload:
            self.data_payload = self.data_payload.hex()

    def serialize(self):

        self.serialization = super().serialize()

        try:
            for key in self.apdu_content:
                if ".raw" not in key:
                    self.serialization[key] = self.apdu_content[key]
        except KeyError:
            pass

        return self.serialization
