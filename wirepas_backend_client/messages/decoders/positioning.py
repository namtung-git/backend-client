"""
    Positioning
    ===========

    Contains helpers to translate network data from positioning tags

    .. Copyright:
        Copyright 2019 Wirepas Ltd under Apache License, Version 2.0.
        See file LICENSE for full license details.
"""

import struct

from .generic import GenericMessage
from ..types import ApplicationTypes


class PositioningMessage(GenericMessage):
    """
    PositioningMessage

    Represents a message sent by the positioning application.
    """

    source_endpoint = 238
    destination_endpoint = 238

    _apdu_format = "B B"
    _apdu_fields = {
        0x00: {
            "name": "POS_APP_MEAS_RSS_SR",
            "unit": -1 / 2,
            "format": "<B B B B",
            "type": "uint16",
            "id": 0x00,
        },
        0x01: {
            "name": "POS_APP_MEAS_RSS_HR",
            "unit": -1 / 2,
            "format": "<B B B B",
            "id": 0x01,
        },
        0x04: {
            "name": "POS_APP_MEAS_VOLTAGE",
            "unit": 1,
            "format": "<H",
            "id": 0x04,
        },
        0xF0: {
            "name": "POS_APP_MEAS_RSS_SR_ANCHOR",
            "unit": -1 / 2,
            "format": "<B B B B",
            "id": 0xF0,
        },
    }

    def __init__(self, *args, **kwargs) -> "PositioningMessage":

        self.data_payload = None
        self.apdu = None
        self.measurements = list()
        super(PositioningMessage, self).__init__(*args, **kwargs)
        self.type = ApplicationTypes.PositioningMessage
        self.decode()

    def decode(self) -> None:
        """ Decodes the APDU content base on the application """

        super().decode()

        apdu_sequence = struct.Struct("<H")
        sequence = apdu_sequence.unpack(
            self.data_payload[0 : apdu_sequence.size]
        )[0]

        # get the first 4 bytes
        self.tlv_decoder(
            self.data_payload[2:], self._apdu_format, self._apdu_fields
        )
        self.apdu = dict(
            sequence=sequence,
            nb_measurements=len(self.measurements),
            measurements=self.measurements,
        )

    def _tlv_value_decoder(
        self, apdu, tlv_fields, tlv_id, tlv_name, tlv_value
    ):

        if (
            tlv_id == 0x00  # POS_APP_MEAS_RSS_SR
            or tlv_id == 0x01  # POS_APP_MEAS_RSS_HR
            or tlv_id == 0xF0  # POS_APP_MEAS_RSS_SR_ANCHOR
        ):

            addr = 0
            addr = tlv_value[0]
            addr = addr | (tlv_value[1] << 8)
            addr = addr | (tlv_value[2] << 16)
            rss = tlv_value[3] * tlv_fields[tlv_id]["unit"]

            self.measurements.append(
                dict(name=tlv_name, address=addr, rss=rss, meas_type=tlv_id)
            )

        elif tlv_id == 0x04:
            self.measurements.append(
                dict(
                    name=tlv_name,
                    voltage=tlv_value[0] * tlv_fields[tlv_id]["unit"],
                    meas_type=tlv_id,
                )
            )
