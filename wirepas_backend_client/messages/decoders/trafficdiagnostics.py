"""
    TrafficDiagnostics
    ==================

    Contains helpers to translate network data into TrafficDiagnostics objects used
    within the library and test framework.

    .. Copyright:
        Copyright 2019 Wirepas Ltd under Apache License, Version 2.0.
        See file LICENSE for full license details.
"""
import struct

from .generic import GenericMessage
from ..types import ApplicationTypes


class TrafficDiagnosticsMessage(GenericMessage):
    """
    TrafficDiagnosticsMessage

    Represents traffic diagnostics report message sent by nodes.

    Message content:
        3.x: access_cycles              uint16
          4.0: cluster_members          uint8
          4.0: cluster_headnode_members uint8
        cluster_channel                 uint8
        channel_reliability             uint8
        rx_amount                       uint16
        tx_amount                       uint16
        aloha_rx_ratio                  uint8
        reserved_rx_success_ratio       uint8
        data_rx_ratio                   uint8
        rx_duplicate_ratio              uint8
        cca_success_ratio               uint8
        broadcast_ratio                 uint8
        failed_unicast_ratio            uint8
        max_reserved_slot_usage         uint8
        average_reserved_slot_usage     uint8
        max_aloha_slot_usage            uint8
    """

    source_endpoint = 251
    destination_endpoint = 255

    _apdu_format = "<HBBHHBBBBBBBBBB"
    _apdu_fields = (
        "access_cycles",
        "cluster_channel",
        "channel_reliability",
        "rx_amount",
        "tx_amount",
        "aloha_rx_ratio",
        "reserved_rx_success_ratio",
        "data_rx_ratio",
        "rx_duplicate_ratio",
        "cca_success_ratio",
        "broadcast_ratio",
        "failed_unicast_ratio",
        "max_reserved_slot_usage",
        "average_reserved_slot_usage",
        "max_aloha_slot_usage",
    )

    def __init__(self, *args, **kwargs) -> "TrafficDiagnosticsMessage":

        self.data_payload = None
        self.apdu = None

        super(TrafficDiagnosticsMessage, self).__init__(*args, **kwargs)
        self.type = ApplicationTypes.TrafficDiagnosticsMessage
        self.decode()

    def decode(self):
        """ Perform the payload decoding """

        super().decode()

        try:
            apdu_values = struct.unpack(self._apdu_format, self.data_payload)

            self.apdu = self.map_list_to_dict(self._apdu_fields, apdu_values)
            # 4.0 interpretation of message fields:
            self.apdu["cluster_members"] = self.apdu["access_cycles"] & 0xFF
            self.apdu["cluster_headnode_members"] = (
                self.apdu["access_cycles"] >> 8
            )

        except struct.error as error:
            self.logger.exception(
                "Could not decode boot diagnostics message: %s", error
            )
