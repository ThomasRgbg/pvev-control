#!/usr/bin/env python3

from pv_fronius.fronius_symo import Symo
from influxdb_cli2.influxdb_cli2 import influxdb_cli2

from config_data import *

import paho.mqtt.client as paho

import time
import datetime
import sys

gen24 = Symo(ipaddr=symo_ip[0])

if gen24 is None:
    print("Gen24 don't like to talk to us")
    sys.exit(1)

class battery:
    def __init__(self, gen24):
        self.operate = self.normal_operation
        self.override = False
        self.state_change = True
        self.state = 0
        self.cur_price = 10
        self.price_lim_discharge = 0.06
        self.price_lim_charge = 0.01

    def set_price_lim_discharge(self, price):
        self.price_lim_discharge = price
        self.state_change = True

    def set_price_lim_charge(self, price):
        self.price_lim_charge = price
        self.state_change = True

    def set_state(self, state):
        self.state = state
        if int(state) == 0:
            self.operate = self.normal_operation
            self.override = False
            self.state_change = True
            print("Set State to Auto")
        elif int(state) == 1:
            self.operate = self.normal_operation
            self.override = True
            self.state_change = True
            print("Set State to Normal Operation (forced)")
        elif int(state) == 2:
            self.operate = self.charge_only
            self.override = True
            self.state_change = True
            print("Set State to Charge Only (forced)")
        #elif int(state) == 3:
            #self.operate = self.slow_charge
            #self.override = False
            #self.state_change = True
            #print("Set State to Slow Charge (until 25%)")
        elif int(state) == 4:
            self.operate = self.gen24opt_charge
            self.override = False
            self.state_change = True
            print("Set State to optimized Engergy balance")
        elif int(state) == 5:
            self.operate = self.low_price
            self.override = False
            self.state_change = True
            print("Set State low price on grid")
        elif int(state) == 6:
            self.operate = self.very_low_price
            self.override = False
            self.state_change = True
            print("Set State very low price on grid")
        elif int(state) == 7:
            self.operate = self.battery_empty
            self.override = False
            self.state_change = True
            print("Set State Battery empty")
        else:
            print("unknown state, nothing changed")

    def get_state(self):
        return self.state

    def normal_operation(self):
        self.state = 1
        if self.state_change:
            print("Battery: Setting Charge unlim, Discharge unlim")
            gen24.set_battery_discharge_rate(None)
            gen24.set_battery_charge_rate(None)
            self.state_change = False

        gen24.enable(auto=False, enable=True)

        battery_soc = gen24.read_data("Battery_SoC")
        print("Battery SOC {0}%".format(battery_soc))
        print("Current Price {0}, Lim Price Discharge {1}, Lim Price Charge {2}".format(self.cur_price, self.price_lim_discharge, self.price_lim_charge))
        
        if (self.cur_price < self.price_lim_discharge) and not self.override:
            print("Set state to low_price")
            self.operate = self.low_price
            self.state_change = True
        elif battery_soc < 15 and not self.override:
            print("Set state to battery_empty")
            self.operate = self.battery_empty
            self.state_change = True
        else:
            print("Keep state Normal Operation")
            self.state_change = False
    
    def charge_only(self):
        self.state = 2
        if self.state_change:
            print("Battery: Setting Charge unlim, Discharge 0")
            gen24.set_battery_discharge_rate(0)
            gen24.set_battery_charge_rate(None)
            self.state_change = False

        gen24.enable(auto=False, enable=True)

        battery_soc = gen24.read_data("Battery_SoC")
        print("Battery SOC {0}%".format(battery_soc))
        print("Current Price {0}, Lim Price Discharge {1}, Lim Price Charge {2}".format(self.cur_price, self.price_lim_discharge, self.price_lim_charge))
        
        if self.cur_price < self.price_lim_charge and not self.override:
            print("Set state to Very low price")
            self.operate = self.very_low_price
            self.state_change = True
        elif (battery_soc > 25 and self.cur_price > self.price_lim_discharge) and not self.override:
            print("Set state to Normal Operation")
            self.operate = self.normal_operation
            self.state_change = True
        else:
            print("Keep state Charge Only")
            self.state_change = False

    #def slow_charge(self):
        #self.state = 3
        #if self.state_change:
            #print("Battery: Setting Charge 1000, Discharge unlim")
            #gen24.set_battery_discharge_rate(None)
            #gen24.set_battery_charge_rate(10)
            #self.state_change = False

        #battery_soc = gen24.read_data("Battery_SoC")
        #print("Battery SOC {0}%".format(battery_soc))
        
        #if battery_soc < 25 and not self.override:
            #print("Set state to Normal Operation")
            #self.operate = self.normal_operation
            #self.state_change = True
        #else:
            #print("Keep state Slow Charge")
            #self.state_change = False

    #def gen24opt_charge(self):
        #self.state = 4
        #if self.state_change:
            #print("Battery: Setting Charge 1000, Discharge unlim")
            #gen24.set_battery_discharge_rate(None)
            #gen24.set_battery_charge_rate(10)
            #self.state_change = False

        #battery_soc = gen24.read_data("Battery_SoC")
        #print("Battery SOC {0}%".format(battery_soc))
        
        #if battery_soc < 25 and not self.override:
            #print("Set state to Normal Operation")
            #self.operate = self.normal_operation
            #self.state_change = True
        #else:
            #print("Keep state Slow Charge")
            #self.state_change = False

    def low_price(self):
        self.state = 5
        if self.state_change:
            print("Battery: Setting Charge unlim, Discharge 0")
            gen24.set_battery_discharge_rate(0)
            gen24.set_battery_charge_rate(None)
            self.state_change = False

        gen24.enable(auto=True)

        battery_soc = gen24.read_data("Battery_SoC")
        print("Battery SOC {0}%".format(battery_soc))
        print("Current Price {0}, Lim Price Discharge {1}, Lim Price Charge {2}".format(self.cur_price, self.price_lim_discharge, self.price_lim_charge))
        
        if self.cur_price < self.price_lim_charge and not self.override:
            print("Set state to Very Low Price")
            self.operate = self.very_low_price
            self.state_change = True
        elif (battery_soc >= 15 and self.cur_price > self.price_lim_discharge) and not self.override:
            print("Set state to Normal Operation")
            self.operate = self.normal_operation
            self.state_change = True
        elif battery_soc < 15:
            print("Set state to battery_empty")
            self.operate = self.battery_empty
            self.state_change = True
        else:
            print("Keep state Low Price")
            self.state_change = False

    def very_low_price(self):
        self.state = 6
        if self.state_change:
            print("Battery: Setting Charge unlim, Discharge -5kW (=Charge Battery")
            gen24.set_battery_discharge_rate(-50)
            gen24.set_battery_charge_rate(None)
            self.state_change = False

        gen24.enable(auto=True)

        battery_soc = gen24.read_data("Battery_SoC")
        print("Battery SOC {0}%".format(battery_soc))
        print("Current Price {0}, Lim Price Discharge {1}, Lim Price Charge {2}".format(self.cur_price, self.price_lim_discharge, self.price_lim_charge))
        
        if self.cur_price > self.price_lim_charge and not self.override:
            print("Set state to Low Price")
            self.operate = self.low_price
            self.state_change = True
        else:
            print("Keep state Very Low Price")
            self.state_change = False

    def battery_empty(self):
        self.state = 7
        if self.state_change:
            print("Battery empty: Setting Charge unlim, Discharge 0")
            gen24.set_battery_discharge_rate(0)
            gen24.set_battery_charge_rate(None)
            self.state_change = False

        gen24.enable(auto=True)

        battery_soc = gen24.read_data("Battery_SoC")
        print("Battery SOC {0}%".format(battery_soc))
        print("Current Price {0}, Lim Price Discharge {1}, Lim Price Charge {2}".format(self.cur_price, self.price_lim_discharge, self.price_lim_charge))

        if self.cur_price < self.price_lim_charge and not self.override:
            print("Set state to Very low price")
            self.operate = self.very_low_price
            self.state_change = True
        elif (battery_soc > 25 and self.cur_price > self.price_lim_discharge) and not self.override:
            print("Set state to Normal Operation")
            self.operate = self.normal_operation
            self.state_change = True
        else:
            print("Keep state Charge Only")

