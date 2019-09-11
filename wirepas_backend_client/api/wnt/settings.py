"""
    Backend
    =======

    .. Copyright:
        Copyright 2019 Wirepas Ltd under Apache License, Version 2.0.
        See file LICENSE for full license details.

"""
# pylint: disable=locally-disabled, duplicate-code

from ...tools import Settings


class WNTSettings(Settings):
    """WNT Settings"""

    def __init__(self, settings: Settings) -> "WNTSettings":

        self.wnt_username = None
        self.wnt_password = None
        self.wnt_hostname = None

        super(WNTSettings, self).__init__(settings)

    def sanity(self) -> bool:
        """ Checks if connection parameters are valid """
        is_valid = (
            self.wnt_username is not None
            and self.wnt_password is not None
            and self.wnt_hostname is not None
        )

        return is_valid
