"""
    Settings
    ========

    .. Copyright:
        Copyright 2019 Wirepas Ltd under Apache License, Version 2.0.
        See file LICENSE for full license details.
"""

# pylint: disable=locally-disabled, duplicate-code

from wirepas_backend_client.tools import Settings


class InfluxSettings(Settings):
    """Influx Settings"""

    _MANDATORY_FIELDS = [
        "influx_username",
        "influx_password",
        "influx_hostname",
        "influx_port",
    ]

    def __init__(self, settings: Settings) -> "InfluxSettings":

        # these are the settings expected from the cmd arguments
        self.influx_username = None
        self.influx_password = None
        self.influx_hostname = None
        self.influx_database = None
        self.influx_port = None
        self.verify_ssl = None
        self.ssl = None
        self.write_csv = None
        self.influx_skip_ssl = None
        self.influx_skip_ssl_check = None

        super(InfluxSettings, self).__init__(settings)

        self.username = self.influx_username
        self.password = self.influx_password
        self.hostname = self.influx_hostname
        self.database = self.influx_database
        self.port = self.influx_port
        self.verify_ssl = not self.influx_skip_ssl_check
        self.ssl = not self.influx_skip_ssl

        if self.write_csv:
            if ".csv" not in self.write_csv:
                self.write_csv += ".csv"

    def __str__(self):
        return super()._helper_str(key_filter="influx")
