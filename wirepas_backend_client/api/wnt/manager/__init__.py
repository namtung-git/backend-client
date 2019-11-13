"""
    Manager
    =======

    Module to handle the sockets endpoints


    classDiagram
    Object <|-- Backend
    Backend : settings // connection details
    Backend : session_id // websocket session
    Backend : serializer // handles conversion to json
    Backend : AuthenticationManager authentication
    Backend : RealtimeManager realtime
    Backend : MetadataManager metadata

    Manager <|-- Authentication
    Manager <|-- Metadata
    Manager <|-- Realtime


    Manager: logger
    Manager: name
    Manager: hostname
    Manager: port
    Manager: session_id
    Manager: _max_queue_length
    Manager: _rx_queue
    Manager: _tx_queue
    Manager: _is_ready
    Manager: _is_ready
    Manager: socket

    Authentication: AuthenticationMessages messages
    Authentication: username
    Authentication: password

    Metadata: RealtimeSituationMessages messages


    .. Copyright:
        Copyright 2019 Wirepas Ltd under Apache License, Version 2.0.
        See file LICENSE for full license details.
"""

# flake8: noqa

from .authentication import AuthenticationManager
from .manager import Manager
from .metadata import MetadataManager
from .realtime import RealtimeManager
