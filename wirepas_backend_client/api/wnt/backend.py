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

from ...tools import Settings, ParserHelper
from .manager import AuthenticationManager, RealtimeManager, MetadataManager


class Backend(object):
    def __init__(
        self, settings, callback_queue=None, logger=None, **kwargs
    ) -> None:
        """Initialization"""

        self.logger = logger or logging.getLogger(__name__)
        self.settings = settings

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

        self.authentication.start()
        message = self.authentication.tx_queue.get(block=True)

        try:
            self.session_id = message["session_id"]
        except KeyError:
            raise

        self.realtime.rx_queue.put(dict(session_id=self.session_id))
        self.metadata.rx_queue.put(dict(session_id=self.session_id))

    def send_request(self) -> None:
        """Send request"""
        pass

    def connect_all(self, exit_signal: bool) -> None:
        """Run method which starts and waits the communication thread(s)

        Returns:
            int: Process return code
        """
        self.login()

        self.realtime.start()
        self.metadata.start()

        while not exit_signal:
            try:
                message = self.realtime.tx_queue.get(block=True, timeout=10)
                if message:
                    print(
                        "<< new message @ {local} ({utc})".format(
                            local=datetime.datetime.now().isoformat(),
                            utc=datetime.datetime.utcnow().isoformat(),
                        )
                    )
                    print(message)
                    print("== EOM")
            except queue.Empty:
                pass

        self.close()

    def close(self):
        self.metadata.stop()
        self.realtime.stop()
        self.authentication.stop()

    def run(self, exit_signal: bool) -> None:
        self.connect_all(exit_signal)


if __name__ == "__main__":

    parse = ParserHelper(description="WNT backend client arguments")

    parse.add_file_settings()
    parse.add_wnt()

    settings = Settings(parse.arguments)
    print(settings)
    Backend(settings).run(False)
