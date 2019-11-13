"""
    Manager
    =======

    .. Copyright:
        Copyright 2019 Wirepas Ltd under Apache License, Version 2.0.
        See file LICENSE for full license details.

"""
import threading
import logging
import queue
import json

from ..connectors import WNTSocket


class Manager(object):
    """
    Manager

    Generic interface that implements the common logic for handling
    the websocket operations.

    Attributes:
        name (str): a logical name associated with the object
        hostname (str): the ip or dns of the instance
        port (int): the port where to seek connection to
        on_open (cb): a function to perform actions when the ws is opened
        on_message (cb): a fucntion to perform actions when a message is received
        on_error (cb): a function to handle error situations
        on_close (cb): a function to handle the closure of the websocket
        max_queue_length (int): maximum amount of message to store in the internal queues
        logger (logging): a logger where to write logging information

    """

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

        self.name = name
        self.hostname = hostname
        self.port = port
        self.session_id = None

        self._max_queue_length = max_queue_length
        self._rx_queue = queue.Queue()
        self._tx_queue = queue.Queue()

        self._is_ready = threading.Event()
        self._is_ready.clear()

        self.socket = WNTSocket(
            hostname=hostname,
            port=port,
            on_open=on_open or self.on_open,
            on_message=on_message or self.on_message,
            on_error=on_error or self.on_error,
            on_close=on_close or self.on_close,
            tx_queue=self._rx_queue,
            rx_queue=self._tx_queue,
            logger=logger,
        )

    def start(self):
        """ Start the websocket """
        self.socket.start()

    def close(self):
        """ Closes the websocket """
        self.socket.stop()

    def stop(self):
        """ Stops the websocket """
        self.close()

    @property
    def is_ready(self):
        return self._is_ready.is_set()

    def wait(self, timeout=10):
        return self._is_ready.wait(timeout)

    @property
    def tx_queue(self):
        """
        Returns the tx queue object

        The tx queue is where the thread dispatches messages to others.

        """
        return self._tx_queue

    @property
    def rx_queue(self):
        """
        Returns the rx queue object

        The rx queue is where the thread receives messages from others.

        """
        return self._rx_queue

    def _check_size(self, q):
        """ Ensure the queues contain up to _max_queue_length items"""
        try:
            if q.qsize() > self._max_queue_length:
                while q.empty():
                    pass
        except queue.Empty:
            pass

    def wait_for_session(self):
        """Waits for a session id in the incoming socket"""

        if self.session_id is None:
            while True:
                message = self._read(block=True, timeout=None)
                try:
                    self.session_id = message["session_id"]
                except KeyError:
                    continue
                break
            self._is_ready.set()

        return True

    def _read(self, block=False, timeout=None):
        """ Obtains messages from the internal queue """
        try:
            message = self._rx_queue.get(block=block, timeout=timeout)
        except queue.Empty:
            message = None
        return message

    def response(self, block=False, timeout=None):
        """ Obtains a response to the outgoing (put) request """
        try:
            message = self._tx_queue.get(block=block, timeout=timeout)
        except queue.Empty:
            message = None
        return message

    def request(self, message):
        """ Sends a message on the websocket and ensure the session id
        is the current one."""
        try:
            message["session_id"] = self.session_id
        except KeyError:
            pass

        self.socket.send(json.dumps(message))

    def _write(self, message):
        """ Sends messages to the tx queue """
        self._check_size(self._tx_queue)
        self._tx_queue.put(message, block=False)

    def on_open(self, _websocket):
        """ Generic function to print open status """
        self.logger.debug("%s socket open", self.name)

    def on_message(self, _websocket, message):
        """ Generic function to print message status """
        self.logger.debug("%s socket message: %s", self.name, message)
        self._write(message)

    def on_error(self, _websocket, error):
        """ Generic function to print error status """
        self.logger.debug("%s socket error: %s", self.name, error)

    def on_close(self, _websocket):
        """ Generic function to print close status """
        self.logger.error("%s socket close", self.name)
