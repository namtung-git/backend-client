# Wirepas Ltd 2019

from fluent import asyncsender as sender
from fluent import event

import os
import time
from wirepas_backend_client.tools import ParserHelper, LoggerHelper

import json
import pandas
import pathlib


class KPI(object):
    """
    KPI

    Generic class to read and handle KPI test cases data

    """

    # TODO: source from yaml configuration file
    perf_stats = dict(
        version=40,
        name=[
            "NWstatus",
            "AvePerfSum",
            "SinksAnaSum",
            "PerfAnaSum",
            "RouteAnaSum",
            "BulkDataLat",
            "McastLat",
            "DLn2nLat",
            "ULtotalLat",
            "ULperHopLat",
        ],
    )

    # TODO: source from yaml configuration file
    schema = dict(
        AvePerfSum=dict(
            name="AvePerfSum",
            block_size_node=44,
            block_size_execution=80,
            block_size_metadata=86,
            header_metadata_loc=0,
            header_element_loc=0,
            columns_mapping=[
                "start_time",
                "end_time",
                "duration_s",
                "logic_duration_s",
                "release",
                "hardware",
                "interface_speed_pps",
                "test_case",
                "stack_mode",
                "nb_sinks",
                "nw_beacon_interval_s",
                "nb_nodes",
                "channel_map",
                "auto_role",
                "ac",
                "sync_control",
                "ipv6_control",
                "description",
                "ul_nodes_per_sub_interval",
                "n2n_nodes_per_sub_interval",
                "mcast_nodes_per_sub_interval",
                "sub_interval_s",
                "random_period_s",
                "sample_len",
                "filename",
                "node_logic_pins",
                "node_logic_current_uA",
                "ble_adv_interval_s",
                "ble_scan_range_start",
                "ble_scan_range_end",
                "ble_scan_modulo",
                "ul_pps_target",
                "ul_achieved",
                "qos1_ul_bytes",
                "qos1_pps_target",
                "qos1_miss_rate",
                "ul_999_limit_s",
                "qos1_ul_achieved",
                "qos1_interval_s",
                "diaf_interval_s",
                "diag_pps_target",
                "n2n_pps",
                "hop_limit/n2n",
                "n2n_miss_rate",
                "n2n_999_limit_s",
                "n2n_reTx_cnt",
                "n2n_reTx_time_ms",
                "offset_for_N2N_dest_address",
                "dl_unic_pps",
                "dl_fast_mode",
                "rpt_cnt",
                "hop_limit/dl",
                "dl_ucast_miss_rate",
                "dl bcast_pps",
                "dl_bcast_miss_rate",
                "dl_bytes",
                "mcast_pps",
                "hop_limit/mcast",
                "mcast_tx_repeat_count",
                "offset_for_MCAST_dest_address",
                "mcast_group_size",
                "bulk_pps",
                "mcast_bulk_transfer_dest",
                "bulk_src_node",
                "hop_limit/bulk_data",
                "ReTx_count_with_bulk_data",
                "Bulk/app_interval_s",
                "Pkts_per_bulk_interval",
                "bulk_dest_node",
                "2nd_source_node_ul_with_bulk_data",
                "TxMod_with_bulkdata",
                "qos_of_bulk_data",
                "stack_tunings",
                "cca_threshold",
                "cca_disable_index",
                "cca_window_size_ms",
                "cca_window_freeze_after_x_attempts",
                "unack_bcast_prob.",
                "delay_divider_for_unack_window",
                "cmd_start_miss_rate",
                "cmd_start_miss",
                "cmd_start_miss_list",
                "cmd_end_miss_rate",
                "cmd_end_miss_list",
                "cmd_bulk_miss",
                "cmd_bulk_miss_list",
                "kpi_data",
                "latency_kpi",
                "latency_ul_200_ms",
                "latency_ul_250_ms",
                "latency_ul_1000_ms",
                "latency_ul_5000_ms",
                "latency_ul_60000_ms",
                "latency_hop_ul_200_ms",
                "latency_hop_ul_250_ms",
                "latency_hop_ul_1000_ms",
                "latency_hop_ul_5000_ms",
                "latency_hop_ul_60000_ms",
                "missed_packets",
                "not_generated_packets",
                "scans_h",
                "periodic_scans_h",
                "need_nbors_h",
                "far_conflicts_h",
                "rest_conflicts_h",
                "route_chngs_h",
                "sync_losts_h",
                "tdma_adjusts_h",
                "minor_adjusts_h",
                "major_adjusts_h",
                "conflict adjusts_h",
                "blacklists_h",
                "other_tdma adjusts_h",
                "boots_h",
                "route_loops_h",
                "sink_chngs_h",
                "subs_removed_h",
                "LL_DL_fails_h",
                "LL_UL_fails_h",
                "scan_nbors_oom_h",
                "other_events_h",
                "blacklisted_chn_cnt_node",
                "cost_255_h",
                "next0_hop chngs_h",
                "heads_cnt(ave)",
                "nodes_active",
                "nodes_active_2h",
                "nodes_active_15min",
                "role_chngs_h",
                "ble_bcon_miss_rate",
            ],
        )
    )

    def __init__(self, data_location):
        super(KPI, self).__init__()
        self.data_location = data_location
        self.df = None
        self.name = None

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

    def __init__(self, name, data_location):
        super(KPI_Stats, self).__init__(data_location=data_location)
        self.name = name
        self._columns = dict()
        self._pointer = dict()
        self._nb_sections = 0
        self._cache_name = pathlib.Path("{}.pkl".format(self.data_location))
        self._columns_mapping = dict()

    def setup(self):
        self.load()
        self.sync()
        self.columns()

    def load(self):

        if self._cache_name.exists():
            self.df = pandas.read_pickle(self._cache_name)
        else:
            super().load()
            self.cache()

        self._nb_sections = int(
            round(
                (
                    len(self.df.columns)
                    - self.schema[self.name]["block_size_execution"]
                    - self.schema[self.name]["block_size_node"]
                )
                / (self.schema[self.name]["block_size_node"]),
                0,
            )
        )

    def cache(self, force_overwrite=False):
        if not self._cache_name.exists():
            self.df.to_pickle(self._cache_name)

    @property
    def nb_sections(self):
        return self._nb_sections

    def sync(self) -> None:
        """ Sync finds the location of the "All nodes" summary """
        self._pointer["start"] = self.df.columns.get_loc("All nodes")
        self._pointer["end"] = (
            self._pointer["start"] + self.schema[self.name]["block_size_node"]
        )
        self._pointer["source"] = "all"

    def columns(self) -> list:
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
                        self.schema[self.name]["header_metadata_loc"],
                        : self.schema[self.name]["block_size_metadata"],
                    ].index,
                )
            )

            header_element = list(
                map(
                    lambda x: x,
                    self.df.iloc[
                        self.schema[self.name]["header_element_loc"],
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
                    self.schema[self.name]["columns_mapping"]
                )
                n = 0
                for c in self._columns:
                    self._columns_mapping[c] = self.schema[self.name][
                        "columns_mapping"
                    ][n]
                    n += 1

            df.columns = self._columns
            df = df.rename(columns=self._columns_mapping)
        except AssertionError:
            print(
                "Mismatch in column's mapping {} x {}".format(
                    len(self._columns),
                    len(self.schema[self.name]["columns_mapping"]),
                )
            )
        return df

    def retrieve(self, start=None, end=None, remap_columns=True):

        if start is None and end is None:
            start = self._pointer["start"]
            end = self._pointer["end"]
            source = self._pointer["source"]

        section = self.df.iloc[
            1:,
            pandas.np.r_[
                : self.schema[self.name]["block_size_metadata"], start:end
            ],
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
            self._pointer["end"] += self.schema[self.name]["block_size_node"]
            # TODO: retrieve node from index header
            idx = self.df[0, self._pointer["start"]].index


# name = ["AvePerfSum"]
def overflow_handler(pendings):
    print(pendings)


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

    filepath = pathlib.Path("./kpi_data/perf_stats_small.xlsx")
    name = "AvePerfSum"

    kpi_stats = KPI_Stats(name=name, data_location=filepath)
    kpi_stats.setup()

    section = kpi_stats.retrieve()
    df = section.apply(
        lambda x: logger.info(json.loads(x.to_json(date_format="iso"))), axis=1
    )
