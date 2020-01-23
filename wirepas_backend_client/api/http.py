"""
    HTTP API
    ============

    Creates a HTTP server and handles incoming requests to the
    gateway MQTT api.

    Please use the MQTT api whenever possible.

    gateways_and_sinks has following scheme:
    { 'gw_id':
        {'sink_id':
            {# Following fields from item of
             # gw-response/get_configs->configs[]
             'started': True/False,
             'app_config_seq': int,
             'app_config_diag': int,
             'app_config_data': bytes,
             # Internal field for monitoring sink's presense
             'present': True/False
            }
        }
    }

    .. Copyright:
        Copyright 2019 Wirepas Ltd under Apache License, Version 2.0.
        See file LICENSE for full license details.
"""
import multiprocessing
import http.server
import time
import urllib
import binascii
import logging
import queue
from threading import Thread

from .stream import StreamObserver
from .mqtt import Topics
from ..tools import Settings


class SinkAndGatewayStatusObserver(Thread):
    """ SinkAndGatewayStatusObserver """

    def __init__(self, exit_signal, gw_status_queue, logger):
        super(SinkAndGatewayStatusObserver, self).__init__()
        self.exit_signal = exit_signal
        self.gw_status_queue = gw_status_queue
        self.logger = logger
        self.gateways_and_sinks = {}

    # pylint: disable=locally-disabled, too-many-nested-blocks, too-many-branches
    def run(self):
        while not self.exit_signal.is_set():
            try:
                status_msg = self.gw_status_queue.get(block=True, timeout=60)
                self.logger.info("HTTP status_msg={}".format(status_msg))
                # New status of gateway received.
                if status_msg["gw_id"] not in self.gateways_and_sinks:
                    # New gateway detected
                    self.gateways_and_sinks[status_msg["gw_id"]] = {}
                # Initially mark all sinks of this gateway as not present
                for sink_id, sink in self.gateways_and_sinks[
                    status_msg["gw_id"]
                ].items():
                    sink["present"] = False

                for config in status_msg["configs"]:
                    # Check that mandatory field sink_id is present in message
                    if "sink_id" in config:
                        if (
                            config["sink_id"]
                            not in self.gateways_and_sinks[status_msg["gw_id"]]
                        ):
                            # New sink detected
                            self.gateways_and_sinks[status_msg["gw_id"]][
                                config["sink_id"]
                            ] = {}
                        sink = self.gateways_and_sinks[status_msg["gw_id"]][
                            config["sink_id"]
                        ]
                        # Check that other mandatory fields are present
                        if (
                            "started" in config
                            and "app_config_seq" in config
                            and "app_config_diag" in config
                            and "app_config_data" in config
                        ):
                            # All mandatory fields are present
                            sink["started"] = config["started"]
                            sink["app_config_seq"] = config["app_config_seq"]
                            sink["app_config_diag"] = config["app_config_diag"]
                            sink["app_config_data"] = config["app_config_data"]
                            sink["present"] = True
                        else:
                            # There are missing fields.
                            self.logger.warning(
                                "Mandatory fields missing from "
                                " gw-response/get_configs: {}".format(
                                    status_msg
                                )
                            )
                            sink["present"] = False
                            if "started" in sink:
                                # Sink has been present before, rely on old values
                                # and keep this sink in the configuration.
                                sink["present"] = True

                # Remove those sinks that are not present in this gateway
                # Cannot delete sink while iterating gateways_and_sinks dict,
                # thus create separate list for sinks to be deleted.
                delete = []
                for sink_id, sink in self.gateways_and_sinks[
                    status_msg["gw_id"]
                ].items():
                    if not sink["present"]:
                        delete.append(sink_id)
                        self.logger.warning(
                            "sink {}/{} is removed".format(
                                status_msg["gw_id"], sink_id
                            )
                        )
                # And delete those sinks in separate loop.
                for i in delete:
                    del self.gateways_and_sinks[status_msg["gw_id"]][i]
                self.logger.info(
                    "HTTP Server gateways_and_sinks={}".format(
                        self.gateways_and_sinks
                    )
                )

            except queue.Empty:
                self.logger.info("HTTP status_msg receiver running")


class HTTPSettings(Settings):
    """HTTP Settings"""

    _MANDATORY_FIELDS = ["http_host", "http_port"]

    def __init__(self, settings: Settings) -> "HTTPSettings":

        self.http_host = None
        self.http_port = None

        super(HTTPSettings, self).__init__(settings)

        self.hostname = self.http_host
        self.port = self.http_port


