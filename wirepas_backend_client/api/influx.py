"""
    Influx handlers
    ===============

    .. Copyright:
        Wirepas Oy licensed under Apache License, Version 2.0.
        See file LICENSE for full license details.

"""
import re
import sys
import json
import numpy
import logging
import datetime
import influxdb
import requests
import google
import google.protobuf.json_format as jformat

import wirepas_messaging

import argparse
import pandas
from ..tools import Settings

import binascii
import multiprocessing
import queue

from .stream import StreamObserver


class InfluxSettings(Settings):
    """MySQL Settings"""

    def __init__(self, settings: Settings) -> "InfluxSettings":

        super(InfluxSettings, self).__init__(settings)

        self.username = self.influx_username
        self.password = self.influx_password
        self.hostname = self.influx_hostname
        self.database = self.influx_database
        self.port = self.influx_port
        self.ssl = True
        self.verify_ssl = True

    def sanity(self) -> bool:
        """ Checks if connection parameters are valid """
        is_valid = (
            self.username is not None
            and self.password is not None
            and self.hostname is not None
            and self.port is not None
            and self.database is not None
        )

        return is_valid


class InfluxObserver(StreamObserver):
    """ InfluxObserver monitors the internal queues and dumps events to the database """

    def __init__(
        self,
        influx_settings: Settings,
        start_signal: multiprocessing.Event,
        exit_signal: multiprocessing.Event,
        tx_queue: multiprocessing.Queue,
        rx_queue: multiprocessing.Queue,
        logger=None,
    ) -> "InfluxObserver":
        super(InfluxObserver, self).__init__(
            start_signal=start_signal,
            exit_signal=exit_signal,
            tx_queue=tx_queue,
            rx_queue=rx_queue,
        )

        self.logger = logger or logging.getLogger(__name__)

        self.influx = Influx(
            username=influx_settings.username,
            password=influx_settings.password,
            hostname=influx_settings.hostname,
            port=influx_settings.port,
            database=influx_settings.database,
            logger=self.logger,
        )

        self.timeout = 1

    def on_data_received(self):
        """ Monitors inbound queuer for data to be written to Influx """
        raise NotImplementedError

    def on_query_received(self):
        """ Monitor inbound queue for queires to be sent to Influx """
        try:
            message = self.rx_queue.get(timeout=self.timeout, block=True)
        except queue.Empty:
            message = None
            pass
        self.logger.debug("Influx query: {}".format(message))
        result = self.influx.query(message)
        self.tx_queue.put(result)
        self.logger.debug("Influx result: {}".format(result))

    def run(self):
        """ Runs until asked to exit """
        try:
            self.influx.connect()
        except Exception as err:
            self.logger.error("error connecting to database {}".format(err))
            pass

        while not self.exit_signal.is_set():
            self.on_query_received()
            try:
                self.influx.close()
            except Exception as err:
                self.logger.exception(
                    "Could not close connection {}".format(err)
                )
                pass


