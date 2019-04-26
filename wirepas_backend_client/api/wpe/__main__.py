"""
    WPE Client
    ==========

    Simple example on how to communicate with the
    wirepas positioning services

    For this example to run successfully,
    you will need to have an instance
    of the engine up and running.

    You will also need a valid service
    definition file with the correct
    certificates in place

    .. Copyright:
        Wirepas Oy licensed under Apache License, Version 2.0.
        See file LICENSE for full license details.

"""
import datetime
import json
import argparse

import grpc

import wirepas_messaging.wpe as messaging
from ...tools import ParserHelper
from . import Service


def main():
    parse = ParserHelper(description="WPE backend client arguments")

    parse.add_file_settings()
    parse.add_wpe()

    args = parse.arguments

    if args.wpe_service_definition:
        service_definition = json.loads(
            open(args.wpe_service_definition).read()
        )
    else:
        raise ValueError("Please provide a valid service definition.")

    service = Service(
        service_definition["flow"], service_handler=messaging.flow_managerStub
    )
    service.dial(secure=args.wpe_unsecure)

    try:
        response = service.stub.status(messaging.Query())
        print("{status}".format(status=response))

    except Exception as error:
        print("failed to query status - {error}".format(error=error))

    # subscribe to the flow if a network id is provided
    if args.wpe_network is not None:
        subscription = messaging.Query(network=args.wpe_network)
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

    main()
