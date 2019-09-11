"""
    Settings
    ==========

    .. Copyright:
        Copyright 2019 Wirepas Ltd under Apache License, Version 2.0.
        See file LICENSE for full license details.
"""
# pylint: disable=locally-disabled, duplicate-code

from ...tools import Settings


class MySQLSettings(Settings):
    """MySQL Settings"""

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

    def sanity(self) -> bool:
        """ Checks if connection parameters are valid """

        is_valid = (
            self.username is not None
            and self.password is not None
            and self.hostname is not None
            and self.port is not None
        )

        return is_valid
