"""
    Interface
    =========

    .. Copyright:
        Copyright 2019 Wirepas Ltd under Apache License, Version 2.0.
        See file LICENSE for full license details.
"""

from .decoders import (
    AdvertiserMessage,
    BootDiagnosticsMessage,
    DiagnosticsMessage,
    GenericMessage,
    NeighborDiagnosticsMessage,
    NodeDiagnosticsMessage,
    PositioningMessage,
    RuuviMessage,
    TestNWMessage,
    TrafficDiagnosticsMessage,
)
from .types import ApplicationTypes


class MessageManager(object):
    """
    MessageManager

    Interface that contains the source and destination endpoint
    mapping to a specific message decoder.

    Attributes:

    _message_type (dict): maps the decoder name to an internal message type

    _endpoint (dict): dictionary with source endpoint as key. Each key
                          contains a dictionary as a value. The value's
                          dictionary key is the destination endpoint.


    """

    _message_type = dict()

    for msg in ApplicationTypes:
        _message_type[msg.name] = msg.value

    _endpoint = dict()
    _endpoint[GenericMessage.source_endpoint] = {
        GenericMessage.destination_endpoint: GenericMessage
    }
    _endpoint[RuuviMessage.source_endpoint] = {
        RuuviMessage.destination_endpoint: RuuviMessage
    }
    _endpoint[TestNWMessage.source_endpoint] = {
        TestNWMessage.destination_endpoint: TestNWMessage
    }
    _endpoint[AdvertiserMessage.source_endpoint] = {
        AdvertiserMessage.destination_endpoint: AdvertiserMessage
    }
    _endpoint[PositioningMessage.source_endpoint] = {
        PositioningMessage.destination_endpoint: PositioningMessage
    }
    _endpoint[DiagnosticsMessage.source_endpoint] = {
        DiagnosticsMessage.destination_endpoint: DiagnosticsMessage
    }
    _endpoint[TrafficDiagnosticsMessage.source_endpoint] = {
        TrafficDiagnosticsMessage.destination_endpoint: TrafficDiagnosticsMessage
    }
    _endpoint[NeighborDiagnosticsMessage.source_endpoint] = {
        NeighborDiagnosticsMessage.destination_endpoint: NeighborDiagnosticsMessage
    }
    _endpoint[NodeDiagnosticsMessage.source_endpoint] = {
        NodeDiagnosticsMessage.destination_endpoint: NodeDiagnosticsMessage
    }
    _endpoint[BootDiagnosticsMessage.source_endpoint] = {
        BootDiagnosticsMessage.destination_endpoint: BootDiagnosticsMessage
    }

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
