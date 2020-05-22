"""
    KPI ADV
    =======

    Script to execute an inventory and otap benchmark for the
    advertiser feature.

    .. Copyright:
        Copyright 2019 Wirepas Ltd under Apache License, Version 2.0.
        See file LICENSE for full license details.
"""

import queue
import random
import datetime
import importlib
import multiprocessing

import pandas

from wirepas_backend_client.messages import AdvertiserMessage
from wirepas_backend_client.tools import ParserHelper, LoggerHelper
from wirepas_backend_client.api import MySQLSettings, MySQLObserver
from wirepas_backend_client.api import MQTTObserver, MQTTSettings
from wirepas_backend_client.management import Daemon, Inventory, Reliability
from wirepas_backend_client.kpi_tester import TestManager


class AdvertiserManager(TestManager):
    """
    Test Manager for the Advertiser use case

    Attributes:
        tx_queue: where a final report is sent
        rx_queue: where Advertiser messages arrive
        exit_signal: signals an exit request
        inventory_target_nodes: nodes to look for during the inventory
        inventory_target_otap: otap sequence to track during inventory
        delay: amount of seconds to wait before starting test
        duration: maximum duration of the test
        logger: package logger

    """

    # pylint: disable=locally-disabled, logging-format-interpolation,
    # logging-too-many-args
    def __init__(
        self,
        tx_queue: multiprocessing.Queue,
        rx_queue: multiprocessing.Queue,
        start_signal: multiprocessing.Event,
        exit_signal: multiprocessing.Event,
        storage_queue: multiprocessing.Queue = None,
        inventory_target_nodes: set = None,
        inventory_target_otap: int = None,
        inventory_target_frequency: int = None,
        delay: int = 5,
        duration: int = 5,
        logger=None,
    ):

        super(AdvertiserManager, self).__init__(
            tx_queue=tx_queue,
            rx_queue=rx_queue,
            start_signal=start_signal,
            exit_signal=exit_signal,
            logger=logger,
        )

        self.storage_queue = storage_queue
        self.delay = delay
        self.duration = duration

        self.inventory = Inventory(
            target_nodes=inventory_target_nodes,
            target_otap_sequence=inventory_target_otap,
            target_frequency=inventory_target_frequency,
            start_delay=delay,
            maximum_duration=duration,
            logger=self.logger,
        )

        self._test_sequence_number = 0
        self._timeout = 1
        self._tasks = list()

    def test_inventory(self, test_sequence_number=0) -> None:
        """
        Inventory test

        This test starts by calculating the time when it should start counting
        and when it should stop its inventory.

        Afterwards, before the time to start the count is reached, any message
        coming in the queue is discarded. Discarding messages is necessary
        otherwise it would lead to false results.

        """

        self._test_sequence_number = test_sequence_number
        self.inventory.sequence = test_sequence_number
        self.inventory.wait()
        self.start_signal.set()
        self.logger.info(
            "starting inventory #{}".format(test_sequence_number),
            dict(sequence=self._test_sequence_number),
        )

        AdvertiserMessage.message_counter = 0
        empty_counter = 0

        while not self.exit_signal.is_set():
            try:
                message = self.rx_queue.get(timeout=self._timeout, block=True)
                empty_counter = 0
            except queue.Empty:
                empty_counter = empty_counter + 1
                if empty_counter > 10:
                    self.logger.debug(
                        "Advertiser messages " "are not being received"
                    )
                    empty_counter = 0

                if self.inventory.is_out_of_time():
                    break
                else:
                    continue

            self.logger.info(message.serialize())

            if self.storage_queue:
                self.storage_queue.put(message)
                if self.storage_queue.qsize() > 100:
                    self.logger.critical("storage queue is too big")

            # create map of apdu["adv"]
            for tag_address, details in message.apdu["adv"].items():
                self.inventory.add(
                    tag_address=tag_address,
                    rss=details["rss"],
                    otap_sequence=details["otap"],
                    tag_sequence=details["sequence"],
                    timestamp=details["time"],
                )

            if self.inventory.is_out_of_time():
                break

            if self.inventory.is_complete():
                self.logger.info(
                    "inventory completed for all target nodes",
                    dict(sequence=self._test_sequence_number),
                )
                break

            if self.inventory.is_otaped():
                self.logger.info(
                    "inventory completed for all otap targets",
                    dict(sequence=self._test_sequence_number),
                )
                break

            if self.inventory.is_frequency_reached():
                self.logger.info(
                    "inventory completed for frequency target",
                    dict(sequence=self._test_sequence_number),
                )
                break

        self.inventory.finish()
        report = self.report()
        self.tx_queue.put(report)
        record = dict(
            test_sequence_number=self._test_sequence_number,
            total_nodes=report["observed_total"],
            inventory_start=report["start"].isoformat("T"),
            inventory_end=report["end"].isoformat("T"),
            node_frequency=str(report["node_frequency"]),
            frequency_by_value=str(report["frequency_by_value"]),
            target_nodes=str(self.inventory.target_nodes),
            target_otap=str(self.inventory.target_otap_sequence),
            target_frequency=str(self.inventory.target_frequency),
            difference=str(self.inventory.difference()),
            elapsed=report["elapsed"],
        )

        self.logger.info(record, dict(sequence=self._test_sequence_number))

    def report(self) -> dict:
        """
        Returns a string with the gathered results.
        """
        msg = dict(
            title="{}:{}".format(__TEST_NAME__, self._test_sequence_number),
            start=self.inventory.start,
            end=self.inventory.finish(),
            elapsed=self.inventory.elapsed,
            difference=self.inventory.difference(),
            inventory_target_nodes=self.inventory.target_nodes,
            inventory_target_otap=self.inventory.target_otap_sequence,
            inventory_target_frequency=self.inventory.target_frequency,
            node_frequency=self.inventory.frequency(),
            frequency_by_value=self.inventory.frequency_by_value(),
            observed_total=len(self.inventory.nodes),
            observed=self.inventory.nodes,
        )
        return msg


