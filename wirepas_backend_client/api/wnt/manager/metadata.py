"""
    Metadata
    ===========

    .. Copyright:
        Copyright 2019 Wirepas Ltd under Apache License, Version 2.0.
        See file LICENSE for full license details.

"""

from wirepas_messaging.wnt.ws_api import ApplicationConfigurationMessages
from wirepas_messaging.wnt.ws_api import AreaMessages
from wirepas_messaging.wnt.ws_api import BuildingMessages
from wirepas_messaging.wnt.ws_api import FloorPlanMessages
from wirepas_messaging.wnt.ws_api import NetworkMessages
from wirepas_messaging.wnt.ws_api import NodeMessages

from .manager import Manager
from ..connectors import WNTSocket


class MetadataManager(Manager):
    """
    MetadataManager

    This class handles the metadata connection and defines the runtime
    behaviour associated with the metadata.

    """

    def __init__(
        self,
        hostname,
        protocol_version,
        port=None,
        name="Medatada",
        logger=None,
        **kwargs
    ):

        super(MetadataManager, self).__init__(
            name=name,
            hostname=hostname,
            port=port or WNTSocket.METADATA_PORT,
            on_open=self.on_open,
            logger=logger,
            kwargs=kwargs,
        )

        self.messages = dict()
        self.messages["building"] = BuildingMessages(
            self.logger, protocol_version
        )
        self.messages["application"] = ApplicationConfigurationMessages(
            self.logger, protocol_version
        )
        self.messages["area"] = AreaMessages(self.logger, protocol_version)
        self.messages["floorplan"] = FloorPlanMessages(
            self.logger, protocol_version
        )
        self.messages["building"] = BuildingMessages(
            self.logger, protocol_version
        )
        self.messages["network"] = NetworkMessages(
            self.logger, protocol_version
        )
        self.messages["node"] = NodeMessages(self.logger, protocol_version)

    def set_session(self):
        for stub in self.messages:
            self.messages[stub].session_id = self.session_id

    def on_open(self, websocket) -> None:
        """Websocket callback when the authentication websocket has been opened

        Args:
            websocket (Websocket): communication socket
        """
        super().on_open(websocket)
        self.wait_for_session()
        self.set_session()

    def __getattr__(self, item):
        """ Returns the message builder object """
        return self.messages[item]
