"""
    Generic
    =======

    Contains a generic interface to handle network to object translations.

    .. Copyright:
        Wirepas Oy licensed under Apache License, Version 2.0.
        See file LICENSE for full license details.
"""

import sys
import json
import enum
import struct
import binascii
import datetime
import logging

import wirepas_messaging
from .types import ApplicationTypes


class GenericMessage(wirepas_messaging.gateway.api.ReceivedDataEvent):
    """
    Generic Message server as a simple packet abstraction

    Attributes:
        type (int): identifies the contents of the message (ApplicationTypes)

    """

    def __init__(self, *args, **kwargs):
        super(GenericMessage, self).__init__(*args, **kwargs)
        self.type = ApplicationTypes.GenericMessage

        self.sent_at = datetime.datetime.utcfromtimestamp(
            self.rx_time_ms_epoch / 1e3
        )

        self.received_at = datetime.datetime.utcnow()
        self.serialization = None

        self.transport_delay = (
            self.received_at - self.sent_at
        ).total_seconds()

    @classmethod
    def from_bus(cls, d):
        """ Translates a bus message into a message object """
        if isinstance(d, dict):
            return cls.from_dict(d)
        else:
            return cls.from_proto(d)

    @classmethod
    def from_dict(cls, d: dict):
        """ Translates a dictionary a message object """
        obj = cls(**d)
        return obj

    @classmethod
    def from_proto(cls, proto):
        """ Translates a protocol buffer into a message object """
        obj = cls.from_payload(proto)
        return obj

    def decode(self):
        """ Implement your own message decoding """
        raise NotImplementedError

    @staticmethod
    def map_list_to_dict(apdu_names, apdu_values):
        apdu = dict()
        j = 0
        for i in apdu_names:
            try:
                apdu[i] = apdu_values[j]
            except IndexError:
                # Detected more apdu_names than apdu_values.
                # By ignoring this, accept optional fields at end of message.
                break
            j += 1
        return apdu

    @staticmethod
    def chunker(seq, size):
        """
            Splits a sequence in multiple parts

            Args:
                seq ([]) : an array
                size (int) : length of each array part

            Returns:
                array ([]) : a chunk of SEQ with given SIZE
        """
        return (seq[pos : pos + size] for pos in range(0, len(seq), size))

    @staticmethod
    def decode_hex_str(hexstr):
        """
            Converts a hex string with spaces and 0x handles to bytes
        """
        hexstr = hexstr.replace("0x", "")
        hexstr = hexstr.replace(" ", "").strip(" ")
        payload = bytes.fromhex(hexstr)
        return payload

    def _serialize_payload(self):
        try:
            return self.data_payload.hex()
        except:
            return None

    def serialize(self):

        self.serialization = {
            "gw_id": self.gw_id,
            "sink_id": self.sink_id,
            "event_id": str(self.event_id),
            "rx_time_ms_epoch": self.rx_time_ms_epoch,
            "source_address": self.source_address,
            "destination_address": self.destination_address,
            "source_endpoint": self.source_endpoint,
            "destination_endpoint": self.destination_endpoint,
            "travel_time_ms": self.travel_time_ms,
            "sent_at": self.sent_at.isoformat("T"),
            "received_at": self.received_at.isoformat("T"),
            "qos": self.qos,
            "data_payload": self._serialize_payload(),
            "data_size": self.data_size,
            "hop_count": self.hop_count,
        }

        return self.serialization

    def __str__(self):
        """ returns the inner dict when printed """
        return str(self.serialize())