class ReliabilityManager(TestManager):
    def __init__(
        self,
        tx_queue: multiprocessing.Queue,
        rx_queue: multiprocessing.Queue,
        start_signal: multiprocessing.Event,
        exit_signal: multiprocessing.Event,
        storage_queue: multiprocessing.Queue = None,
        delay: int = 5,
        duration: int = 5,
        logger=None,
    ):

        super(ReliabilityManager, self).__init__(
            tx_queue=tx_queue,
            rx_queue=rx_queue,
            start_signal=start_signal,
            exit_signal=exit_signal,
            logger=logger,
        )

        self.storage_queue = storage_queue
        self.delay = delay
        self.duration = duration

        self.reliability = Reliability(
            start_delay=delay, maximum_duration=duration, logger=self.logger
        )

        self._test_sequence_number = 0
        self._timeout = 1
        self._tasks = list()

    def test_reliability(self, test_sequence_number=0) -> None:
        """
        Inventory test

        This test starts by calculating the time when it should start counting
        and when it should stop its inventory.

        Afterwards, before the time to start the count is reached, any message
        coming in the queue is discarded. Discarding messages is necessary
        otherwise it would lead to false results.

        """

        self._test_sequence_number = test_sequence_number
        self.reliability.sequence = test_sequence_number
        self.reliability.wait()
        self.start_signal.set()
        self.logger.info(
            "starting reliability #{}".format(test_sequence_number),
            dict(sequence=self._test_sequence_number),
        )

        AdvertiserMessage.message_counter = 0
        empty_counter = 0

        while not self.exit_signal.is_set():
            try:
                message = self.rx_queue.get(timeout=self._timeout, block=True)
                empty_counter = 0
            except queue.Empty:
                empty_counter = empty_counter + 1
                if empty_counter > 10:
                    self.logger.debug(
                        "Advertiser messages " "are not being received"
                    )
                    empty_counter = 0

                if self.reliability.is_out_of_time():
                    break
                else:
                    continue

            self.logger.info(message.serialize())

            for key, value in message.apdu["adv"].items():
                self.logger.info(
                    "tag: {0}/ tag sequence: {1} / "
                    "node: {2} / node sequence: {3}".format(
                        key,
                        value,
                        message.source_address,
                        message.apdu["adv_message_count"],
                    )
                )

            if self.storage_queue:
                self.storage_queue.put(message)
                if self.storage_queue.qsize() > 100:
                    self.logger.critical("storage queue is too big")

            # create map of apdu["adv"]
            self.reliability.add_routers_and_missed_routers(
                router_address=message.source_address,
                adv_message_count=message.apdu["adv_message_count"],
                timestamp=message.tx_time.isoformat("T"),
            )

            for tag_address, details in message.apdu["adv"].items():
                self.reliability.add_tags_and_missed_tags(
                    tag_address=tag_address,
                    tag_sequence=details["sequence"],
                    timestamp=details["time"],
                )

            if self.reliability.is_out_of_time():
                break

        self.reliability.finish()
        report = self.report()
        self.tx_queue.put(report)
        record = dict(
            test_sequence_number=self._test_sequence_number,
            inventory_start=report["start"].isoformat("T"),
            missed_router_msg=report["missed_router_msg"],
            missed_tag_msg=report["missed_tag_msg"],
            inventory_end=report["end"].isoformat("T"),
            elapsed=report["elapsed"],
        )

        self.logger.info(record, dict(sequence=self._test_sequence_number))

    def report(self) -> dict:
        """
        Returns a string with the gathered results.
        """
        msg = dict(
            title="{}:{}".format(__TEST_NAME__, self._test_sequence_number),
            start=self.reliability.start,
            end=self.reliability.finish(),
            missed_router_msg=self.reliability.missed_msg_in_router(),
            missed_tag_msg=self.reliability.missed_msg_in_tag(),
            elapsed=self.reliability.elapsed,
        )
        return msg


