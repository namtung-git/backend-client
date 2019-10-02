"""
    Diagnostics
    ===========

    Contains helpers to translate network data from positioning tags

    .. Copyright:
        Copyright 2019 Wirepas Ltd.
        See LICENSE file for full license details.
"""

import json
import pkg_resources

from .generic import GenericMessage
from ..types import ApplicationTypes

__default_ids = str(
    pkg_resources.resource_filename(
        "wirepas_backend_client.messages", "decoders/diagnostics.json"
    )
)


with open(__default_ids) as data_file:
    cbor_ids = json.load(data_file)


class DiagnosticsMessage(GenericMessage):
    """
    DiagnosticsMessage

    Represents a Wirepas diagnostics message (WIP).

    """

    _source_endpoint = 247
    _destination_endpoint = 247

    _apdu_format = "cbor"
    _apdu_fields = None

    def __init__(self, *args, **kwargs) -> "DiagnosticsMessage":

        self.data_payload = None
        self.apdu = None
        self.serialization = None
        super(DiagnosticsMessage, self).__init__(*args, **kwargs)

        self._apdu_fields = cbor_ids
        if "field_definition" in kwargs:
            self._field_definition = kwargs["field_definition"]
            self._apdu_fields = self.load_fields(self._field_definition)

        self.type = ApplicationTypes.DiagnosticsMessage
        self.decode()

    @staticmethod
    def load_fields(path) -> None:
        # Read CBOR fields from JSON file
        with open(path) as data_file:
            cbor_fields = json.load(data_file)

        return cbor_fields

    def decode(self) -> None:
        """ Decodes the APDU content base on the application """

        super().decode()
        contents = super().cbor_decode(self.data_payload)

        if self._apdu_fields is not None and contents is not None:
            try:
                for k, v in contents.items():
                    try:
                        name = self._apdu_fields[str(k)]
                        self.apdu[name] = v

                    except KeyError:
                        self.logger.exception(
                            "Error serializing field  %s->%s", k, v
                        )
            except AttributeError:
                self.logger.exception(
                    "apdu_content=%s<-%s", contents, self.data_payload
                )
            except Exception:
                self.logger.exception("unknown exception when serializing")

        return self.serialization
