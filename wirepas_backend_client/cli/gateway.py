"""
    Cli Module
    ===========

    Contains the cmd cli interface

    launch as wm-gw-cli or python -m wirepas_gateway_client.cli

    .. Copyright:
        Copyright 2019 Wirepas Ltd under Apache License, Version 2.0.
        See file LICENSE for full license details.
"""

import cmd
import json
from wirepas_messaging.gateway.api import GatewayState

from ..mesh.sink import Sink
from ..mesh.gateway import Gateway


class GatewayCliCommands(cmd.Cmd):
    """
    GatewayCliCommands

    Implements a simple interactive cli to browse the network devices
    and send basic commands.
    """

    # pylint: disable=locally-disabled, no-member, too-many-arguments, unused-argument
    # pylint: disable=locally-disabled, too-many-boolean-expressions
    # pylint: disable=locally-disabled, invalid-name
    # pylint: disable=locally-disabled, too-many-function-args
    # pylint: disable=locally-disabled, too-many-public-methods

    def __init__(self, **kwargs):
        super().__init__()
        self.intro = (
            "Welcome to the Wirepas Gateway Client cli!\n"
            "Connecting to {mqtt_username}@{mqtt_hostname}:{mqtt_port}"
            " (unsecure: {mqtt_force_unsecure})\n\n"
            "You can now set all your command arguments using key=value!\n\n"
            "Type help or ? to list commands\n\n"
            "Type ! to escape shell commands\n"
            "Use Arrow Up/Down to navigate your command history\n"
            "Use TAB for auto complete\n"
            "Use CTRL-D, bye or q to exit\n"
        )

        self._prompt_base = "wm-gw-cli"
        self._prompt_format = "{} | {} > "
        self._display_pending_response = False
        self._display_pending_event = False
        self._display_pending_data = False
        self._selection = dict(sink=None, gateway=None, network=None)

    @property
    def gateway(self):
        """
        Returns the currently selected gateway
        """
        return self._selection["gateway"]

    @property
    def sink(self):
        """
        Returns the currently selected sink
        """
        return self._selection["sink"]

    @property
    def network(self):
        """
        Returns the currently selected network
        """
        return self._selection["network"]

    def on_update_prompt(self):
        """ Updates the prompt with the gateway and sink selection """

        new_prompt = "{}".format(self._prompt_base)

        if self._selection["gateway"]:
            new_prompt = "{}:{}".format(
                new_prompt, self._selection["gateway"].device_id
            )

        if self._selection["sink"]:
            new_prompt = "{}:{}".format(
                new_prompt, self._selection["sink"].device_id
            )

        self.prompt = self._prompt_format.format(
            self.time_format(), new_prompt
        )

    def on_print(self, reply, reply_greeting=None, pretty=None):
        """ Prettified reply """
        serialization = reply
        try:
            serialization = reply.serialize()
            print(
                f"{self._reply_greeting} {serialization['gw_id']}"
                f"/{serialization['sink_id']}"
                f"/{serialization['network_id']}"
                f"|{serialization['source_endpoint']}"
                f"->{serialization['destination_endpoint']}"
                f"@{serialization['tx_time']}"
            )
        except AttributeError:
            serialization = None

        if self._minimal_prints:
            return

        indent = None
        if pretty or self._pretty_prints:
            indent = 4

        if serialization:
            print(json.dumps(serialization, indent=indent))
        else:
            print(reply)

    def on_response_queue_message(self, message):
        """ Method called when retrieving a message from the response queue """
        if self._display_pending_response:
            self.on_print(message, "Pending response message <<")

    def on_data_queue_message(self, message):
        """ Method called when retrieving a message from the data queue """
        if self._display_pending_data:
            self.on_print(message, "Pending data message <<")

    def on_event_queue_message(self, message):
        """ Method called when retrieving a message from the event queue """
        if self._display_pending_event:
            self.on_print(message, "Pending event message <<")

    def do_toggle_print_pending_responses(self, line):
        """
        When True prints any response that is going to be discarded
        """
        self._display_pending_response = not self._display_pending_response
        print(
            "display pending responses: {}".format(
                self._display_pending_response
            )
        )

    def do_toggle_print_pending_events(self, line):
        """
        When True prints any event that is going to be discarded
        """
        self._display_pending_event = not self._display_pending_event
        print("display pending events: {}".format(self._display_pending_event))

    def do_toggle_print_pending_data(self, line):
        """
        When True prints any data that is going to be discarded
        """
        self._display_pending_data = not self._display_pending_data
        print("display pending events: {}".format(self._display_pending_data))

    # track status
    def do_track_devices(self, line):
        """
        Displays the current selected devices for the desired amount of time.

        A key press will exit the loop.

        Usage:
            track_devices argument=value

        Arguments:
            - iterations=Inf
            - update_rate=1
            - silent=False

        Returns:
            Prints the current known devices
        """
        options = dict(
            iterations=dict(type=int, default=float("Inf")),
            update_rate=dict(type=int, default=1),
            silent=dict(type=bool, default=None),
        )

        args = self.retrieve_args(line, options)

        self._tracking_loop(self.do_list, **args)

    def do_track_data_packets(self, line):
        """
        Displays the incoming packets for one / all devices.

        A newline will exit the tracking loop

        Usage:
            track_data_packets argument=value

        Arguments:
            - gw_id=None
            - sink_id=None
            - network_id=None # filter by network
            - source_address=None
            - source_endpoint=None
            - destination_endpoint=None
            - iterations=Inf
            - update_rate=1 # period to print status if no message is acquired
            - show_events=False # will display answers as well
            - silent=False # when True the loop number is not printed

        Returns:
            Prints
        """

        options = dict(
            gw_id=dict(type=str, default=None),
            sink_id=dict(type=str, default=None),
            network_id=dict(type=int, default=None),
            source_address=dict(type=int, default=None),
            source_endpoint=dict(type=int, default=None),
            destination_endpoint=dict(type=int, default=None),
            iterations=dict(type=int, default=float("Inf")),
            update_rate=dict(type=int, default=1),
            show_events=dict(type=bool, default=False),
            silent=dict(type=bool, default=False),
        )

        args = self.retrieve_args(line, options)
        args["cli"] = self

        def handler_cb(cli, **kwargs):

            source_address = kwargs.get("source_address", None)
            source_endpoint = kwargs.get("source_endpoint", None)
            destination_endpoint = kwargs.get("destination_endpoint", None)
            network_id = kwargs.get("network_id", None)
            gw_id = kwargs.get("gw_id", None)
            sink_id = kwargs.get("sink_id", None)
            show_events = kwargs.get("show_events", None)

            def print_on_match(message):
                if (
                    cli.is_match(message, "gw_id", gw_id)
                    and cli.is_match(message, "sink_id", sink_id)
                    and cli.is_match(message, "network_id", network_id)
                    and cli.is_match(message, "source_address", source_address)
                    and cli.is_match(
                        message, "source_endpoint", source_endpoint
                    )
                    and cli.is_match(
                        message, "destination_endpoint", destination_endpoint
                    )
                ):
                    cli.on_print(message)

            for message in cli.consume_data_queue():
                print_on_match(message)

            if show_events:
                for message in cli.consume_event_queue():
                    print_on_match(message)

        self._tracking_loop(cb=handler_cb, **args)

        # commands

    def do_ls(self, line):
        """
        See list
        """
        self.do_list(line)

    def do_list(self, line):
        """
        Lists all known networks and devices

        Usage:
            list

        Returns:
            Prints all known nodes
        """
        self.do_networks(line)

    def do_selection(self, line):
        """
        Displays the current selected devices

        Usage:
            selection

        Returns:
            Prints the currently selected sink, gateay and network
        """
        for k, v in self._selection.items():
            print("{} : {}".format(k, v))

    def _set_target(self):
        """ utility method to call when either the gateway or sink are undefined"""
        print("Please define your target gateway and sink")
        if self.gateway is None:
            self.do_set_gateway("")

        if self.sink is None:
            self.do_set_sink("")

    def do_set_sink(self, line):
        """
        Sets the sink to use with the commands

        Usage:
            set_sink [Enter for default]

        Returns:
            Prompts the user for the sink to use when building
            network requests
        """
        if self.gateway is None:
            self.do_set_gateway(line)

        try:
            sinks = list(self.device_manager.sinks)

            if not sinks:
                self.do_gateway_configuration(line="")
                sinks = list(self.device_manager.sinks)
        except TypeError:
            sinks = list()

        custom_index = len(sinks)
        if sinks:
            list(
                map(
                    lambda sink: print(
                        f"{sinks.index(sink)} "
                        f":{sink.network_id}"
                        f":{sink.gateway_id}"
                        f":{sink.device_id}"
                    ),
                    sinks,
                )
            )
        print(f"{custom_index} : custom sink id")
        arg = input("Please enter your sink selection [0]: ") or 0
        try:
            arg = int(arg)
            self._selection["sink"] = sinks[arg]

        except (ValueError, IndexError):
            arg = input("Please enter your custom sink id: ")
            self._selection["sink"] = Sink(device_id=arg)
            print(f"Sink set to: {self._selection['sink']}")

    def do_set_gateway(self, line):
        """
        Sets the gateways to use with the commands

        Usage:
            set_gateway [Enter for default]

        Returns:
            Prompts the user for the gateway to use when building
            network requests
        """
        try:
            gateways = list(self.device_manager.gateways)
        except TypeError:
            gateways = list()

        custom_index = len(gateways)
        if gateways:
            list(
                map(
                    lambda gw: print(
                        f"{gateways.index(gw)} "
                        f":{gw.device_id}"
                        f":{gw.state}"
                    ),
                    gateways,
                )
            )

        print(f"{custom_index} : custom gateway id")
        arg = input("Please enter your gateway selection [0]: ") or 0
        try:
            arg = int(arg)
            self._selection["gateway"] = gateways[arg]

        except (ValueError, IndexError):
            arg = input("Please enter your custom gateway id: ")
            self._selection["gateway"] = Gateway(device_id=arg)
            print(f"Gateway set to: {self._selection['gateway']}")

    def do_clear_offline_gateways(self, line):
        """
        Removes offline gateways from the remote broker.

        Usage:
            clear_offline_gateways
        """

        gateways = list(self.device_manager.gateways)
        for gateway in gateways:
            if gateway.state.value == GatewayState.OFFLINE.value:
                message = self.mqtt_topics.event_message(
                    "clear", **dict(gw_id=gateway.device_id)
                )
                message["data"].Clear()
                message["data"] = message["data"].SerializeToString()
                message["retain"] = True

                print("sending clear for gateway {}".format(message))

                # remove from state
                self.device_manager.remove(gateway.device_id)
                self.notify()

                self.request_queue.put(message)
                continue

    def do_sinks(self, line):
        """
        Displays the available sinks

        Usage:
            sinks

        Returns:
            Prints the discovered sinks
        """
        for sink in self.device_manager.sinks:
            print(sink)

    def do_gateways(self, line):
        """
        Displays the available gateways

        Usage:
            gateways

        Returns:
            Prints the discovered gateways
        """
        for gateway in self.device_manager.gateways:
            print(gateway)

    def do_nodes(self, line):
        """
        Displays the available nodes

        Usage:
            nodes

        Returns:
            Prints the discovered nodes
        """
        for nodes in self.device_manager.nodes:
            print(nodes)

    def do_networks(self, line):
        """
        Displays the available networks

        Usage:
            networks

        Returns:
            Prints the discovered networks
        """

        for network in self.device_manager.networks:
            print(network)

    def do_gateway_configuration(self, line):
        """
        Acquires gateway configuration from the server.

        If no gateway is set, it will acquire configuration from all
        online gateways.

        When a gateway is selected, the configuration will only be
        requested for that particular gateway.

        Usage:
            gateway_configuration

        Returns:
            Current configuration for each gateway
        """

        for gateway in self.device_manager.gateways:

            if gateway.state.value == GatewayState.OFFLINE.value:
                continue

            if self.gateway is not None:
                if self.gateway.device_id != gateway.device_id:
                    continue

            gw_id = gateway.device_id

            print("requesting configuration for {}".format(gw_id))
            message = self.mqtt_topics.request_message(
                "get_configs", **dict(gw_id=gw_id)
            )
            self.request_queue.put(message)
            self.wait_for_answer(gateway.device_id)

    def do_set_app_config(self, line):
        """
        Builds and sends an app config message

        Usage:
            set_app_config  argument=value

        Arguments:
            - sequence=1  # the sequence number - must be higher than the current one
            - data=001100 # payloady in hex string or plain string
            - interval=60 # a valid diagnostic interval (by default 60)

        Returns:
            Result of the request and app config currently set
        """
        options = dict(
            app_config_seq=dict(type=int, default=None),
            app_config_data=dict(type=int, default=None),
            app_config_diag=dict(type=int, default=60),
        )

        args = self.retrieve_args(line, options)

        if self.gateway and self.sink:
            # sink_id interval app_config_data seq

            gateway_id = self.gateway.device_id
            sink_id = self.sink.device_id

            if not self.is_valid(args) or not sink_id:
                self.do_help("set_app_config", args)

            message = self.mqtt_topics.request_message(
                "set_config",
                **dict(
                    sink_id=sink_id,
                    gw_id=gateway_id,
                    new_config={
                        "app_config_diag": args["app_config_diag"],
                        "app_config_data": args["app_config_data"],
                        "app_config_seq": args["app_config_seq"],
                    },
                ),
            )

            self.request_queue.put(message)
            self.wait_for_answer(gateway_id)

        else:
            self._set_target()
            self.do_set_app_config(line)

    def do_scratchpad_status(self, line):
        """
        Retrieves the scratchpad status from the sink

        Usage:
            scratchpad_status

        Returns:
            The scratchpad loaded on the target gateway:sink pair
        """

        if self.gateway and self.sink:
            gateway_id = self.gateway.device_id
            sink_id = self.sink.device_id

            message = self.mqtt_topics.request_message(
                "otap_status", **dict(sink_id=sink_id, gw_id=gateway_id)
            )

            self.request_queue.put(message)
            self.wait_for_answer(gateway_id)

        else:
            self._set_target()

    def do_scratchpad_update(self, line):
        """
        Sends a scratchpad update command to the sink

        Usage:
            scratchpad_update

        Returns:
            The update status
        """

        if self.gateway and self.sink:
            gateway_id = self.gateway.device_id
            sink_id = self.sink.device_id

            message = self.mqtt_topics.request_message(
                "otap_process_scratchpad",
                **dict(sink_id=sink_id, gw_id=gateway_id),
            )

            message["qos"] = 2

            self.request_queue.put(message)
            self.wait_for_answer(gateway_id)

        else:
            self._set_target()

    def do_scratchpad_upload(self, line):
        """
        Uploads a scratchpad to the target sink/gateway pair

        Usage:
            scratchpad_upload argument=value

        Arguments:
            - filepath=~/myscratchpad.otap # the path to the scratchpad
            - sequence=1 # the scratchpad sequence number

        Returns:
            The status of the upload success
        """

        options = dict(
            file_path=dict(type=int, default=None),
            seq=dict(type=int, default=None),
        )

        args = self.retrieve_args(line, options)

        if self.gateway and self.sink:
            gateway_id = self.gateway.device_id
            sink_id = self.sink.device_id

            try:
                with open(args["file_path"], "rb") as f:
                    scratchpad = f.read()
            except FileNotFoundError:
                scratchpad = None

            if not self.is_valid(args):
                self.do_help("scratchpad_upload", args)

            message = self.mqtt_topics.request_message(
                "otap_load_scratchpad",
                **dict(
                    sink_id=sink_id,
                    scratchpad=scratchpad,
                    seq=args["seq"],
                    gw_id=gateway_id,
                ),
            )
            message["qos"] = 2

            self.request_queue.put(message)
            self.wait_for_answer(gateway_id)

        else:
            self._set_target()
            self.scratchpad_upload(line=line)

    def do_send_data(self, line):
        """
        Sends a custom payload to the target address.

        Usage:
            send_data argument=value

        Arguments:
            - source_endpoint= 10 (default=None)
            - destination_endpoint=11   (default=None)
            - destination_address=101   (default=None)
            - payload=0011   (default=None)
            - timeout=0 # skip wait for a response (default=0)
            - qos=1 # normal priority (default=1)
            - is_unack_csma_ca=0  # if true only sent to CB-MAC nodes (default=0)
            - hop_limit=0  # maximum number of hops this message can do to reach its destination (<16) (default=0 - disabled)
            - initial_delay_ms=0 # initial delay to add to travel time (default: 0)

        Returns:
            Answer or timeout
        """

        options = dict(
            source_endpoint=dict(type=int, default=None),
            destination_endpoint=dict(type=int, default=None),
            destination_address=dict(type=int, default=None),
            payload=dict(type=self.strtobytes, default=None),
            timeout=dict(type=int, default=0),
            qos=dict(type=int, default=1),
            is_unack_csma_ca=dict(type=bool, default=0),
            hop_limit=dict(type=int, default=0),
            initial_delay_ms=dict(type=int, default=0),
        )

        args = self.retrieve_args(line, options)

        if self.gateway and self.sink:

            if not self.is_valid(args):
                self.do_help("send_data", args)

            gateway_id = self.gateway.device_id
            sink_id = self.sink.device_id

            message = self.mqtt_topics.request_message(
                "send_data",
                **dict(
                    sink_id=sink_id,
                    dest_add=args["destination_address"],
                    src_ep=args["source_endpoint"],
                    dst_ep=args["destination_endpoint"],
                    payload=args["payload"],
                    qos=args["qos"],
                    is_unack_csma_ca=args["is_unack_csma_ca"],
                    hop_limit=args["hop_limit"],
                    initial_delay_ms=args["initial_delay_ms"],
                    gw_id=gateway_id,
                ),
            )

            self.request_queue.put(message)
            self.wait_for_answer(gateway_id)
        else:
            self._set_target()
            self.do_send_data(line)

    def do_set_config(self, line):
        """
        Set a config on the target sink.

        Usage:
            set_config argument=value

        Arguments:
            - node_role=1 (int),
            - node_address=1003 (int),
            - network_address=100 (int),
            - network_channel=1 (int)
            - started=True (bool)

        Returns:
            Answer or timeout
        """
        options = dict(
            node_role=dict(type=int, default=None),
            node_address=dict(type=int, default=None),
            network_address=dict(type=int, default=None),
            network_channel=dict(type=int, default=None),
            started=dict(type=bool, default=None),
        )
        args = self.retrieve_args(line, options)

        if self.gateway and self.sink:
            gateway_id = self.gateway.device_id
            sink_id = self.sink.device_id

            new_config = {}
            for key, val in args:
                if val:
                    new_config[key] = val

            if not new_config:
                self.do_help("set_config", args)

            message = self.mqtt_topics.request_message(
                "set_config",
                **dict(
                    sink_id=sink_id, gw_id=gateway_id, new_config=new_config
                ),
            )
            self.request_queue.put(message)
            self.wait_for_answer(
                f"{gateway_id}/{sink_id}", timeout=self.timeout
            )

        else:
            self._set_target()
