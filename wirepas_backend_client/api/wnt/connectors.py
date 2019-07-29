"""
    Sock
    ====
    .. Copyright:
        Copyright 2019 Wirepas Ltd under Apache License, Version 2.0.
        See file LICENSE for full license details.

"""
import logging
import ssl
import threading

import websocket


class WNTSocket(object):
    """
    WNTSocket

    This class handles websocket connections to WNT backend
    """

    PROTOCOL = "wss"
    AUTHENTICATION_PORT = 8813
    METADATA_PORT = 8812
    REALTIME_SITUATION_PORT = 8811

    def __init__(
        self,
        hostname: str,
        port: int,
        on_open=None,
        on_message=None,
        on_error=None,
        on_close=None,
        tracing=True,
        tx_queue=None,
        rx_queue=None,
        logger=None,
    ):

        super(WNTSocket, self).__init__()

        self.logger = logger or logging.getLogger(__name__)

        self.hostname = hostname
        self.port = port
        self.on_open = on_open
        self.on_message = on_message
        self.on_error = on_error
        self.on_close = on_close
        self.tracing = tracing

        self.url = "{0}://{1}:{2}".format(
            self.PROTOCOL, self.hostname, self.port
        )
        self._thread = None
        self._socket = None

    @property
    def socket(self):
        """ Returns the socket object """
        return self._socket

    def connect(self, url, with_trace=True) -> websocket.WebSocketApp:
        """ Connect establishes the websocket connection"""

        websocket.enableTrace(with_trace)
        self._socket = websocket.WebSocketApp(
            url,
            on_open=self.on_open,
            on_message=self.on_message,
            on_error=self.on_error,
            on_close=self.on_close,
        )
        self._socket.keep_running = True

    def start(self, daemon=True, sslopt=None, **kwargs):
        """
        Start launches a thread for the websocket connection.

        Tracing for the websocket connection must be set during the
        objects initialization.

        Args:
            daemon (bool): should the thread be tied to its parent
            sslopt (dict): dictionary with TLS options
        """

        self.connect(url=self.url, with_trace=self.tracing)

        if sslopt is None:
            sslopt = dict(cert_reqs=ssl.CERT_NONE, check_hostname=False)

        self._thread = threading.Thread(
            target=self.run, kwargs=dict(sslopt=sslopt)
        )
        self._thread.socket = self._socket
        self._thread.daemon = daemon
        self._thread.start()

    def send(self, message: str) -> None:
        """
        Sends a message over the websocket

        Args:
            message (str): a serialized message
        """
        self._socket.send(message)

    def stop(self):
        """Requests the websocket thread to stop"""
        self._socket.keep_running = False

    def run(self, sslopt=None):
        """Starts the websocket's thread loop"""
        self._socket.run_forever(sslopt=sslopt)
