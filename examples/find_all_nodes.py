# Copyright 2019 Wirepas Ltd
#
# See file LICENSE for full license details.

import json
import wirepas_backend_client

from wirepas_backend_client.api.mqtt import retrieve_message, MQTTSettings
from wirepas_backend_client.tools import ParserHelper, LoggerHelper


class NodeObserver(wirepas_backend_client.api.MQTTObserver):
    """
    NodeObserver

    This class is an example on how to reuse the MQTTObserver interface
    to setup a MQTT consumer without having to deal with the connection
    parameters and callback assignment.

    The class defines a set of nodes where it tracks the nodes seen over
    the network.

    The class also contains a list of topics and callbacks which define
    the behavior when a message is received in such callback.

    In this example, the message_subscirbe_handlers associates the
    function returned by generate_data_receive_cb to any message
    arriving on the topic "gw-event/received_data/#".

    """

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
        """ How nodes are shown in the terminal window """
        node_enum = 1
        node_repr = dict()

        for node in sorted(self.nodes):
            node_repr[str(node_enum)] = node
            node_enum += 1

        node_repr["total"] = len(self.nodes)
        node_json = json.dumps(node_repr)
        print(node_json)

        return node_repr


def main(settings, logger):
    """ Main loop """

    # process management
    daemon = wirepas_backend_client.management.Daemon(logger=logger)

    # create the process queues
    daemon.build(
        "search",
        NodeObserver,
        dict(
            mqtt_settings=MQTTSettings(settings),
            message_publish_handlers=dict(),
            logger=logger,
            start_signal=None,
        ),
    )

    daemon.start()


if __name__ == "__main__":

    parser = ParserHelper("Find all nodes arguments")
    parser.add_file_settings()
    parser.add_mqtt()
    parser.add_fluentd()
    settings = parser.settings(settings_class=MQTTSettings)

    if settings.sanity():
        log = LoggerHelper(
            module_name="find all nodes",
            args=settings,
            level=settings.debug_level,
        )
        logger = log.setup()

        main(settings, logger)
    else:
        print("Please review your MQTT connection settings")
