"""
    MSAP Attributes
    ===============

    This file contains the MSAP attributes
    that are required to interface with the Wirepas Mesh
    over the remote API.

"""

from .attributes import Attribute


class AttributeMSAP(Attribute):
    def __init__(self, **kwargs):
        super().__init__(service_class="MSAP", **kwargs)


class StackStatus(AttributeMSAP):
    def __init__(self, value):
        super().__init__(identifier=1, value=value, field_format="<HB")


class PDUBufferUsage(AttributeMSAP):
    def __init__(self, value):
        super().__init__(identifier=2, value=value, field_format="<HB")


class PDUBufferCapacity(AttributeMSAP):
    def __init__(self, value):
        super().__init__(identifier=3, value=value, field_format="<HB")


class Reserved(AttributeMSAP):
    def __init__(self, value):
        super().__init__(identifier=4, value=value, field_format="<HB")


class Energy(AttributeMSAP):
    def __init__(self, value):
        super().__init__(identifier=5, value=value, field_format="<HB")


class Autostart(AttributeMSAP):
    def __init__(self, value):
        super().__init__(identifier=6, value=value, field_format="<HB")


class RouteCount(AttributeMSAP):
    def __init__(self, value):
        super().__init__(identifier=7, value=value, field_format="<HB")


class SystemTime(AttributeMSAP):
    def __init__(self, value):
        super().__init__(identifier=8, value=value, field_format="<HI")


class AccessCycleRange(AttributeMSAP):
    _valid_ranges = [0, 2000, 4000, 8000]

    def __init__(self, value: int):

        if value not in self._valid_ranges:
            raise ValueError("Supported values are: 2000, 4000, or 8000")

        super().__init__(identifier=9, value=value, field_format="<HI")

    @property
    def valid_ranges(self):
        return self._valid_ranges


class AccessCycleLimits(AttributeMSAP):
    def __init__(self, value):
        super().__init__(identifier=10, value=value, field_format="<HI")


class CurrentAccessCycle(AttributeMSAP):
    def __init__(self, value):
        super().__init__(identifier=11, value=value, field_format="<HH")


class ImageBlockMax(AttributeMSAP):
    def __init__(self, value):
        super().__init__(identifier=12, value=value, field_format="<HB")


class MulticastGroups(AttributeMSAP):
    def __init__(self, value):
        super().__init__(identifier=13, value=value, field_format="<HB")
