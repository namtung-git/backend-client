# Copyright 2019 Wirepas Ltd
#
# See file LICENSE for full license details.
#

import multiprocessing
import http.server
import time
import urllib
import binascii
import logging
import socketserver

from threading import Thread

from .stream import StreamObserver
from ..tools import Settings
from ..tools import ExitSignal
from .. import messages
from functools import wraps
from ..messages.interface import MessageManager
from .mqtt import Topics
import queue

# Following globals are used for delivering data between
# HTTPObserver class and HTTPServer class
http_tw_queue = None
gateways_and_sinks = {}
# { 'gw_id':
#     {'sink_id':
#         {# Following fields from item of gw-response/get_configs->configs[]
#          'started': True/False,
#          'app_config_seq': int,
#          'app_config_diag': int,
#          'app_config_data': bytes,
#          # Internal field for monitoring sink's presense
#          'present': True/False
#         }
#     }
# }

mqtt_topics = Topics()


class SinkAndGatewayStatusObserver(Thread):
    def __init__(self, exit_signal, gw_status_queue, logger):
        super(SinkAndGatewayStatusObserver, self).__init__()
        self.exit_signal = exit_signal
        self.gw_status_queue = gw_status_queue
        self.logger = logger

    def run(self):
        while not self.exit_signal.is_set():
            try:
                status_msg = self.gw_status_queue.get(block=True, timeout=60)
                self.logger.info("HTTP status_msg={}".format(status_msg))
                # New status of gateway received.
                if status_msg["gw_id"] not in gateways_and_sinks:
                    # New gateway detected
                    gateways_and_sinks[status_msg["gw_id"]] = {}
                # Initially mark all sinks of this gateway as not present
                for sink_id, sink in gateways_and_sinks[
                    status_msg["gw_id"]
                ].items():
                    sink["present"] = False

                for config in status_msg["configs"]:
                    # Check that mandatory field sink_id is present in message
                    if "sink_id" in config:
                        if (
                            config["sink_id"]
                            not in gateways_and_sinks[status_msg["gw_id"]]
                        ):
                            # New sink detected
                            gateways_and_sinks[status_msg["gw_id"]][
                                config["sink_id"]
                            ] = {}
                        sink = gateways_and_sinks[status_msg["gw_id"]][
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
                            if "started" in sink:
                                # Sink has been present before, rely on old values
                                # and keep this sink in the configuration.
                                sink["present"] = True
                # Remove those sinks that are not present in this gateway
                # Cannot delete sink while iterating gateways_and_sinks dict,
                # thus create separate list for sinks to be deleted.
                delete = []
                for sink_id, sink in gateways_and_sinks[
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
                    del gateways_and_sinks[status_msg["gw_id"]][i]
                self.logger.info(
                    "HTTP Server gateways_and_sinks={}".format(
                        gateways_and_sinks
                    )
                )

            except queue.Empty:
                self.logger.info("HTTP status_msg receiver running")


class HTTPSettings(Settings):
    """HTTP Settings"""

    def __init__(self, settings: Settings) -> "HTTPSettings":

        self.http_host = None
        self.http_port = None

        super(HTTPSettings, self).__init__(settings)

        self.hostname = self.http_host
        self.port = self.http_port

    def sanity(self) -> bool:
        """ Checks if connection parameters are valid """

        is_valid = self.hostname is not None and self.port is not None

        return is_valid


class ConnectionServer(http.server.ThreadingHTTPServer):

    close_connection = False
    request_queue_size = 10
    allow_reuse_address = True
    timeout = 10
    protocol_version = "HTTP/1.0"

    def __init__(
        self, server_address, RequestHandlerClass, bind_and_activate=True
    ):

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

    def __init__(
        self,
        http_settings: Settings,
        start_signal: multiprocessing.Event,
        exit_signal: multiprocessing.Event,
        tx_queue: multiprocessing.Queue,
        rx_queue: multiprocessing.Queue,
        gw_status_queue: multiprocessing.Queue,
        request_wait_timeout: int = 10,
        close_connection: bool = False,
        request_queue_size: int = 100,
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
        global http_tx_queue
        http_tx_queue = tx_queue

        while not self.exit_signal.is_set():
            try:
                # Crate the HTTP server.
                self.httpd = ConnectionServer(
                    (self.hostname, self.port),
                    HTTPServer,
                    bind_and_activate=True,
                )
                self.logger.info(
                    "HTTP Server is serving at port: {}".format(self.port)
                )
                break
            except Exception as ex:
                self.logger.error(
                    'ERROR: Opening HTTP Server port {} failed. Reason: "{}". Retrying after 10 seconds.'.format(
                        self.port, ex
                    )
                )
                time.sleep(10)

        self.status_observer = SinkAndGatewayStatusObserver(
            self.exit_signal, self.gw_status_queue, self.logger
        )

    def run(self):
        # Start status observer thread
        self.status_observer.start()

        # Run until killed.
        try:
            while not self.exit_signal.is_set():
                # Handle a http request.
                self.logger.info("Waiting for next request")
                self.httpd.handle_request()
        except Exception as err:
            print(err)

        self.httpd.server_close()
        self.logger.info("HTTP Control server killed")
        self.status_observer.join()

    def kill(self):
        """Kill the gateway thread.
        """

        # Send a dummy request to let the handle_request to proceed.
        urllib.urlopen("http://{}:{}".format(self.hostname, self.port)).read()


class HTTPServer(http.server.SimpleHTTPRequestHandler):

    """A simple HTTP server class.

    Only overrides the do_GET from the HTTP server so it catches
    all the GET requests and processes them into commands.
    """

    # flake8: noqa
    def do_GET(self):
        """Process a single HTTP GET request.
        """

        print("GET request: {}".format(self.path))

        try:
            # Parse into commands and parameters
            splitted = urllib.parse.urlsplit(self.path)
            command = splitted.path.split("/")[1]

            # Convert the parameter list into a dictionary.
            params = dict(
                urllib.parse.parse_qsl(urllib.parse.urlsplit(self.path).query)
            )

            # By default assume good from people and their code
            http_response = 200

            # Go through all gateways and sinks that are currently known to be
            # online.
            for gateway_id, sinks in gateways_and_sinks.items():
                for sink_id, sink in sinks.items():

                    if command == "datatx":

                        try:
                            dest_add = int(params["destination"])
                            src_ep = int(params["source_ep"])
                            dst_ep = int(params["dest_ep"])
                            qos = int(params["qos"])
                            payload = binascii.unhexlify(params["payload"])
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

                            while count:
                                count -= 1

                                # Create sendable message.
                                global http_tx_queue
                                message = mqtt_topics.request_message(
                                    "send_data",
                                    dict(
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
                                # Insert the message(s) tx queue
                                http_tx_queue.put(message)

                        except Exception as err:
                            print("Malformed data tx request {}".format(err))
                            http_response = 500

                    elif command == "start":

                        new_config = {"started": True}
                        message = mqtt_topics.request_message(
                            "set_config",
                            dict(
                                sink_id=sink_id,
                                gw_id=gateway_id,
                                new_config=new_config,
                            ),
                        )
                        http_tx_queue.put(message)

                    elif command == "stop":

                        new_config = {"started": False}
                        message = mqtt_topics.request_message(
                            "set_config",
                            dict(
                                sink_id=sink_id,
                                gw_id=gateway_id,
                                new_config=new_config,
                            ),
                        )
                        http_tx_queue.put(message)

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
                        new_config = {
                            "app_config_diag": diag,
                            "app_config_data": data,
                            "app_config_seq": seq,
                        }
                        message = mqtt_topics.request_message(
                            "set_config",
                            dict(
                                sink_id=sink_id,
                                gw_id=gateway_id,
                                new_config=new_config,
                            ),
                        )
                        http_tx_queue.put(message)
                    else:
                        http_response = 500
        except Exception as err:
            print(err)

        # Respond to front-end
        self.send_response(http_response)
        self.end_headers()