def fetch_report(
    args, rx_queue, timeout, report_output, number_of_runs, exit_signal, logger
):
    """ Reporting loop executed between test runs """
    reports = {}
    for run in range(0, number_of_runs):
        try:
            report = rx_queue.get(timeout=timeout, block=True)
            reports[run] = report
        except queue.Empty:
            report = None
            logger.warning("timed out waiting for report")

        if exit_signal.is_set():
            raise RuntimeError

    df = pandas.DataFrame.from_dict(reports)
    if args.output_time:
        filepath = "{}_{}".format(
            datetime.datetime.now().isoformat(), args.output
        )
    else:
        filepath = "{}".format(args.output)

    df.to_json(filepath)


def main(args, logger):
    """ Main loop """

    # process management
    daemon = Daemon(logger=logger)

    mysql_settings = MySQLSettings(args)
    mqtt_settings = MQTTSettings(args)

    if mysql_settings.sanity():
        mysql_available = True
        daemon.build(
            __STORAGE_ENGINE__,
            MySQLObserver,
            dict(mysql_settings=mysql_settings),
        )

        daemon.set_run(
            __STORAGE_ENGINE__,
            task_kwargs=dict(parallel=True),
            task_as_daemon=False,
        )
    else:
        mysql_available = False
        logger.info("Skipping Storage module")

    if mqtt_settings.sanity():

        mqtt_process = daemon.build(
            "mqtt",
            MQTTObserver,
            dict(
                mqtt_settings=mqtt_settings,
                logger=logger,
                allowed_endpoints=set([AdvertiserMessage.source_endpoint]),
            ),
        )

        topic = "gw-event/received_data/{gw_id}/{sink_id}/{network_id}/{source_endpoint}/{destination_endpoint}".format(
            gw_id=args.mqtt_subscribe_gateway_id,
            sink_id=args.mqtt_subscribe_sink_id,
            network_id=args.mqtt_subscribe_network_id,
            source_endpoint=args.mqtt_subscribe_source_endpoint,
            destination_endpoint=args.mqtt_subscribe_destination_endpoint,
        )

        mqtt_process.message_subscribe_handlers = {
            topic: mqtt_process.generate_data_received_cb()
        }

        daemon.set_run("mqtt", task=mqtt_process.run)

        # when the duration or
        if args.testcase == "inventory" or args.testcase is None:
            # build each process and set the communication
            adv_manager = daemon.build(
                "adv_manager",
                AdvertiserManager,
                dict(
                    inventory_target_nodes=args.target_nodes,
                    inventory_target_otap=args.target_otap,
                    inventory_target_frequency=args.target_frequency,
                    logger=logger,
                    delay=args.delay,
                    duration=args.duration,
                ),
                receive_from="mqtt",
                storage=mysql_available,
                storage_name=__STORAGE_ENGINE__,
            )

            adv_manager.execution_jitter(
                _min=args.jitter_minimum, _max=args.jitter_maximum
            )
            adv_manager.register_task(
                adv_manager.test_inventory, number_of_runs=args.number_of_runs
            )

            daemon.set_loop(
                fetch_report,
                dict(
                    args=args,
                    rx_queue=adv_manager.tx_queue,
                    timeout=args.delay + args.duration + 60,
                    report_output=args.output,
                    number_of_runs=args.number_of_runs,
                    exit_signal=daemon.exit_signal,
                    logger=logger,
                ),
            )
        if args.testcase == "reliability":
            reliability_manager = daemon.build(
                "reliability_manager",
                ReliabilityManager,
                dict(delay=args.delay, duration=args.duration, logger=logger),
                receive_from="mqtt",
                storage=mysql_available,
                storage_name=__STORAGE_ENGINE__,
            )

            reliability_manager.register_task(
                reliability_manager.test_reliability,
                number_of_runs=args.number_of_runs,
            )

            daemon.set_loop(
                fetch_report,
                dict(
                    args=args,
                    rx_queue=reliability_manager.tx_queue,
                    timeout=args.delay + args.duration + 60,
                    report_output=args.output,
                    number_of_runs=args.number_of_runs,
                    exit_signal=daemon.exit_signal,
                    logger=logger,
                ),
            )

        daemon.start()
    else:
        print("Please check you MQTT settings")
        print(mqtt_settings)


