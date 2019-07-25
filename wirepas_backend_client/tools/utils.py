"""
    Utils
    =======

    Contains multipurpose utilities for serializing objects and obtaining
    arguments from the command line.

    .. Copyright:
        Wirepas Oy licensed under Apache License, Version 2.0.
        See file LICENSE for full license details.
"""

import json
import datetime
import threading
import google
import binascii


def deferred_thread(fn):
    """
    Decorator to handle a request on its own Thread
    to avoid blocking the calling Thread on I/O.
    It creates a new Thread but it shouldn't impact the performances
    as requests are not supposed to be really frequent (few per seconds)
    """

    def wrapper(*args, **kwargs):
        thread = threading.Thread(target=fn, args=args, kwargs=kwargs)
        thread.start()
        return thread

    return wrapper


class JsonSerializer(json.JSONEncoder):

    proto_as_json = False
    sort_keys = True
    indent = 4

    def __init__(self, proto_as_json: bool = False, **kwargs):
        super(JsonSerializer, self).__init__(**kwargs)
        self.proto_as_json = proto_as_json

    def default(self, obj) -> str:
        """Lookup table for serializing objects

        Pylint complains about the method signature, but this is the
        recommended way of implementing a custom JSON serialization as
        seen in:

        https://docs.python.org/3/library/json.html#json.JSONEncoder

        """

        if isinstance(obj, (datetime.datetime, datetime.date)):
            return obj.isoformat()

        if isinstance(obj, (bytearray, bytes)):
            return binascii.hexlify(obj)
        if isinstance(obj, set):
            return str(obj)

        if hasattr(obj, "DESCRIPTOR"):
            if self.proto_as_json is True:
                pstr = google.protobuf.json_format.MessageToJson(
                    obj, including_default_value_fields=True
                )
            else:
                pstr = google.protobuf.json_format.MessageToDict(
                    obj, including_default_value_fields=True
                )
            return pstr

        raise json.JSONEncoder.default(self, obj)

    @classmethod
    def serialize(cls, obj):
        return json.dumps(
            obj, cls=cls, sort_keys=cls.sort_keys, indent=cls.indent
        )


class ExitSignal(object):
    """Wrapper around and exit signal"""

    def __init__(self, signal=None):
        super(ExitSignal, self).__init__()

        if signal is None:
            signal = False

        self.signal = signal

    def is_set(self) -> bool:
        try:
            self.signal.is_set()
        except AttributeError:
            return self.signal

    def set(self) -> bool:
        try:
            self.signal.set()
        except AttributeError:
            return self.signal


def chunker(seq, size) -> list():
    """
        Splits a sequence in multiple parts

        Args:
            seq ([]) : an array
            size (int) : length of each array part

        Returns:
            array ([]) : a chunk of SEQ with given SIZE
    """
    return (seq[pos : pos + size] for pos in range(0, len(seq), size))
