"""
    CSAP Attributes
    ===============

    This file contains the CSAP attributes
    that are required to interface with the Wirepas Mesh
    over the remote API.

"""

from .attributes import Attribute


class AttributeCSAP(Attribute):
    def __init__(self, **kwargs):
        super().__init__(service_class="CSAP", **kwargs)


class NodeAddress(AttributeCSAP):
    def __init__(self, value):
        super().__init__(identifier=1, value=value, field_format="<I")


class NetworkAddress(AttributeCSAP):
    def __init__(self, value):
        super().__init__(identifier=2, value=value, field_format="<BBB")


class NetworkChannel(AttributeCSAP):
    def __init__(self, value):
        super().__init__(identifier=3, value=value, field_format="<B")


class NodeRole(AttributeCSAP):
    def __init__(self, value):
        super().__init__(identifier=4, value=value, field_format="<B")


class MTU(AttributeCSAP):
    def __init__(self, value):
        super().__init__(identifier=5, value=value, field_format="<B")


class PDUBufferSize(AttributeCSAP):
    def __init__(self, value):
        super().__init__(identifier=6, value=value, field_format="<B")


class ImageSequence(AttributeCSAP):
    def __init__(self, value):
        super().__init__(identifier=7, value=value, field_format="<B")


class MeshApiVersion(AttributeCSAP):
    def __init__(self, value):
        super().__init__(identifier=8, value=value, field_format="<BB")


class FirmwareMajor(AttributeCSAP):
    def __init__(self, value):
        super().__init__(identifier=9, value=value, field_format="<BB")


class FirmwareMinor(AttributeCSAP):
    def __init__(self, value):
        super().__init__(identifier=10, value=value, field_format="<BB")


class FirmwareMaintenance(AttributeCSAP):
    def __init__(self, value):
        super().__init__(identifier=11, value=value, field_format="<BB")


class FirmwareDevelopment(AttributeCSAP):
    def __init__(self, value):
        super().__init__(identifier=12, value=value, field_format="<BB")


class CipherKey(AttributeCSAP):
    def __init__(self, value):
        super().__init__(identifier=13, value=value, field_format="<16s")


class AuthenticationKey(AttributeCSAP):
    def __init__(self, value):
        super().__init__(identifier=14, value=value, field_format="<16s")


class ChannelLimits(AttributeCSAP):
    def __init__(self, value):
        super().__init__(identifier=15, value=value, field_format="<H")


class AppConfigDataSize(AttributeCSAP):
    def __init__(self, value):
        super().__init__(identifier=16, value=value, field_format="<16s")


class HwMagic(AttributeCSAP):
    def __init__(self, value):
        super().__init__(identifier=17, value=value, field_format="<16")


class StackProfile(AttributeCSAP):
    def __init__(self, value):
        super().__init__(identifier=18, value=value, field_format="<16")


class OfflineScan(AttributeCSAP):
    def __init__(self, value):
        super().__init__(identifier=20, value=value, field_format="<16")


class ChannelMap(AttributeCSAP):
    def __init__(self, value):
        super().__init__(identifier=21, value=value, field_format="<32")


class FeatureLockBits(AttributeCSAP):
    def __init__(self, value):
        super().__init__(identifier=22, value=value, field_format="<32")


class FeatureLockKey(AttributeCSAP):
    def __init__(self, value):
        super().__init__(identifier=23, value=value, field_format="<16s")
