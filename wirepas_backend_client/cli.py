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
import datetime
import logging
import os
import readline
import select
import subprocess
import sys
import ast

from wirepas_messaging.gateway.api import GatewayState

from .api import Topics
from .management import Daemon
from .mesh.interfaces.mqtt import NetworkDiscovery


class BackendShell(cmd.Cmd):
    """
    BackendShell

    Implements a simple interactive cli to browse the network devices
    and send basic commands.

    Attributes:
        intro (str) : what is printed on the terminal upon initialisation
        prompt (str)

    """

    # pylint: disable=locally-disabled, too-many-arguments, unused-argument

    intro = (
        "Welcome to the Wirepas Gateway Client cli!\n"
        "Connecting to {mqtt_username}@{mqtt_hostname}:{mqtt_port}"
        " (unsecure: {mqtt_force_unsecure})\n\n"
        "Type help or ? to list commands\n\n"
        "Type ! to escape shell commands\n"
        "Use Arrow Up/Down to navigate your command history\n"
        "Use CTRL-D or bye to exit\n"
    )

    _prompt_base = "wm-gw-cli"
    _prompt_format = "{} | {} > "
    prompt = _prompt_format.format(
        datetime.datetime.now().strftime("%H:%M.%S"), _prompt_base
    )

    _bstr_as_hex = True
    _pretty_prints = True
    _silent_loop = False
    _max_queue_size = 1000

    _file = None
    _histfile = os.path.expanduser("~/.wm-shell-history")
    _histfile_size = 1000

    _tracking_loop_timeout = 1
    _tracking_loop_iterations = 60

    _reply_greeting = "answer <<"

    def __init__(
        self,
        shared_state,
        tx_queue,
        rx_queue,
        settings,
        data_queue=None,
        event_queue=None,
        timeout=10,
        histfile_size=1000,
        exit_signal=None,
        logger=None,
    ):
        super(BackendShell, self).__init__()

        self.settings = settings
        self.intro = self.intro.format(**self.settings.to_dict())

        self.request_queue = tx_queue
        self.response_queue = rx_queue

        self.data_queue = data_queue
        self.event_queue = event_queue

        self._shared_state = shared_state
        self.device_manager = None
        self.mqtt_topics = Topics()

        self.logger = logger or logging.getLogger(__name__)
        self.exit_signal = exit_signal
        self.timeout = timeout
        self._histfile_size = histfile_size
        self._selection = dict(sink=None, gateway=None, network=None)

    @staticmethod
    def time_format():
        """ The prompt time format """
        return datetime.datetime.now().strftime("%H:%M.%S")

    def consume_response_queue(self):
        """ Exhausts the response queue """
        while not self.response_queue.empty():
            message = self.response_queue.get(block=False)
            self.cli_print(message, "Pending response <<")

    def consume_data_queue(self):
        """ Exhausts the data queue """
        while not self.data_queue.empty():
            message = self.data_queue.get(block=False)
            yield message

    def consume_event_queue(self):
        """ Exhausts the event queue """
        while not self.event_queue.empty():
            message = self.event_queue.get(block=False)
            yield message

    def _trim_queues(self):
        """ Trim queues ensures that queue size does not run too long"""
        if self.data_queue.qsize() > self._max_queue_size:
            self.consume_data_queue()

        if self.event_queue.qsize() > self._max_queue_size:
            self.consume_event_queue()

        if self.response_queue.qsize() > self._max_queue_size:
            self.consume_response_queue()

    def _update_prompt(self):
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

    def _tracking_loop(
        self, cb, timeout=None, iterations=None, silent=False, cb_args=None
    ):
        """ Simple tracking loop for period cli tasks """

        if cb_args is None:
            cb_args = dict(arg="")

        if timeout is None:
            timeout = self._tracking_loop_timeout

        if iterations is None:
            iterations = self._tracking_loop_iterations

        n_iter = 0
        while n_iter < iterations:
            n_iter = n_iter + 1

            if not silent or self._silent_loop is True:
                print(
                    "#{} : {}".format(
                        n_iter, datetime.datetime.now().isoformat("T")
                    )
                )

            cb(**cb_args)

            i, _, _ = select.select([sys.stdin], [], [], timeout)
            if i:
                sys.stdin.readline().strip()
                return True

    def _set_target(self):
        """ utility method to call when either the gateway or sink are undefined"""
        print("Please define your target gateway and sink")
        if self.gateway is None:
            self.do_set_gateway("")

        if self.sink is None:
            self.do_set_sink("")

    def cli_print(self, reply, reply_greeting=None, pretty=None):
        """ Prettified reply """

        def _print(k, v, output_fmt="{}: {}"):
            if isinstance(v, bytes) and self._bstr_as_hex:
                v = v.hex()
            print(output_fmt.format(k, v))

        if self._reply_greeting or reply_greeting:
            print(reply_greeting or self._reply_greeting)

        if pretty is True or self._pretty_prints is True:

            for k, v in reply.__dict__.items():
                if isinstance(v, list):
                    for lv in v:
                        for kk, vv in lv.items():
                            _print(kk, vv, output_fmt="     {}: {}")
                elif isinstance(v, dict):
                    for kk, vv in v.items():
                        _print(kk, vv, output_fmt="     {}: {}")
                else:
                    _print(k, v, output_fmt="  {}: {}")

        else:
            print(reply)

    @staticmethod
    def is_match(message, field, value):
        """ Checks if the class has an attribute that matches the provided field """
        match = True
        try:
            if value:
                match = bool(value == getattr(message, field))
        except AttributeError:
            pass

        return match

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

    def notify(self):
        """
        Notify sets the shared dictionary to propagate changes to the other
        processes
        """
        self._shared_state["devices"] = self.device_manager

    # track status
    def do_track_devices(self, arg):
        """
        Displays the current selected devices for the desired amount of time.

        A newline will exit the tracking loop

        Usage:
            # iteration print>
            track_devices <amount of iterations (default: 60)> <update rate (default: 1)> <disable

        Returns:
            Prints the current known devices
        """

        iterations = None
        update_rate = None
        silent = False

        if arg:
            params = arg.split(" ")
            iterations = int(params[0])
            try:
                update_rate = int(params[1])
            except IndexError:
                pass

            try:
                silent = bool(params[2])
            except IndexError:
                pass

        self._tracking_loop(
            self.do_list,
            iterations=iterations,
            silent=silent,
            timeout=update_rate,
        )

    def do_track_data_packets(self, arg):
        """
        Displays the incoming packets for one / all devices.

        A newline will exit the tracking loop

        Usage:
            track_data_packets <node> <amount of iterations (default: 60)> <update rate (default: 1)> <silent (default: False) >

        Returns:
            Prints the current known devices
        """

        source_address = None
        iterations = None
        update_rate = None
        silent = False

        if arg:
            params = arg.split(" ")

            try:
                source_address = int(params[0])
            except IndexError:
                pass

            try:
                iterations = int(params[1])
            except IndexError:
                pass

            try:
                update_rate = int(params[2])
            except IndexError:
                pass

            try:
                silent = bool(params[3])
            except IndexError:
                pass

        def handler_cb(cli, source_address=None, **kwargs):

            for message in cli.consume_data_queue():
                if cli.is_match(message, "source_address", source_address):
                    cli.cli_print(message)

            for message in cli.consume_event_queue():
                if cli.is_match(message, "source_address", source_address):
                    cli.cli_print(message)

        self._tracking_loop(
            cb=handler_cb,
            iterations=iterations,
            timeout=update_rate,
            silent=silent,
            cb_args=dict(cli=self, source_address=source_address),
        )

        # commands

    def do_toggle_byte_print(self, arg):
        """
        Switches the byte prints as hex strings or python byte strings
        """
        self._bstr_as_hex = not self._bstr_as_hex
        print("hex prints: {}".format(self._bstr_as_hex))

    def do_toggle_pretty_print(self, arg):
        """
        Switches between json or pretty print
        """
        self._pretty_prints = not self._pretty_prints
        print("pretty prints: {}".format(self._pretty_prints))

    def do_toggle_silent_loop(self, arg):
        """
        Enables/disables the tracking loop verbosity
        """
        self._silent_loop = not self._silent_loop
        print("track loop prints: {}".format(self._silent_loop))

    def do_set_loop_iterations(self, arg):
        """
        Sets the amount of loop iterations
        """
        self._tracking_loop_iterations = int(arg)
        print(
            "track loop iterations: {}".format(self._tracking_loop_iterations)
        )

    def do_set_loop_timeout(self, arg):
        """
        Sets the loop evaluation time
        """
        self._tracking_loop_timeout = int(arg)
        print("track loop timeout: {}".format(self._tracking_loop_timeout))

    def do_set_reply_greeting(self, arg):
        """
        Sets the reply greeting
        """

        if arg == "" or arg.lower() == "none":
            arg = None

        self._reply_greeting = arg
        print("reply greeting set to: {}".format(self._reply_greeting))

    def do_settings(self, arg):
        """
        Prints outs the settings acquired upon starting
        """
        self.cli_print(self.settings, reply_greeting="settings:")

    def do_ls(self, arg):
        """
        See list
        """
        self.do_list(arg)

    def do_list(self, arg):
        """
        Lists all devices

        Usage:
            list

        Returns:
            Prints all known nodes
        """
        if not arg:
            self.do_networks(arg)
        else:
            params = arg.split()
            if "gateway" in params[0]:
                self.do_gateways(arg)

    def do_selection(self, arg):
        """
        Displays the current selected devices

        Usage:
            selection

        Returns:
            Prints the currently selected sink, gateay and network
        """
        for k, v in self._selection.items():
            print("{} : {}".format(k, v))

    def do_set_sink(self, arg):
        """
        Sets the sink to use with the commands

        Usage:
            set_sink [Enter for default]

        Returns:
            Prompts the user for the sink to use when building
            network requests
        """
        if self.gateway is None:
            arg = input("Please define your gateway first")
            self.do_set_gateway(arg)

        sinks = list(self.device_manager.sinks)
        if not sinks:
            self.do_gateway_configuration(arg="")
            sinks = list(self.device_manager.sinks)

        if sinks:
            for sink in sinks:
                print(
                    "{index} : {nw_id}:{gw_id}:{device_id}".format(
                        index=sinks.index(sink),
                        nw_id=sink.network_id,
                        gw_id=sink.gateway_id,
                        device_id=sink.device_id,
                    )
                )

            arg = input("Please enter your sink selection [0]: ")

        try:
            if arg:
                arg = int(arg)
            else:
                arg = 0

            if arg < 0:
                raise ValueError

            self._selection["sink"] = sinks[arg]

        except (KeyError, ValueError):
            self._selection["sink"] = None

    def do_set_gateway(self, arg):
        """
        Sets the gateways to use with the commands

        Usage:
            set_gateway [Enter for default]

        Returns:
            Prompts the user for the gateway to use when building
            network requests
        """

        gateways = list(self.device_manager.gateways)
        if gateways:
            for gateway in gateways:
                print(
                    "{} : {} : {}".format(
                        gateways.index(gateway),
                        gateway.device_id,
                        gateway.state,
                    )
                )

            arg = input("Please enter your gateway selection [0]: ")

            try:
                if arg:
                    arg = int(arg)
                else:
                    arg = 0

                if arg < 0:
                    raise ValueError

                self._selection["gateway"] = gateways[arg]

            except (KeyError, ValueError):
                self._selection["gateway"] = None

    def do_clear_offline_gateways(self, arg):
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

    def do_sinks(self, arg):
        """
        Displays the available sinks

        Usage:
            sinks

        Returns:
            Prints the discovered sinks
        """
        for sink in self.device_manager.sinks:
            print(sink)

    def do_gateways(self, arg):
        """
        Displays the available gateways

        Usage:
            gateways

        Returns:
            Prints the discovered gateways
        """
        for gateway in self.device_manager.gateways:
            print(gateway)

    def do_nodes(self, arg):
        """
        Displays the available nodes

        Usage:
            nodes

        Returns:
            Prints the discovered nodes
        """
        for nodes in self.device_manager.nodes:
            print(nodes)

    def do_networks(self, arg):
        """
        Displays the available networks

        Usage:
            networks

        Returns:
            Prints the discovered networks
        """

        for network in self.device_manager.networks:
            print(network)

    def do_gateway_configuration(self, arg):
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
            try:
                message = self.response_queue.get(
                    block=True, timeout=self.timeout
                )

                self.cli_print(message)
            except:
                print("got no reply for {}".format(gateway.device_id))

    def do_set_app_config(self, arg):
        """
        Builds and sends an app config message

        Usage:
            set_app_config sequence data interval

        Returns:
            Result of the request and app config currently set
        """

        if self.gateway and self.sink:
            # sink_id interval app_config_data seq
            params = arg.split(" ")
            gateway_id = self.gateway.device_id
            sink_id = self.sink.device_id

            if len(params) >= 2 and sink_id:
                app_config_seq = int(params[0])
                try:
                    app_config_data = bytes.fromhex(params[1])
                except:
                    app_config_data = bytes(params[1], "utf-8")

                try:
                    app_config_diag = int(params[2])
                except:
                    app_config_diag = 60

                message = self.mqtt_topics.request_message(
                    "set_config",
                    **dict(
                        sink_id=sink_id,
                        gw_id=gateway_id,
                        new_config={
                            "app_config_diag": app_config_diag,
                            "app_config_data": app_config_data,
                            "app_config_seq": app_config_seq,
                        },
                    ),
                )
                self.request_queue.put(message)
                try:
                    message = self.response_queue.get(
                        block=True, timeout=self.timeout
                    )
                    self.cli_print(message)
                except:
                    print("got no reply for {}".format(gateway_id))
            else:
                self.do_help("set_app_config")
        else:
            self._set_target()

    def do_scratchpad_status(self, arg):
        """
        Retrieves the scratchpad status from the sink

        Usage:
            scratchpad_status

        Returns:
            The scratchpad loaded on the target gateway:sink pair
        """

        arg.split()

        if self.gateway and self.sink:
            gateway_id = self.gateway.device_id
            sink_id = self.sink.device_id

            message = self.mqtt_topics.request_message(
                "otap_status", **dict(sink_id=sink_id, gw_id=gateway_id)
            )

            self.request_queue.put(message)
            try:
                message = self.response_queue.get(
                    block=True, timeout=self.timeout
                )
                self.cli_print(message)
            except Exception as err:
                print("got no reply for {} due to: {}".format(gateway_id, err))
        else:
            self._set_target()

    def do_scratchpad_update(self, arg):
        """
        Sends a scratchpad update command to the sink

        Usage:
            scratchpad_update

        Returns:
            The update status
        """
        arg.split()

        if self.gateway and self.sink:
            gateway_id = self.gateway.device_id
            sink_id = self.sink.device_id

            message = self.mqtt_topics.request_message(
                "otap_process_scratchpad",
                **dict(sink_id=sink_id, gw_id=gateway_id),
            )

            message["qos"] = 2

            self.request_queue.put(message)
            try:
                message = self.response_queue.get(
                    block=True, timeout=self.timeout
                )
                self.cli_print(message)
            except Exception as err:
                print("got no reply for {} due to: {}".format(gateway_id, err))
        else:
            self._set_target()

    def do_scratchpad_upload(self, arg):
        """
        Uploads a scratchpad to the target sink/gateway pair

        Usage:
            scratchpad_upload filepath sequence

        Returns:
            The status of the upload success
        """
        params = arg.split()

        if self.gateway and self.sink:
            gateway_id = self.gateway.device_id
            sink_id = self.sink.device_id
            file_path = params[0]
            seq = int(params[1])

            try:
                with open(file_path, "rb") as f:
                    scratchpad = f.read()
            except:
                scratchpad = None

            if scratchpad:
                message = self.mqtt_topics.request_message(
                    "otap_load_scratchpad",
                    **dict(
                        sink_id=sink_id,
                        scratchpad=scratchpad,
                        seq=seq,
                        gw_id=gateway_id,
                    ),
                )
                message["qos"] = 2

                self.request_queue.put(message)
                try:
                    message = self.response_queue.get(
                        block=True, timeout=self.timeout
                    )
                    self.cli_print(message)
                except Exception as err:
                    print(
                        "got no reply for {} due to: {}".format(
                            gateway_id, err
                        )
                    )
        else:
            self._set_target()

    def do_send_data(self, arg):
        """
        Sends a custom payload to the target address.

        There are two parameters that assume default values:

        * timeout: skip wait for a response (default: 0)

        * qos : normal priority (default: 1)

        * is_unack_csma_ca:  if true only sent to CB-MAC nodes (default: false)

        * hop_limit: maximum number of hops this message can do to reach its destination (<16)  (default: 0 - disabled)

        * initial_delay: initial delay to add to travel time (default: 0)

        Usage:
            send_data <source_endpoint> <destination_endpoint> <destination address> <payload> <timeout> <qos> <is_unack_csma_ca> <hop_limit> <initial_delay>

        Returns:
            Answer or timeout
        """

        params = arg.split()

        if self.gateway and self.sink:
            gateway_id = self.gateway.device_id
            sink_id = self.sink.device_id
            source_endpoint = int(params[0])
            destination_endpoint = int(params[1])
            destination_address = int(params[2])

            try:
                payload = bytes.fromhex(params[3])
            except:
                payload = bytes(params[3], "utf-8")

            try:
                timeout = int(params[4])
            except:
                timeout = 0

            try:
                qos = int(params[5])
            except:
                qos = 1

            try:
                is_unack_csma_ca = bool(params[6])
            except:
                is_unack_csma_ca = False

            try:
                hop_limit = int(params[7])
            except:
                hop_limit = 0

            try:
                initial_delay_ms = int(params[8])
            except:
                initial_delay_ms = 0

            message = self.mqtt_topics.request_message(
                "send_data",
                **dict(
                    sink_id=sink_id,
                    dest_add=destination_address,
                    src_ep=source_endpoint,
                    dst_ep=destination_endpoint,
                    payload=payload,
                    qos=qos,
                    is_unack_csma_ca=is_unack_csma_ca,
                    hop_limit=hop_limit,
                    initial_delay_ms=initial_delay_ms,
                    gw_id=gateway_id,
                ),
            )

            self.request_queue.put(message)
            try:
                if timeout:
                    message = self.response_queue.get(
                        block=True, timeout=timeout
                    )
                    self.cli_print(message)
            except Exception as err:
                print("got no reply for {} due to: {}".format(gateway_id, err))
        else:
            self._set_target()

    def do_set_config(self, arg):
        """
        Set a config on the target sink.

        set_config allows to set several sink attributes. The attributes
        are set by defining one or multiple key=value pairs.

        The supported keys and an example of the value are as follows:

            * node_role=1 (int),

            * node_address=1003 (int),

            * network_address=100 (int),

            * network_channel=1 (int)

            * started=True (bool)

        Usage:
            set_config key1=value1 key2=value2 ... keyn=valuen keys can be:

        Returns:
            Answer or timeout
        """
        params = arg.split()

        available_keys = [
            "node_role",
            "node_address",
            "network_address",
            "network_channel",
            "started",
        ]

        if self.gateway and self.sink:
            gateway_id = self.gateway.device_id
            sink_id = self.sink.device_id

            new_config = {}
            for conf in params:
                key, val = conf.split("=")
                if key not in available_keys:
                    print(
                        "{} is not an available key: {}".format(
                            key, available_keys
                        )
                    )
                    continue

                try:
                    new_config[key] = ast.literal_eval(val)
                except ValueError:
                    print("Cannot parse value for {} ".format(key))

            if not new_config:
                print("No key to set")
                return

            message = self.mqtt_topics.request_message(
                "set_config",
                **dict(
                    sink_id=sink_id, gw_id=gateway_id, new_config=new_config
                ),
            )
            self.request_queue.put(message)
            try:
                message = self.response_queue.get(
                    block=True, timeout=self.timeout
                )
                self.cli_print(message)
            except:
                print("got no reply for {}".format(gateway_id))

        else:
            self._set_target()

    def do_bye(self, arg):
        """
        Exits the cli

        Usage:
            bye
        """
        print("Thank you for using Wirepas Gateway Client")
        self.close()
        if not self.exit_signal.is_set():
            self.exit_signal.set()

        return True

    def do_q(self, arg):
        """
        Exits the cli

        Usage:
            bye
        """
        return self.do_bye(arg)

    def do_eof(self, arg):
        """ Captures CTRL-D """
        return self.do_bye(arg)

    def do_EOF(self, arg):
        """ Captures CTRL-D """
        return self.do_bye(arg)

    @staticmethod
    def do_shell(arg):
        """ Escape shell commands with ! """
        try:
            subprocess.run(arg.split())  # doesn't capture output
        except FileNotFoundError:
            print("Unknown shell command: {}".format(arg.split()))

    def emptyline(self):
        """ What happens when an empty line is provided """
        self.consume_response_queue()

    def precmd(self, line):
        """ Executes before a command is run in onecmd """
        if (
            self._file
            and "playback" not in line
            and "bye" not in line
            and "close" not in line
        ):
            print(line, file=self._file)
        return line

    def onecmd(self, arg):
        """
            Executes each command, escaping it for errors and updates the
            prompt with the current time and selection identifiers.

        """
        try:
            self.device_manager = self._shared_state["devices"]
            if self.device_manager and not self.exit_signal.is_set():
                self.consume_response_queue()
                self._trim_queues()
                self._update_prompt()
                rc = cmd.Cmd.onecmd(self, arg)
                self._update_prompt()
            elif self.exit_signal.is_set():
                print("Failure establishing MQTT connection...")
                return self.do_bye(arg)
            else:
                rc = cmd.Cmd.onecmd(self, arg)
        except Exception as err:
            if self.device_manager is None:
                print(
                    (
                        "Please check your connection settings.\n"
                        "Is the gateway sending data?"
                    )
                )
            else:
                print("Something went wrong:{}".format(err))
            rc = False
        return rc

    def preloop(self):
        """ runs before the cmd loop is started """
        if os.path.exists(self._histfile):
            readline.read_history_file(self._histfile)

    def postloop(self):
        """ runs when the cmd loop finishes """
        readline.set_history_length(self._histfile_size)
        readline.write_history_file(self._histfile)

    # ----- record and playback -----
    def do_record(self, arg="shell-session.record"):
        """
        Saves typed commands in a file for later playback

        Usage:
            record [filename (default: shell-session.record)]
        """
        self.close()
        self._file = open(arg, "w")

    def do_playback(self, arg="shell-session.record"):
        """
        Plays commands from a file

        Usage:
            plaback [filename (default: shell-session.record)]
        """
        try:
            with open(arg) as f:
                lines = f.read().splitlines()
                if "bye" in lines[-1]:
                    del lines[-1]
                self.cmdqueue.extend(lines)
        except TypeError:
            print("wrong file name")

    def close(self):
        """
        Terminates the playback recording
        """
        if self._file:
            self._file.close()
            self._file = None


