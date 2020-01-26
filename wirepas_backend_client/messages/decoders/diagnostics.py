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

    Represents a Wirepas diagnostics message.

    The diagnostic messages are encoded in cbor and
    this class requires a json file that contains the
    id to name mapping.

    In addition to that, any vector field should state
    its members in the same json file.

    """

    source_endpoint = 247
    destination_endpoint = 255
    _apdu_format = "cbor"
    _apdu_fields = None
    _version_field = ["firmware_app", "firmware_stack"]

    def __init__(self, *args, **kwargs) -> "DiagnosticsMessage":

        self.data_payload = None
        self.apdu = None
        self.cbor_contents = None
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
        """ Fetches definitions from a json file"""

        with open(path) as data_file:
            cbor_fields = json.load(data_file)

        return cbor_fields

    def decode(self) -> None:
        """ Decodes the APDU content base on the application """

        super().decode()
        self.cbor_contents = super().cbor_decode(self.data_payload)

        if self._apdu_fields is not None and self.cbor_contents is not None:
            try:
                for cbor_id, value in self.cbor_contents.items():
                    try:
                        name = self._apdu_fields[str(cbor_id)]
                    except KeyError:
                        unknown_field = {str(cbor_id): value}
                        if "unknown_field" not in self.apdu:
                            self.apdu["unknown_field"] = list()
                        self.apdu["unknown_field"].append(unknown_field)
                        self.logger.error("unknown cbor id %s", unknown_field)
                        continue

                    if name in self._apdu_fields:
                        vector = self._apdu_fields[name]
                        value = self.cbor_vector_to_dict(vector, value)

                    if name in self.apdu:
                        try:
                            self.apdu[name].append(value)
                        except AttributeError:
                            self.apdu[name] = [self.apdu[name], value]
                    else:
                        self.apdu[name] = value

                    # if it is version, convert
                    if name in self._version_field:
                        value = self.int_to_version(value)
                        self.apdu[name] = value

            except AttributeError:
                self.logger.exception(
                    "apdu_content=%s<-%s",
                    self.cbor_contents,
                    self.data_payload,
                )

    def cbor_vector_to_dict(self, vector: dict, values: list) -> dict:
        """
            This function takes a list of decoded cbor values and a
            dictionary containing the name and the index of such values.

            The input dictionary's key is used to index the input array
            whereas the input dictionary's value is used as the key for
            the output dictionary.
        """

        named_vector = dict()
        try:
            for idx, value in enumerate(values, start=0):
                name = vector[str(idx)]
                named_vector[name] = value
        except (KeyError, IndexError):
            message = f"Error decoding vector: vector={vector}, values={values}, idx={idx}"
            self.logger.exception(message)
            self.emit_message(self.logger.error, message)

        return named_vector

    @staticmethod
    def int_to_version(version_int):
        """
            This function takes the value from the apdu dictionary,
            and convert the value to the version number
            Args
                The version in int

            Returns
                The version with the correct format x.x.x.x
        """
        version_length = 4
        version_list = []
        version_final = version_int

        try:
            version_hex = version_int.to_bytes(version_length, byteorder="big")
            for i in range(0, version_length):
                version_list.append(ord(version_hex[i : i + 1]))
            version_final = ".".join([str(i) for i in version_list])
        except (IndexError, OverflowError):
            pass

        return version_final
