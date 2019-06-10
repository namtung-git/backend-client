# Wirepas Ltd 2019

from fluent import asyncsender as sender
from fluent import event

import os
import time
from wirepas_backend_client.tools import ParserHelper, LoggerHelper

import yaml
import json
import pandas
import pathlib


class KPI(object):
    """
    KPI

    Generic class to read and handle KPI test cases data

    """

    def __init__(self, data_location, schema_file):
        super(KPI, self).__init__()
        self.data_location = data_location
        self.df = None
        self.name = None
        with open(schema_file) as f:
            self.schema = yaml.load(f, Loader=yaml.FullLoader)

    def load(self):
        self.df = pandas.read_excel(
            self.data_location,
            sheet_name=self.name,
            converters={
                "Start time": KPI.localized_datetime,
                "End time": KPI.localized_datetime,
            },
        )
        return self.df

    @staticmethod
    def localized_datetime(item):
        item = pandas.to_datetime(item)
        item = item.tz_localize("EET")
        return item

    @staticmethod
    def serialize(item):
        item.to_json()

    def to_json(self):
        djs = pandas.DataFrame()
        djs = self.df.apply(KPI.serialize, axis=1)
        return djs

    def __str__(self):
        return str(self.data_location)


class KPI_Stats(KPI):
    """
    KPI_Stats

    This interface handles the parsing of a sheet from the test KPI
    document (perf stats)

    """

    def __init__(self, name, data_location, schema_file):
        super(KPI_Stats, self).__init__(
            data_location=data_location, schema_file=schema_file
        )
        self.name = name
        try:
            self.schema = self.schema["perf_stats"][self.name]
        except KeyError:
            self.schema = None
            pass

        self._columns = dict()
        self._pointer = dict()
        self._nb_sections = 0
        self._cache_name = pathlib.Path(
            "{}-{}.pkl".format(self.data_location, self.name)
        )
        self._columns_mapping = dict()

        self.load()

        if self.schema:
            self.sync()
            self.columns()

    def load(self):

        if self._cache_name.exists():
            self.df = pandas.read_pickle(self._cache_name)
        else:
            super().load()
            self.cache()

        if self.schema:
            self._nb_sections = int(
                round(
                    (
                        len(self.df.columns)
                        - self.schema["block_size_execution"]
                        - self.schema["block_size_node"]
                    )
                    / (self.schema["block_size_node"]),
                    0,
                )
            )

    def cache(self, force_overwrite=False):
        if not self._cache_name.exists():
            self.df.to_pickle(self._cache_name)

    @property
    def nb_sections(self):
        return self._nb_sections

    def sync(self):
        """ Sync finds the location of the "All nodes" summary """
        self._pointer["start"] = self.df.columns.get_loc("All nodes")
        self._pointer["end"] = (
            self._pointer["start"] + self.schema["block_size_node"]
        )
        self._pointer["source"] = "all"

    def columns(self):
        """
        Builds a list with the column header

        This function retrieves the metadata header and obtains the header
        of the per device section.

        The goal is to allow slicing the spreadsheet in multiple dataframes
        for section of the performance statistics.
        """

        if not self._columns:
            header_execution = list(
                map(
                    lambda x: x,
                    self.df.iloc[
                        self.schema["header_metadata_loc"],
                        : self.schema["block_size_metadata"],
                    ].index,
                )
            )

            header_element = list(
                map(
                    lambda x: x,
                    self.df.iloc[
                        self.schema["header_element_loc"],
                        self._pointer["start"] : self._pointer["end"],
                    ].values,
                )
            )

            self._columns = header_execution + header_element

        return self._columns

    def _map_columns(self, df):

        if not self._columns:
            self.columns()

        try:
            if not self._columns_mapping:
                self._columns_mapping = dict()
                assert len(self._columns) == len(
                    self.schema["columns_mapping"]
                )
                n = 0
                for c in self._columns:
                    self._columns_mapping[c] = self.schema["columns_mapping"][
                        n
                    ]
                    n += 1

            df.columns = self._columns
            df = df.rename(columns=self._columns_mapping)
        except AssertionError:
            print(
                "Mismatch in column's mapping {} x {}".format(
                    len(self._columns), len(self.schema["columns_mapping"])
                )
            )
        return df

    def retrieve(self, start=None, end=None, remap_columns=True):

        if start is None and end is None:
            start = self._pointer["start"]
            end = self._pointer["end"]
            source = self._pointer["source"]

        section = self.df.iloc[
            1:, pandas.np.r_[: self.schema["block_size_metadata"], start:end]
        ]
        section["source"] = source

        if remap_columns is True:
            section = self._map_columns(section)

        return section

    def __iter__(self):
        """ iterated through the node sections """
        for _ in range(0, self._nb_sections - 1, 1):
            yield self.retrieve(self._pointer["start"], self._pointer["end"])
            self._pointer["start"] = self._pointer["end"]
            self._pointer["end"] += self.schema["block_size_node"]
            # TODO: retrieve node from index header
            # idx = self.df[0, self._pointer["start"]].index


if __name__ == "__main__":

    try:
        debug_level = os.environ["DEBUG_LEVEL"]
    except KeyError:
        debug_level = "info"

    parser = ParserHelper(description="Default arguments")

    parser.add_file_settings()
    parser.add_mqtt()
    parser.add_test()
    parser.add_database()
    parser.add_fluentd()

    settings = parser.settings(skip_undefined=False)

    log = LoggerHelper(
        module_name="kpi_test", args=settings, level=debug_level
    )
    logger = log.setup()

    filepath = pathlib.Path("./kpi_data/perf_stats.xlsx")

    kpi = dict()
    name = "NWstatus"
    kpi[name] = KPI_Stats(
        name=name,
        data_location=filepath,
        schema_file="./examples/test_kpi_definitions.yaml",
    )

    name = "AvePerfSum"
    kpi[name] = KPI_Stats(
        name=name,
        data_location=filepath,
        schema_file="./examples/test_kpi_definitions.yaml",
    )

    name = "SinksAnaSum"
    kpi[name] = KPI_Stats(
        name=name,
        data_location=filepath,
        schema_file="./examples/test_kpi_definitions.yaml",
    )

    name = "PerfAnaSum"
    kpi[name] = KPI_Stats(
        name=name,
        data_location=filepath,
        schema_file="./examples/test_kpi_definitions.yaml",
    )

    name = "RouteAnaSum"
    kpi[name] = KPI_Stats(
        name=name,
        data_location=filepath,
        schema_file="./examples/test_kpi_definitions.yaml",
    )

    name = "BulkDataLat"
    kpi[name] = KPI_Stats(
        name=name,
        data_location=filepath,
        schema_file="./examples/test_kpi_definitions.yaml",
    )

    name = "McastLat"
    kpi[name] = KPI_Stats(
        name=name,
        data_location=filepath,
        schema_file="./examples/test_kpi_definitions.yaml",
    )

    name = "DLn2nLat"
    kpi[name] = KPI_Stats(
        name=name,
        data_location=filepath,
        schema_file="./examples/test_kpi_definitions.yaml",
    )

    name = "ULtotalLat"
    kpi[name] = KPI_Stats(
        name=name,
        data_location=filepath,
        schema_file="./examples/test_kpi_definitions.yaml",
    )

    name = "ULperHopLat"
    kpi[name] = KPI_Stats(
        name=name,
        data_location=filepath,
        schema_file="./examples/test_kpi_definitions.yaml",
    )

    # section = kpi_stats.retrieve()
    # df = section.apply(
    #    lambda x: logger.info(json.loads(x.to_json(date_format="iso"))), axis=1
    # )
