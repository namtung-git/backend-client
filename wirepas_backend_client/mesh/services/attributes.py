"""
    Mesh Attributes
    ===============

    Generic definition of mesh attributes

"""

import struct


class Attribute:
    """Attribute"""

    def __init__(
        self, identifier, value, field_format, service_class, **kwargs
    ):

        self._identifier = identifier
        self._value = value
        self._format = field_format
        self._service_class = service_class

    @property
    def name(self):
        return self.__class__.__name__

    @property
    def identifier(self):
        return self._identifier

    @property
    def value(self):
        return self._value

    @property
    def format(self):
        return self._format

    @property
    def service_class(self):
        return self._service_class

    @identifier.setter
    def identifier(self, identifier):
        self._identifier = identifier

    @value.setter
    def value(self, value):
        self._value = value

    @property
    def bytes(self):
        return bytearray(
            struct.pack(self._format, self.identifier, self._value)
        )

    def __str__(self):
        identity = f"{self.name}{self._identifier, self._value}"
        return identity
