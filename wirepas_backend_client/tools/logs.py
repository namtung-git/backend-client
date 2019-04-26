"""
    Logs
    ====

    Contains helpers to setup the application logging facilities

    .. Copyright:
        Wirepas Oy licensed under Apache License, Version 2.0.
        See file LICENSE for full license details.
"""

import sys
import logging
from fluent import handler as fluent_handler


class ContextFilter(logging.Filter):
    """
    This is a filter which injects contextual information into the log.

    Rather than use actual contextual information, we just use random
    data in this demo.
    """

    def filter(self, record):
        try:
            self.add_sequence(record)
        except KeyError:
            pass

        return True

    def add_sequence(self, record):
        args = record.args
        if "sequence" in args:
            try:
                record.msg["sequence"] = record.args["sequence"]
            except (KeyError, TypeError):
                record.msg = dict(
                    msg=record.msg, sequence=record.args["sequence"]
                )


class LoggerHelper(object):
    """docstring for LoggerHelper"""

    def __init__(self, module_name, args, level: str = "debug", **kwargs):
        super(LoggerHelper, self).__init__()

        for key, value in args.__dict__.items():
            if value is not None or "fluent" in key:
                self.__dict__[key] = value

        self._logger = logging.getLogger(module_name)
        self._name = module_name
        self._level = "{0}".format(level.upper())
        self._handlers = dict()

        self._log_format = dict()
        self._log_format["stdout"] = logging.Formatter(
            "%(asctime)s | [%(levelname)s] %(name)s: %(message)s"
        )

        self._log_format["fluentd"] = {
            "host": "%(hostname)s",
            "where": "%(module)s.%(funcName)s",
            "type": "%(levelname)s",
            "stack_trace": "%(exc_text)s",
        }

        try:
            self._logger.setLevel(eval("logging.{0}".format(self._level)))
        except Exception:
            self._logger.setLevel(logging.DEBUG)

    @property
    def level(self):
        """ Return the logging level """
        return self._level

    @level.setter
    def level(self, value):
        """ Sets the log level """
        self._level = "{0}".format(value.upper())

        try:
            self._logger.setLevel(eval("logging.{0}".format(self._level)))
        except Exception:
            self._logger.setLevel(logging.DEBUG)

    def format(self, name):
        """ Return the format for a known stream """
        return self._log_format[name]

    def add_stdout(self):
        """ Adds a handler for stdout """
        try:
            if self._handlers["stdout"]:
                self._handlers["stdout"].close()
        except KeyError:
            self._handlers["stdout"] = None

        self._handlers["stdout"] = logging.StreamHandler(stream=sys.stdout)
        self._handlers["stdout"].setFormatter(self.format("stdout"))
        self._logger.addHandler(self._handlers["stdout"])

    def add_fluentd(self):
        """ Adds a handler for fluentd if the hostname has been defined """
        if self.fluentd_hostname:

            try:
                if self._handlers["fluentd"]:
                    self._handlers["fluentd"].close()
            except KeyError:
                self._handlers["fluentd"] = None

            print(
                "sending logs to fluentd at: {}".format(
                    (
                        self.fluentd_tag,
                        self.fluentd_record,
                        self.fluentd_hostname,
                        self.fluentd_port,
                    )
                )
            )

            self._handlers["fluentd"] = fluent_handler.FluentHandler(
                "{}.{}".format(self.fluentd_tag, self.fluentd_record),
                host=self.fluentd_hostname,
                port=self.fluentd_port,
            )
            fluentd_formatter = fluent_handler.FluentRecordFormatter(
                self.format("fluentd")
            )

            self._handlers["fluentd"].setFormatter(fluentd_formatter)
            self._logger.addHandler(self._handlers["fluentd"])
            self._logger.addFilter(ContextFilter())

    def setup(self, level: str = None):
        """
        Constructs the logger with the system arguments provided upon
        the object creation.
        """

        if level is not None:
            self.level = level

        self.add_stdout()
        self.add_fluentd()

        return self._logger

    def add_custom_level(self, debug_level_name, debug_level_number):
        """ Add a custom debug level for log filtering purposes.
            To set a logging level called sensitive please call

            self.add_custom_level(debug_level_name='sensitive',
                                  debug_level_number=100)

            afterwards the method will be available to the logger as

            logger.sensitive('my logging message')
        """

        logging.addLevelName(debug_level_number, debug_level_name.upper())

        def cb(self, message, *pargs, **kws):
            # Yes, logger takes its '*pargs' as 'args'.
            if self.isEnabledFor(debug_level_number):
                self._log(debug_level_number, message, pargs, **kws)

        setattr(logging.Logger, debug_level_name, cb)

        assert (
            logging.getLevelName(debug_level_number)
            == debug_level_name.upper()
        )

    def close(self):
        """ Attempts to close log handlers """
        for name, handler in self._handlers.items():
            try:
                handler.close()
            except:
                pass
