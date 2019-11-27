"""
    Connectors
    ==========

    .. Copyright:
        Copyright 2019 Wirepas Ltd under Apache License, Version 2.0.
        See file LICENSE for full license details.

"""

import grpc


class Service(object):
    """
    Service establishes a channel to the given service

    Attributes:
        service_definition (dict) : dictionary with
                                    {
                                     'address':host,
                                     'client': handler
                                     'name':service_name
                                     }.

        stub (grpc stub) : grpc service object
        channel (grpc channel) : grpc channel
    """

    def __init__(self, service_definition: dict, service_handler=None):
        super(Service, self).__init__()
        self._service_definition = service_definition
        self._authority = None
        self.stub = None
        self.channel = None

        if service_handler:
            self._service_handler = service_handler
        else:
            try:
                self._service_handler = self._service_definition["client"]
            except KeyError:
                raise KeyError(
                    "Missing client key " "(service handler callback)"
                )

    def __getattr__(self, name):
        return self.stub.name

    @property
    def service_definition(self):
        """ Returns WPE service configuration """
        return self._service_definition

    @property
    def handler(self):
        """ Returns the client handler from the service definition """
        return self._service_definition["client"]

    @property
    def address(self):
        """ Returns the server address from the service definition """
        return self._service_definition["address"]

    @property
    def ssl_root_certificate(self):
        """ Returns the ca certificate path from the service definition """
        return self._service_definition["root.crt"]

    @property
    def ssl_client_key(self):
        """ Returns the client key path from the service definition """
        return self._service_definition["client.key"]

    @property
    def ssl_client_certificate(self):
        """ Returns the client certificate path from the service definition """
        return self._service_definition["client.crt"]

    @property
    def ssl_host_cn_override(self):
        """ Returns the comon name override string from the service definition """
        return self._service_definition["override_cn"]

    def dial(self, unsecure=False, cb=None):
        """

        Dial establishes a grpc channel

        Args:
            secure (bool): when false uses insecure connections
            cb (fct): a function callback to handle the channel status

        """

        if not unsecure:
            try:
                self._secure_connection(cb)
            except KeyError:
                self._insecure_connection(cb)
        else:
            self._insecure_connection(cb)

        if cb is not None:
            self.channel.subscribe(cb)

        self.stub = self._service_handler(self.channel)

    def _insecure_connection(self, cb=None):
        """ Constructs an insecure channel """
        self.channel = grpc.insecure_channel(self.address)

    def _secure_connection(self, cb=None):
        """ Constructs an insecure channel """
        self._authority = grpc.ssl_channel_credentials(
            root_certificates=open(self.ssl_root_certificate, "rb").read(),
            private_key=open(self.ssl_client_key, "rb").read(),
            certificate_chain=open(self.ssl_client_certificate, "rb").read(),
        )

        self.channel = grpc.secure_channel(
            self.address,
            self._authority,
            options=(
                ("grpc.ssl_target_name_override", self.ssl_host_cn_override),
            ),
        )

    def __str__(self):
        return str(self._service_definition)
