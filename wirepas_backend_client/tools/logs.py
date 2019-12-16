"""
    Logs
    ====

    Contains helpers to setup the application logging facilities

    .. Copyright:
        Copyright 2019 Wirepas Ltd under Apache License, Version 2.0.
        See file LICENSE for full license details.
"""


import logging
import sys

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

    @staticmethod
    def add_sequence(record):
        """ If the record contains arguments, a sequence is field is added to the message """
        args = record.args
        if "sequence" in args:
            try:
                record.msg["sequence"] = record.args["sequence"]
            except (KeyError, TypeError):
                record.msg = dict(
                    msg=record.msg, sequence=record.args["sequence"]
                )


class LoggerHelper:
    """LoggerHelper"""

    DEBUG_LEVEL_VALUE_MQTT = 2

    def __init__(self, module_name, args=None, level: str = None):
        super(LoggerHelper, self).__init__()

        if args:
            for key, value in args.__dict__.items():
                if value is not None or "fluent" in key:
                    self.__dict__[key] = value

        if level is None:
            level = "debug"

        self._logger = logging.getLogger(module_name)
        self._name = module_name
        self._level = level.upper()
        self._handlers = dict()

        self.add_custom_level(
            name="MQTT", logger=self.logger, value=self.DEBUG_LEVEL_VALUE_MQTT
        )
        self._log_format = dict()
        self._log_format["stdout"] = logging.Formatter(
            "%(asctime)s | [%(levelname)s] %(name)s@%(filename)s:%(lineno)d: %(message)s"
        )

        self._log_format["stderr"] = logging.Formatter(
            "%(asctime)s | [%(levelname)s] %(name)s@%(filename)s:%(lineno)d: %(message)s"
        )

        self._log_format["fluentd"] = {
            "host": "%(hostname)s",
            "where": "%(module)s%(filename)s:%(lineno)d",
            "type": "%(levelname)s",
            "stack_trace": "%(exc_text)s",
        }

        try:
            self._logger.setLevel(getattr(logging, self._level))
        except Exception:
            self._logger.error("unrecognized log level %s", self._level)
            self._logger.setLevel(logging.DEBUG)
            raise

    @property
    def logger(self):
        """ Returns the inner logger object """
        return self._logger

    @property
    def level(self):
        """ Return the logging level """
        return self._level

    @level.setter
    def level(self, value):
        """ Sets the log level """
        self._level = "{0}".format(value.upper())

        try:
            self._logger.setLevel(getattr(logging, self._level))
        except Exception:
            self._logger.setLevel(logging.DEBUG)

    @staticmethod
    def add_custom_level(name, value, logger, level_callback=None):
        """ Add a custom logging level """

        def level_handler(self, message, *args, **kwargs):
            if self.isEnabledFor(value):
                self.log(value, message, *args, **kwargs)

        if hasattr(logging, name):
            return

        if level_callback:
            callback = level_callback
        else:
            callback = level_handler

        logging.addLevelName(value, name)
        setattr(logging, name, value)
        setattr(logging.Logger, name.lower(), callback)

        if logging.getLevelName(value) != name.upper():
            raise ValueError("Log name does not match")

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

    def add_stderr(self, value="error"):
        """ Adds a handler for stderr """
        try:
            if self._handlers["stderr"]:
                self._handlers["stderr"].close()
        except KeyError:
            self._handlers["stderr"] = None

        self._handlers["stderr"] = logging.StreamHandler(stream=sys.stderr)
        self._handlers["stderr"].setFormatter(self.format("stderr"))
        # By default stderr handler limits logging level to error.
        # In case logger itself has higher value, e.g. critical,
        # it will limit the input of this handler.
        try:
            level = "{0}".format(value.upper())
            self._handlers["stderr"].setLevel(getattr(logging, level))
        except Exception:
            self._handlers["stderr"].setLevel(logging.ERROR)
        self._logger.addHandler(self._handlers["stderr"])

    def add_fluentd(self):
        """ Adds a handler for fluentd if the hostname has been defined """
        try:
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
        except AttributeError:
            self._logger.warning(
                "Fluentd hostname not defined in settings. Skipping!"
            )

    def setup(self, level: str = None, propagate: bool = False):
        """
        Constructs the logger with the system arguments provided upon
        the object creation.
        """

        if level is not None:
            self.level = level

        self.add_stdout()
        self.add_fluentd()
        self._logger.propagate = propagate

        return self._logger

    def close(self):
        """ Attempts to close log handlers """
        for name, handler in self._handlers.items():
            try:
                handler.close()
            except Exception as err:
                self._logger.error(
                    "Could not close logging handler %s due to %s", name, err
                )
