"""
    Handlers
    =========

    Contains class to handle MySQL interaction

    .. Copyright:
        Copyright 2019 Wirepas Ltd under Apache License, Version 2.0.
        See file LICENSE for full license details.
"""
import os

try:
    import MySQLdb
except ImportError:
    pass

import logging
import multiprocessing
import queue
import time

from ..stream import StreamObserver

from wirepas_backend_client.messages import BootDiagnosticsMessage
from wirepas_backend_client.messages import NeighborDiagnosticsMessage
from wirepas_backend_client.messages import NodeDiagnosticsMessage
from wirepas_backend_client.messages import TestNWMessage
from wirepas_backend_client.messages import TrafficDiagnosticsMessage
from wirepas_backend_client.messages import DiagnosticsMessage
from wirepas_backend_client.tools import Settings

from .connectors import MySQL


class MySQLObserver(StreamObserver):
    """ MySQLObserver monitors the internal queues and dumps events to the database """

    def __init__(
        self,
        mysql_settings: Settings,
        start_signal: multiprocessing.Event,
        exit_signal: multiprocessing.Event,
        tx_queue: NodeDiagnosticsMessage = None,
        rx_queue: multiprocessing.Queue = None,
        parallel: bool = True,
        n_workers: int = 1,
        timeout: int = 10,
        logger=None,
    ) -> "MySQLObserver":
        super(MySQLObserver, self).__init__(
            start_signal=start_signal,
            exit_signal=exit_signal,
            tx_queue=tx_queue,
            rx_queue=rx_queue,
        )

        self.logger = logger or logging.getLogger(__name__)

        self.mysql = MySQL(
            username=mysql_settings.username,
            password=mysql_settings.password,
            hostname=mysql_settings.hostname,
            port=mysql_settings.port,
            database=mysql_settings.database,
            connection_timeout=mysql_settings.connection_timeout,
            logger=self.logger,
        )
        self.settings = mysql_settings
        self.timeout = timeout
        self.parallel = parallel
        self.n_workers = n_workers
        self.checkSum = 0
        self.first_message_processed = False

    def _map_message(self, mysql, message, incrementCounter: int):
        """ Inserts the message according to its type """

        ret: bool = True

        # This GW is sending integrity test data
        reliability_test_gw: str = "virtual-gw1"

        if self.first_message_processed is False:
            self.first_message_processed = True
            self.logger.info("MySQL processor received first message.")
            self.logger.info(
                "MySQL processor integrity test GW NAME is '{}".format(
                    reliability_test_gw
                )
            )

        if message.gw_id == reliability_test_gw:
            mysql.check_and_write_integrity_test_data(message)
        else:
            if (
                mysql.put_to_received_packets(message, incrementCounter)
                is True
            ):

                if isinstance(message, DiagnosticsMessage):
                    ret = mysql.put_diagnostics(message, incrementCounter)

                elif isinstance(message, TestNWMessage):
                    ret = mysql.put_testnw_measurements(
                        message, incrementCounter
                    )

                elif isinstance(message, BootDiagnosticsMessage):
                    ret = mysql.put_boot_diagnostics(message, incrementCounter)

                elif isinstance(message, NeighborDiagnosticsMessage):
                    ret = mysql.put_neighbor_diagnostics(
                        message, incrementCounter
                    )

                elif isinstance(message, NodeDiagnosticsMessage):
                    ret = mysql.put_node_diagnostics(message, incrementCounter)

                elif isinstance(message, TrafficDiagnosticsMessage):
                    ret = mysql.put_traffic_diagnostics(
                        message, incrementCounter
                    )

                if ret is False:
                    mysql.logger.warning("Data insertion error (2).")
            else:
                mysql.logger.warning("Data insertion error (1).")
                ret = False

    def ping_data_base(self, exit_signal, logger, mysql, pid) -> bool:
        ret: bool = False
        try:
            mysql.database.ping(True)
            ret = True
        except MySQLdb.OperationalError:
            logger.exception(
                "MySQL worker %s: connection restart failed.", pid
            )
            mysql.close()
            while not exit_signal.is_set():
                try:
                    mysql.connect(table_creation=False)
                    logger.exception(
                        "MySQL worker %s: connection restart failed.", pid
                    )
                    break
                except MySQLdb.Error:
                    logger.exception(
                        "MySQL worker %s: connection restart failed.", pid
                    )
                    time.sleep(5)
        return ret

    def pool_on_data_received(self, n_workers=1):
        """ Monitor inbound queue for messages to be stored in MySQL """

        def work(storage_q, exit_signal, settings, timeout, logger):

            mysql = MySQL(
                username=settings.username,
                password=settings.password,
                hostname=settings.hostname,
                port=settings.port,
                database=settings.database,
                connection_timeout=settings.connection_timeout,
                logger=logger,
            )

            mysql.connect(table_creation=False)
            pid = os.getpid()

            incrementCounter: int = 0

            logger.info("starting MySQL worker %s", pid)

            last_tx_flush_time = time.perf_counter()
            flush_time_threshold_sec: int = 1

            while not exit_signal.is_set():
                try:
                    msgs = storage_q.get(block=True, timeout=timeout)
                    for msg in msgs:
                        try:
                            if (
                                self._map_message(mysql, msg, incrementCounter)
                                is False
                            ):
                                print("Problem of adding message")
                            incrementCounter += 1
                        except MySQLdb.Error:
                            logger.exception(
                                "MySQL worker %s: connection restart failed.",
                                pid,
                            )

                except queue.Empty:
                    continue
                except queue.Full:
                    print("queue.Full")
                except EOFError:
                    print("EOFError")
                    break
                except KeyboardInterrupt:
                    break

                self.ping_data_base(exit_signal, logger, mysql, pid)

                elapsed_time_since_flush = (
                    time.perf_counter() - last_tx_flush_time
                )

                if elapsed_time_since_flush > flush_time_threshold_sec:
                    mysql.flush_pending_inserts()
                    last_tx_flush_time = time.perf_counter()

            logger.warning("exiting MySQL worker %s", pid)
            return pid

        workers = dict()
        for pseq in range(0, n_workers):
            workers[pseq] = multiprocessing.Process(
                target=work,
                args=(
                    self.rx_queue,
                    self.exit_signal,
                    self.settings,
                    self.timeout,
                    self.logger,
                ),
            ).start()

        self._wait_for_exit(workers=workers)

    def run(self, **kwargs):
        """ Runs until asked to exit """
        try:
            self.parallel = kwargs["parallel"]
        except KeyError:
            pass

        try:
            self.n_workers = kwargs["n_workers"]
        except KeyError:
            pass

        try:
            self.mysql.connect()
        except Exception as err:
            self.logger.exception("error connecting to database %s", err)
            self.exit_signal.set()
            raise

        if self.parallel:
            self.logger.info(
                "Starting // mysql work. " "Number of workers is %s",
                self.n_workers,
            )
            self.pool_on_data_received(n_workers=self.n_workers)
        else:
            self.logger.info("Starting single threaded mysql work")
            self.on_data_received()

        self.mysql.close()

    def _wait_for_exit(self, workers: dict = None):
        """ waits until the exit signal is set """
        while not self.exit_signal.is_set():
            self.logger.debug(
                "MySQL is running (waiting for %s)", self.timeout
            )
            time.sleep(self.timeout)
            if workers:
                for seq, worker in workers.items():
                    if worker.is_alive():
                        continue
                    self.logger.error("Worker %s is dead. Exiting", seq)
                    self.exit_signal.set()
                    break
