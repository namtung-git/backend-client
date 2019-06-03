from .types import ApplicationTypes
from .generic import GenericMessage
from .advertiser import AdvertiserMessage
from .bootdiagnostics import BootDiagnosticsMessage
from .neighbordiagnostics import NeighborDiagnosticsMessage
from .nodediagnostics import NodeDiagnosticsMessage
from .testnw import TestNWMessage
from .trafficdiagnostics import TrafficDiagnosticsMessage
from .ruuvi import RuuviMessage
from .positioning import PositioningMessage
from .diagnostics import Diagnostics


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
    def type(name):
        try:
            return MessageManager._message_type[name.lower()]
        except KeyError:
            return GenericMessage

    @staticmethod
    def map(source_endpoint=0, destination_endpoint=0):
        try:
            return MessageManager._endpoint[int(source_endpoint)][
                int(destination_endpoint)
            ]
        except KeyError:
            return GenericMessage
        except ValueError:
            return GenericMessage
