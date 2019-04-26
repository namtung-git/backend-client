"""
    Stream API
    ============

    Contains a generic class to handle IO streams.

    .. Copyright:
        Wirepas Oy licensed under Apache License, Version 2.0.
        See file LICENSE for full license details.
"""
import multiprocessing
import logging


class StreamObserver(object):
    """
    StreamObserver

    Simple interface class to store and manage the queue access

    Attributes:
        push_data: signal to start sending data to the tx_queue
        tx_queue: where to PUT packets
        rx_queue: where to GET packets
        logger: logging interface

    """

    def __init__(
        self,
        start_signal: multiprocessing.Event,
        tx_queue: multiprocessing.Queue,
        rx_queue: multiprocessing.Queue,
        exit_signal: multiprocessing.Event = None,
        logger: logging.Logger = None,
    ) -> "StreamObserver":
        super(StreamObserver, self).__init__()

        self.start_signal = start_signal
        self.exit_signal = exit_signal
        self.tx_queue = tx_queue
        self.rx_queue = rx_queue
        self.logger = logger

    def send_data(self, message: dict):
        pass

    def receive_data(self, message: dict, *args, **kwargs):
        if self.push_data.is_set() and message is not None:
            self.tx_queue.put(message)

    def generate_data_received_cb(self) -> callable:
        """ Returns a callback to process the incoming data """
        return self.receive

    def generate_data_send_cb(self) -> callable:
        """ Returns a callback to publish the outgoing data """
        return self.send_data
