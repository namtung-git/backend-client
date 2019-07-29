# Copyright 2019 Wirepas Ltd

import requests

from wirepas_backend_client.api import Influx
from wirepas_backend_client.api import InfluxSettings
from wirepas_backend_client.tools import ParserHelper, LoggerHelper


def main(settings, logger):
    """ Main loop """

    influx = Influx(
        hostname=settings.hostname,
        port=settings.port,
        username=settings.username,
        password=settings.password,
        database=settings.database,
        ssl=settings.ssl,
        verify_ssl=settings.verify_ssl,
    )

    results = list()

    try:
        influx.connect()

        if settings.query_statement:
            result_set = influx.query(statement=settings.query_statement)
            if result_set:
                for point in result_set:
                    r = result_set[point]
                    results.append(r)
                    if settings.write_csv:
                        r.to_csv("{}_{}".format(point, settings.write_csv))
                    logger.info(
                        "Custom query ({}) {}:{}".format(
                            settings.query_statement, point, r
                        )
                    )

        else:
            r = influx.traffic_diagnostics(
                last_n_seconds=settings.last_n_seconds
            )
            if r:
                results.append(r)
                r.to_csv("./traffic_diagnostics.csv")
                logger.info("Traffic diagnostics (251) {}".format(r))

            r = influx.neighbor_diagnostics(
                last_n_seconds=settings.last_n_seconds
            )
            if r:
                results.append(r)
                r.to_csv("./neighbor_diagnostics.csv")
                logger.info("Neighbor diagnostics (252) {}".format(r))

            r = influx.node_diagnostics(last_n_seconds=settings.last_n_seconds)
            if r:
                results.append(r)
                r.to_csv("./node_diagnostics.csv")
                logger.info("Node diagnostics (253) {}".format(r))

            r = influx.boot_diagnostics(last_n_seconds=settings.last_n_seconds)
            if r:
                results.append(r)
                r.to_csv("./boot_diagnostics.csv")
                logger.info("Boot diagnostics (254) {}".format(r))

            r = influx.location_measurements(
                last_n_seconds=settings.last_n_seconds
            )
            if r:
                results.append(r)
                logger.info("Location measurement {}".format(r))

            r = influx.location_updates(last_n_seconds=settings.last_n_seconds)
            if r:
                results.append(r)
                logger.info("Location update {}".format(r))

    except requests.exceptions.ConnectionError:
        results = "Could not find host"

    return results, influx


if __name__ == "__main__":

    parser = ParserHelper("Gateway client arguments")
    parser.add_file_settings()
    parser.add_influx()
    parser.add_fluentd()
    parser.query.add_argument(
        "--last_n_seconds",
        default=6000,
        action="store",
        type=str,
        help="Amount of seconds to lookup in the past.",
    )
    parser.query.add_argument(
        "--write_csv",
        default="custom_query.csv",
        action="store",
        type=str,
        help="File where to write custom csv.",
    )
    settings = parser.settings(settings_class=InfluxSettings)

    if settings.sanity():
        logger = LoggerHelper(
            module_name="Influx viewer",
            args=settings,
            level=settings.debug_level,
        ).setup()
        results, influx = main(settings, logger)
    else:
        print("Please check your connection settings")
