"""
    Connections
    ===========

    .. Copyright:
        Copyright 2019 Wirepas Ltd under Apache License, Version 2.0.
        See file LICENSE for full license details.

"""

import logging
import influxdb
import pandas

# pylint: disable=locally-disabled, unused-import
import google

# pylint: enable=unused-import
import wirepas_messaging


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
        username: str,
        password: str,
        database: str,
        ssl: bool = True,
        verify_ssl: bool = True,
        logger: logging.Logger = None,
    ):
        super(Influx, self).__init__()
        self.logger = logger or logging.getLogger(__name__)
        self.hostname = hostname
        self.port = port
        self.user = username
        self.password = password
        self.database = database
        self.ssl = ssl
        self.verify_ssl = verify_ssl
        self._message_field_map = dict()
        self._message_number_map = dict()
        self._message_fields = list(
            wirepas_messaging.wnt.Message.DESCRIPTOR.fields
        )
        self._influxdb = None

        # query settings
        self.epoch = None
        self.expected_response_code = 200
        self.raise_errors = True
        self.chunked = False
        self.chunk_size = 0
        self.method = "GET"
        self.dropna = True

        self._field_init()

    @property
    def fields(self) -> dict:
        """ Returns the field map gathered from the proto file """
        return self._message_field_map

    def _map_array_fields(self, payload: str) -> str:
        """ Replaces the coded fields in array elements """
        if isinstance(payload, str):
            for k, v in self.fields.items():
                payload = (
                    payload.replace("{}=".format(k), "'{}':".format(v))
                    .replace("[", "{")
                    .replace("]", "}")
                )

        return payload

    @staticmethod
    def _decode_array(payload: str, elements: dict) -> list:
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

            for _type, _convertion in elements.items():
                if _type in values[0]:
                    target[_type] = _convertion["base"](
                        "".join(filter(lambda c: c not in "{}'", values[1]))
                    )
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
                name = "{}/{}".format(parent_name, nested_field.name)

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
        self._influxdb = influxdb.DataFrameClient(
            host=self.hostname,
            port=self.port,
            username=self.user,
            password=self.password,
            database=self.database,
            ssl=self.ssl,
            verify_ssl=self.verify_ssl,
        )

    def query(self, statement: str, params=None, named_fields=True) -> dict():
        """ Sends the query to the database object """

        result = self._influxdb.query(
            statement,
            params=params,
            database=self.database,
            epoch=self.epoch,
            expected_response_code=self.expected_response_code,
            raise_errors=self.raise_errors,
            chunked=self.chunked,
            chunk_size=self.chunk_size,
            method=self.method,
            dropna=self.dropna,
        )

        if not result:
            result = pandas.DataFrame()
        else:
            if named_fields:
                for key in result.keys():
                    result[key].rename(columns=self.fields, inplace=True)
                    result[key] = result[key].applymap(self._map_array_fields)

        return result

    def query_by_time(
        self, measurement, last_n_seconds, from_date=None, until_date=None
    ):
        """ Makes a query either based on last amount of seconds or a date"""
        __table = "{}".format(measurement)

        if from_date and until_date:
            __query = "SELECT * FROM {table} WHERE time >= '{from_date}' AND time <= '{until_date}'".format(
                table=__table, from_date=from_date, until_date=until_date
            )

        elif from_date:
            __query = "SELECT * FROM {table} WHERE time >= '{from_date}'".format(
                table=__table, from_date=from_date
            )

        elif until_date:
            __query = "SELECT * FROM {table} WHERE time >= '{until_date}'".format(
                table=__table, until_date=until_date
            )
        else:
            __query = "SELECT * FROM {table} WHERE time > now() - {seconds}s".format(
                table=__table, seconds=last_n_seconds
            )
        print(__query)
        try:
            result = self.query(__query)[measurement]
            result.index.name = "Timestamp"
        except KeyError:
            result = pandas.DataFrame()

        return result

    def location_measurements(
        self, last_n_seconds=60, from_date=None, until_date=None
    ):
        """ Retrieves location measurements from the server """
        __measurement = "location_measurement"
        __elements = dict(
            type={"base": int}, value={"base": float}, target={"base": int}
        )

        df = self.query_by_time(
            __measurement, last_n_seconds, from_date, until_date
        )

        if not df.empty:
            try:
                df["positioning_mesh_data/payload"] = df[
                    "positioning_mesh_data/payload"
                ].apply(lambda x: self._decode_array(x, __elements))
            except KeyError:
                pass

        return df

    def location_updates(
        self, last_n_seconds=120, from_date=None, until_date=None
    ):
        """ Retrieves location measurements from the server """
        __measurement = "location_update"
        df = self.query_by_time(
            __measurement, last_n_seconds, from_date, until_date
        )

        return df

    def traffic_diagnostics(
        self, last_n_seconds=1000, from_date=None, until_date=None
    ):
        """ Retrieves traffic diagnostic measurements (endpoint 251) """
        __measurement = "endpoint_251"
        df = self.query_by_time(
            __measurement, last_n_seconds, from_date, until_date
        )

        return df

    def neighbor_diagnostics(
        self, last_n_seconds=1000, from_date=None, until_date=None
    ):
        """ Retrieves neighbor diagnostic measurements (endpoint 252) """
        __measurement = "endpoint_252"
        df = self.query_by_time(
            __measurement, last_n_seconds, from_date, until_date
        )

        return df

    def node_diagnostics(
        self, last_n_seconds=1000, from_date=None, until_date=None
    ):
        """ Retrieves neighbor diagnostic measurements (endpoint 253) """
        __measurement = "endpoint_253"
        df = self.query_by_time(
            __measurement, last_n_seconds, from_date, until_date
        )

        return df

    def boot_diagnostics(
        self, last_n_seconds=1000, from_date=None, until_date=None
    ):
        """ Retrieves neighbor diagnostic measurements (endpoint 254) """
        __measurement = "endpoint_254"
        df = self.query_by_time(
            __measurement, last_n_seconds, from_date, until_date
        )

        return df
