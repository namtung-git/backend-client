"""
    Arguments
    =========

    Contains helpers to parse application arguments

    .. Copyright:
        Wirepas Oy licensed under Apache License, Version 2.0.
        See file LICENSE for full license details.
"""


import json
import logging
import argparse
import datetime
import binascii
import time
import yaml
import ssl
import pkg_resources

from fluent import handler as fluent_handler


def serialize(obj) -> str:
    """ Serializes an object into json """
    return json.dumps(obj, default=json_serial, sort_keys=True, indent=4)


def json_serial(obj) -> str:
    """JSON serializer for objects not serializable by default json code"""

    if isinstance(obj, (datetime.datetime, datetime.date)):
        return obj.isoformat()

    if isinstance(obj, (bytearray, bytes)):
        return binascii.hexlify(obj)
    if isinstance(obj, set):
        return str(obj)

    raise TypeError("Type %s not serializable" % type(obj))


class Settings(object):
    """Simple class to handle library settings"""

    def __init__(self, settings: dict):
        super(Settings, self).__init__()
        for k, v in settings.items():
            self.__dict__[k] = v

    def items(self):
        return self.__dict__.items()

    @classmethod
    def from_args(cls, args, skip_undefined=True):
        settings = dict()

        try:
            if args.settings:
                with open(args.settings, "r") as f:
                    settings = yaml.load(f)
        except:
            pass

        for key, value in args.__dict__.items():
            if value is not None or skip_undefined is False:
                if key in settings and settings[key] is None:
                    settings[key] = value
                if key not in settings:
                    settings[key] = value

        return cls(settings)

    def __str__(self):
        return str(self.__dict__)


