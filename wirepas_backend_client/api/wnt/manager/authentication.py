"""
    Authentication
    ==============

    .. Copyright:
        Copyright 2019 Wirepas Ltd under Apache License, Version 2.0.
        See file LICENSE for full license details.

"""

import json

from wirepas_messaging.wnt.ws_api import AuthenticationMessages

from .manager import Manager
from ..connectors import WNTSocket


class AuthenticationManager(Manager):
    """
    AuthenticationManager

    This class handles operations done over the authentication
    websocket.

    """

    def __init__(
        self,
        hostname,
        protocol_version,
        username,
        password,
        port=None,
        name="Authentication",
        logger=None,
        **kwargs
    ):

        super(AuthenticationManager, self).__init__(
            name=name,
            hostname=hostname,
            port=port or WNTSocket.AUTHENTICATION_PORT,
            on_open=self.on_open,
            on_message=self.on_message,
            logger=logger,
        )

        self.username = username
        self.password = password
        self.messages = AuthenticationMessages(self.logger, protocol_version)

    def on_open(self, websocket) -> None:
        """
        Websocket callback when the authentication websocket has been opened

        Args:
            websocket (websocket): communication socket
        """
        super().on_open(websocket)
        self.socket.send(
            json.dumps(
                self.messages.message_login(self.username, self.password)
            )
        )

    def on_message(self, websocket, message) -> None:
        """
        Websocket callback when a new authentication message arrives

        Args:
            websocket (websocket): communication socket
            message (str): received message
        """
        self.messages.parse_login(json.loads(message))
        self.session_id = self.messages.session_id
        self._write(dict(session_id=self.session_id))
