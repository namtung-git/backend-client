"""
    Realtime
    ========

    .. Copyright:
        Copyright 2019 Wirepas Ltd under Apache License, Version 2.0.
        See file LICENSE for full license details.

"""

import json

import wirepas_messaging.wnt as wnt_proto
from wirepas_messaging.wnt.ws_api import RealtimeSituationMessages

from .manager import Manager
from ..connectors import WNTSocket


class RealtimeManager(Manager):
    """
    RealtimeManager

    This class handles the connection and messages on the realtime
    websocket.

    The realtime websocket offers realtime data about the status of the
    mesh and devices.

    """

    def __init__(
        self,
        hostname,
        protocol_version,
        port=None,
        name="Realtime",
        logger=None,
        **kwargs
    ):

        super(RealtimeManager, self).__init__(
            name=name,
            hostname=hostname,
            port=port or WNTSocket.REALTIME_SITUATION_PORT,
            on_message=self.on_message,
            on_open=self.on_open,
            logger=logger,
        )

        self.messages = RealtimeSituationMessages(
            self.logger, protocol_version
        )

    def on_open(self, websocket) -> None:
        """
        Websocket callback when the authentication websocket has been opened

        Args:
            websocket (Websocket): communication socket
        """
        super().on_open(websocket)
        self.wait_for_session()
        self.socket.send(
            json.dumps(
                self.messages.message_realtime_situation_login(self.session_id)
            )
        )

    def on_message(self, websocket, message) -> None:
        """
        Websocket callback when a new authentication message arrives

        Args:
            websocket (Websocket): communication socket
            message (str): received message
        """

        if self._is_ready.is_set():
            proto_message = wnt_proto.Message()
            try:
                proto_message.ParseFromString(message)
            except TypeError:
                message = json.loads(message)
                if message["result"] != 1:
                    raise ValueError("Could not login")

            self._write(proto_message)
        else:
            if self.messages.parse_realtime_situation_login(
                json.loads(message)
            ):
                super().on_open(websocket)
            else:
                raise ValueError("Could not log in to realtime endpoint")
