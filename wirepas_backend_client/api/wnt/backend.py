"""
    Backend
    =======

    .. Copyright:
        Wirepas Oy licensed under Apache License, Version 2.0.
        See file LICENSE for full license details.

"""

import queue
import logging
import datetime

from ...tools import Settings, JsonSerializer
from .manager import AuthenticationManager, RealtimeManager, MetadataManager


class WNTSettings(Settings):
    """WNT Settings"""

    def __init__(self, settings: Settings) -> "WNTSettings":

        super(WNTSettings, self).__init__(settings)

    def sanity(self) -> bool:
        """ Checks if connection parameters are valid """
        is_valid = (
            self.wnt_username is not None
            and self.wnt_password is not None
            and self.wnt_hostname is not None
        )

        return is_valid


class Backend(object):
    def __init__(
        self, settings, callback_queue=None, logger=None, **kwargs
    ) -> None:
        """
        Backend

        The Backend class aims to support a connection to a given WNT
        instance. It assumes default ports for the client websockets.

        """

        self.logger = logger or logging.getLogger(__name__)
        self.settings = settings
        self.session_id = None

        self.authentication = AuthenticationManager(
            hostname=self.settings.wnt_hostname,
            username=self.settings.wnt_username,
            password=self.settings.wnt_password,
            protocol_version=self.settings.wnt_protocol_version,
            logger=self.logger,
        )

        self.realtime = RealtimeManager(
            hostname=self.settings.wnt_hostname,
            protocol_version=self.settings.wnt_protocol_version,
            logger=self.logger,
        )

        self.metadata = MetadataManager(
            hostname=self.settings.wnt_hostname,
            protocol_version=self.settings.wnt_protocol_version,
            logger=self.logger,
        )

    def login(self) -> None:
        """ login retrieves a session id from the authentication ws.

        If the acquisition is successful, the token is stored under
        the objects's session_id attribute.

        """

        self.authentication.start()
        message = self.authentication.tx_queue.get(block=True)

        try:
            self.session_id = message["session_id"]
        except KeyError:
            raise

        self.realtime.rx_queue.put(dict(session_id=self.session_id))
        self.metadata.rx_queue.put(dict(session_id=self.session_id))

    def send_request(self) -> None:
        """Send request """
        pass

    def connect_all(self, exit_signal: bool) -> None:
        """
        connect_all logins with the server instance and starts the
        realtime and metadata websockets.

        It then prints all the messages sent by WNT.
        """
        self.login()

        self.realtime.start()
        self.metadata.start()

        while not exit_signal:
            try:
                message = self.realtime.tx_queue.get(block=True, timeout=10)
                if message:
                    self.logger.info(
                        "{utc} | {message}".format(
                            utc=datetime.datetime.utcnow().isoformat("T"),
                            message=JsonSerializer.serialize(message),
                        )
                    )
            except queue.Empty:
                pass

        self.close()

    def close(self):
        """ Terminates the websocket connections """
        self.metadata.stop()
        self.realtime.stop()
        self.authentication.stop()

    def run(self, exit_signal: bool) -> None:
        """ Defines the object's main loop """
        self.connect_all(exit_signal)


if __name__ == "__main__":

    print("Please use the package's entrypoint.")
