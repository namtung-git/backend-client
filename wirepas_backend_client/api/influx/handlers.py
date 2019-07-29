"""
    Handlers
    ========

    .. Copyright:
        Copyright 2019 Wirepas Ltd under Apache License, Version 2.0.
        See file LICENSE for full license details.
"""


import logging
import multiprocessing
import queue

from .connectors import Influx
from ..stream import StreamObserver
from ...tools import Settings


class InfluxObserver(StreamObserver):
    """
    InfluxObserver monitors the internal queues and dumps events
    to the database
    """

    def __init__(
        self,
        influx_settings: Settings,
        start_signal: multiprocessing.Event,
        exit_signal: multiprocessing.Event,
        tx_queue: multiprocessing.Queue,
        rx_queue: multiprocessing.Queue,
        logger=None,
    ):
        super(InfluxObserver, self).__init__(
            start_signal=start_signal,
            exit_signal=exit_signal,
            tx_queue=tx_queue,
            rx_queue=rx_queue,
        )

        self.logger = logger or logging.getLogger(__name__)

        self.influx = Influx(
            username=influx_settings.username,
            password=influx_settings.password,
            hostname=influx_settings.hostname,
            port=influx_settings.port,
            database=influx_settings.database,
            logger=self.logger,
        )

        self.timeout = 1

    def on_data_received(self):
        """ Monitors inbound queuer for data to be written to Influx """
        raise NotImplementedError

    def on_query_received(self):
        """ Monitor inbound queue for queires to be sent to Influx """
        try:
            message = self.rx_queue.get(timeout=self.timeout, block=True)
        except queue.Empty:
            message = None

        self.logger.debug("Influx query: %s", message)
        result = self.influx.query(message)
        self.tx_queue.put(result)
        self.logger.debug("Influx result: %s", result)

    def run(self):
        """ Runs until asked to exit """
        try:
            self.influx.connect()
        except Exception as err:
            self.logger.error("error connecting to database %s", err)

        while not self.exit_signal.is_set():
            try:
                self.on_query_received()
            except EOFError:
                break
