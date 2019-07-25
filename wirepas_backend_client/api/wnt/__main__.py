"""
    WNT Client
    ==========

    Simple example on how to communicate with the
    wirepas network tool services.

    .. Copyright:
        Wirepas Oy licensed under Apache License, Version 2.0.
        See file LICENSE for full license details.

"""

from .backend import WNTSettings, Backend
from ...tools import ParserHelper, LoggerHelper


def main():
    """ Main entrypoint to connect and talk to a WNT instance """

    parser = ParserHelper(description="WNT client arguments")
    parser.add_file_settings()
    parser.add_wnt()
    parser.add_fluentd()

    settings = parser.settings(settings_class=WNTSettings)

    logger = LoggerHelper(
        module_name="wm-wnt-viewer", args=settings, level=settings.debug_level
    ).setup()

    if settings.sanity():
        Backend(settings=settings, logger=logger).run(False)
    else:
        logger.error("There is something wrong with your WNT arguments.")


if __name__ == "__main__":

    main()
