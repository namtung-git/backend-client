"""
    Settings
    ==========

    .. Copyright:
        Copyright 2019 Wirepas Ltd under Apache License, Version 2.0.
        See file LICENSE for full license details.
"""
# pylint: disable=locally-disabled, duplicate-code

from wirepas_backend_client.tools import Settings


class MySQLSettings(Settings):
    """MySQL Settings"""

    _MANDATORY_FIELDS = [
        "db_username",
        "db_password",
        "db_hostname",
        "db_port",
    ]

    def __init__(self, settings: Settings) -> "MySQLSettings":

        self.db_username = None
        self.db_password = None
        self.db_hostname = None
        self.db_database = None
        self.db_port = None
        self.db_connection_timeout = None

        super(MySQLSettings, self).__init__(settings)

        self.username = self.db_username
        self.password = self.db_password
        self.hostname = self.db_hostname
        self.database = self.db_database
        self.port = self.db_port
        self.connection_timeout = self.db_connection_timeout

    def __str__(self):
        return super()._helper_str(key_filter="mysql")
