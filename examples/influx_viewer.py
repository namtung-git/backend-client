# Wirepas Oy
#
# See file LICENSE for full license details.

import os
import requests

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

        r = influx.location_measurements(60)
        if r:
            results.append(r)
            logger.info("Location measurement {}".format(r))

        r = influx.location_updates()
        if r:
            results.append(r)
            logger.info("Location update {}".format(r))

    except requests.exceptions.ConnectionError:
        results = "Could not find host"

    return results


if __name__ == "__main__":

    try:
        debug_level = os.environ["DEBUG_LEVEL"]
    except KeyError:
        debug_level = "debug"

    parser = ParserHelper("Gateway client arguments")
    parser.add_file_settings()
    parser.add_influx()
    parser.add_fluentd()
    settings = parser.settings(settings_class=InfluxSettings)

    if settings.sanity():
        log = LoggerHelper(
            module_name="Influx viewer", args=settings, level=debug_level
        )
        logger = log.setup()

        results = main(settings, logger)
    else:
        print("Please check your connection settings")
