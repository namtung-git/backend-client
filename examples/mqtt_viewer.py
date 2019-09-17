# Copyright 2019 Wirepas Ltd
#
# See file LICENSE for full license details.

import os
import time
import queue

from wirepas_backend_client.api import MQTTSettings
from wirepas_backend_client.tools import ParserHelper, LoggerHelper
from wirepas_backend_client.tools.utils import deferred_thread
from wirepas_backend_client.mesh.interfaces import NetworkDiscovery
from wirepas_backend_client.management import Daemon


def loop(
    exit_signal, logger, data_queue, event_queue, response_queue, sleep_for=100
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
            try:
                logger.info(message.serialize())
            except AttributeError:
                continue

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
    net = daemon.build(
        "discovery",
        NetworkDiscovery,
        dict(
            data_queue=data_queue,
            event_queue=event_queue,
            response_queue=response_queue,
            mqtt_settings=settings,
        ),
    )

    print("MAIN", net.message_subscribe_handlers)

    daemon.set_loop(
        loop,
        dict(
            exit_signal=daemon.exit_signal,
            logger=logger,
            data_queue=data_queue,
            event_queue=event_queue,
            response_queue=response_queue,
        ),
    )
    daemon.start()


if __name__ == "__main__":

    try:
        DEBUG_LEVEL = os.environ["WM_DEBUG_LEVEL"]
    except KeyError:
        DEBUG_LEVEL = "info"

    PARSER = ParserHelper(description="Default arguments")

    PARSER.add_file_settings()
    PARSER.add_mqtt()
    PARSER.add_test()
    PARSER.add_database()
    PARSER.add_fluentd()

    SETTINGS = PARSER.settings(settings_class=MQTTSettings)

    if SETTINGS.sanity():
        LOGGER = LoggerHelper(
            module_name="MQTT viewer", args=SETTINGS, level=DEBUG_LEVEL
        ).setup()

        # sets up the message_decoding which is picked up by the
        # message decoders
        LoggerHelper(
            module_name="message_decoding", args=SETTINGS, level=DEBUG_LEVEL
        ).setup()

        main(SETTINGS, LOGGER)
    else:
        print(SETTINGS)