def launch_cli(settings, logger):
    """ command line launcher """

    # process management
    daemon = Daemon(logger=logger)

    shared_state = daemon.create_shared_dict(devices=None)
    data_queue = daemon.create_queue()
    event_queue = daemon.create_queue()

    discovery = daemon.build(
        "discovery",
        NetworkDiscovery,
        dict(
            shared_state=shared_state,
            data_queue=data_queue,
            event_queue=event_queue,
            mqtt_settings=settings,
            logger=logger,
        ),
    )

    shell = BackendShell(
        shared_state=shared_state,
        data_queue=data_queue,
        event_queue=event_queue,
        rx_queue=discovery.tx_queue,
        tx_queue=discovery.rx_queue,
        settings=settings,
        exit_signal=daemon.exit_signal,
        logger=logger,
    )
    daemon.set_loop(shell.cmdloop)
    daemon.start()


def main():
    """ entrypoint loop """

    from .tools import ParserHelper, LoggerHelper
    from .api import MQTTSettings

    PARSER = ParserHelper("Gateway client arguments")
    PARSER.add_file_settings()
    PARSER.add_mqtt()
    PARSER.add_fluentd()
    SETTINGS = PARSER.settings(settings_class=MQTTSettings)

    if SETTINGS.debug_level is None:
        SETTINGS.debug_level = "warning"

    LOGGER = LoggerHelper(
        module_name="gw-cli", args=SETTINGS, level=SETTINGS.debug_level
    ).setup()

    if SETTINGS.sanity():
        launch_cli(SETTINGS, LOGGER)
    else:
        print("Please review your connection settings")
        print(SETTINGS)


if __name__ == "__main__":

    main()