bat = battery(gen24)

influxdb = influxdb_cli2(influxdb_url, influxdb_token, influxdb_org, influxdb_bucket)
influxdb_table = 'pv_fronius'    

def get_current_price():
    results = influxdb.query_data('grid_tibber', 'price_total', datetime.datetime.utcnow()+datetime.timedelta(hours=-1), datetime.datetime.utcnow())
    if results:
        return results[0][3]

def get_last_price_lim_discharge():
    results = influxdb.query_data('pv_fronius', 'battery_price_lim_discharge', datetime.datetime.utcnow()+datetime.timedelta(hours=-24), datetime.datetime.utcnow())
    if results:
        # print(results)
        print(results[-1][3])
        return results[-1][3]

def get_last_price_lim_charge():
    results = influxdb.query_data('pv_fronius', 'battery_price_lim_charge', datetime.datetime.utcnow()+datetime.timedelta(hours=-24), datetime.datetime.utcnow())
    if results:
        # print(results)
        print(results[-1][3])
        return results[-1][3]

def on_connect(client, userdata, flags, rc):
    print("Connection returned result: " + str(rc))
    client.subscribe("pentling/pv_fronius/battery_state_set", 1)
    client.subscribe("pentling/pv_fronius/battery_price_lim_discharge", 1)
    client.subscribe("pentling/pv_fronius/battery_price_lim_charge", 1)

