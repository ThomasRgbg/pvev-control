#!/usr/bin/env python3

import sys
import time
import argparse

from pv_fronius.fronius_symo import Symo
from influxdb_cli2.influxdb_cli2 import influxdb_cli2

from config_data import *

if __name__ == "__main__":
    import time
    
    argparser = argparse.ArgumentParser()
    
    argparser.add_argument("-a", "--address", help="IP Address of Symo", 
                           action='store')
    argparser.add_argument("-t", "--database-table", help="Name of Database Table", 
                           action='store')
    argparser.add_argument("-c", "--config", help="Use predefined config (starts with 0)", 
                           action='store')
    args = argparser.parse_args()
    
    print(args)
    
    if args.config and args.address:
        print("Can not use predefined config and setting address via commandline at some time") 
        sys.exit(1)
    elif args.config:
        print("Using config profile {0}".format(args.config))
        ipaddr = symo_ip[int(args.config)]
        influxdb_table = symo_table[int(args.config)]
    elif args.address and args.database_table:
        ipaddr = args.address
        influxdb_table = args.database_table
    else:
        print("No or wrong parameters set")
        sys.exit(1)

    print("Using IP {0}, Database Table {1}".format(ipaddr, influxdb_table))

    influxdb = influxdb_cli2(influxdb_url, influxdb_token, org=influxdb_org, bucket=influxdb_bucket)
    influxdb_table = 'pv_fronius'    
    
    symo = Symo(ipaddr)
    print("Found Inverter {0}".format(symo.name))

    parameters = symo.get_all_parameters()
    parameter_ignore = 'Sunspec'
    calculated_parameters = symo.get_all_calculated()

    while True:
        
        for name in parameters:
            if parameter_ignore in name:
                continue
            value = symo.read_data(name)
            
            print('{0} = {1}'.format(name,value))
            
            influxdb.write_sensordata(influxdb_table, name, value)
            time.sleep(0.02)
            
        for name in calculated_parameters:
            if parameter_ignore in name:
                continue
            value = symo.read_calculated_value(name)
            
            print('{0} = {1}'.format(name,value))
            
            influxdb.write_sensordata(influxdb_table, name, value)
            time.sleep(0.02)


        time.sleep(60)
