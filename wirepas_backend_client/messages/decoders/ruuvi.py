"""
    Ruuvi
    =====

    Contains helpers to translate network data from Ruuvi devices

    .. Copyright:
        Copyright 2019 Wirepas Ltd. All Rights Reserved.
        See file LICENSE.txt for full license details.
"""

from .generic import GenericMessage
from ..types import ApplicationTypes


class RuuviMessage(GenericMessage):
    """
    RuuviMessage

    Represents a message sent by the Ruuvi application.
    """

    source_endpoint = 11
    destination_endpoint = 11

    _apdu_format = "tlv"
    _tlv_header = "<B B"
    _tlv_fields = {
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

    def __init__(self, *args, **kwargs) -> "RuuviMessage":

        self.data_payload = None
        self.apdu = dict()
        super(RuuviMessage, self).__init__(*args, **kwargs)
        self.type = ApplicationTypes.Ruuvi
        self._apdu_fields = self._tlv_fields
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

        super().decode()
        self.apdu = self.tlv_decoder(
            self.data_payload, self._tlv_header, self._tlv_fields
        )

    def _tlv_value_decoder(
        self, apdu, tlv_fields, tlv_id, tlv_name, tlv_value
    ):
        try:
            apdu[tlv_name] = tlv_value[0] * tlv_fields[tlv_id]["unit"]
        except KeyError:
            pass
        return apdu

    def _apdu_serialization(self):

        try:
            for key in self.apdu:
                if ".raw" not in key:
                    self.serialization[key] = self.apdu[key]
        except KeyError:
            pass

        return self.serialization
