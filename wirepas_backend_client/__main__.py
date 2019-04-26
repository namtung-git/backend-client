"""
    Main
    =======

    Contains a generic interface to handle network to object translations.

    .. Copyright:
        Wirepas Oy licensed under Apache License, Version 2.0.
        See file LICENSE for full license details.
"""

import os
import json
import argparse
import datetime
import grpc
import wirepas_messaging

from wirepas_backend_client.api.wpe import Service
from wirepas_backend_client.tools import Settings, ParserHelper, LoggerHelper
from wirepas_backend_client.api.wnt import Backend
from wirepas_backend_client.cli import launch_cli


def wnt_client():
    """ launches the wnt client """

    parse = ParserHelper(description="WNT backend client arguments")

    parse.add_file_settings()
    parse.add_wnt()
    settings = parse.settings()

    try:
        Backend(settings).run(False)
    except AttributeError:
        print("There is something wrong with your wnt arguments.")
        print("Here's the configuration interpreted:\n {}".format(settings))


def gw_cli():
    """ launches the gateway client """

    parser = ParserHelper.default_args("Gateway client arguments")
    args = parser.arguments

    try:
        debug_level = os.environ["WM_DEBUG_LEVEL"]
    except KeyError:
        debug_level = "warning"

    my_log = LoggerHelper(module_name="gw-cli", args=args, level=debug_level)
    logger = my_log.setup()
    launch_cli(args, logger)


def wpe_client():
    """ launches the wpe client """

    parse = ParserHelper(description="WPE backend client arguments")

    parse.add_file_settings()
    parse.add_wpe()

    settings = parse.settings()

    if settings.wpe_service_definition:
        service_definition = json.loads(
            open(settings.wpe_service_definition).read()
        )
    else:
        raise ValueError("Please provide a valid service definition.")

    service = Service(
        service_definition["flow"],
        service_handler=wirepas_messaging.wpe.flow_managerStub,
    )
    service.dial(secure=settings.wpe_unsecure)

    try:
        response = service.stub.status(wirepas_messaging.wpe.Query())
        print("{status}".format(status=response))

    except Exception as error:
        print("failed to query status - {error}".format(error=error))

    # subscribe to the flow if a network id is provided
    if settings.wpe_network is not None:
        subscription = wirepas_messaging.wpe.Query(
            network=settings.wpe_network
        )
        status = service.stub.subscribe(subscription)
        print("subscription status: {status}".format(status=status))

        if status.code == status.CODE.Value("SUCCESS"):

            subscription.subscriber_id = status.subscriber_id
            print("observation starting for: {0}".format(subscription))

            try:
                for message in service.stub.observe(subscription):
                    print("<< {}".format(datetime.datetime.now()))
                    print("{0}".format(message))
                    print("===")

            except KeyboardInterrupt:
                pass

            subscription = service.stub.unsubscribe(subscription)

            print("subscription termination:{0}".format(subscription))

        else:
            print("unsuficient parameters")


if __name__ == "__main__":
    gw_cli()
