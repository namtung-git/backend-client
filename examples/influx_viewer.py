# Copyright 2019 Wirepas Ltd
#
# Here's an example of a settings file that connects towards a secure
# instance port.
#
# Pay attention to the port and ssl flags.
#
# ---
# influx_username: user
# influx_password: userpwd
# influx_database: "wirepas"
# influx_hostname: hostname or ip
#
# influx_port: "8886"
# influx_skip_ssl: false #(default)
# influx_skip_ssl_check: false #(default)
#
# In some special cases you might want to use ssl but ignore the
# certificate validity (self hosted). For that, make sure you use:
#
# influx_skip_ssl: false
# influx_skip_ssl_check: true
#
# If you want to use a fully non secure port, please update the port number
# and set the flags accordingly:
#
# influx_skip_ssl: true
# influx_skip_ssl_check: true


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
            if not os.path.exists(settings.write_path):
                os.makedirs(settings.write_path)
            r = influx.traffic_diagnostics(
                last_n_seconds=settings.last_n_seconds,
                from_date=settings.from_date,
                until_date=settings.until_date,
            )
            if not r.empty:
                results.append(r)
                r.to_csv(
                    "{}/traffic_diagnostics.csv".format(settings.write_path)
                )
                logger.info("Traffic diagnostics (251) {}".format(r))

            r = influx.neighbor_diagnostics(
                last_n_seconds=settings.last_n_seconds,
                from_date=settings.from_date,
                until_date=settings.until_date,
            )
            if not r.empty:
                results.append(r)
                r.to_csv(
                    "{}/neighbor_diagnostics.csv".format(settings.write_path)
                )
                logger.info("Neighbor diagnostics (252) {}".format(r))

            r = influx.node_diagnostics(
                last_n_seconds=settings.last_n_seconds,
                from_date=settings.from_date,
                until_date=settings.until_date,
            )
            if not r.empty:
                results.append(r)
                r.to_csv("{}/node_diagnostics.csv".format(settings.write_path))
                logger.info("Node diagnostics (253) {}".format(r))

            r = influx.boot_diagnostics(
                last_n_seconds=settings.last_n_seconds,
                from_date=settings.from_date,
                until_date=settings.until_date,
            )
            if not r.empty:
                results.append(r)
                r.to_csv("{}/boot_diagnostics.csv".format(settings.write_path))
                logger.info("Boot diagnostics (254) {}".format(r))

            r = influx.location_measurements(
                last_n_seconds=settings.last_n_seconds,
                from_date=settings.from_date,
                until_date=settings.until_date,
            )
            if not r.empty:
                results.append(r)
                r.to_csv(
                    "{}/location_measurements.csv".format(settings.write_path)
                )
                logger.info("Location measurement {}".format(r))

            r = influx.location_updates(
                last_n_seconds=settings.last_n_seconds,
                from_date=settings.from_date,
                until_date=settings.until_date,
            )
            if not r.empty:
                results.append(r)
                r.to_csv("{}/location_updates.csv".format(settings.write_path))
                logger.info("Location update {}".format(r))

    except requests.exceptions.ConnectionError:
        results = "Could not find host"
        raise

    return results, influx


if __name__ == "__main__":

    PARSER = ParserHelper("Gateway client arguments")
    PARSER.add_file_settings()
    PARSER.add_influx()
    PARSER.add_fluentd()
    PARSER.query.add_argument(
        "--last_n_seconds",
        default=6000,
        action="store",
        type=int,
        help="Amount of seconds to lookup in the past.",
    )
    PARSER.query.add_argument(
        "--write_csv",
        default="custom_query.csv",
        action="store",
        type=str,
        help="File where to write custom csv.",
    )

    PARSER.query.add_argument(
        "--write_path",
        default="./influx_data",
        action="store",
        type=str,
        help="path where to store default queries.",
    )

    PARSER.query.add_argument(
        "--from_date",
        default=None,
        action="store",
        type=str,
        help="Datetime where to point start of data time query, eg, 2019-01-07T10:00:00Z.",
    )

    PARSER.query.add_argument(
        "--until_date",
        default=None,
        action="store",
        type=str,
        help="Datetime where to point start of data time query, eg, 2019-01-07T10:00:00Z.",
    )

    SETTINGS = PARSER.settings(settings_class=InfluxSettings)

    if SETTINGS.sanity():
        logger = LoggerHelper(
            module_name="Influx viewer",
            args=SETTINGS,
            level=SETTINGS.debug_level,
        ).setup()
        results, influx = main(SETTINGS, logger)
    else:
        print("Please review your connection settings:")
        print(SETTINGS)