class ParserHelper(object):
    """
    ParserHelper

    Handles the creation and decoding of arguments

    """

    def __init__(
        self,
        description="argument parser",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    ):
        super(ParserHelper, self).__init__()
        self._parser = argparse.ArgumentParser(
            description=description, formatter_class=formatter_class
        )

        self._groups = dict()

    @property
    def parser(self):
        """ Returns the parser object """
        return self._parser

    @property
    def arguments(self):
        """ Returns arguments that it can parse and throwing an error otherwise """
        self._arguments = self.parser.parse_args()
        return self._arguments

    @property
    def known_arguments(self):
        """ returns the unknown arguments it could not parse """
        self._arguments, self._unknown_arguments = (
            self.parser.parse_known_args()
        )
        return self._arguments

    @property
    def unkown_arguments(self):
        """ returns the unknown arguments it could not parse """
        return self._unknown_arguments

    def settings(self, settings_class=None, skip_undefined=True) -> "Settings":
        self._arguments = self.parser.parse_args()

        if settings_class is None:
            settings_class = Settings

        settings = settings_class.from_args(self._arguments, skip_undefined)

        return settings

    def __getattr__(self, name):
        if name not in self._groups:
            self._groups[name] = self._parser.add_argument_group(name)

        return self._groups[name]

    def add_file_settings(self):
        """ For file setting handling"""
        self.file_settings.add_argument(
            "--settings",
            type=str,
            required=False,
            default="settings.yml",
            help="settings file.",
        )

    def add_mqtt(self):
        """ Commonly used MQTT arguments """

        self.mqtt.add_argument(
            "--mqtt_hostname",
            default="localhost",
            action="store",
            type=str,
            help="MQTT broker hostname ",
        )

        self.mqtt.add_argument(
            "--mqtt_topic",
            default="#",
            action="store",
            type=str,
            help="MQTT topic to subscribe to",
        )

        self.mqtt.add_argument(
            "--mqtt_username",
            default="user",
            action="store",
            type=str,
            help="MQTT broker username ",
        )

        self.mqtt.add_argument(
            "--mqtt_password",
            default="uoaiduaosjfdpkajf0+po0i318",
            action="store",
            type=str,
            help="MQTT broker password",
        )

        self.mqtt.add_argument(
            "--mqtt_port",
            default=1883,
            action="store",
            type=int,
            help="MQTT broker port",
        )

        self.mqtt.add_argument(
            "--mqtt_ca_certs",
            default=str(
                pkg_resources.resource_filename(
                    "wirepas_backend_client", "certs/extwirepas.pem"
                )
            ),
            action="store",
            type=str,
            help=(
                "A string path to the Certificate "
                "Authority certificate files that "
                "are to be treated as trusted by "
                "this client"
            ),
        )

        self.mqtt.add_argument(
            "--mqtt_certfile",
            default=None,
            action="store",
            type=str,
            help=("Strings pointing to the PEM encoded " "client certificate"),
        )

        self.mqtt.add_argument(
            "--mqtt_keyfile",
            default=None,
            action="store",
            type=str,
            help=(
                "Strings pointing to the PEM "
                "encoded client private keys "
                "respectively"
            ),
        )

        self.mqtt.add_argument(
            "--mqtt_cert_reqs",
            default=ssl.CERT_REQUIRED,
            action="store",
            type=str,
            help=(
                "Defines the certificate "
                "requirements that the client "
                "imposes on the broker"
            ),
        )

        self.mqtt.add_argument(
            "--mqtt_tls_version",
            default=ssl.PROTOCOL_TLSv1_2,
            action="store",
            type=str,
            help=(
                "Specifies the version of the "
                " SSL / TLS protocol to be used"
            ),
        )

        self.mqtt.add_argument(
            "--mqtt_ciphers",
            default=None,
            action="store",
            type=str,
            help=(
                "A string specifying which "
                "encryption ciphers are allowable "
                "for this connection"
            ),
        )

        self.mqtt.add_argument(
            "--mqtt_persist_session",
            default=True,
            action="store_true",
            help=(
                "When False the broker will buffer"
                "session packets between "
                "reconnection"
            ),
        )

        self.mqtt.add_argument(
            "--mqtt_force_unsecure",
            default=False,
            action="store_true",
            help=("When True the broker will skip " "the TLS handshake"),
        )

        self.mqtt.add_argument(
            "--mqtt_allow_untrusted",
            default=False,
            action="store_true",
            help=("When true the client will skip " "the TLS check"),
        )

    def add_test(self):
        """ Commonly used arguments for test execution """
        self.test.add_argument(
            "--delay",
            default=None,
            type=int,
            help="Initial wait in seconds - set None for random",
        )

        self.test.add_argument(
            "--duration", default=10, type=int, help="Time to collect data for"
        )

        self.test.add_argument(
            "--nodes",
            default="range(0,100)",
            type=str,
            help="Where to fetch nodes",
        )

        self.test.add_argument(
            "--jitter_minimum",
            default=0,
            type=int,
            help="Minimum amount of sleep between tasks",
        )

        self.test.add_argument(
            "--jitter_maximum",
            default=0,
            type=int,
            help="Maximum amount of sleep between tasks",
        )

        self.test.add_argument(
            "--input",
            default="report.json",
            type=str,
            help="file where to read from",
        )

        self.test.add_argument(
            "--output",
            default="report.json",
            type=str,
            help="file where to ouput the report",
        )

        self.test.add_argument(
            "--output_time",
            action="store_true",
            help=("appends datetime information to " "the output filename"),
        )

        self.test.add_argument(
            "--target_otap", default=None, type=int, help="target_otap"
        )

        self.test.add_argument(
            "--target_frequency",
            default=None,
            type=int,
            help=(
                "Number of messages that should " "be observed for each node"
            ),
        )

        self.test.add_argument(
            "--number_of_runs",
            default=1,
            type=int,
            help="Number of test runs to execute",
        )

    def add_database(self):
        """ Commonly used database arguments """
        self.database.add_argument(
            "--db_hostname",
            default=None,
            action="store",
            type=str,
            help="Database hostname",
        )

        self.database.add_argument(
            "--db_port",
            default=3306,
            action="store",
            type=int,
            help="Database port",
        )

        self.database.add_argument(
            "--db_database",
            default="dbname",
            action="store",
            type=str,
            help="Database schema to use",
        )

        self.database.add_argument(
            "--db_username",
            default="dbuser",
            action="store",
            type=str,
            help="Database user",
        )

        self.database.add_argument(
            "--db_password",
            default="dbpasswordpassword",
            action="store",
            type=str,
            help="Database password",
        )

    def add_fluentd(self):
        """ Commonly used fluentd arguments """
        self.fluentd.add_argument(
            "--fluentd_hostname",
            default=None,
            action="store",
            type=str,
            help="Fluentd hostname",
        )

        self.fluentd.add_argument(
            "--fluentd_port",
            default=24224,
            action="store",
            type=int,
            help="Fluentd port",
        )

        self.fluentd.add_argument(
            "--fluentd_record",
            default="log",
            action="store",
            type=str,
            help="Name of record to use (tag.record)",
        )

        self.fluentd.add_argument(
            "--fluentd_tag",
            default="python",
            action="store",
            type=str,
            help="How to tag outgoing data to fluentd",
        )

    def add_http(self):
        """ Commonly used http server arguments """
        self.http.add_argument(
            "--http_host",
            default="0.0.0.0",
            action="store",
            type=str,
            help=("Hostname or ip-address that " "HTTP server is bind to "),
        )

        self.http.add_argument(
            "--http_port",
            default=8000,
            action="store",
            type=int,
            help="HTTP server port ",
        )

    def add_wnt(self):
        """ WNT related settings """
        self.wnt.add_argument(
            "--wnt_username",
            type=str,
            required=False,
            default=None,
            help="username to login with.",
        )

        self.wnt.add_argument(
            "--wnt_password", type=str, default=None, help="password for user."
        )

        self.wnt.add_argument(
            "--wnt_hostname",
            default=None,
            type=str,
            help="domain where to point requests.",
        )

        self.wnt.add_argument(
            "--wnt_protocol_version",
            type=int,
            default=2,
            help="WS API protocol version.",
        )

    def add_wpe(self):
        """ Commonly used http server arguments """
        self.wpe.add_argument(
            "--wpe_service_definition",
            type=str,
            required=False,
            default="./services.json",
            help="service configuration file.",
        )

        self.wpe.add_argument(
            "--wpe_unsecure",
            required=False,
            action="store_false",
            help="forces the creation of unsecure channels.",
        )

        self.wpe.add_argument(
            "--wpe_network",
            required=False,
            default=None,
            type=int,
            help="network id to subscribe to.",
        )

    def add_influx(self):

        self.influx.add_argument(
            "--influx_hostname",
            type=str,
            required=False,
            default="localhost",
            help="hostname of InfluxDB http API",
        )

        self.influx.add_argument(
            "--influx_port",
            type=int,
            required=False,
            default=8886,
            help="port of InfluxDB http API",
        )

        self.influx.add_argument(
            "--influx_username",
            type=str,
            required=False,
            default="influx",
            help="user of InfluxDB http API",
        )

        self.influx.add_argument(
            "--influx_password",
            type=str,
            required=False,
            default="influxpwd",
            help="password of InfluxDB http API",
        )

        self.influx.add_argument(
            "--influx_database",
            type=str,
            required=False,
            default="wirepas",
            help="port of InfluxDB http API",
        )

        self.influx.add_argument(
            "--no-influx_ssl",
            action="store_false",
            required=False,
            help="use https when talking to the API",
        )

    def dump(self, path):
        """ dumps the arguments into a file """
        with open(path, "w") as f:
            f.write(serialize(vars(self._arguments)))

    @classmethod
    def default_args(cls, text="Default arguments") -> "ParserHelper":
        parse = cls(description=text)

        parse.add_file_settings()
        parse.add_mqtt()
        parse.add_test()
        parse.add_database()
        parse.add_fluentd()
        parse.add_http()

        return parse
