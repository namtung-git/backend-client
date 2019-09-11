"""
    Interface
    =========

    .. Copyright:
        Copyright 2019 Wirepas Ltd under Apache License, Version 2.0.
        See file LICENSE for full license details.
"""

from .advertiser import AdvertiserMessage
from .bootdiagnostics import BootDiagnosticsMessage
from .diagnostics import Diagnostics
from .generic import GenericMessage
from .neighbordiagnostics import NeighborDiagnosticsMessage
from .nodediagnostics import NodeDiagnosticsMessage
from .positioning import PositioningMessage
from .ruuvi import RuuviMessage
from .testnw import TestNWMessage
from .trafficdiagnostics import TrafficDiagnosticsMessage
from .types import ApplicationTypes


class MessageManager(object):
    """
    MessageManager

    """

    _message_type = dict()

    for msg in ApplicationTypes:
        _message_type[msg.name] = msg.value

    _endpoint = dict()
    _endpoint[0] = {0: GenericMessage}
    _endpoint[11] = {11: RuuviMessage}
    _endpoint[100] = {100: TestNWMessage}
    _endpoint[200] = {200: AdvertiserMessage}
    _endpoint[238] = {238: PositioningMessage}
    _endpoint[247] = {247: Diagnostics}
    _endpoint[251] = {255: TrafficDiagnosticsMessage}
    _endpoint[252] = {255: NeighborDiagnosticsMessage}
    _endpoint[253] = {255: NodeDiagnosticsMessage}
    _endpoint[254] = {255: BootDiagnosticsMessage}

    def __init__(self):
        super(MessageManager, self).__init__()

    @staticmethod
    def type(name: str):
        """ Provides the message type """
        try:
            return MessageManager._message_type[name.lower()]
        except KeyError:
            return GenericMessage

    @staticmethod
    def map(source_endpoint: int = 0, destination_endpoint: int = 0):
        """
        Provides the constructor to build the decoder for the given
        source and destination endpoint pair
        """
        try:
            return MessageManager._endpoint[int(source_endpoint)][
                int(destination_endpoint)
            ]
        except KeyError:
            return GenericMessage
        except ValueError:
            return GenericMessage
