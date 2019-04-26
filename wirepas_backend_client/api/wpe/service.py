"""
    Caller
    =======

    .. Copyright:
        Wirepas Oy licensed under Apache License, Version 2.0.
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
        return self._service_definition

    @property
    def handler(self):
        return self._service_definition["client"]

    @property
    def address(self):
        return self._service_definition["address"]

    @property
    def ssl_root_certificate(self):
        return self._service_definition["root.crt"]

    @property
    def ssl_client_key(self):
        return self._service_definition["client.key"]

    @property
    def ssl_client_certificate(self):
        return self._service_definition["client.crt"]

    @property
    def ssl_host_cn_override(self):
        return self._service_definition["override_cn"]

    def dial(self, secure=True, cb=None):

        if secure:
            try:
                self._secure_connection(cb)
            except KeyError:
                self._unsecure_connection(cb)
        else:
            self._unsecure_connection(cb)

        if cb is not None:
            self.channel.subscribe(cb)

        self.stub = self._service_handler(self.channel)

    def _unsecure_connection(self, cb=None):
        self.channel = grpc.insecure_channel(self.address)

    def _secure_connection(self, cb=None):

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
