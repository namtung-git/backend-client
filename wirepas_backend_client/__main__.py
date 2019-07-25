"""
    Main
    =======

    Contains a generic interface to handle network to object translations.

    .. Copyright:
        Wirepas Oy licensed under Apache License, Version 2.0.
        See file LICENSE for full license details.
"""

from .cli import main as cli_main
from .api.wnt import wnt_main
from .api.wpe import wpe_main


def wnt_client():
    """ launches the wnt client """
    wnt_main()


def gw_cli():
    """ launches the gateway client """
    cli_main()


def wpe_client():
    """ launches the wpe client """
    wpe_main()


if __name__ == "__main__":
    gw_cli()
