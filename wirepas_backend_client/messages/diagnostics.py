"""
    Diagnostics
    ===========

    Contains helpers to translate network data from positioning tags

    .. Copyright:
        Copyright 2019 Wirepas Ltd.
        See LICENSE file for full license details.
"""

import datetime
import json

import cbor2
import pkg_resources

from .generic import GenericMessage


class Diagnostics(GenericMessage):
    """
    Diagnostic

    Represents a message sent by advertiser devices.

    Attributes:
        SOURCE_EP (int): Diagnostics v2 source endpoint
        DESTINATION_EP (int): Diagnostics v2 destination endpoint
        MESSAGE_COUNTER (int): Number of messages decoded so far (by this instance)
    """

    SOURCE_EP = 247
    DESTINATION_EP = 247
    MESSAGE_COUNTER = 0

    def __init__(self, *args, **kwargs) -> "Diagnostics":

        self.data_payload = None
        super(Diagnostics, self).__init__(*args, **kwargs)

        self.timestamp = self.rx_time_ms_epoch
        self.apdu_content = None
        self.serialization = dict()
        self.decode_time = None

        try:
            self.field_defintion = kwargs["field_definition"]
        except Exception:
            self.field_definition = str(
                pkg_resources.resource_filename(
                    "wirepas_backend_client", "messages/diag_cbor_id.json"
                )
            )

        self.CBOR_FIELDS = None
        self._load_fields(path=self.field_definition)
        self.decode()

    def _load_fields(self, path) -> None:
        # Read CBOR fields from JSON file
        with open(path) as data_file:
            self.CBOR_FIELDS = json.load(data_file)

    def decode(self) -> None:
        """ Decodes the APDU content base on the application """

        self.decode_time = datetime.datetime.utcnow().isoformat("T")

        try:
            self.apdu_content = cbor2.loads(self.data_payload)
        except cbor2.decoder.CBORDecodeError as err:
            self.logger.exception(err)

        if self.data_payload:
            self.data_payload = self.data_payload.hex()

    def serialize(self):
        """ Extends the packet serilization """

        self.serialization = super().serialize()

        if self.CBOR_FIELDS is not None and self.apdu_content is not None:
            try:
                for k, v in self.apdu_content.items():
                    try:
                        name = self.CBOR_FIELDS[str(k)]
                        self.serialization[name] = v

                    except KeyError:
                        self.logger.exception(
                            "Error serializing field  %s->%s", k, v
                        )
            except AttributeError:
                self.logger.exception(
                    "apdu_content=%s<-%s", self.apdu_content, self.data_payload
                )
            except Exception:
                self.logger.exception("unknown exception when serializing")

        if self.data_payload:
            self.serialization["payload"] = self.data_payload

        return self.serialization
