"""
    Utils
    =======

    Contains multipurpose utilities for serializing objects and obtaining
    arguments from the command line.

    .. Copyright:
        Wirepas Oy licensed under Apache License, Version 2.0.
        See file LICENSE for full license details.
"""
import sys
import json
import logging
import argparse
import datetime
import time
import yaml
import threading

from fluent import handler as fluent_handler


def deferred_thread(fn):
    """
    Decorator to handle a request on its own Thread
    to avoid blocking the calling Thread on I/O.
    It creates a new Thread but it shouldn't impact the performances
    as requests are not supposed to be really frequent (few per seconds)
    """

    def wrapper(*args, **kwargs):
        thread = threading.Thread(target=fn, args=args, kwargs=kwargs)
        thread.start()
        return thread

    return wrapper


class ExitSignal(object):
    """Wrapper around and exit signal"""

    def __init__(self, signal=None):
        super(ExitSignal, self).__init__()

        if signal is None:
            signal = False

        self.signal = signal

    def is_set(self) -> bool:
        try:
            self.signal.is_set()
        except AttributeError:
            return self.signal

    def set(self) -> bool:
        try:
            self.signal.set()
        except AttributeError:
            return self.signal


def chunker(seq, size) -> list():
    """
        Splits a sequence in multiple parts

        Args:
            seq ([]) : an array
            size (int) : length of each array part

        Returns:
            array ([]) : a chunk of SEQ with given SIZE
    """
    return (seq[pos : pos + size] for pos in range(0, len(seq), size))