if __name__ == "__main__":

    __MYSQL_ENABLED__ = importlib.util.find_spec("MySQLdb")
    __STORAGE_ENGINE__ = "mysql"
    __TEST_NAME__ = "test_advertiser"

    PARSE = ParserHelper(description="KPI ADV arguments")
    PARSE.add_mqtt()
    PARSE.add_test()
    PARSE.add_database()
    PARSE.add_fluentd()
    PARSE.add_file_settings()
    SETTINGS = PARSE.settings()

    LOGGER = LoggerHelper(
        module_name=__TEST_NAME__, args=SETTINGS, level=SETTINGS.debug_level
    ).setup()

    if SETTINGS.delay is None:
        SETTINGS.delay = random.randrange(0, 60)

    # pylint: disable=locally-disabled, no-member
    try:
        nodes = set({int(line) for line in open(SETTINGS.nodes, "r")})
    except FileNotFoundError:
        LOGGER.warning("Could not find nodes file")
        nodes = set()

    SETTINGS.target_nodes = nodes
    if SETTINGS.jitter_minimum > SETTINGS.jitter_maximum:
        SETTINGS.jitter_maximum = SETTINGS.jitter_minimum

    LOGGER.info(
        {
            "test_suite_start": datetime.datetime.utcnow().isoformat("T"),
            "run_arguments": SETTINGS.to_dict(),
        }
    )
    # pylint: enable=no-member

    main(SETTINGS, LOGGER)
    PARSE.dump(
        "run_information_{}.txt".format(datetime.datetime.now().isoformat())
    )
