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

from wirepas_backend_client.api.wnt import wnt_main
from wirepas_backend_client.api.wpe import wpe_main
from wirepas_backend_client.cli.cli_starter import start_cli
from wirepas_backend_client.kpi_tester import start_kpi_tester
from wirepas_backend_client.provisioning import prov_main


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

    args = parser.parse_args()

    # CShop mode argument
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


if __name__ == "__main__":
    start_backend_client()
