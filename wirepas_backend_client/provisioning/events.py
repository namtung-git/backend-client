"""
    Provisioning events
    ===================

    .. Copyright:
        Copyright 2020 Wirepas Ltd under Apache License, Version 2.0.
        See file LICENSE for full license details.
"""

from wirepas_backend_client.messages import GenericMessage


class ProvisioningEvent(object):
    def __init__(self):
        super(ProvisioningEvent, self).__init__()
        self.type = "generic"


class ProvisioningEventTimeout(ProvisioningEvent):
    def __init__(self):
        super(ProvisioningEventTimeout, self).__init__()
        self.type = "timeout"


class ProvisioningEventPacketReceived(ProvisioningEvent):
    def __init__(self, msg: GenericMessage):
        super(ProvisioningEventPacketReceived, self).__init__()
        self.type = "packet_rxd"
        self.msg = msg


class ProvisioningEventPacketSent(ProvisioningEvent):
    def __init__(self, req_id, res):
        super(ProvisioningEventPacketSent, self).__init__()
        self.type = "packet_sent"
        self.req_id = req_id
        self.res = res
