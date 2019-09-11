"""
    Settings
    ========

    .. Copyright:
        Copyright 2019 Wirepas Ltd under Apache License, Version 2.0.
        See file LICENSE for full license details.
"""

# pylint: disable=locally-disabled, duplicate-code

from ...tools import Settings


class InfluxSettings(Settings):
    """Influx Settings"""

    def __init__(self, settings: Settings) -> "InfluxSettings":

        # these are the settings expected from the cmd arguments
        self.influx_username = None
        self.influx_password = None
        self.influx_hostname = None
        self.influx_database = None
        self.influx_port = None
        self.verify_ssl = True
        self.ssl = True
        self.write_csv = None

        super(InfluxSettings, self).__init__(settings)

        self.username = self.influx_username
        self.password = self.influx_password
        self.hostname = self.influx_hostname
        self.database = self.influx_database
        self.port = self.influx_port

        if self.write_csv:
            if ".csv" not in self.write_csv:
                self.write_csv += ".csv"

    def sanity(self) -> bool:
        """ Checks if connection parameters are valid """
        is_valid = (
            self.username is not None
            and self.password is not None
            and self.hostname is not None
            and self.port is not None
            and self.database is not None
        )

        return is_valid
