# Wirepas Oy
#
# See file LICENSE for full license details.

import os
import requests
import wirepas_backend_client
from wirepas_backend_client.api import Influx

from wirepas_backend_client.api import InfluxSettings
from wirepas_backend_client.tools import ParserHelper, LoggerHelper


def main(settings, logger):
    """ Main loop """

    influx = Influx(
        hostname=settings.hostname,
        port=settings.port,
        user=settings.username,
        password=settings.password,
        database=settings.database,
        ssl=settings.ssl,
        verify_ssl=settings.verify_ssl,
    )

    results = list()

    try:
        influx.connect()
        result = influx.location_measurements(60)
        print("Location measurement {}".format(result))
        result = influx.location_updates()
        print("Location update {}".format(result))

    except requests.exceptions.ConnectionError:
        results = "Could not find host"

    return results


if __name__ == "__main__":

    try:
        debug_level = os.environ["DEBUG_LEVEL"]
    except KeyError:
        debug_level = "debug"

    parser = ParserHelper.default_args("Gateway client arguments")
    settings = parser.settings(settings_class=InfluxSettings)

    log = LoggerHelper(
        module_name="Influx viewer", args=parser.arguments, level=debug_level
    )
    logger = log.setup()

    results = main(settings, logger)
