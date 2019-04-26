"""
    Positioning
    ===========

    Contains helpers to translate network data from positioning tags

    .. Copyright:
        Wirepas Oy licensed under Apache License, Version 2.0.
        See file LICENSE for full license details.
"""

import collections
import binascii
import datetime
import logging
import struct
import json
import time
import math

from .types import ApplicationTypes
from .generic import GenericMessage

from .. import tools


class PositioningMessage(GenericMessage):
    """
    PositioningMessage

    Represents a message sent by advertiser devices.

    Attributes:
        SOURCE_EP (int): Positioning source endpoint
        DESTINATION_EP (int): Positioning destination endpoint
        MESSAGE_COUNTER (int): Number of messages decoded so far (by this instance)
    """

    SOURCE_EP = 238
    DESTINATION_EP = 238
    MESSAGE_COUNTER = 0

    def __init__(self, *args, **kwargs) -> "PositioningMessage":

        super(PositioningMessage, self).__init__(*args, **kwargs)

        self.timestamp = self.rx_time_ms_epoch
        self.apdu_content = dict()
        self.decode_time = None
        self.decode()

    def decode(self) -> None:
        """ Decodes the APDU content base on the application """

        self.decode_time = datetime.datetime.utcnow().isoformat("T")

        if isinstance(self.data_payload, str):
            self.data_payload = bytes(self.data_payload, "utf8")

        format_header = struct.Struct("<H B B")
        format_meas = struct.Struct("<B B B B")

        # get the first 4 bytes
        header = format_header.unpack(self.data_payload[0:4])
        body = self.data_payload[4:]
        sequence = header[0]
        msg_type = header[1]
        payload_len = header[2]

        if len(body) % 4:
            self.logger.error("invalid payload {0}".format(len(body) / 4))
            return None

        measurements = list()
        for chunk in self.chunker(body, format_meas.size):
            if len(body) < 4:
                continue
            values = format_meas.unpack(chunk)

            addr = 0
            addr = values[0]
            addr = addr | (values[1] << 8)
            addr = addr | (values[2] << 16)
            rss = values[-1] * -0.5

            measurements.append(dict(address=addr, rss=rss))

        self.apdu_content = dict(
            sequence=sequence,
            type=msg_type,
            length=payload_len,
            nb_measurements=len(measurements),
            measurements=measurements,
        )

        if self.data_payload:
            self.data_payload = self.data_payload.hex()

    def serialize(self):
        """ Extends the packet serilization """

        self.serialization = super().serialize()

        for meas in self.apdu_content["measurements"]:
            self.serialization[str(meas["address"])] = meas["rss"]

        return self.serialization
