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

import wirepas_messaging.wpe as messaging
from ...tools import ParserHelper, LoggerHelper, JsonSerializer
from . import Service, WPESettings


def main():
    """ Main entrypoint to connect and talk to a WPE instance """

    parse = ParserHelper(description="WPE client arguments")

    parse.add_file_settings()
    parse.add_fluentd()
    parse.add_wpe()

    settings = parse.settings(settings_class=WPESettings)

    logger = LoggerHelper(
        module_name="wm-wpe-viewer", args=settings, level=settings.debug_level
    ).setup()

    if settings.sanity():

        # loads connection details from a json file
        service_definition = json.loads(
            open(settings.wpe_service_definition).read()
        )
        service = Service(
            service_definition["flow"],
            service_handler=messaging.flow_managerStub,
        )
        service.dial(secure=settings.wpe_unsecure)

        # checks if the remote server is connected
        try:
            response = service.stub.status(messaging.Query())
            logger.debug("{status}".format(status=response))

        except Exception as err:
            logger.exception("failed to query status - {}".format(err))

        # subscribe to the flow if a network id is provided
        if settings.wpe_network is not None:
            subscription = messaging.Query(network=settings.wpe_network)
            status = service.stub.subscribe(subscription)
            logger.debug("subscription status: {status}".format(status=status))

            if status.code == status.CODE.Value("SUCCESS"):

                subscription.subscriber_id = status.subscriber_id
                logger.info(
                    "observation starting for: {0}".format(subscription)
                )

                try:
                    for message in service.stub.observe(subscription):
                        logger.info(
                            "{utc} | {message}".format(
                                utc=datetime.datetime.utcnow().isoformat("T"),
                                message=JsonSerializer.serialize(message),
                            )
                        )

                except KeyboardInterrupt:
                    pass

                subscription = service.stub.unsubscribe(subscription)

                logger.info(
                    "subscription termination:{0}".format(subscription)
                )

            else:
                logger.error("insufficient parameters")

    else:
        logger.error("Please provide a valid service definition.")
        raise ValueError("Please provide a valid service definition.")


if __name__ == "__main__":

    main()
