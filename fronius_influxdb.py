#!/usr/bin/env python3

import sys
import time
import argparse
import logging

import paho.mqtt.client as paho

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
        "Can not use predefined config and setting address  at same time")
    sys.exit(1)
elif args.device:
    logging.info("Using device profile {0}".format(args.device))
    # Todo: make it more elegant
    if int(args.device) == 0:
        config_section = 'symo0'
    elif int(args.device) == 1:
        config_section = 'symo1'
    else:
        logging.error("invalid or unknown device selected")
        sys.exit(1)

    ipaddr = config.get(config_section, 'ipaddr')
    influxdb_table = config.get(config_section, 'database_table')

    if config.get(config_section, 'publish_mqtt', fallback="false") == "true":
        mqtt = paho.Client()
        # For the moment publish only
        # mqtt.on_connect = on_connect
        # mqtt.on_message = on_message
        mqtt.pv_topic = config.get(config_section, 'mqtt_topic', fallback="")
        mqtt.pv_publish_fronius = config.get(config_section,
                                             'mqtt_publish_fronius',
                                             fallback="").split(',')
        mqtt.pv_publish_name = config.get(config_section,
                                          'mqtt_publish_name',
                                          fallback="").split(',')
        mqtt.connect(config.get('mqtt', 'server'),
                     config.getint('mqtt', 'port'))
        mqtt.loop_start()
    else:
        mqtt = None

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

        if mqtt is not None and name in mqtt.pv_publish_fronius:
            topic = mqtt.pv_topic + '/' + mqtt.pv_publish_name[mqtt.pv_publish_fronius.index(name)]
            if args.verbose:
                logging.info('mqtt publish: {0} = {1}'.format(topic, value))
            mqtt.publish(topic, value)

        time.sleep(0.02)

    for name in calculated_parameters:
        if parameter_ignore in name:
            continue
        value = symo.read_calculated_value(name)

        if args.verbose:
            logging.info('{0} = {1}'.format(name, value))

        influxdb.write_sensordata(influxdb_table, name, value)

        if mqtt is not None and name in mqtt.pv_publish_fronius:
            topic = mqtt.pv_topic + '/' + mqtt.pv_publish_name[mqtt.pv_publish_fronius.index(name)]
            if args.verbose:
                logging.info('mqtt publish: {0} = {1}'.format(topic, value))
            mqtt.publish(topic, value)

        time.sleep(0.02)

    time.sleep(60)
