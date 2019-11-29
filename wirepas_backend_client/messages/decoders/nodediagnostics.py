"""
    NodeDiagnostics
    ===============

    Contains helpers to translate network data into NodeDiagnostics objects used
    within the library and test framework.

    .. Copyright:
        Copyright 2019 Wirepas Ltd under Apache License, Version 2.0.
        See file LICENSE for full license details.
"""
import struct

from .generic import GenericMessage
from ..types import ApplicationTypes


class NodeDiagnosticsMessage(GenericMessage):
    """
    NodeDiagnosticsMessage

    Represents traffic diagnostics report message sent by nodes.

    Message content:
        access_cycle                  uint16
        role                          uint8
        voltage                       uint8
        max_buffer_usage              uint8
        average_buffer_usage          uint8
        mem_alloc_fails               uint8
        normal_priority_buf_delay     uint8
        high_priority_buf_delay       uint8
        network_scans                 uint8
        3.x: dl_delay_avg_0           uint16
          4.0: lltx_msg_w_ack         uint16
        3.x: dl_delay_min_0           uint16
          4.0: lltx_msg_unack         uint16
        3.x: dl_delay_max_0           uint16
          4.0  llrx_w_unack_ok        uint16
        3.x: dl_delay_samples_0       uint16
          4.0: llrx_ack_not_received  uint16
        3.x: dl_delay_avg_1           uint16
          4.0: lltx_cca_unack_fail    uint16
        3.x: dl_delay_min_1           uint16
          4.0: lltx_cca_w_ack_fail    uint16
        3.x: dl_delay_max_1           uint16
          4.0: llrx_w_ack_ok          uint16
        3.x: dl_delay_samples_1       uint16
          4.0: llrx_ack_otherreasons  uint16
        dropped_packets_0             uint8
        dropped_packets_1             uint8
        route_address                 uint24 (uint16, uint8)
        cost_info_next_hop_0          uint24 (uint16, uint8)
        cost_info_cost_0              uint8
        cost_info_link_quality_0      uint8
        3.x: cost_info_next_hop_1     uint24 (uint16, uint8)
        3.x: cost_info_cost_1         uint8
        3.x: cost_info_link_quality_1 uint8
          4.0: blacklistexceeded      uint40
        event_0                       uint8
        ...
        event_14                      uint8
        duty_cycle                    uint16
        current_antenna               uint8
        4.2: pending_ucast_cluster    uint8
        4.2: pending_ucast_members    uint8
        4.2: pending_bcast_le_members uint8
        4.2: pending_bcast_ll_members uint8
        4.2: pending_bcast_unack      uint8
        4.2: pending_expire_queue     uint8
        4.2: pending_bcast_next_hop   uint8
        4.2: pending_reroute_packets  uint8
    """

    source_endpoint = 253
    destination_endpoint = 255

    _GT_42 = 59

    _apdu_format = {
        ">=4.2": "<HBBBBBBBBHHHHHHHHBBHBHBBBHBBBBBBBBBBBBBBBBBBHBBBBBBBBB",
        "<=4.0": "<HBBBBBBBBHHHHHHHHBBHBHBBBHBBBBBBBBBBBBBBBBBBHB",
    }

    _apdu_fields = (
        "access_cycle",
        "role",
        "voltage",
        "max_buffer_usage",
        "average_buffer_usage",
        "mem_alloc_fails",
        "normal_priority_buf_delay",
        "high_priority_buf_delay",
        "network_scans",
        "dl_delay_avg_0",
        "dl_delay_min_0",
        "dl_delay_max_0",
        "dl_delay_samples_0",
        "dl_delay_avg_1",
        "dl_delay_min_1",
        "dl_delay_max_1",
        "dl_delay_samples_1",
        "dropped_packets_0",
        "dropped_packets_1",
        "route_address_lo",
        "route_address_hi",
        "cost_info_next_hop_0_lo",
        "cost_info_next_hop_0_hi",
        "cost_info_cost_0",
        "cost_info_link_quality_0",
        "cost_info_next_hop_1_lo",
        "cost_info_next_hop_1_hi",
        "cost_info_cost_1",
        "cost_info_link_quality_1",
        "events_0",
        "events_1",
        "events_2",
        "events_3",
        "events_4",
        "events_5",
        "events_6",
        "events_7",
        "events_8",
        "events_9",
        "events_10",
        "events_11",
        "events_12",
        "events_13",
        "events_14",
        "duty_cycle",
        "current_antenna",
        "pending_ucast_cluster",
        "pending_ucast_members",
        "pending_bcast_le_members",
        "pending_bcast_ll_members",
        "pending_bcast_unack",
        "pending_expire_queue",
        "pending_bcast_next_hop",
        "pending_reroute_packets",
    )

    def __init__(self, *args, **kwargs) -> "NodeDiagnosticsMessage":

        self.data_payload = None
        self.apdu = None

        super(NodeDiagnosticsMessage, self).__init__(*args, **kwargs)
        self.type = ApplicationTypes.NodeDiagnosticsMessage
        self.decode()

    def decode(self):
        """ Perform the payload decoding """
        super().decode()

        try:
            if self.data_size > self._GT_42:
                # Node Diagnostics with buffer statistics (4.2 and newer)
                apdu_values = struct.unpack(
                    self._apdu_format[">=4.2"], self.data_payload
                )
            else:
                # Node Diagnostics without buffer statistics (4.0 and older)
                apdu_values = struct.unpack(
                    self._apdu_format["<=4.0"], self.data_payload
                )

            self.apdu = self.map_list_to_dict(self._apdu_fields, apdu_values)

            self.apdu["voltage"] = float(self.apdu["voltage"]) / 100.0 + 2.0

            # Create 24bit fields from 16bit and 8bit parts.
            self.apdu["route_address"] = self.apdu["route_address_lo"] | (
                self.apdu["route_address_hi"] << 16
            )
            self.apdu["cost_info_next_hop_0"] = self.apdu[
                "cost_info_next_hop_0_lo"
            ] | (self.apdu["cost_info_next_hop_0_hi"] << 16)
            self.apdu["cost_info_next_hop_1"] = self.apdu[
                "cost_info_next_hop_1_lo"
            ] | (self.apdu["cost_info_next_hop_1_hi"] << 16)
            # 4.0 interpretation of message fields:
            self.apdu["lltx_msg_w_ack"] = self.apdu["dl_delay_avg_0"]
            self.apdu["lltx_msg_unack"] = self.apdu["dl_delay_min_0"]
            self.apdu["llrx_w_unack_ok"] = self.apdu["dl_delay_max_0"]
            self.apdu["llrx_ack_not_received"] = self.apdu[
                "dl_delay_samples_0"
            ]
            self.apdu["lltx_cca_unack_fail"] = self.apdu["dl_delay_avg_1"]
            self.apdu["lltx_cca_w_ack_fail"] = self.apdu["dl_delay_min_1"]
            self.apdu["llrx_w_ack_ok"] = self.apdu["dl_delay_max_1"]
            self.apdu["llrx_ack_otherreasons"] = self.apdu[
                "dl_delay_samples_1"
            ]
            self.apdu["blacklistexceeded"] = (
                self.apdu["cost_info_next_hop_1"]
                | (self.apdu["cost_info_cost_1"] << 24)
                | (self.apdu["cost_info_link_quality_1"] << 32)
            )

        except struct.error as error:
            self.logger.exception(
                "Could not decode boot diagnostics message: %s", error
            )