class ConnectionServer(http.server.ThreadingHTTPServer):
    """ ConnectionServer """

    # pylint: disable=locally-disabled, too-many-arguments

    close_connection = False
    request_queue_size = 10000
    allow_reuse_address = True
    timeout = 600
    protocol_version = "HTTP/1.1"

    def __init__(
        self,
        server_address,
        RequestHandlerClass,
        bind_and_activate=True,
        logger=None,
        http_tx_queue=None,
        status_observer=None,
    ):
        self.logger = logger or logging.getLogger(__name__)
        self.http_tx_queue = http_tx_queue
        self.status_observer = status_observer

        super(ConnectionServer, self).__init__(
            server_address, RequestHandlerClass, bind_and_activate
        )

    def get_request(self):
        """Get the request and client address from the socket.

        May be overridden.

        """
        try:
            value = self.socket.accept()
        except Exception as err:
            print("socket accept exception: {}".format(err))
            value = None
        return value


class HTTPObserver(StreamObserver):
    """
    HTTPObserver has three Observer functions:
    monitors the web traffic and sends requests to mqtt broker,
    monitors mqtt messages about sending status (not implemented ### TODO ###),
    monitors what gateways and sinks are online.
    """

    # pylint: disable=locally-disabled, too-many-arguments, broad-except, unused-argument
    def __init__(
        self,
        http_settings: Settings,
        start_signal: multiprocessing.Event,
        exit_signal: multiprocessing.Event,
        tx_queue: multiprocessing.Queue,
        rx_queue: multiprocessing.Queue,
        gw_status_queue: multiprocessing.Queue,
        request_wait_timeout: int = 600,
        close_connection: bool = False,
        request_queue_size: int = 1000,
        allow_reuse_address: bool = True,
        logger=None,
    ) -> "HTTPObserver":
        super(HTTPObserver, self).__init__(
            start_signal=start_signal,
            exit_signal=exit_signal,
            tx_queue=tx_queue,
            rx_queue=rx_queue,
        )

        self.logger = logger or logging.getLogger(__name__)

        self.port = http_settings.port
        self.hostname = http_settings.hostname
        self.gw_status_queue = gw_status_queue
        self.http_tx_queue = tx_queue

        self.status_observer = SinkAndGatewayStatusObserver(
            self.exit_signal, self.gw_status_queue, self.logger
        )

        while not self.exit_signal.is_set():
            try:
                # Crate the HTTP server.
                self.httpd = ConnectionServer(
                    (self.hostname, self.port),
                    wbcHTTPRequestHandler,
                    bind_and_activate=True,
                    logger=self.logger,
                    http_tx_queue=self.http_tx_queue,
                    status_observer=self.status_observer,
                )

                self.httpd.request_wait_timeout = request_wait_timeout
                self.httpd.close_connection = close_connection
                self.httpd.request_queue_size = request_queue_size
                self.httpd.allow_reuse_address = allow_reuse_address
                self.logger.info(
                    "HTTP Server is serving at port: %s", self.port
                )
                break

            except Exception as ex:
                self.logger.error(
                    "ERROR: Opening HTTP Server port %s failed. Reason: %s. Retrying after 10 seconds.",
                    self.port,
                    ex,
                )
                time.sleep(10)

    def run(self):
        """ main loop: starts status observer thread """
        self.status_observer.start()

        # Run until killed.
        try:
            while not self.exit_signal.is_set():
                # Handle a http request.
                self.logger.info("Waiting for next request")
                self.httpd.handle_request()
        except Exception as err:
            self.logger.exception(err)

        self.httpd.server_close()
        self.logger.info("HTTP Control server killed")
        self.status_observer.join()

    def kill(self):
        """Kill the gateway thread.
        """

        # Send a dummy request to let the handle_request to proceed.
        urllib.request.urlopen(
            "http://{}:{}".format(self.hostname, self.port)
        ).read()


class wbcHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    """A simple HTTP server class.

    Only overrides the do_GET from the HTTP server so it catches
    all the GET requests and processes them into commands.
    """

    # pylint: disable=locally-disabled, too-many-arguments, broad-except, unused-argument, invalid-name
    # pylint: disable=locally-disabled, too-many-statements, too-many-locals, too-many-branches, too-many-nested-blocks

    def __init__(self, request, client_address, server):
        self.logger = server.logger or logging.getLogger(__name__)
        self.http_tx_queue = server.http_tx_queue
        self.status_observer = server.status_observer
        self.mqtt_topics = Topics()
        super(wbcHTTPRequestHandler, self).__init__(
            request, client_address, server
        )

    def end_headers(self):
        self.send_my_headers()
        super().end_headers()

    def send_my_headers(self):
        self.send_header(
            "Cache-Control", "no-cache, no-store, must-revalidate"
        )
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")

    def _process_request(self, verb):
        """ Decodes an incoming http request regardless of its verb"""

        __default_command = "info"

        # Parse into commands and parameters
        splitted = urllib.parse.urlsplit(self.path)
        params = dict(
            urllib.parse.parse_qsl(urllib.parse.urlsplit(self.path).query)
        )
        try:
            command = splitted.path.split("/")[1]
        except KeyError:
            command = __default_command

        if command == "":
            command = __default_command

        self.logger.info(
            dict(
                protocol="http",
                verb=verb,
                path=self.path,
                params=str(params),
                command=command,
                gateways_and_sinks=str(
                    self.status_observer.gateways_and_sinks
                ),
            )
        )
        self._mesh_control(command, params)

    # flake8: noqa
    def do_GET(self):
        """Process a single HTTP GET request.
        """
        self._process_request("GET")

    def do_POST(self):
        """Process a single HTTP POST request.
        """
        self._process_request("POST")

    def _mesh_control(self, command, params):
        """ Decodes an incoming payload and acts upon it """

        # By default assume that gateway configuration does not need
        # refreshing after command is executed
        refresh = False

        # default http request answer and code
        error = None
        response = dict()

        response["path"] = self.path
        response["params"] = str(params)
        response["gateways_and_sinks"] = str(
            self.status_observer.gateways_and_sinks
        )
        response["command"] = command
        response["text"] = f"{command} ok!"
        response["code"] = 200

        # Go through all gateways and sinks that are currently known
        gateways_and_sinks = self.status_observer.gateways_and_sinks
        for gateway_id, sinks in gateways_and_sinks.items():

            messages = list()

            # Sends the command towards all the discovered sinks
            for sink_id, sink in sinks.items():

                if command == "datatx":
                    try:
                        dest_add = int(params["destination"])
                        src_ep = int(params["source_ep"])
                        dst_ep = int(params["dest_ep"])
                        qos = int(params["qos"])
                        payload = binascii.unhexlify(params["payload"])
                    except KeyError as error:
                        response["code"] = 500
                        response["text"] = f"Missing field: {error}"
                        break
                    except Exception as error:
                        response["code"] = 500
                        response["text"] = f"Unkonwn error: {error}"
                        break

                    try:
                        is_unack_csma_ca = params["fast"] in [
                            "true",
                            "1",
                            "yes",
                            "y",
                        ]
                    except KeyError:
                        is_unack_csma_ca = False

                    try:
                        hop_limit = int(params["hoplimit"])
                    except KeyError:
                        hop_limit = 0

                    try:
                        count = int(params["count"])
                    except KeyError:
                        count = 1

                    # sends a or multiple messages according to the count
                    # parameter in the request
                    while count:
                        count -= 1
                        message = self.mqtt_topics.request_message(
                            "send_data",
                            **dict(
                                sink_id=sink_id,
                                gw_id=gateway_id,
                                dest_add=dest_add,
                                src_ep=src_ep,
                                dst_ep=dst_ep,
                                qos=qos,
                                payload=payload,
                                is_unack_csma_ca=is_unack_csma_ca,
                                hop_limit=hop_limit,
                            ),
                        )
                        messages.append(message)

                elif command == "start":

                    new_config = dict(started=True)
                    message = self.mqtt_topics.request_message(
                        "set_config",
                        **dict(
                            sink_id=sink_id,
                            gw_id=gateway_id,
                            new_config=new_config,
                        ),
                    )
                    messages.append(message)
                    refresh = True

                elif command == "stop":

                    new_config = dict(started=False)
                    message = self.mqtt_topics.request_message(
                        "set_config",
                        **dict(
                            sink_id=sink_id,
                            gw_id=gateway_id,
                            new_config=new_config,
                        ),
                    )
                    messages.append(message)
                    refresh = True

                elif command == "setconfig":

                    try:
                        seq = int(params["seq"])
                    except KeyError:
                        if sink["app_config_seq"] == 254:
                            seq = 1
                        else:
                            seq = sink["app_config_seq"] + 1
                    try:
                        diag = int(params["diag"])
                    except KeyError:
                        diag = sink["app_config_diag"]

                    try:
                        data = bytes.fromhex(params["data"])
                    except KeyError:
                        data = sink["app_config_data"]

                    new_config = dict(
                        app_config_diag=diag,
                        app_config_data=data,
                        app_config_seq=seq,
                    )
                    message = self.mqtt_topics.request_message(
                        "set_config",
                        **dict(
                            sink_id=sink_id,
                            gw_id=gateway_id,
                            new_config=new_config,
                        ),
                    )
                    messages.append(message)
                    refresh = True

                elif command == "info":

                    response["command"] = command
                    response["gateway"] = gateway_id
                    response["sink"] = sink_id
                    response["started"] = sink["started"]
                    response["app_config_seq"] = str(sink["app_config_seq"])
                    response["app_config_diag"] = str(sink["app_config_diag"])
                    response["app_config_data"] = str(sink["app_config_data"])
                    refresh = True

                else:

                    response["code"] = 500
                    response["text"] = "Unknown command"
                    break

                # Renews information about remote gateways
                if refresh:
                    refresh = False
                    message = self.mqtt_topics.request_message(
                        "get_configs", **dict(gw_id=gateway_id)
                    )
                    messages.append(message)

                # sends all messages
                for message in messages:
                    self.logger.info({message["topic"]: str(message["data"])})
                    self.http_tx_queue.put(message)

        if response["code"] != 200:
            self.logger.error(response)

        # send code and response message
        self.send_response(code=response["code"], message=response["text"])
        self.end_headers()
        self.logger.info(response)
