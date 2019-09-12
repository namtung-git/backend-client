"""
    Generic
    =======

    Contains a generic interface to handle network to object translations.

    .. Copyright:
        Copyright 2019 Wirepas Ltd under Apache License, Version 2.0.
        See file LICENSE for full license details.
"""

import datetime
import logging

import wirepas_messaging

from .types import ApplicationTypes


class GenericMessage(wirepas_messaging.gateway.api.ReceivedDataEvent):
    """
    Generic Message serves as a simple packet abstraction.

    The base class is inherited from wirepas_messaging (ReceivedDataEvent).

    This class offers a few common attributes such as:

        rx_time (datetime): arrival time of the packet at the sink
        tx_time (datetime): departure time of the message from the node
        received_at (datetime): when the packet was received by the framework
        transport_delay (int): amount of seconds the packet traveled over the network
        serialization (str): representation of the packet for transport

    """

    def __init__(self, *args, **kwargs):
        super(GenericMessage, self).__init__(*args, **kwargs)

        self.type = ApplicationTypes.GenericMessage

        # ensure data size is correct
        if self.data_payload is None:
            self.data_size = 0
            self.data_payload = bytes()
        else:
            self.data_size = len(self.data_payload)
            if isinstance(self.data_payload, str):
                self.data_payload = bytes(self.data_payload, "utf8")

        self.rx_time = datetime.datetime.utcfromtimestamp(
            self.rx_time_ms_epoch / 1e3
        ) - datetime.timedelta(seconds=self.travel_time_ms / 1e3)

        self.tx_time = self.rx_time - datetime.timedelta(
            seconds=self.travel_time_ms / 1e3
        )
        self.received_at = datetime.datetime.utcnow()

        # localize to UTC
        self.rx_time = self.rx_time.replace(tzinfo=datetime.timezone.utc)
        self.tx_time = self.tx_time.replace(tzinfo=datetime.timezone.utc)
        self.received_at = self.received_at.replace(
            tzinfo=datetime.timezone.utc
        )

        self.transport_delay = (
            self.received_at - self.tx_time
        ).total_seconds()
        self.serialization = None

    @property
    def logger(self):
        """
        Retrieves the message_decoding logger.

        If you wish the messages to show debug information, please
        remember to configure the logging prior to this call.

        """
        return logging.getLogger("message_decoding")

    @classmethod
    def from_bus(cls, d):
        """ Translates a bus message into a message object """
        if isinstance(d, dict):
            return cls.from_dict(d)

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
    def map_list_to_dict(apdu_names: list, apdu_values: list):
        """
        Maps a list of apdu values and apdu names into a single dictionary.

        Args:
            apdu_name (list): list of apdu names
            apdu_values (list): list of apdu values

        """

        apdu = dict()
        value_index = 0

        for name in apdu_names:
            try:
                apdu[name] = apdu_values[value_index]
            except IndexError:
                # Detected more apdu_names than apdu_values.
                # By ignoring this, accept optional fields at end of message.
                break
            value_index += 1

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
        except AttributeError:
            return None

    def serialize(self):
        """ Provides a generic serialization of the message"""

        self.serialization = {
            "gw_id": self.gw_id,
            "sink_id": self.sink_id,
            "event_id": str(self.event_id),
            "rx_time": self.rx_time.isoformat("T"),
            "tx_time": self.tx_time.isoformat("T"),
            "source_address": self.source_address,
            "destination_address": self.destination_address,
            "source_endpoint": self.source_endpoint,
            "destination_endpoint": self.destination_endpoint,
            "travel_time_ms": self.travel_time_ms,
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
