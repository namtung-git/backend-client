"""
    Main
    ====

    Defines the package's entrypoints.

    .. Copyright:
        Copyright 2019 Wirepas Ltd under Apache License, Version 2.0.
        See file LICENSE for full license details.
"""

import argparse
import sys

from .api.wnt import wnt_main
from .api.wpe import wpe_main
from .cli import start_cli
from .kpi_tester import start_kpi_tester
from .provisioning import prov_main


def wnt_client():
    """ launches the wnt client """
    wnt_main()


def gw_cli():
    """ launches the gateway client """
    start_cli()


def wpe_client():
    """ launches the wpe client """
    wpe_main()


def kpi_tester():
    """ launches the wpe client """
    start_kpi_tester()


def provisioning_server():
    """ launches the provisioning server """
    prov_main()


def start_backend_client():
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", help="mode help")
    parser.add_argument("--settings", help="settings help")

    parse_ok: bool = False

    try:
        args = parser.parse_args()
        parse_ok = True
    except Exception:
        print(
            "Add mode using 'cli' 'wnt_client' 'wpe_client' "
            "'provisioning_server' or 'kpi_tester' as first argument"
        )

    # CShop mode argument
    if parse_ok is True:
        arg_list: list = [sys.argv[0]]
        for a in sys.argv[2:]:
            arg_list.append(a)
        sys.argv = arg_list

        if args.mode == "cli":
            gw_cli()
        elif args.mode == "kpi_tester":
            start_kpi_tester()
        elif args.mode == "provisioning_server":
            provisioning_server()
        elif args.mode == "wpe_client":
            wpe_client()
        elif args.mode == "wnt_client":
            wnt_client()
        else:
            print(
                "Add mode using 'cli' 'wnt_client' 'wpe_client' "
                "'provisioning_server' or 'kpi_tester' as first argument"
            )
    else:
        # Launch default
        gw_cli()


if __name__ == "__main__":
    start_backend_client()
