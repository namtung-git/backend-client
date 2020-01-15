"""
    Advertiser
    ==========

    Contains helpers to translate network data into Advertiser objects used
    within the library and test framework.

    .. Copyright:
        Copyright 2019 Wirepas Ltd under Apache License, Version 2.0.
        See file LICENSE for full license details.
"""
# pylint: disable=locally-disabled, logging-format-interpolation


from .generic import GenericMessage
from ..types import ApplicationTypes
from ... import tools
import struct


class AdvertiserMessage(GenericMessage):
    """
    AdvertiserMessage

    Represents a message sent by advertiser devices.

    Attributes:
        _source_endpoint (int): Advertiser source endpoint
        _destination_endpoint (int): Advertiser destination endpoint
        _message_type_rss (int): APDU's RSS message type
        _message_type_otap (int): APDU's OTAP message type
        _message_counter (int): How many messages have been seen so far

        timestamp (int): Message received time
        type (int): Type of application message (ApplicationTypes)
        apdu["adv"] (dict): Dictionary containing the apdu contents
        apdu["adv_type"] (int): APDU type
        apdu["adv_reserved_field"] (int): APDU reserved field
        index (int): Message sequence number (as observed from the client side)
    """

    # pylint: disable=locally-disabled, too-many-instance-attributes

    source_endpoint = 200
    destination_endpoint = 200

    message_counter = 0
    message_type_rss = 2
    message_type_otap = 3

    def __init__(self, *args, **kwargs) -> "AdvertiserMessage":

        self.data_payload = None
        super(AdvertiserMessage, self).__init__(*args, **kwargs)
        self.timestamp = self.rx_time_ms_epoch
        self.type = ApplicationTypes.AdvertiserMessage

        self.apdu["adv"] = dict()
        self.apdu["adv_type"] = None
        self.apdu["adv_reserved_field"] = None
        self.index = None
        self.count()
        self.decode()

    def count(self):
        """ Increases the message counter """
        AdvertiserMessage.message_counter = (
            AdvertiserMessage.message_counter + 1
        )
        self.index = self.message_counter
        return self.index

    def decode(self) -> None:
        """
        Unpacks the advertiser data from the APDU to the inner
        apdu["adv"] dict.

        The advertiser APDU contains

        Header (2 bytes): Type | Reserved

        Measurements (N bytes):
            Addr: 3 bytes
            Value: 1 byte (eg, RSS or OTAP)
        """

        super().decode()

        s_header = struct.Struct("<B B")
        s_advertisement = struct.Struct("<B B B B")

        header = s_header.unpack(self.data_payload[0:2])

        self.apdu["adv_type"] = header[0]
        self.apdu["adv_reserved_field"] = header[1]

        # switch on type
        body = self.data_payload[2:]
        for chunk in tools.chunker(body, s_advertisement.size):
            if len(chunk) < 4:
                continue

            values = s_advertisement.unpack(chunk)

            address = values[0]
            address = address | (values[1] << 8)
            address = address | (values[2] << 16)

            value_field = values[-1]
            if self.apdu["adv_type"] == AdvertiserMessage.message_type_rss:
                rss = values[-1] / 2 - 127
                otap = None
                value_field = rss
            elif self.apdu["adv_type"] == AdvertiserMessage.message_type_otap:
                rss = None
                otap = values[-1]
                value_field = otap
            else:
                rss = None
                otap = None

            if address not in self.apdu["adv"]:
                self.apdu["adv"][address] = dict(
                    time=None, rss=list(), otap=list(), value=list()
                )

            self.apdu["adv"][address]["time"] = self.timestamp
            self.apdu["adv"][address]["rss"].append(rss)
            if otap:
                self.apdu["adv"][address]["otap"].append(otap)
            self.apdu["adv"][address]["value"].append(value_field)

    def _apdu_serialization(self):
        """ Standard apdu serialization. """
        if self.apdu:
            for field in self.apdu:
                if field in "advertisers":
                    self.serialization[field] = str(
                        sorted(list(self.apdu[field].keys()))
                    )
                    continue
                try:
                    self.serialization[field] = self.apdu[field]
                except KeyError:
                    pass

            self.serialization["index"] = self.index
