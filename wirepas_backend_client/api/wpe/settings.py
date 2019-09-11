"""
    Caller
    =======

    .. Copyright:
        Copyright 2019 Wirepas Ltd under Apache License, Version 2.0.
        See file LICENSE for full license details.

"""
# pylint: disable=locally-disabled, duplicate-code

from ...tools import Settings


class WPESettings(Settings):
    """WPE Settings"""

    def __init__(self, settings: Settings) -> "WPESettings":

        self.wpe_service_definition = None
        self.wpe_network = None
        self.wpe_unsecure = False

        super(WPESettings, self).__init__(settings)

    def sanity(self) -> bool:
        """ Checks if connection parameters are valid """
        is_valid = self.wpe_service_definition is not None
        return is_valid
