"""
    BootDiagnostics
    ===============

    Contains helpers to translate network data into BootDiagnostics objects used
    within the library and test framework.

    .. Copyright:
        Copyright 2019 Wirepas Ltd under Apache License, Version 2.0.
        See file LICENSE for full license details.
"""
import struct

from .generic import GenericMessage
from .types import ApplicationTypes


class BootDiagnosticsMessage(GenericMessage):
    """
    BootDiagnosticsMessage

    Represents neighbor diagnostics report message sent by nodes.

    Message content:
        boot_count           uint8
        node_role            uint8
        sw_dev_version       uint8
        sw_maint_version     uint8
        sw_minor_version     uint8
        sw_major_version     uint8
        scratchpad_sequence  uint16
        hw_magic             uint16
        stack_profile        uint16
        otap_enabled         uint8
        boot_line_number     uint16
        file_hash            uint16
        stack_trace[0..2]    uint32
        cur_seq              uint16
    """

    def __init__(self, *args, **kwargs) -> "BootDiagnosticsMessage":

        self.data_payload = None
        super(BootDiagnosticsMessage, self).__init__(*args, **kwargs)
        self.type = ApplicationTypes.BootDiagnosticsMessage
        self.apdu = None
        self.decode()

    def decode(self):
        """ Perform the payload decoding """
        apdu_values = struct.unpack("<BBBBBBHHHBHHIIIH", self.data_payload)
        apdu_names = (
            "boot_count",
            "node_role",
            "sw_dev_version",
            "sw_maint_version",
            "sw_minor_version",
            "sw_major_version",
            "scratchpad_sequence",
            "hw_magic",
            "stack_profile",
            "otap_enabled",
            "boot_line_number",
            "file_hash",
            "stack_trace_0",
            "stack_trace_1",
            "stack_trace_2",
            "cur_seq",
        )
        self.apdu = self.map_list_to_dict(apdu_names, apdu_values)
