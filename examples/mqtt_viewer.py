# Copyright 2019 Wirepas Ltd
#
# See file LICENSE for full license details.

import time
import queue
import json

from wirepas_backend_client.api import MQTTSettings
from wirepas_backend_client.tools import ParserHelper, LoggerHelper
from wirepas_backend_client.tools.utils import deferred_thread
from wirepas_backend_client.mesh.interfaces import NetworkDiscovery
from wirepas_backend_client.management import Daemon


def loop(
    exit_signal,
    logger,
    data_queue,
    event_queue,
    response_queue,
    sleep_for=100,
    logfile_path=None,
):
    """
    Client loop

    This loop goes through each message queue and gathers the shared
    messages.
    """

    @deferred_thread
    def get_data(exit_signal, q, block=True, timeout=60):

        while not exit_signal.is_set():

            try:
                message = q.get(block=block, timeout=timeout)
            except queue.Empty:
                continue

            logger.info(message.serialize(flat_keys=True))

            if logfile_path:
                with open(logfile_path, "a") as traffic_log:
                    traffic_log.write(json.dumps(message.serialize()))
                    traffic_log.write("\n")

    @deferred_thread
    def consume_queue(exit_signal, q, block=True, timeout=60):

        while not exit_signal.is_set():
            try:
                q.get(block=block, timeout=timeout)
            except queue.Empty:
                continue

    get_data(exit_signal, data_queue)
    consume_queue(exit_signal, event_queue)
    consume_queue(exit_signal, response_queue)

    while not exit_signal.is_set():
        time.sleep(sleep_for)


def main(settings, logger):
    """ Main loop """

    # process management
    daemon = Daemon(logger=logger)

    data_queue = daemon.create_queue()
    event_queue = daemon.create_queue()
    response_queue = daemon.create_queue()

    # create the process queues
    daemon.build(
        "discovery",
        NetworkDiscovery,
        dict(
            data_queue=data_queue,
            event_queue=event_queue,
            response_queue=response_queue,
            gateway_id=settings.mqtt_subscribe_gateway_id,
            sink_id=settings.mqtt_subscribe_sink_id,
            network_id=settings.mqtt_subscribe_network_id,
            source_endpoint=settings.mqtt_subscribe_source_endpoint,
            destination_endpoint=settings.mqtt_subscribe_destination_endpoint,
            mqtt_settings=settings,
        ),
    )

    daemon.set_loop(
        loop,
        dict(
            exit_signal=daemon.exit_signal,
            logger=logger,
            data_queue=data_queue,
            event_queue=event_queue,
            response_queue=response_queue,
            logfile_path=settings.logfile_path,
        ),
    )
    daemon.start()


if __name__ == "__main__":

    PARSER = ParserHelper(description="Default arguments")

    PARSER.add_file_settings()
    PARSER.add_mqtt()
    PARSER.add_database()
    PARSER.add_fluentd()
    PARSER.record.add_argument(
        "--logfile_path",
        default=None,
        action="store",
        type=str,
        help="Path where to store MQTT traffic to.",
    )

    SETTINGS = PARSER.settings(settings_class=MQTTSettings)

    if SETTINGS.debug_level is None:
        SETTINGS.debug_level = "info"

    if SETTINGS.sanity():
        LOGGER = LoggerHelper(
            module_name="MQTT viewer",
            args=SETTINGS,
            level=SETTINGS.debug_level,
        ).setup()

        # sets up the message_decoding which is picked up by the
        # message decoders
        LoggerHelper(
            module_name="message_decoding",
            args=SETTINGS,
            level=SETTINGS.debug_level,
        ).setup()

        main(SETTINGS, LOGGER)
    else:
        print(SETTINGS)
