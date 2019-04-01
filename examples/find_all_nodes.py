# Copyright 2018 Wirepas Ltd. All Rights Reserved.
#
# See file LICENSE.txt for full license details.
import os
import wirepas_messaging
import wirepas_backend_client
import multiprocessing
import time


from wirepas_backend_client.api.mqtt import retrieve_message, MQTTSettings
from wirepas_backend_client.tools import ParserHelper, LoggerHelper, Settings


class NodeObserver(wirepas_backend_client.api.MQTTObserver):
    """docstring for NodeObserver"""

    def __init__(self, **kwargs):
        super(NodeObserver, self).__init__(**kwargs)

        self.nodes = set()

        self.message_publish_handlers = dict()
        self.message_subscribe_handlers = {
            "gw-event/received_data/#": self.generate_data_receive_cb()
        }

    def generate_data_receive_cb(self) -> callable:
        @retrieve_message
        def on_data_received(message):
            """ Retrieves a MQTT message and sends it to the tx_queue """
            self.nodes.add(message.source_address)
            self.print_nodes()
            self.logger.debug(message)

        return on_data_received

    def generate_data_send_cb(self) -> callable:
        """ Provides a callback that handles data publishing """

        def on_data_send(mqtt_publish, topic):
            """ pass call back to mqtt client """
            pass

        return on_data_send

    def print_nodes(self):
        print("Found nodes (total: {})".format(len(self.nodes)))
        for node in sorted(self.nodes):
            print(node)


def main(args, logger):
    """ Main loop """

    # process management
    daemon = wirepas_backend_client.management.Daemon(logger=logger)

    # create the process queues
    daemon.build(
        "search",
        NodeObserver,
        dict(
            mqtt_settings=MQTTSettings.from_args(args),
            message_publish_handlers=dict(),
            logger=logger,
            start_signal=None,
        ),
    )

    daemon.start()


if __name__ == "__main__":

    try:
        debug_level = os.environ["DEBUG_LEVEL"]
    except KeyError:
        debug_level = "debug"

    parser = ParserHelper.default_args("Gateway client arguments")
    args = parser.arguments

    log = LoggerHelper(
        module_name="Influx viewer", args=args, level=debug_level
    )
    logger = log.setup()

    main(args, logger)
