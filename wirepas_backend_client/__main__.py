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
import datetime
import wirepas_messaging

from .cli import launch_cli
from .api.wnt import Backend
from .api.wpe import Service
from .api import MQTTSettings
from .tools import ParserHelper, LoggerHelper


def wnt_client():
    """ launches the wnt client """

    parser = ParserHelper(description="WNT backend client arguments")

    parser.add_file_settings()
    parser.add_wnt()
    settings = parser.settings()

    try:
        Backend(settings).run(False)
    except AttributeError:
        print("There is something wrong with your wnt arguments.")


def gw_cli():
    """ launches the gateway client """

    parser = ParserHelper("Gateway client arguments")

    parser.add_file_settings()
    parser.add_mqtt()
    parser.add_fluentd()

    settings = parser.settings(settings_class=MQTTSettings)

    if settings.sanity():
        try:
            debug_level = os.environ["WM_DEBUG_LEVEL"]
        except KeyError:
            debug_level = "warning"

        my_log = LoggerHelper(
            module_name="gw-cli", args=settings, level=debug_level
        )
        logger = my_log.setup()

        launch_cli(settings, logger)
    else:
        print("Please review your connection settings")


def wpe_client():
    """ launches the wpe client """

    parser = ParserHelper(description="WPE backend client arguments")

    parser.add_file_settings()
    parser.add_wpe()

    settings = parser.settings()

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
            print("insufficient parameters")


if __name__ == "__main__":
    gw_cli()
