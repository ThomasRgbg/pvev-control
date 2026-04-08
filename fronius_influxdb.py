#!/usr/bin/env python3

import sys
import time
import argparse
import logging

from configparser import ConfigParser

from config_data import *
from influxdb_cli2.influxdb_cli2 import influxdb_cli2
from pv_fronius.fronius_symo import Symo


logging.basicConfig(format='fronius_influxdb: %(message)s', level=logging.INFO)


argparser = argparse.ArgumentParser()

argparser.add_argument("-a", "--address", help="IP Address of Symo",
                       action='store')
argparser.add_argument("-v", "--verbose", help="Be more verbose",
                       action='store_true')
argparser.add_argument("-t", "--database-table", help="Name of Database Table",
                       action='store')
argparser.add_argument("-d", "--device", help="Use predefined device (0/1)",
                       action='store')
argparser.add_argument("-c", "--config", help="configfile", action='store')
args = argparser.parse_args()


if args.config:
    config = ConfigParser(delimiters='=')

    if ".cfg" in args.config:
        config.configfile = args.config
        config.read(config.configfile)
    else:
        logging.error("Invalid configfile: {0}".format(args.config))
        sys.exit(1)
else:
    logging.info("no config file used")

if args.device and args.address:
    logging.error(
        "Can not use predefined config and setting address via commandline at same time")
    sys.exit(1)
elif args.device:
    logging.info("Using device profile {0}".format(args.device))
    # Todo: make it more elegant
    if int(args.device) == 0:
        ipaddr = config.get('symo0', 'ipaddr')
        influxdb_table = config.get('symo0', 'database_table')
    elif int(args.device) == 1:
        ipaddr = config.get('symo1', 'ipaddr')
        influxdb_table = config.get('symo1', 'database_table')
    else:
        logging.error("invalid device selected")
        sys.exit(1)
elif args.address and args.database_table:
    ipaddr = args.address
    influxdb_table = args.database_table
else:
    logging.error("No or wrong parameters set")
    sys.exit(1)

logging.info("Using IP {0}, Database Table {1}".format(ipaddr, influxdb_table))

influxdb = influxdb_cli2(influxdb_url, influxdb_token,
                         org=influxdb_org, bucket=influxdb_bucket)

symo = Symo(ipaddr)
logging.info("Found Inverter {0}".format(symo.name))

parameters = symo.get_all_parameters()
parameter_ignore = 'Sunspec'
calculated_parameters = symo.get_all_calculated()

while True:

    for name in parameters:
        if parameter_ignore in name:
            continue
        value = symo.read_data(name)

        if args.verbose:
            logging.info('{0} = {1}'.format(name, value))

        influxdb.write_sensordata(influxdb_table, name, value)
        time.sleep(0.02)

    for name in calculated_parameters:
        if parameter_ignore in name:
            continue
        value = symo.read_calculated_value(name)

        if args.verbose:
            logging.info('{0} = {1}'.format(name, value))

        influxdb.write_sensordata(influxdb_table, name, value)
        time.sleep(0.02)

    time.sleep(60)
