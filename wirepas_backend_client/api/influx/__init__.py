"""

    Influx Module
    =============

    This module contains wrappers to talk with an influx database.

    It is especially targetting influxdb with a WNT data model.

    WNT databases:
        - analytics_next_hop
        - analytics_nodestate
        - analytics_packet
        - analytics_traveltime_kpi
        - endpoint_251
        - endpoint_252
        - endpoint_253
        - endpoint_254
        - location_measurement
        - location_update

    .. Copyright:
        Copyright 2019 Wirepas Ltd under Apache License, Version 2.0.
        See file LICENSE for full license details.
"""


from wirepas_backend_client.api.influx.connectors import Influx
from wirepas_backend_client.api.influx.settings import InfluxSettings, Settings

__all__ = ["InfluxSettings", "Influx", "Settings"]
