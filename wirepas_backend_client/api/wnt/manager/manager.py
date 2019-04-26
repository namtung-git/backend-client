"""
    Manager
    =======

    .. Copyright:
        Wirepas Oy licensed under Apache License, Version 2.0.
        See file LICENSE for full license details.

"""

import logging
import queue
from ..sock import WNTSocket


class Manager(object):
    """docstring for Manager"""

    def __init__(
        self,
        name,
        hostname,
        port,
        on_open=None,
        on_message=None,
        on_error=None,
        on_close=None,
        max_queue_length=1000,
        logger=None,
        **kwargs
    ):
        super(Manager, self).__init__()

        self.logger = logger or logging.getLogger(__name__)
        self._rx_queue = queue.Queue()
        self._tx_queue = queue.Queue()

        self.name = name
        self.hostname = hostname
        self.port = port

        self.socket = WNTSocket(
            hostname=hostname,
            port=port,
            logger=logger,
            on_open=on_open or self.on_open,
            on_message=on_message or self.on_message,
            on_error=on_error or self.on_error,
            on_close=on_close or self.on_close,
            tx_queue=self._rx_queue,
            rx_queue=self._tx_queue,
        )

        self._max_queue_length = max_queue_length
        self.session_id = None

    def start(self):
        self.socket.start()

    def close(self):
        self.socket.stop()

    @property
    def tx_queue(self):
        return self._tx_queue

    @property
    def rx_queue(self):
        return self._rx_queue

    def _check_size(self, queue):
        # queue management
        try:
            if queue.qsize() > self._max_queue_length:
                while queue.empty():
                    pass
        except queue.Empty:
            pass

    def wait_for_session(self):
        """Waits for a session id in the incoming socket"""

        if self.session_id is None:
            while True:
                message = self.read(block=True, timeout=None)
                try:
                    self.session_id = message["session_id"]
                except KeyError:
                    continue
                break
        return True

    def read(self, block=False, timeout=None):
        try:
            message = self._rx_queue.get(block=block, timeout=timeout)
        except queue.Empty:
            message = None
        return message

    def write(self, message):
        self._check_size(self._tx_queue)
        self._tx_queue.put(message, block=False)

    def on_open(self, _websocket):
        self.logger.error("{} socket open".format(self.name))

    def on_message(self, _websocket, message):
        self.logger.error("{} socket message: {}".format(self.name, message))

    def on_error(self, _websocket, error):
        self.logger.error("{} socket error: {}".format(self.name, error))

    def on_close(self, _websocket):
        self.logger.error("{} socket close".format(self.name))