class Influx(object):
    """
    Influx

    Simple class to handle Influx connections and decode the contents
    based on WM concepts.

    Attributes:
        hostname (str): ip or hostname where to connect to
        port (int)
        user (str)
        password (str)
        database (str)

    """

    def __init__(
        self,
        hostname: str,
        port: int,
        user: str,
        password: str,
        database: str,
        ssl: bool,
        verify_ssl: bool,
    ):
        super(Influx, self).__init__()

        self.hostname = hostname
        self.port = port
        self.user = user
        self.password = password
        self.database = database
        self.ssl = ssl
        self.verify_ssl = verify_ssl
        self._message_field_map = dict()
        self._message_number_map = dict()
        self._message_fields = list(
            wirepas_messaging.wnt.Message.DESCRIPTOR.fields
        )
        self._field_init()

    @property
    def fields(self) -> dict:
        """ Returns the field map gathered from the proto file """
        return self._message_field_map

    def _map_array_fields(self, payload: str) -> str:
        """ Replaces the coded fields in array elements """
        for k, v in self.fields.items():
            payload = payload.replace("{}=".format(k), "{}:".format(v))
        return payload

    def _decode_array(self, payload: str, elements: dict) -> list:
        """
        Maps the elements of an array present in the payload string

        Args:
            payload (str): An influx WM message
            elements (dict): A dictionary of elements to look for

        Returns:
            An array with named fields as dictionary
        """
        payload = payload.replace("[", "").replace("]", "")
        payload = payload.split(",")

        # elements = name:{base:int}
        array = list()
        target = dict()

        for entry in payload:
            values = entry.split(":")

            for k, v in elements.items():
                if k in values[0]:
                    target[k] = elements[k]["base"](values[1])
                    break

            if len(target.keys()) == len(elements.keys()):
                array.append(target.copy())
                target = dict()

        return array

    def _map_nested_field(
        self,
        parent_name: str,
        parent_pseudo_name: str,
        field: "google.protobuf.descriptor.FieldDescriptor",
    ) -> None:
        """
        Maps nested fields inside a proto definition.

        This method checks if an element in the proto definition has
        other nested messages under it and adds its fields to the map
        definition. The naming is kept coherent.

        Args:
            parent_name (str): the upper root names (messageA.messageB)
            parent_pseudo_name (str): the coded name in WM format (Message_number)
            field (FieldDescriptor): protobuf class describing the imediate parent field

        """

        parent_pseudo_name = "{}_{{}}".format(parent_pseudo_name)

        if field.message_type:
            nested_fields = list(field.message_type.fields)
            for nested_field in nested_fields:

                pseudo_name = parent_pseudo_name.format(nested_field.number)
                name = "{}.{}".format(parent_name, nested_field.name)

                self._message_field_map[pseudo_name] = name
                self._map_nested_field(
                    parent_name=name,
                    parent_pseudo_name=pseudo_name,
                    field=nested_field,
                )

    def _field_init(self):
        """
        Creates internal maps for translating names to fileds and vice versa
        """

        for field in self._message_fields:

            name = "Message_{}".format(field.number)

            self._message_number_map[field.number] = {name: field.name}
            self._message_field_map[name] = field.name

            self._map_nested_field(
                parent_name=field.name, parent_pseudo_name=name, field=field
            )

        return self._message_field_map

    def connect(self):
        """ Setup an Influx client connection """
        self.client = influxdb.DataFrameClient(
            host=self.hostname,
            port=self.port,
            username=self.user,
            password=self.password,
            database=self.database,
            ssl=self.ssl,
            verify_ssl=self.verify_ssl,
        )

    def location_measurements(self, last_n_seconds=60):
        """ Retrieves location measurements from the server """
        __measurement = "location_measurement"
        __table = '"wirepas"."autogen"."{}"'.format(__measurement)
        __elements = dict(
            type={"base": int}, value={"base": float}, target={"base": int}
        )

        query = ("SELECT * FROM {} " "WHERE time > now() - {}s").format(
            __table, last_n_seconds
        )

        try:
            df = self.query(query)[__measurement]

            df["positioning_mesh_data.payload"] = df[
                "positioning_mesh_data.payload"
            ].map(lambda x: self._map_array_fields(x))

            df["positioning_mesh_data.payload"] = df[
                "positioning_mesh_data.payload"
            ].map(lambda x: self._decode_array(x, __elements))
        except KeyError:
            df = None

        return df

    def location_updates(self, last_n_seconds=120):
        """ Retrieves location measurements from the server """
        __measurement = "location_update"
        __table = '"wirepas"."autogen"."{}"'.format(__measurement)

        query = ("SELECT * FROM {} " "WHERE time > now() - {}s").format(
            __table, last_n_seconds
        )

        try:
            df = self.query(query)[__measurement]
        except KeyError:
            df = None

        return df

    def query(self, statement: str, named_fields=True) -> pandas.DataFrame:
        """ Sends the query to the database object """

        result = self.client.query(statement)
        if named_fields:
            for key in result.keys():
                result[key].rename(columns=self.fields, inplace=True)

        return result


if __name__ == "__main__":

    def main(
        hostname="localhost",
        port=8086,
        user="influxuser",
        password="influxuserpassword",
        database="wirepas",
        ssl=True,
        verify_ssl=True,
    ):
        """Instantiate a connection to the InfluxDB."""

        db = Influx(
            hostname=hostname,
            port=port,
            user=user,
            password=password,
            database=database,
            ssl=ssl,
            verify_ssl=verify_ssl,
        )

        results = list()

        try:
            db.connect()
            results.append(db.location_measurements())
            results.append(db.location_updates())

        except requests.exceptions.ConnectionError:
            results = "Could not find host"

        return results

    def parse_args():
        """Parse the args."""
        parser = argparse.ArgumentParser(
            description="example code to play with InfluxDB"
        )
        parser.add_argument(
            "--influx_hostname",
            type=str,
            required=False,
            default="localhost",
            help="hostname of InfluxDB http API",
        )

        parser.add_argument(
            "--influx_port",
            type=int,
            required=False,
            default=8886,
            help="port of InfluxDB http API",
        )

        parser.add_argument(
            "--influx_user",
            type=str,
            required=False,
            default="influxuser",
            help="user of InfluxDB http API",
        )

        parser.add_argument(
            "--influx_password",
            type=str,
            required=False,
            default="influxuserpassword",
            help="password of InfluxDB http API",
        )

        parser.add_argument(
            "--influx_database",
            type=str,
            required=False,
            default="wirepas",
            help="port of InfluxDB http API",
        )

        parser.add_argument(
            "--influx_ssl",
            action="store_false",
            required=False,
            help="use https when talking to the API",
        )

        return parser.parse_args()

    args = parse_args()

    df = main(hostname=args.influx_hostname, port=args.influx_port)
