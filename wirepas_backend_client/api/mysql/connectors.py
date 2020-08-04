"""
    Connections
    ===========

    .. Copyright:
        Copyright 2019 Wirepas Ltd under Apache License, Version 2.0.
        See file LICENSE for full license details.
"""
# pylint: disable=locally-disabled, too-many-lines

try:
    import MySQLdb
    from MySQLdb._exceptions import DatabaseError, IntegrityError, DataError
except ImportError:
    print("Failed to import MySQLdb")
    pass

import logging
import json
from time import perf_counter, time


class MySQL(object):
    """
    MySQL connection handler
    """

    def __init__(
        self,
        username: str,
        password: str,
        hostname: str,
        database: str,
        port: int,
        connection_timeout: int,
        logger: logging.Logger = None,
    ):

        super(MySQL, self).__init__()

        self.stat_inserts_fail = 0
        self.stat_inserts_ok = 0
        self.integrity_checks_failed = 0
        self.exceptions_occurred_count = 0
        self.itemsInDBTot = 0
        self.sql_insert_update_statements = dict()
        self.sql_integrity_check_statements = []
        self.sql_insert_variable_statements = dict()
        self.logger = logger or logging.getLogger(__name__)

        self.hostname = hostname
        self.username = username
        self.password = password
        self.database_name = database
        self.database = None
        self.port = port
        self.cursor = None
        self.connection_timeout = connection_timeout
        self.prev_update_interval_perf_time = None
        self.integrity_check_sum = 0
        self.integrity_check_sum_is_failing: bool = False

    def connect(self, table_creation=True) -> None:
        """ Establishes a connection and service loop. """
        # pylint: disable=locally-disabled, protected-access

        self.logger.info(
            "MySQL connection to %s:%s@%s:%s",
            self.username,
            self.password,
            self.hostname,
            self.port,
        )
        self.database = MySQLdb.connect(
            host=self.hostname,
            user=self.username,
            passwd=self.password,
            port=self.port,
            connect_timeout=self.connection_timeout,
        )

        self.database.autocommit = False

        self.cursor = self.database.cursor()
        self.cursor.execute("SHOW DATABASES")

        try:
            self.cursor.execute(
                "CREATE DATABASE {}".format(self.database_name)
            )
        except MySQLdb._exceptions.ProgrammingError as error_message:
            if error_message.args[0] != 1007:
                self.logger.error(
                    "Could not create database %s", self.database_name
                )
                raise

        self.cursor.execute("USE {}".format(self.database_name))

        if table_creation:
            self.create_tables()

        self.logger.info("MySQL ready.")

    def close(self: "MySQL") -> None:
        """ Handles disconnect from database object """
        self.cursor.close()
        self.database.close()

    def create_tables(self):
        """
        Create tables if they do not exist
        """
        # pylint: disable=locally-disabled, too-many-statements

        # Create integrity test tables
        try:
            self.cursor.execute("DROP TABLE integrity_test")
            self.database.commit()
        except DatabaseError:
            pass
        except DataError:
            pass
        except IntegrityError:
            pass

        query = (
            "CREATE TABLE IF NOT EXISTS integrity_test ("
            " message_time TIMESTAMP(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),"
            " db_write_time TIMESTAMP(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),"
            " checksum_number BIGINT UNSIGNED NOT NULL"
            ") ENGINE = InnoDB;"
        )
        self.cursor.execute(query)

        # Create payload test tables
        query = (
            "CREATE TABLE IF NOT EXISTS known_nodes ("
            "  network_address BIGINT UNSIGNED NOT NULL,"
            "  node_address INT UNSIGNED NOT NULL,"
            "  last_time TIMESTAMP(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),"
            "  voltage DOUBLE NULL,"
            "  node_role SMALLINT UNSIGNED NULL,"
            "  firmware_version INT UNSIGNED NULL,"
            "  scratchpad_seq INT UNSIGNED NULL,"
            "  hw_magic INT UNSIGNED NULL,"
            "  stack_profile INT UNSIGNED NULL,"
            "  boot_count INT UNSIGNED NULL,"
            "  file_line_num INT UNSIGNED NULL,"
            "  file_name_hash INT UNSIGNED NULL,"
            "  UNIQUE INDEX node (network_address, node_address)"
            ") ENGINE = InnoDB;"
        )
        self.cursor.execute(query)

        query = (
            "CREATE TABLE IF NOT EXISTS received_packets ("
            "  id BIGINT NOT NULL AUTO_INCREMENT UNIQUE,"
            "  logged_time TIMESTAMP(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),"
            "  launch_time TIMESTAMP(6) NULL,"
            "  path_delay_ms BIGINT UNSIGNED NOT NULL,"
            "  network_address BIGINT UNSIGNED NOT NULL,"
            "  sink_address INT UNSIGNED NOT NULL,"
            "  source_address INT UNSIGNED NOT NULL,"
            "  dest_address INT UNSIGNED NOT NULL,"
            "  source_endpoint SMALLINT UNSIGNED NOT NULL,"
            "  dest_endpoint SMALLINT UNSIGNED NOT NULL,"
            "  qos SMALLINT UNSIGNED NOT NULL,"
            "  num_bytes SMALLINT UNSIGNED NOT NULL,"
            "  hop_count SMALLINT UNSIGNED DEFAULT NULL,"
            "  PRIMARY KEY (id),"
            "  INDEX (logged_time),"
            "  INDEX (launch_time),"
            "  INDEX (source_address),"
            "  INDEX packets_from_node (network_address, source_address)"
            ") ENGINE = InnoDB;"
        )
        self.cursor.execute(query)

        # See if we need to expand the old received_packets table with
        # the hop_count column.
        query = "SHOW COLUMNS FROM received_packets;"
        self.cursor.execute(query)
        self.database.commit()
        values = self.cursor.fetchall()
        column_names = map(lambda x: x[0], values)
        if "hop_count" not in column_names:
            # hop_count was not in the table so add it.
            query = (
                "ALTER TABLE received_packets\n"
                "ADD COLUMN hop_count SMALLINT UNSIGNED DEFAULT NULL;"
            )
            self.cursor.execute(query)
            self.database.commit()

        query = (
            "CREATE TABLE IF NOT EXISTS diagnostics_json ("
            "  received_packet BIGINT NOT NULL,"
            "  FOREIGN KEY (received_packet) REFERENCES received_packets(id),"
            "  apdu JSON NOT NULL"
            ") ENGINE = InnoDB;"
        )
        self.cursor.execute(query)

        createtable = (
            "CREATE TABLE IF NOT EXISTS advertiser_json ("
            "  received_packet BIGINT NOT NULL,"
            "  FOREIGN KEY (received_packet) REFERENCES received_packets(id),"
            "  apdu JSON NOT NULL"
            ") ENGINE = InnoDB;"
        )
        self.cursor.execute(createtable)

        query = "SHOW COLUMNS FROM advertiser_json;"
        self.cursor.execute(query)
        self.database.commit()
        values = self.cursor.fetchall()
        column_names = map(lambda x: x[0], values)
        if "received_packet" not in column_names:
            # hop_count was not in the table so add it.
            query = (
                "ALTER TABLE advertiser_json\n"
                "ADD COLUMN received_packet BIGINT NOT NULL;"
            )
            self.cursor.execute(query)
            self.database.commit()

        # Create test nw app database
        default_test_ids = 10
        default_column_count = 30

        for test_data_id in range(1, default_test_ids):
            table_name = f"TestData_ID_{test_data_id}"

            query = """
                    CREATE TABLE IF NOT EXISTS `{}` (
                    received_packet BIGINT NOT NULL,
                    `logged_time` DOUBLE DEFAULT NULL,
                    `launch_time` DOUBLE DEFAULT NULL,
                    `ID_ctrl` INT UNSIGNED DEFAULT NULL,
                    `field_count` int DEFAULT 0,
                    """.format(
                table_name
            )

            for i in range(1, default_column_count + 1):
                query += "`DataCol_{}` INT UNSIGNED DEFAULT NULL,".format(i)
            query += "INDEX (logged_time),"
            query += "INDEX (launch_time),"
            query += "INDEX (ID_ctrl),"
            query += (
                "FOREIGN KEY (received_packet) REFERENCES received_packets(id)"
            )
            query += ") ENGINE=InnoDB;"

            self.cursor.execute(query)
            self.database.commit()

        query = (
            "CREATE TABLE IF NOT EXISTS diagnostic_traffic ("
            "  received_packet BIGINT NOT NULL,"
            "  access_cycles INT UNSIGNED NOT NULL,"
            "  cluster_channel SMALLINT UNSIGNED NOT NULL,"
            "  channel_reliability SMALLINT UNSIGNED NOT NULL,"
            "  rx_count INT UNSIGNED NOT NULL,"
            "  tx_count INT UNSIGNED NOT NULL,"
            "  aloha_rxs SMALLINT UNSIGNED NOT NULL,"
            "  resv_rx_ok SMALLINT UNSIGNED NOT NULL,"
            "  data_rxs SMALLINT UNSIGNED NOT NULL,"
            "  dup_rxs SMALLINT UNSIGNED NOT NULL,"
            "  cca_ratio SMALLINT UNSIGNED NOT NULL,"
            "  bcast_ratio SMALLINT UNSIGNED NOT NULL,"
            "  tx_unicast_fail SMALLINT UNSIGNED NOT NULL,"
            "  resv_usage_max SMALLINT UNSIGNED NOT NULL,"
            "  resv_usage_avg SMALLINT UNSIGNED NOT NULL,"
            "  aloha_usage_max SMALLINT UNSIGNED NOT NULL,"
            "  FOREIGN KEY (received_packet) REFERENCES received_packets(id)"
            ") ENGINE = InnoDB;"
        )
        self.cursor.execute(query)

        # See if we need to expand the old diagnostic_traffic table with
        # the cluster_members and/or cluster_headnode_members column.
        query = "SHOW COLUMNS FROM diagnostic_traffic;"
        self.cursor.execute(query)
        self.database.commit()
        values = self.cursor.fetchall()
        column_names = map(lambda x: x[0], values)
        if "cluster_members" not in column_names:
            # cluster_members was not in the table so add it.
            query = (
                "ALTER TABLE diagnostic_traffic\n"
                "ADD COLUMN cluster_members SMALLINT UNSIGNED DEFAULT NULL;"
            )
            self.cursor.execute(query)
            self.database.commit()
        if "cluster_headnode_members" not in column_names:
            # cluster_headnode_members was not in the table so add it.
            query = (
                "ALTER TABLE diagnostic_traffic\n"
                "ADD COLUMN cluster_headnode_members SMALLINT UNSIGNED DEFAULT NULL;"
            )
            self.cursor.execute(query)
            self.database.commit()

        query = (
            "CREATE TABLE IF NOT EXISTS diagnostic_neighbor ("
            "  received_packet BIGINT NOT NULL,"
            "  node_address INT UNSIGNED NOT NULL,"
            "  cluster_channel SMALLINT UNSIGNED NOT NULL,"
            "  radio_power SMALLINT UNSIGNED NOT NULL,"
            "  device_info SMALLINT UNSIGNED NOT NULL,"
            "  norm_rssi SMALLINT UNSIGNED NOT NULL,"
            "  FOREIGN KEY (received_packet) REFERENCES received_packets(id)"
            ") ENGINE = InnoDB;"
        )
        self.cursor.execute(query)

        query = (
            "CREATE TABLE IF NOT EXISTS diagnostic_node ("
            "  received_packet BIGINT NOT NULL,"
            "  access_cycle_ms INT UNSIGNED NOT NULL,"
            "  node_role SMALLINT UNSIGNED NOT NULL,"
            "  voltage DOUBLE NOT NULL,"
            "  buf_usage_max SMALLINT UNSIGNED NOT NULL,"
            "  buf_usage_avg SMALLINT UNSIGNED NOT NULL,"
            "  mem_alloc_fails SMALLINT UNSIGNED NOT NULL,"
            "  tc0_delay SMALLINT UNSIGNED NOT NULL,"
            "  tc1_delay SMALLINT UNSIGNED NOT NULL,"
            "  network_scans SMALLINT UNSIGNED NOT NULL,"
            "  downlink_delay_avg_0 INT UNSIGNED NOT NULL,"
            "  downlink_delay_min_0 INT UNSIGNED NOT NULL,"
            "  downlink_delay_max_0 INT UNSIGNED NOT NULL,"
            "  downlink_delay_samples_0 INT UNSIGNED NOT NULL,"
            "  downlink_delay_avg_1 INT UNSIGNED NOT NULL,"
            "  downlink_delay_min_1 INT UNSIGNED NOT NULL,"
            "  downlink_delay_max_1 INT UNSIGNED NOT NULL,"
            "  downlink_delay_samples_1 INT UNSIGNED NOT NULL,"
            "  dropped_packets_0 SMALLINT UNSIGNED NOT NULL,"
            "  dropped_packets_1 SMALLINT UNSIGNED NOT NULL,"
            "  route_address INT UNSIGNED NOT NULL,"
            "  next_hop_address_0 INT UNSIGNED NOT NULL,"
            "  cost_0 SMALLINT UNSIGNED NOT NULL,"
            "  quality_0 SMALLINT UNSIGNED NOT NULL,"
            "  next_hop_address_1 INT UNSIGNED NOT NULL,"
            "  cost_1 SMALLINT UNSIGNED NOT NULL,"
            "  quality_1 SMALLINT UNSIGNED NOT NULL,"
            "  FOREIGN KEY (received_packet) REFERENCES received_packets(id)"
            ") ENGINE = InnoDB;"
        )
        self.cursor.execute(query)

        self.update_diagnostic_node_table_4_0()
        self.update_diagnostic_node_table_4_2()

        query = (
            "CREATE TABLE IF NOT EXISTS diagnostic_event ("
            "  received_packet BIGINT NOT NULL,"
            "  position SMALLINT NOT NULL,"
            "  event SMALLINT NOT NULL,"
            "  FOREIGN KEY (received_packet) REFERENCES received_packets(id),"
            "  UNIQUE INDEX event_id (received_packet, position)"
            ") ENGINE = InnoDB;"
        )
        self.cursor.execute(query)

        query = (
            "CREATE TABLE IF NOT EXISTS diagnostic_boot ("
            "  received_packet BIGINT NOT NULL,"
            "  boot_count INT UNSIGNED NOT NULL,"
            "  node_role SMALLINT UNSIGNED NOT NULL,"
            "  firmware_version INT UNSIGNED NOT NULL,"
            "  scratchpad_seq INT UNSIGNED NOT NULL,"
            "  hw_magic INT UNSIGNED NOT NULL,"
            "  stack_profile INT UNSIGNED NOT NULL,"
            "  otap_enabled BOOL NOT NULL,"
            "  file_line_num INT UNSIGNED NOT NULL,"
            "  file_name_hash INT UNSIGNED NOT NULL,"
            "  stack_trace_0 INT UNSIGNED NOT NULL,"
            "  stack_trace_1 INT UNSIGNED NOT NULL,"
            "  stack_trace_2 INT UNSIGNED NOT NULL,"
            "  current_seq INT UNSIGNED DEFAULT NULL,"
            "  FOREIGN KEY (received_packet) REFERENCES received_packets(id)"
            ") ENGINE = InnoDB;"
        )
        self.cursor.execute(query)

        # See if we need to expand the old diagnostic_boot table with
        # the current_seq.
        query = "SHOW COLUMNS FROM diagnostic_boot;"
        self.cursor.execute(query)

        values = self.cursor.fetchall()
        column_names = map(lambda x: x[0], values)
        if "current_seq" not in column_names:
            # current_seq was not in the table so add it.
            query = (
                "ALTER TABLE diagnostic_boot\n"
                "ADD COLUMN current_seq INT UNSIGNED DEFAULT NULL;"
            )
            self.cursor.execute(query)

        query = (
            "CREATE TABLE IF NOT EXISTS sink_command ( "
            "id BIGINT NOT NULL AUTO_INCREMENT UNIQUE, "
            "address INT UNSIGNED NOT NULL, "
            "command varchar(255), "
            "param LONGBLOB, "
            "launch_time TIMESTAMP(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6), "
            "ready_time TIMESTAMP NULL, "
            "result INT UNSIGNED, "
            "PRIMARY KEY (id), "
            "INDEX(address) "
            ") ENGINE = InnoDB;"
        )
        self.cursor.execute(query)

        # Create table for received remote statuses
        createtable = (
            "CREATE TABLE IF NOT EXISTS remote_status ( "
            "id BIGINT NOT NULL AUTO_INCREMENT UNIQUE, "
            "address INT UNSIGNED NOT NULL, "
            "sink_address INT UNSIGNED NOT NULL, "
            "reception_time TIMESTAMP(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6), "
            "crc INT UNSIGNED, "
            "otap_seq INT UNSIGNED NOT NULL, "
            "scratchpad_type INT UNSIGNED, "
            "scratchpad_status INT UNSIGNED, "
            "processed_length INT UNSIGNED, "
            "processed_crc INT UNSIGNED, "
            "processed_seq INT UNSIGNED, "
            "fw_mem_area_id INT UNSIGNED, "
            "fw_major_version INT UNSIGNED, "
            "fw_minor_version INT UNSIGNED, "
            "fw_maintenance_version INT UNSIGNED, "
            "fw_development_version INT UNSIGNED, "
            "seconds_until_update INT UNSIGNED, "
            "legacy_status INT UNSIGNED, "
            "PRIMARY KEY (id), "
            "INDEX(address), "
            "INDEX(sink_address) "
            ") ENGINE = InnoDB;"
        )
        self.cursor.execute(createtable)

        createtable = (
            "CREATE TABLE IF NOT EXISTS advertiser_json ("
            "  received_packet BIGINT NOT NULL,"
            "  FOREIGN KEY (received_packet) REFERENCES received_packets(id),"
            "  apdu JSON NOT NULL"
            ") ENGINE = InnoDB;"
        )
        self.cursor.execute(createtable)

        # Create event codes
        createtable = (
            "CREATE TABLE IF NOT EXISTS diagnostic_event_codes ( "
            "code SMALLINT UNSIGNED UNIQUE NOT NULL, "
            "name TEXT, "
            "description TEXT, "
            "PRIMARY KEY (code) "
            ") ENGINE = InnoDB;"
        )
        self.cursor.execute(createtable)

        # Populate event codes
        createtable = (
            "REPLACE INTO diagnostic_event_codes "
            "(code, name, description) VALUES "
            '(0x08, "role_change_to_subnode", '
            '"Role change: change to subnode"),'
            '(0x09, "role_change_to_headnode", '
            '"Role change: change to headnode"),'
            '(0x10, "route_change_unknown", '
            '"Route change: unknown reason"),'
            '(0x18, "scan_ftdma_adjust",'
            '"Scan: changing channel or no cluster channel selected"),'
            '(0x19, "scan_f_confl_near_nbor",'
            '"Scan: FTDMA conflict with cluster"),'
            '(0x1a, "scan_f_confl_far_nbor",'
            '"Scan: FTDMA conflict with neighbor\'s neighbor"),'
            '(0x1b, "scan_t_confl_nbor",'
            '"Scan: timing conflict with cluster"),'
            '(0x1c, "scan_t_confl_between_nbors",'
            '"Scan: timing conflict between two or more clusters"),'
            '(0x1d, "scan_need_nbors",'
            '"Scan: need more clusters"),'
            '(0x1e, "scan_periodic",'
            '"Scan: periodic scan"),'
            '(0x1f, "scan_role_change",'
            '"Scan: role change"),'
            '(0x20, "boot_por",'
            '"Boot: power-on reset"),'
            '(0x21, "boot_intentional",'
            '"Boot: reboot requested"),'
            '(0x22, "boot_assert",'
            '"Boot: software assert"),'
            '(0x23, "boot_fault",'
            '"Boot: fault handler"),'
            '(0x24, "boot_wdt",'
            '"Boot: watchdog timer"),'
            '(0x25, "boot_unknown",'
            '"Boot: unknown reason"),'
            '(0x28, "sync_lost_synced",'
            '"Sync lost: lost sync to synced cluster"),'
            '(0x29, "sync_lost_joined",'
            '"Sync lost: lost sync to next hop cluster"),'
            '(0x30, "tdma_adjust_minor_boundary",'
            '"TDMA adjust: minor boundary adjust"),'
            '(0x31, "tdma_adjust_major_boundary",'
            '"TDMA adjust: not in slot boundary"),'
            '(0x32, "tdma_adjust_next_hop",'
            '"TDMA adjust: FTDMA conflict with next hop"),'
            '(0x33, "tdma_adjust_cluster",'
            '"TDMA adjust: FTDMA conflict with neighboring cluster"),'
            '(0x34, "tdma_adjust_neighbor",'
            '"TDMA adjust: FTDMA conflict with neighbor"),'
            '(0x35, "tdma_adjust_no_channel",'
            '"TDMA adjust: no channel"),'
            '(0x36, "tdma_adjust_blacklist",'
            '"TDMA adjust: channel change due to blacklisting"),'
            '(0x37, "tdma_adjust_unknown",'
            '"TDMA adjust: unknown reason"),'
            '(0x38, "peripheral_fail_unknown",'
            '"Peripheral failure: unknown reason"),'
            '(56, "sink_changed",'
            '"Changed routing to another sink"),'
            '(57, "fhma_adjust",'
            '"FHMA adjust event"),'
            '(0x40, "routing_loop_unknown",'
            '"Routing loop: unknown reason"), '
            '(72, "subnode_removed",'
            '"Removed subnode member in favour of headnode"),'
            '(73, "ll_dl_fail_chead",'
            '"Cluster head: removed member due to failing LL downklink"), '
            '(74, "ll_dl_fail_member", '
            '"Member: removed from the cluster head due to failing'
            ' LL downlink"), '
            '(75, "ll_ul_fail",'
            '"Cluster removed due to failing LL communication"),'
            '(76, "scan too many results",'
            '"Too many scan results to process (could also be temporal)"),'
            '(77, "own_active_late",'
            '"Own active start was late");'
        )

        self.cursor.execute(createtable)

        # Create file name hashes table
        # Note: population of this cannot be done here. Content is due to
        # change

        createtable = (
            "CREATE TABLE IF NOT EXISTS file_name_hashes ("
            "id SMALLINT UNSIGNED NOT NULL UNIQUE,"
            "name TEXT,"
            "PRIMARY KEY (id)"
            ") ENGINE = InnoDB;"
        )

        self.cursor.execute(createtable)

        # Create trigger for updating known nodes when received packets is
        # inserted
        trigger = "DROP TRIGGER IF EXISTS after_received_packets_insert;"
        self.cursor.execute(trigger)

        # Note, there is no DELIMITER here
        trigger = """CREATE
                       TRIGGER after_received_packets_insert AFTER INSERT
                       ON received_packets
                       FOR EACH ROW BEGIN
                           INSERT INTO known_nodes (network_address, node_address, last_time)
                           VALUES
                           (new.network_address,new.source_address, CURRENT_TIMESTAMP(6))
                           ON DUPLICATE KEY UPDATE last_time=CURRENT_TIMESTAMP(6);
                       END;"""
        self.cursor.execute(trigger)

        # Create a trigger for updating diagnostics node information to known
        # nodes
        trigger = "DROP TRIGGER IF EXISTS after_diagnostics_node_insert;"
        self.cursor.execute(trigger)

        trigger = """CREATE TRIGGER `after_diagnostics_node_insert` AFTER INSERT
                     ON `diagnostic_node`
                     FOR EACH ROW BEGIN
                        INSERT INTO known_nodes (network_address, node_address, voltage, node_role)
                        SELECT rp.network_address,
                            rp.source_address,
                            new.voltage,
                            new.node_role
                        FROM received_packets rp
                        WHERE rp.id = new.received_packet
                        ON DUPLICATE KEY UPDATE voltage=new.voltage,node_role=new.node_role;
                     END;"""
        self.cursor.execute(trigger)

        # Create a trigger for updating boot info to known nodes
        trigger = "DROP TRIGGER IF EXISTS after_diagnostic_boot_insert;"
        self.cursor.execute(trigger)

        trigger = """CREATE TRIGGER `after_diagnostic_boot_insert` AFTER INSERT ON `diagnostic_boot` FOR EACH ROW BEGIN
        INSERT INTO known_nodes (
            network_address,
            node_address,
             node_role,
              firmware_version,
              scratchpad_seq,
              hw_magic,
              stack_profile,
              boot_count,
              file_line_num,
              file_name_hash)
        SELECT rp.network_address,
            rp.source_address,
            new.node_role,
            new.firmware_version,
            new.scratchpad_seq,
            new.hw_magic,
            new.stack_profile,
            new.boot_count,
            new.file_line_num,
            new.file_name_hash
        FROM received_packets rp
        WHERE rp.id=new.received_packet
        ON DUPLICATE KEY UPDATE
        node_role=new.node_role,
        firmware_version=new.firmware_version,
        scratchpad_seq=new.scratchpad_seq,
        hw_magic=new.hw_magic,
        stack_profile=new.stack_profile,
        boot_count=new.boot_count,
        file_line_num=new.file_line_num,
        file_name_hash=new.file_name_hash;
        END;"""
        self.cursor.execute(trigger)

        # Create the debug log table
        createtable = (
            "CREATE TABLE IF NOT EXISTS log("
            "  recordtime text,"
            "  debuglog text"
            "  ) ENGINE = InnoDB;"
        )
        self.cursor.execute(createtable)

        self.database.commit()

    def update_diagnostic_node_table_4_0(self):
        """ Checks if there is a need to expand the old diagnostic_node
        table with the new fields introduced in stack release 4.0"""

        query = "SHOW COLUMNS FROM diagnostic_node;"
        self.cursor.execute(query)
        self.database.commit()
        values = self.cursor.fetchall()
        column_names = map(lambda x: x[0], values)
        if "lltx_msg_w_ack" not in column_names:
            # lltx_msg_w_ack was not in the table so add it.
            query = (
                "ALTER TABLE diagnostic_node\n"
                "ADD COLUMN lltx_msg_w_ack INT UNSIGNED DEFAULT NULL;"
            )
            self.cursor.execute(query)
            self.database.commit()
        if "lltx_msg_unack" not in column_names:
            # lltx_msg_unack not in the table so add it.
            query = (
                "ALTER TABLE diagnostic_node\n"
                "ADD COLUMN lltx_msg_unack INT UNSIGNED DEFAULT NULL;"
            )
            self.cursor.execute(query)
            self.database.commit()
        if "llrx_w_unack_ok" not in column_names:
            # llrx_w_unack_ok not in the table so add it.
            query = (
                "ALTER TABLE diagnostic_node\n"
                "ADD COLUMN llrx_w_unack_ok INT UNSIGNED DEFAULT NULL;"
            )
            self.cursor.execute(query)
            self.database.commit()
        if "llrx_ack_not_received" not in column_names:
            # llrx_ack_not_received not in the table so add it.
            query = (
                "ALTER TABLE diagnostic_node\n"
                "ADD COLUMN llrx_ack_not_received INT UNSIGNED DEFAULT NULL;"
            )
            self.cursor.execute(query)
            self.database.commit()
        if "lltx_cca_unack_fail" not in column_names:
            # lltx_cca_unack_fail not in the table so add it.
            query = (
                "ALTER TABLE diagnostic_node\n"
                "ADD COLUMN lltx_cca_unack_fail INT UNSIGNED DEFAULT NULL;"
            )
            self.cursor.execute(query)
            self.database.commit()
        if "lltx_cca_w_ack_fail" not in column_names:
            # lltx_cca_w_ack_fail not in the table so add it.
            query = (
                "ALTER TABLE diagnostic_node\n"
                "ADD COLUMN lltx_cca_w_ack_fail INT UNSIGNED DEFAULT NULL;"
            )
            self.cursor.execute(query)
            self.database.commit()
        if "llrx_w_ack_ok" not in column_names:
            # llrx_w_ack_ok not in the table so add it.
            query = (
                "ALTER TABLE diagnostic_node\n"
                "ADD COLUMN llrx_w_ack_ok INT UNSIGNED DEFAULT NULL;"
            )
            self.cursor.execute(query)
            self.database.commit()
        if "llrx_ack_otherreasons" not in column_names:
            # llrx_ack_otherreasons not in the table so add it.
            query = (
                "ALTER TABLE diagnostic_node\n"
                "ADD COLUMN llrx_ack_otherreasons INT UNSIGNED DEFAULT NULL;"
            )
            self.cursor.execute(query)
            self.database.commit()
        if "blacklistexceeded" not in column_names:
            # blacklistexceeded not in the table so add it.
            query = (
                "ALTER TABLE diagnostic_node\n"
                "ADD COLUMN blacklistexceeded BIGINT UNSIGNED DEFAULT NULL;"
            )
            self.cursor.execute(query)
            self.database.commit()

    def update_diagnostic_node_table_4_2(self):
        """ Checks if there is a need to expand the old diagnostic_node
        table with the new fields introduced in stack release 4.2"""

        query = "SHOW COLUMNS FROM diagnostic_node;"
        self.cursor.execute(query)
        self.database.commit()
        values = self.cursor.fetchall()
        column_names = map(lambda x: x[0], values)
        # Optional buffer statistics
        if "pending_ucast_cluster" not in column_names:
            query = (
                "ALTER TABLE diagnostic_node\n"
                "ADD COLUMN pending_ucast_cluster INT UNSIGNED DEFAULT NULL;"
            )
            self.cursor.execute(query)
            self.database.commit()
        if "pending_ucast_members" not in column_names:
            query = (
                "ALTER TABLE diagnostic_node\n"
                "ADD COLUMN pending_ucast_members INT UNSIGNED DEFAULT NULL;"
            )
            self.cursor.execute(query)
            self.database.commit()
        if "pending_bcast_le_members" not in column_names:
            query = (
                "ALTER TABLE diagnostic_node\n"
                "ADD COLUMN pending_bcast_le_members INT UNSIGNED DEFAULT NULL;"
            )
            self.cursor.execute(query)
            self.database.commit()
        if "pending_bcast_ll_members" not in column_names:
            query = (
                "ALTER TABLE diagnostic_node\n"
                "ADD COLUMN pending_bcast_ll_members INT UNSIGNED DEFAULT NULL;"
            )
            self.cursor.execute(query)
            self.database.commit()
        if "pending_bcast_unack" not in column_names:
            query = (
                "ALTER TABLE diagnostic_node\n"
                "ADD COLUMN pending_bcast_unack INT UNSIGNED DEFAULT NULL;"
            )
            self.cursor.execute(query)
            self.database.commit()
        if "pending_expire_queue" not in column_names:
            query = (
                "ALTER TABLE diagnostic_node\n"
                "ADD COLUMN pending_expire_queue INT UNSIGNED DEFAULT NULL;"
            )
            self.cursor.execute(query)
            self.database.commit()
        if "pending_bcast_next_hop" not in column_names:
            query = (
                "ALTER TABLE diagnostic_node\n"
                "ADD COLUMN pending_bcast_next_hop INT UNSIGNED DEFAULT NULL;"
            )
            self.cursor.execute(query)
            self.database.commit()
        if "pending_reroute_packets" not in column_names:
            query = (
                "ALTER TABLE diagnostic_node\n"
                "ADD COLUMN pending_reroute_packets INT UNSIGNED DEFAULT NULL;"
            )
            self.cursor.execute(query)
            self.database.commit()

    def store_variable_statement_to_update_list(
        self, statement: str, values: str, incrementCounter: int
    ):

        ret: bool = False

        if len(statement) > 0:

            if incrementCounter not in self.sql_insert_variable_statements:
                self.sql_insert_variable_statements[incrementCounter] = list()

            self.sql_insert_variable_statements[incrementCounter].append(
                (statement, values)
            )

            ret = True

        return ret

    def store_insert_to_update_list(
        self, sql_insert: str, incrementCounter: int
    ) -> bool:

        ret: bool = False

        if len(sql_insert) > 0:
            if incrementCounter not in self.sql_insert_update_statements:
                # There should be at least one element already added.
                # received packet message is first and others relations to it
                ret = False
            else:
                self.sql_insert_update_statements[incrementCounter].append(
                    sql_insert
                )

            ret = True

        return ret

    def check_and_write_integrity_test_data(self, message) -> bool:

        # Incoming message payload should be 102 bytes.
        # First 8 bytes form ascii hex coded 32 bit uint and rest is fill data
        # 00000001------------------------------------ up to 102 bytes
        s = message.data_payload.decode("utf-8")
        seqStr = s[0:8]
        try:
            checksum_number = int(seqStr, 16)
        except ValueError:
            errorMsg = "Failed to convert checksum number"
            self.logger.error(errorMsg)
            return

        if self.integrity_check_sum == 0:
            self.integrity_check_sum = checksum_number
        else:
            if checksum_number - 1 == self.integrity_check_sum:
                if self.integrity_check_sum_is_failing is True:
                    self.logger.info(
                        "Sequence number now ok. number={}".format(
                            checksum_number
                        )
                    )
                self.integrity_check_sum_is_failing = False
            else:
                self.integrity_checks_failed += 1
                self.integrity_check_sum_is_failing = True
                msgStr = "Checksum failed. prev={} curr={}".format(
                    self.integrity_check_sum, checksum_number
                )
                self.logger.error(msgStr)

            self.integrity_check_sum = checksum_number

        epoch_time = int(time())

        statement = (
            "INSERT INTO integrity_test (message_time, db_write_time,"
            " checksum_number) VALUES (from_unixtime({}), "
            "from_unixtime({}), {})".format(
                message.rx_time_ms_epoch / 1000, epoch_time, checksum_number
            )
        )

        self.sql_integrity_check_statements.append(statement)
        return True

    def put_to_received_packets(self, message, incrementCounter: int) -> bool:
        """ Insert received packet to the database """

        try:
            hop_count = message.hop_count
        except:
            hop_count = 0
        query = (
            "INSERT INTO received_packets (logged_time, launch_time, path_delay_ms, network_address, sink_address, source_address, "
            "dest_address, source_endpoint, dest_endpoint, qos, num_bytes, hop_count) "
            "VALUES (from_unixtime({}), from_unixtime({}), {}, {}, {}, {}, {}, {}, {}, {}, {}, {});".format(
                message.rx_time_ms_epoch / 1000,
                (message.rx_time_ms_epoch - message.travel_time_ms) / 1000,
                message.travel_time_ms,
                message.network_id,
                message.destination_address,
                message.source_address,
                message.destination_address,
                message.source_endpoint,
                message.destination_endpoint,
                message.qos,
                len(message.data_payload),
                hop_count,
            )
        )

        if incrementCounter not in self.sql_insert_update_statements:
            self.sql_insert_update_statements[incrementCounter] = list()
            self.sql_insert_update_statements[incrementCounter].append(query)
            ret = True
        else:
            # This message should be first one.
            ret = False

        if ret is False:
            self.logger.warning(
                "put_to_received_packets " "failed to store data"
            )

        return ret

    def put_diagnostics(self, message, incrementCounter: int) -> bool:
        """ Dumps the diagnostic object into a table """

        ret: bool = False

        statement = (
            "INSERT INTO diagnostics_json (received_packet, apdu) "
            "VALUES (LAST_INSERT_ID(), %s)"
        )
        values = json.dumps(message.serialize())
        ret = self.store_variable_statement_to_update_list(
            statement, values, incrementCounter
        )
        if ret is False:
            self.logger.warning("put_diagnostics " "failed to store data")
        return ret

    def put_advertiser(self, message, incrementCounter: int) -> bool:

        ret: bool = False

        """ Dumps the advertiser object into a table """

        statement = "INSERT INTO advertiser_json (received_packet, apdu) VALUES (LAST_INSERT_ID(), %s)"
        message.full_adv_serialization = True
        values = json.dumps(message.serialize())

        ret = self.store_variable_statement_to_update_list(
            statement, values, incrementCounter
        )

        if ret is False:
            self.logger.warning("put_advertiser " "failed to store data")
        return ret

    def put_traffic_diagnostics(self, message, incrementCounter: int):
        """ Insert traffic diagnostic packets """

        ret: bool = False

        query = (
            "INSERT INTO diagnostic_traffic "
            "(received_packet, access_cycles, "
            "cluster_members, cluster_headnode_members, cluster_channel, "
            "channel_reliability, rx_count, tx_count, aloha_rxs, resv_rx_ok, "
            "data_rxs, dup_rxs, cca_ratio, bcast_ratio, tx_unicast_fail, "
            "resv_usage_max, resv_usage_avg, aloha_usage_max)"
            "VALUES (LAST_INSERT_ID(),{},{},{},{},{},{},{},{},{},{},{},{},{},"
            "{},{},{},{});".format(
                message.apdu["access_cycles"],
                message.apdu["cluster_members"],
                message.apdu["cluster_headnode_members"],
                message.apdu["cluster_channel"],
                message.apdu["channel_reliability"],
                message.apdu["rx_amount"],
                message.apdu["tx_amount"],
                message.apdu["aloha_rx_ratio"],
                message.apdu["reserved_rx_success_ratio"],
                message.apdu["data_rx_ratio"],
                message.apdu["rx_duplicate_ratio"],
                message.apdu["cca_success_ratio"],
                message.apdu["broadcast_ratio"],
                message.apdu["failed_unicast_ratio"],
                message.apdu["max_reserved_slot_usage"],
                message.apdu["average_reserved_slot_usage"],
                message.apdu["max_aloha_slot_usage"],
            )
        )

        ret = self.store_insert_to_update_list(query, incrementCounter)

        if ret is False:
            self.logger.warning(
                "put_traffic_diagnostics " "failed to store data"
            )

        return ret

    def put_neighbor_diagnostics(self, message, incrementCounter: int) -> bool:
        """ Insert neighbor diagnostic packets """
        ret: bool = False

        # See if any neighbors, do not do insert
        try:
            if message.neighbor[0]["address"] == 0:
                ret = True
                return ret
        except KeyError:
            ret = True
            return ret

        # Insert all neighbors at once
        values = []
        for i in range(0, 14):
            try:
                if message.neighbor[i]["address"] == 0:
                    break
            except KeyError:
                # Number of neighbors depends on profile and can be less than
                # 14
                break

            values.append(
                "(LAST_INSERT_ID(),{},{},{},{},{})".format(
                    message.neighbor[i]["address"],
                    message.neighbor[i]["cluster_channel"],
                    message.neighbor[i]["radio_power"],
                    message.neighbor[i]["node_info"],
                    message.neighbor[i]["rssi"],
                )
            )

        query = (
            "INSERT INTO diagnostic_neighbor "
            "(received_packet, node_address, cluster_channel, "
            "radio_power, device_info, norm_rssi) "
            "VALUES {};".format(",".join(values))
        )

        ret = self.store_insert_to_update_list(query, incrementCounter)
        return ret

    def put_boot_diagnostics(self, message, incrementCounter: int) -> bool:
        """ Insert boot diagnostic packets """

        ret: bool = False

        query = (
            "INSERT INTO diagnostic_boot "
            "(received_packet, boot_count, node_role, firmware_version, "
            "scratchpad_seq, hw_magic, stack_profile, otap_enabled, "
            "file_line_num, file_name_hash, stack_trace_0, stack_trace_1, "
            "stack_trace_2, current_seq) "
            "VALUES (LAST_INSERT_ID(), {}, {}, {}, {}, {}, {}, {}, {}, "
            "{}, {}, {}, {}, {});".format(
                message.apdu["boot_count"],
                message.apdu["node_role"],
                message.apdu["firmware_version"],
                message.apdu["scratchpad_sequence"],
                message.apdu["hw_magic"],
                message.apdu["stack_profile"],
                message.apdu["otap_enabled"],
                message.apdu["boot_line_number"],
                message.apdu["file_hash"],
                message.apdu["stack_trace_0"],
                message.apdu["stack_trace_1"],
                message.apdu["stack_trace_2"],
                message.apdu["cur_seq"],
            )
        )
        ret = self.store_insert_to_update_list(query, incrementCounter)

        if ret is False:
            self.logger.warning("put_advertiser " "failed to store data")
        return ret

    def put_node_diagnostics(self, message, incrementCounter: int) -> bool:
        """ Insert node diagnostic packets """
        # pylint: disable=locally-disabled, too-many-branches

        ret: bool = False

        pending_ucast_cluster = "NULL"
        pending_ucast_members = "NULL"
        pending_bcast_le_mbers = "NULL"
        pending_bcast_ll_mbers = "NULL"
        pending_bcast_unack = "NULL"
        pending_expire_queue = "NULL"
        pending_bcast_next_hop = "NULL"
        pending_reroute_packets = "NULL"

        # Optional buffer statistics
        if "pending_ucast_cluster" in message.apdu:
            pending_ucast_cluster = message.apdu["pending_ucast_cluster"]

        if "pending_ucast_members" in message.apdu:
            pending_ucast_members = message.apdu["pending_ucast_members"]

        if "pending_bcast_le_members" in message.apdu:
            pending_bcast_le_mbers = message.apdu["pending_bcast_le_members"]

        if "pending_bcast_ll_members" in message.apdu:
            pending_bcast_ll_mbers = message.apdu["pending_bcast_ll_members"]

        if "pending_bcast_unack" in message.apdu:
            pending_bcast_unack = message.apdu["pending_bcast_unack"]

        if "pending_expire_queue" in message.apdu:
            pending_expire_queue = message.apdu["pending_expire_queue"]

        if "pending_bcast_next_hop" in message.apdu:
            pending_bcast_next_hop = message.apdu["pending_bcast_next_hop"]

        if "pending_reroute_packets" in message.apdu:
            pending_reroute_packets = message.apdu["pending_reroute_packets"]

        query = (
            "INSERT INTO diagnostic_node "
            "(received_packet, access_cycle_ms, node_role, voltage, "
            "buf_usage_max, buf_usage_avg, mem_alloc_fails, "
            "tc0_delay, tc1_delay, network_scans, "
            "downlink_delay_avg_0, downlink_delay_min_0, "
            "downlink_delay_max_0, downlink_delay_samples_0, "
            "downlink_delay_avg_1, downlink_delay_min_1, "
            "downlink_delay_max_1, downlink_delay_samples_1, "
            "lltx_msg_w_ack, "
            "lltx_msg_unack, "
            "llrx_w_unack_ok, "
            "llrx_ack_not_received, "
            "lltx_cca_unack_fail, "
            "lltx_cca_w_ack_fail, "
            "llrx_w_ack_ok, "
            "llrx_ack_otherreasons, "
            "dropped_packets_0, dropped_packets_1, route_address, "
            "next_hop_address_0, cost_0, quality_0, "
            "next_hop_address_1, cost_1, quality_1, "
            "blacklistexceeded, "
            "pending_ucast_cluster, "
            "pending_ucast_members, "
            "pending_bcast_le_members, "
            "pending_bcast_ll_members, "
            "pending_bcast_unack, "
            "pending_expire_queue, "
            "pending_bcast_next_hop, "
            "pending_reroute_packets) "
            "VALUES (LAST_INSERT_ID(),{},{},{},{},{},{},{},{},{},{},{},{},{},"
            "{},{},{},{},{},{},{},{},{},{},{},{},{},{},{},{},{},{},{},{},{},"
            "{},{},{},{},{},{},{},{},{});".format(
                message.apdu["access_cycle"],
                message.apdu["role"],
                message.apdu["voltage"],
                message.apdu["max_buffer_usage"],
                message.apdu["average_buffer_usage"],
                message.apdu["mem_alloc_fails"],
                message.apdu["normal_priority_buf_delay"],
                message.apdu["high_priority_buf_delay"],
                message.apdu["network_scans"],
                message.apdu["dl_delay_avg_0"],
                message.apdu["dl_delay_min_0"],
                message.apdu["dl_delay_max_0"],
                message.apdu["dl_delay_samples_0"],
                message.apdu["dl_delay_avg_1"],
                message.apdu["dl_delay_min_1"],
                message.apdu["dl_delay_max_1"],
                message.apdu["dl_delay_samples_1"],
                message.apdu["lltx_msg_w_ack"],
                message.apdu["lltx_msg_unack"],
                message.apdu["llrx_w_unack_ok"],
                message.apdu["llrx_ack_not_received"],
                message.apdu["lltx_cca_unack_fail"],
                message.apdu["lltx_cca_w_ack_fail"],
                message.apdu["llrx_w_ack_ok"],
                message.apdu["llrx_ack_otherreasons"],
                message.apdu["dropped_packets_0"],
                message.apdu["dropped_packets_1"],
                message.apdu["route_address"],
                message.apdu["cost_info_next_hop_0"],
                message.apdu["cost_info_cost_0"],
                message.apdu["cost_info_link_quality_0"],
                message.apdu["cost_info_next_hop_1"],
                message.apdu["cost_info_cost_1"],
                message.apdu["cost_info_link_quality_1"],
                message.apdu["blacklistexceeded"],
                pending_ucast_cluster,
                pending_ucast_members,
                pending_bcast_le_mbers,
                pending_bcast_ll_mbers,
                pending_bcast_unack,
                pending_expire_queue,
                pending_bcast_next_hop,
                pending_reroute_packets,
            )
        )
        ret = self.store_insert_to_update_list(query, incrementCounter)
        if ret is True:
            # Create events

            events = []
            max_event_count: int = 15
            for i in range(0, max_event_count):
                event = message.apdu["events_{}".format(i)]
                if event != 0:
                    # LAST_INSERT_ID() will be replaced when doing bulk update
                    # with packet id
                    events.append(
                        "({},{},{})".format("LAST_INSERT_ID()", i, event)
                    )

            if events:
                query = (
                    "INSERT INTO diagnostic_event "
                    "(received_packet, position, event) "
                    "VALUES {};".format(",".join(events))
                )
                ret = self.store_insert_to_update_list(query, incrementCounter)

        if ret is False:
            self.logger.warning("put_node_diagnostics " "failed to store data")
        return ret

    def put_testnw_measurements(self, message, incrementCounter: int) -> bool:
        """ Insert received test network application packets """

        ret: bool = False

        for row in range(message.apdu["row_count"]):
            table_name = "TestData_ID_" + str(message.apdu["testdata_id"][row])

            data_column_names = ",".join(
                map(
                    lambda x: "DataCol_" + str(x),
                    range(1, message.apdu["number_of_fields"][row] + 1),
                )
            )

            data_column_values = ",".join(
                map(str, message.apdu["datafields"][row])
            )

            query = (
                "INSERT INTO "
                + table_name
                + " "
                + "(received_packet,"
                + "logged_time,"
                + "launch_time,"
                + "field_count,"
                + "ID_ctrl,"
                + data_column_names
                + ")"
                + " VALUES ("
                + "LAST_INSERT_ID(),"
                + "{0:.32f},".format(message.rx_time_ms_epoch / 1000)
                + "{0:.32f},".format(
                    (message.rx_time_ms_epoch - message.travel_time_ms) / 1000
                )
                + str(message.apdu["number_of_fields"][row])
                + ","
                + str(message.apdu["id_ctrl"][row])
                + ","
                + data_column_values
                + ")"
            )
            ret = self.store_insert_to_update_list(query, incrementCounter)
            if ret is False:
                self.logger.warning(
                    "put_testnw_measurements " "failed to store data"
                )
                break
            else:
                pass

        return ret

    def flush_pending_inserts(self):

        update_start_time = perf_counter()

        dump_statements: bool = False
        dump_sql_stats: bool = False
        item_count_to_be_added = len(self.sql_insert_update_statements)
        exceptions_occurred: int = 0

        packet_id_before_update = (
            self.get_latest_packet_id_from_received_packets()
        )
        current_packet_id = packet_id_before_update

        try:
            commitNeeded: bool = False
            cursor = self.database.cursor()
            first_select_done: bool = False

            if len(self.sql_integrity_check_statements) > 0:
                commitNeeded = True
                self.do_integrity_check(cursor)

            for insertRef in self.sql_insert_update_statements.keys():
                msgs: list = self.sql_insert_update_statements[insertRef]
                if len(msgs) >= 1:
                    packetMsg = msgs[0]

                    # [A] Update primary table.
                    if cursor.execute(packetMsg) == 0:
                        raise Exception("Data base update failed")

                    if first_select_done is False:
                        # now we have transaction in progress (implicit start)
                        # Assume that inserts auto incremented primary key
                        # values  are monotonically increasing with step size 1

                        # sync packet id from DB
                        current_packet_id = (
                            self.get_latest_packet_id_from_received_packets()
                        )
                        first_select_done = True
                    else:
                        # We are inside transaction. Use value and save one
                        # select per message (access over network to DB)
                        current_packet_id += 1

                    if dump_statements is True:
                        print(current_packet_id, packetMsg)

                    # [B] Update other tables. packet id must match to first
                    # message that was used to update primary table [A].
                    self.handle_additional_data(
                        current_packet_id, cursor, dump_statements, msgs
                    )

                    commitNeeded = True

                    # [C] Check also JSON messages and add them. Packet id
                    # must match to primary table [A].
                    if insertRef in self.sql_insert_variable_statements:
                        self.handle_variable_statements(
                            current_packet_id,
                            cursor,
                            dump_statements,
                            insertRef,
                        )

                else:
                    self.logger.error("only 1 item in sql_insert_update_list")

            # Commit all
            if commitNeeded is True:
                self.database.commit()

        except Exception as e:
            exceptions_occurred += 1
            self.database.rollback()
            self.logger.error("SQL update error", e)

        packet_id_after_update = (
            self.get_latest_packet_id_from_received_packets()
        )

        # clear lists
        self.sql_insert_update_statements.clear()
        self.sql_insert_variable_statements.clear()

        self.itemsInDBTot += packet_id_after_update - packet_id_before_update
        update_stop_time = perf_counter()

        self.handle_insert_result(
            dump_sql_stats,
            item_count_to_be_added,
            packet_id_after_update,
            packet_id_before_update,
            update_start_time,
            update_stop_time,
            exceptions_occurred,
        )

    def handle_additional_data(
        self, current_packet_id, cursor, dump_statements, msgs
    ):
        for additionalData in msgs[1:]:
            modified = self.add_packet_id(additionalData, current_packet_id)
            if dump_statements is True:
                print(current_packet_id, modified)

            if cursor.execute(modified) == 0:
                raise Exception("Database child table update " "failed")

    def handle_variable_statements(
        self, current_packet_id, cursor, dump_statements, insertRef
    ):
        jsonMsgs: list = self.sql_insert_variable_statements[insertRef]
        for jsonMsg in jsonMsgs:
            a, b = jsonMsg
            modA = self.add_packet_id(a, current_packet_id)
            if dump_statements is True:
                print(current_packet_id, modA, b)

            if cursor.execute(modA, (b,)) == 0:
                raise Exception("No affected rows when " "updating JSON")

    def do_integrity_check(self, cursor):
        for integrity_statement in self.sql_integrity_check_statements:
            if cursor.execute(integrity_statement) == 0:
                raise Exception("Integrity check row insert failed")
        self.sql_integrity_check_statements.clear()

    def handle_insert_result(
        self,
        dump_sql_stats,
        item_count,
        packet_id_after_update,
        packet_id_before_update,
        update_start_time,
        update_stop_time,
        exceptions_occurred: int,
    ):
        if (
            packet_id_after_update - packet_id_before_update
        ) - item_count == 0:
            self.stat_inserts_ok += 1
            self.exceptions_occurred_count = exceptions_occurred

            msgsPerSec: float = 0
            if packet_id_after_update - packet_id_before_update > 0:
                msgsPerSec = (
                    packet_id_after_update - packet_id_before_update
                ) / (update_stop_time - update_start_time)

            interval_time_span: float = perf_counter()
            interval_time_elapsed_time: float = 0
            if self.prev_update_interval_perf_time is not None:
                interval_time_elapsed_time = (
                    interval_time_span - self.prev_update_interval_perf_time
                )

            self.prev_update_interval_perf_time = interval_time_span

            update_load: float = 0

            if interval_time_elapsed_time > 0:
                update_load = (
                    update_stop_time - update_start_time
                ) / interval_time_elapsed_time

            if dump_sql_stats is True:
                self.logger.debug(
                    "MySQL inserts PASS. Packet id before update:{} and after "
                    "update:{} ({} msgs). Inserts ok/nok:{}/{} ({}%) "
                    "Time elapsed:{} ms ({} msgs/sec) Load:{}% Exceptions:{}"
                    " IcheckFails:{}".format(
                        packet_id_before_update,
                        packet_id_after_update,
                        packet_id_after_update - packet_id_before_update,
                        self.stat_inserts_ok,
                        self.stat_inserts_fail,
                        "{:.1f}".format(
                            self.stat_inserts_ok
                            / (self.stat_inserts_fail + self.stat_inserts_ok)
                            * 100.0
                        ),
                        int((update_stop_time - update_start_time) * 1000),
                        "{:.2f}".format(msgsPerSec),
                        "{:.1f}".format(update_load * 100),
                        self.exceptions_occurred_count,
                        self.integrity_checks_failed,
                    )
                )
        else:
            self.stat_inserts_fail += 1
            self.logger.error(
                "MySQL inserts FAIL. Packet id before update:{} and after "
                "update:{} ({} msgs) Inserts ok/nok:{}/{} ({}%) Exceptions:{} "
                "IcheckFails:{}".format(
                    packet_id_before_update,
                    packet_id_after_update,
                    packet_id_after_update - packet_id_before_update,
                    self.stat_inserts_ok,
                    self.stat_inserts_fail,
                    "{:.1f}".format(
                        self.stat_inserts_ok
                        / (self.stat_inserts_fail + self.stat_inserts_ok)
                        * 100.0
                    ),
                    self.exceptions_occurred_count,
                    self.integrity_checks_failed,
                )
            )

    def get_latest_packet_id_from_received_packets(self) -> int:
        ret: int = 0
        try:
            sql_select_Query = (
                "SELECT id FROM received_packets ORDER BY ID DESC LIMIT 1"
            )
            cursor = self.database.cursor()
            cursor.execute(sql_select_Query)
            records = cursor.fetchall()
            if len(records) > 0:
                ret = records[0][0]

        except Exception as e:
            print(e)
            ret = 0

        return ret

    @staticmethod
    def add_packet_id(sql_insert_qry, packetId):
        # Replaces all occurrences of LAST_INSERT_ID() with given
        # packet id. If not match, returns original query

        ret: str = ""
        replaceStr: str = "LAST_INSERT_ID()"
        if replaceStr in sql_insert_qry:
            ret = sql_insert_qry.replace(
                replaceStr, "{}".format(int(packetId))
            )
        else:
            ret = sql_insert_qry

        return ret
