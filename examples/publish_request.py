# Copyright 2019 Wirepas Ltd
#
# See file LICENSE for full license details.

import time
import queue

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
    request_queue,
    shared_state,
    mqtt_api,
    poll_period,
    logfile_path=None,
):
    """
    This loop exemplifies how to query all the gateway status on a periodic
    basis.

    The NetworkDiscovery class builds a view of the network based on the
    messages that it receives through the broker. The downstream
    communication is done by placing a request in the output queue of
    the network object.

    The mqtt_api object could be used to create any other request
    towards Wirepas Mesh.

    In case you do not need the network state, please take a look at
    the MQTT handler (MQTTObserver class).

    For an extensive example on how to send data towards the mesh, please
    take a look at the cli.
    """

    @deferred_thread
    def consume_queue(exit_signal, q, name, block=True, timeout=60):

        while not exit_signal.is_set():
            try:
                message = q.get(block=block, timeout=timeout)
            except queue.Empty:
                continue
            logger.info(f"{name}: {message}")

    consume_queue(exit_signal=exit_signal, q=data_queue, name="data")
    consume_queue(exit_signal=exit_signal, q=event_queue, name="event")

    while not exit_signal.is_set():

        devices = shared_state["devices"]

        if devices is None:
            time.sleep(1)  # trying again soon
            continue

        for gateway in devices.gateways:
            request = mqtt_api.request_message(
                "get_configs", **dict(gw_id=gateway.gateway_id)
            )
            request_queue.put(request)
            print(f"{request['topic']}: {request['data']}")

            try:
                reply = response_queue.get(timeout=10, block=True)
                print(reply)
            except queue.Empty:
                print(f"No answer from {gateway.gateway_id}")

        time.sleep(poll_period)


def main(settings, logger):
    """ Main loop """

    # process management
    daemon = Daemon(logger=logger)

    shared_state = daemon.create_shared_dict(devices=None)
    data_queue = daemon.create_queue()
    event_queue = daemon.create_queue()

    # create the process queues
    network = daemon.build(
        "discovery",
        NetworkDiscovery,
        dict(
            data_queue=data_queue,
            shared_state=shared_state,
            event_queue=event_queue,
            mqtt_settings=settings,
        ),
    )

    daemon.set_loop(
        loop,
        dict(
            data_queue=data_queue,
            event_queue=event_queue,
            response_queue=network.response_queue,
            request_queue=network.request_queue,
            mqtt_api=network.mqtt_topics,
            shared_state=shared_state,
            exit_signal=daemon.exit_signal,
            poll_period=settings.poll_period,
            logger=logger,
        ),
    )
    daemon.start()


if __name__ == "__main__":

    PARSER = ParserHelper(description="Default arguments")

    PARSER.add_file_settings()
    PARSER.add_mqtt()

    # Adds a custom cmd argument
    PARSER.requests.add_argument(
        "--poll_period",
        default=600,
        action="store",
        type=int,
        help="Period on which to poll the gateway status.",
    )

    SETTINGS = PARSER.settings(settings_class=MQTTSettings)

    if SETTINGS.debug_level is None:
        SETTINGS.debug_level = "error"

    if SETTINGS.sanity():
        LOGGER = LoggerHelper(
            module_name="Publish example",
            args=SETTINGS,
            level=SETTINGS.debug_level,
        ).setup()

        main(SETTINGS, LOGGER)
    else:
        print(SETTINGS)