# The callback for when a PUBLISH message is received from the server.
def on_message(client, userdata, msg):
    print(msg.topic+": {0}".format(msg.payload) )
    if msg.topic == "pentling/pv_fronius/battery_state_set":
        if int(msg.payload) >= 0 and int(msg.payload) <= 5:
            print("MQTT: receive battery_state_set {0}".format(msg.payload))
            bat.set_state(int(msg.payload))
    if msg.topic == "pentling/pv_fronius/battery_price_lim_discharge":
        if float(msg.payload) >= 0 and float(msg.payload) <= 30.0:
            print("MQTT: receive battery_price_lim_discharge {0}".format(msg.payload))
            bat.price_lim_discharge = float(msg.payload)
            bat.state_change = True
    if msg.topic == "pentling/pv_fronius/battery_price_lim_charge":
        if float(msg.payload) >= 0 and float(msg.payload) <= 30.0:
            print("MQTT: receive battery_price_lim_charge {0}".format(msg.payload))
            bat.price_lim_charge = float(msg.payload)
            bat.state_change = True

mqtt= paho.Client()
mqtt.on_connect = on_connect
mqtt.on_message = on_message
mqtt.connect(mqtt_ip, mqtt_port)
mqtt.loop_start()

force_switch_on = False
force_switch_off = False

lim = get_last_price_lim_discharge()
if lim:
    bat.set_price_lim_discharge(lim)

lim = get_last_price_lim_charge()
if lim:
    bat.set_price_lim_charge(lim)

while True:
    bat.cur_price = get_current_price()
    
    bat.operate()
    
    print("MQTT: send battery_state {0}".format(int(bat.get_state())))
    mqtt.publish("pentling/pv_fronius/battery_state", int(bat.get_state()))
    influxdb.write_sensordata(influxdb_table, 'battery_state', int(bat.get_state()))
    influxdb.write_sensordata(influxdb_table, 'battery_price_lim_discharge', bat.price_lim_discharge)
    influxdb.write_sensordata(influxdb_table, 'battery_price_lim_charge', bat.price_lim_charge)

    print("--------")
    for i in range(int(60)):
        time.sleep(5)
        #print(i)
        if bat.state_change == True:
            print("break")
            break
