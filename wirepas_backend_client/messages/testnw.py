"""
    TestNW
    ======

    Contains helpers to translate network data into TestNW objects used
    within the library and test framework.

    .. Copyright:
        Copyright 2019 Wirepas Ltd under Apache License, Version 2.0.
        See file LICENSE for full license details.
"""

from .generic import GenericMessage
from .types import ApplicationTypes


class TestNWMessage(GenericMessage):
    """
    NodeDiagnosticsMessage

    Represents traffic diagnostics report message sent by nodes.

    Message content:
        row[0..]
            id       byte
                         test_data_id               4 lowest bits
                         id_ctrl                    4 highest bits
            size     byte
                         number_of_fields           6 lowest bits
                         bytes_per_field_minus_one  2 highest bits
            datafields[number_of_fields][bytes_per_field]
    """

    def __init__(self, *args, **kwargs) -> "TestNWMessage":

        self.data_payload = None
        super(TestNWMessage, self).__init__(*args, **kwargs)
        self.type = ApplicationTypes.TestNWMessage

        self.row_count = 0
        self.testdata_id = list()
        self.id_ctrl = list()
        self.number_of_fields = list()
        self.bytes_per_field = list()
        self.datafields = list()

        self.decode()

    def decode(self):
        """ Perform the payload decoding """

        apdu_offset = 0

        try:
            while apdu_offset < len(self.data_payload):
                if self.data_payload[apdu_offset] == 0:
                    break
                # Test data ID is the 4 lowest bits from the first byte
                self.testdata_id.append(self.data_payload[apdu_offset] & 0x0F)
                # ID_ctrl is the 4 highest bits of the first byte
                self.id_ctrl.append(self.data_payload[apdu_offset] & 0xF0)
                apdu_offset += 1
                # Number of fields is the lowest 6 bits of second byte
                self.number_of_fields.append(
                    self.data_payload[apdu_offset] & 0x3F
                )
                # Bytes per field is the two highest bits of second byte + 1
                self.bytes_per_field.append(
                    (self.data_payload[apdu_offset] >> 6) + 1
                )
                apdu_offset += 1

                self.datafields.append([])
                for _ in range(self.number_of_fields[self.row_count]):
                    value = 0
                    for j in range(self.bytes_per_field[self.row_count]):
                        value += self.data_payload[apdu_offset] << (j * 8)
                        apdu_offset += 1
                    self.datafields[self.row_count].append(value)
                self.row_count += 1
        except IndexError:
            print("A broken testnw apdu")
