"""
    Decorators
    ==========

    .. Copyright:
        Copyright 2019 Wirepas Ltd under Apache License, Version 2.0.
        See file LICENSE for full license details.
"""


from functools import wraps

from ...messages.interface import MessageManager


def decode_topic_message(f):
    """ Decorator to decode incoming proto message """

    @wraps(f)
    def wrapper_retrieve_message(client, userdata, message, **kwargs):
        """ Receives an MQTT message and retrieves its protobuffer """
        topic = message.topic.split("/")
        source_endpoint = topic[-2]
        destination_endpoint = topic[-1]
        message = MessageManager.map(
            source_endpoint, destination_endpoint
        ).from_bus(message.payload)
        f(message, topic)

    return wrapper_retrieve_message


def topic_message(f):
    """ Decorator to decode incoming proto message """

    @wraps(f)
    def wrapper_retrieve_message(client, userdata, message, **kwargs):
        """ Receives an MQTT message and retrieves its protobuffer """
        topic = message.topic.split("/")
        f(message.payload, topic)

    return wrapper_retrieve_message


def retrieve_message(f):
    """ Decorator to decode incoming proto message """

    @wraps(f)
    def wrapper_retrieve_message(client, userdata, message, **kwargs):
        """ Receives an MQTT message and retrieves its protobuffer """
        topic = message.topic.split("/")
        source_endpoint = topic[-2]
        destination_endpoint = topic[-1]
        data = MessageManager.map(
            source_endpoint, destination_endpoint
        ).from_bus(message.payload)
        f(data)

    return wrapper_retrieve_message
