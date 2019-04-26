"""
    Realtime
    ========

    .. Copyright:
        Wirepas Oy licensed under Apache License, Version 2.0.
        See file LICENSE for full license details.

"""

import json
import logging
import wirepas_messaging.wnt as wnt_proto
from wirepas_messaging.wnt import RealtimeSituationMessages

from ..sock import WNTSocket
from .manager import Manager


class RealtimeManager(Manager):
    """docstring for RealtimeManager"""

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

        self.logger = logger or logging.getLogger(__name__)
        self.session_id = None
        self._logged_in = None
        self.messages = RealtimeSituationMessages(
            self.logger, protocol_version
        )

    def on_open(self, websocket) -> None:
        """Websocket callback when the authentication websocket has been opened

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
        """Websocket callback when a new authentication message arrives

        Args:
            websocket (Websocket): communication socket
            message (str): received message
        """
        # super().on_message(websocket, message)
        if self._logged_in:
            proto_message = wnt_proto.Message()
            proto_message.ParseFromString(message)
            # self.send(proto_message)
            self.write(proto_message)
        else:
            if not self.messages.parse_realtime_situation_login(
                json.loads(message)
            ):
                raise ValueError("Could not log in to realtime endpoint")
            else:
                self._logged_in = True
                super().on_open(websocket)
