#!/usr/bin/env python3

# Version history
# V1 Baseline
# V2 fix consideration of min/max charging values
 
from influxdb_cli2.influxdb_cli2 import influxdb_cli2
from go_e_charger.go_e_charger_httpv2 import GoeCharger
from pv_fronius.fronius_symo import Symo

from config_data import *

import paho.mqtt.client as paho

import time
import datetime
import sys
import statistics

go_e_charger = GoeCharger(ipaddr=go_e_charger_ip)
influxdb2 = influxdb_cli2(influxdb_url, influxdb_token, influxdb_org, influxdb_bucket)
influxdb_table = go_e_table   

gen24 = Symo(ipaddr=symo_ip[0])

if gen24 is None:
    print("Gen24 don't like to talk to us")
    sys.exit(1)

def get_current_price():
    results = influxdb2.query_data('grid_tibber', 'price_total', datetime.datetime.utcnow()+datetime.timedelta(hours=-1), datetime.datetime.utcnow())
    if results:
        return results[0][3]

class evcontrol:
    def __init__(self, go_e_charger, gen24, influxdb):
        self.go_e_charger = go_e_charger
        self.gen24 = gen24
        self.influxdb = influxdb
        
        self.power_available = [ 3*230.0 ]
        self.power_available_len = 4   #len(self.power_available)
        self.debugstate = 0

        self.charge_below_price = 0.0
        val = self.get_setting_from_db('charge_below_price')
        if val: 
            self.charge_below_price = val
        
        oldmode = self.get_setting_from_db('mode')
        if oldmode:
            print("Reuse last mode from DB")
            self.change_mode(oldmode)
            self.max_charge_power = 8000
            val = self.get_setting_from_db('max_charge_power')
            if val: 
                self.max_charge_power = val

            self.min_charge_power = 0
            val = self.get_setting_from_db('min_charge_power')
            if val: 
                self.min_charge_power = val

        else:
            print("Use default mode")
            self.change_mode(1)

        # self.opmode = self.state_max_auto_charging

        self.disconnectcounter = 0
        self.needtoswitchcounter = 0

        self.update_values_before()
        self.update_values_after()

    def get_setting_from_db(self, name):
        results = influxdb2.query_data('ev_golf', name, datetime.datetime.utcnow()+datetime.timedelta(hours=-8), datetime.datetime.utcnow())
        if results:
            return results[-1][3]
        else:
            return None

    def load_setup_from_db(self, name, target):
        value = self.get_setting_from_db(name)
        if value and int(value) > 0:
            print("got from DB: {0} = {1}".format(name, value))
            return value
        else:
            print("could not get {0} from DB, do not change".format(name))

    def write_setup_to_db(self, name, value):
        print("Write Setting {0} = {1} to DB".format(name, value))
        self.influxdb.write_sensordata('ev_golf', name, value)

    def change_mode(self, newmode):
        print("set new state: {0}".format(newmode))
        if newmode == 1:
            self.opmode = self.state_max_auto_charging
            self.max_charge_power = 8000
            self.min_charge_power = 0
        elif newmode == 2:
            self.opmode = self.state_min_auto_charging
        elif newmode == 20:
            self.opmode = self.state_manual_charging
        elif newmode == 21:
            self.opmode = self.state_force_on_charging
            self.max_charge_power = 4200
            self.min_charge_power = 0
        elif newmode == 22:
            self.opmode = self.state_force_off_charging
        elif newmode == 25:
            self.opmode = self.state_pricelim_charging
            self.max_charge_power = 8000
            self.min_charge_power = 0
        else:
            self.change_mode(1)
        self.write_setup_to_db('mode', newmode)
    
    def state_max_auto_charging(self):
        self.update_values_before()
        print(self.max_charge_power)

        #if self.power_to_grid < -100.0:
            #self.power_available.append(self.power_to_grid)
            #print("-> Getting significant power from Grid, no excess power available for EV")
            #self.debugstate = 3

        if self.house_battery_soc < 40:
            self.power_available.append(0.0)
            print("-> House battery lower than 40%, don't do anything")
            self.debugstate = 2
            

        elif self.power_generated > 4*230.0:
            if self.power_generated > self.power_consumption - self.power_to_ev:
                power_now_available = (self.power_generated - (self.power_consumption - self.power_to_ev))
                print("-> PV-Generating at least more than 4*230.0W: {0}".format(power_now_available))
                if power_now_available <= self.min_charge_power:
                    power_now_available = self.min_charge_power
                if power_now_available >= self.max_charge_power:
                    power_now_available = self.max_charge_power
                self.power_available.append(power_now_available)
                self.debugstate = 5
            else:
                print("-> PV-Generating at least more than 4*230.0W, but house takes it already")
                self.power_available.append(self.min_charge_power)
                self.debugstate = 6
        else:
            print("Less than 4*230.0W generated")
            self.power_available.append(self.min_charge_power)
            self.debugstate = 7

        self.do_switching(6*230.0)
        self.update_values_after()

    
    def state_min_auto_charging(self):
        self.update_values_before()
                
        if self.house_battery_soc < 50:
            self.power_available.append(0.0)
            print("-> House battery lower than 50%, don't do anything")
            self.debugstate = 12

        elif self.power_to_grid < -100.0:
            self.power_available.append(0.0)
            print("-> Getting significant power from Grid, no excess power available for EV")
            self.debugstate = 13

        elif self.power_generated > 5500.0:
            if (self.power_generated-5500) > (self.power_consumption - self.power_to_ev):
                self.power_available.append((self.power_generated-5500) - (self.power_consumption - self.power_to_ev))
                print("-> PV-Generating at least more than 5500W, taking out 150W for the rest of the house")
                self.debugstate = 15
            else:
                self.power_available.append(0.0)
                print("-> PV-Generating at least more than 5500W, but house takes it already")
                self.debugstate = 16
        else:
            self.power_available.append(0.0)
            print("Less than 2000W generated")
            self.debugstate = 17

        self.do_switching(6*230.0)
        self.update_values_after()
    
    def state_manual_charging(self):
        self.debugstate = 20

        if self.go_e_charger.CableLocked() == True:
            self.disconnectcounter = 0
        else:
            self.disconnectcounter += 1
        
        print("disconnectcounter {0}".format(self.disconnectcounter))
        if self.disconnectcounter > 15:
            self.disconnectcounter = 0
            self.change_mode(22)

        self.power_available = [0.0]
        self.update_values_before()
        time.sleep(5)
        self.update_values_after()
    
    def state_force_on_charging(self):
        self.debugstate = 21
        
        if self.go_e_charger.CableLocked() == True:
            self.disconnectcounter = 0
        else:
            self.disconnectcounter += 1
        
        print("disconnectcounter {0}".format(self.disconnectcounter))
        if self.disconnectcounter > 15:
            self.disconnectcounter = 0
            self.change_mode(22)
        
        self.update_values_before()
        self.power_available = [self.max_charge_power]
        self.do_switching(1, force=True)
        self.update_values_after()
    
    def state_force_off_charging(self):
        self.debugstate = 22
        self.update_values_before()
        self.power_available = [0.0]
        self.do_switching(100000, force=True)
        self.update_values_after()

    def state_pricelim_charging(self):
        # global charge_below_price
        self.update_values_before()
        
        current_price = get_current_price()        
 
        print("------------------------------------------")
        if current_price <= self.charge_below_price:
            print("current price: {0} - charge_below_price {1} - switch on ".format(current_price, self.charge_below_price))
            self.debugstate = 25
            self.power_available = [self.max_charge_power]
            self.do_switching(1, force=True)
        else:
            print("current price: {0} - charge_below_price {1} - switch off ".format(current_price, self.charge_below_price))
            self.debugstate = 26
            self.power_available = [0.0]
            self.do_switching(100000, force=True)
        print("------------------------------------------")

        self.update_values_after()
    
    def update_values_before(self):
        influxdb_table = 'ev_golf'    

        #self.go_e_charger.responses = go_e_charger.GetStatusAll()
        # print(self.go_e_charger.responses)

        self.power_to_grid = self.gen24.read_data("Meter_Power_Total") * -1.0
        self.power_consumption = self.gen24.read_calculated_value("Consumption_Sum") 
        self.power_generated = self.gen24.read_calculated_value("PV_Power")
        self.power_to_ev = self.go_e_charger.P_All
        self.house_battery_soc = self.gen24.read_data("Battery_SoC")
        
        print("pwr_gen: {0}, pwr_grid: {1}, pwr_consum: {2}, pwr_ev: {3}".format(self.power_generated, self.power_to_grid, self.power_consumption, self.power_to_ev))

        self.influxdb.write_sensordata(influxdb_table, 'power_to_ev', self.power_to_ev)
        self.influxdb.write_sensordata(influxdb_table, 'charge_below_price', self.charge_below_price)


    def update_values_after(self):
        influxdb_table = 'ev_golf'    

        self.influxdb.write_sensordata(influxdb_table, 'debugstate', self.debugstate)
        self.influxdb.write_sensordata(influxdb_table, 'power_available', statistics.fmean(self.power_available))

        go_e_charger_dump = go_e_charger.GetStatusAll(filtered=True)
        print(go_e_charger_dump)

        self.influxdb.write_sensordata(influxdb_table, 'go_e_i_l1', go_e_charger_dump['i_l1'])
        self.influxdb.write_sensordata(influxdb_table, 'go_e_i_l2', go_e_charger_dump['i_l2'])
        self.influxdb.write_sensordata(influxdb_table, 'go_e_i_l3', go_e_charger_dump['i_l3'])
        self.influxdb.write_sensordata(influxdb_table, 'go_e_p_all', go_e_charger_dump['p_all'])


        self.influxdb.write_sensordata(influxdb_table, 'energy_total', go_e_charger_dump['energy_total'])
        self.influxdb.write_sensordata(influxdb_table, 'energy_to_ev', go_e_charger_dump['energy_since_connect']/1000.0)
        self.influxdb.write_sensordata(influxdb_table, 'km_to_ev', go_e_charger_dump['energy_since_connect']/1000.0 * (100/15))
        self.influxdb.write_sensordata(influxdb_table, 'ev_charger_amps', go_e_charger_dump['charger_max_current'])
        self.influxdb.write_sensordata(influxdb_table, 'ev_charger_phases', go_e_charger_dump['phase_switch_mode'])



    def do_switching(self, p_needed, force=False):
        influxdb_table = 'ev_golf'    
        
        while len(self.power_available) > self.power_available_len:
            self.power_available.pop(0)    
        if len(self.power_available) == 0:
            self.power_available = [0.0]

        print("Values in buffer")
        print(self.power_available)
        print("Average Power Available: {0} W, need {1} W".format(statistics.fmean(self.power_available),p_needed))
        
        p_avail = statistics.fmean(self.power_available)
        if  p_avail >= p_needed:
            print("Switch on")
            value = statistics.fmean(self.power_available)
            if self.go_e_charger.CableLocked() == True:
                self.go_e_charger.setChargingP(value)
            self.influxdb.write_sensordata(influxdb_table, 'ev_switch_state', 1 )
            
            self.go_e_charger.ForceOn = 1
            
            if self.needtoswitchcounter > 0:
                self.needtoswitchcounter -= 1
            
        else: 
            self.needtoswitchcounter += 1
            print("Tendency to Switch off, counter {0}".format(self.needtoswitchcounter))

            
            if self.needtoswitchcounter >= 20 or force == True:
                self.needtoswitchcounter = 0
                
                print("Really Switch off")
                self.influxdb.write_sensordata(influxdb_table, 'ev_switch_state', 0 )
                self.go_e_charger.ForceOn = 0

        if statistics.fmean(self.power_available) > 100:
            time.sleep(5)
        else:
            time.sleep(55)

golfonso = evcontrol(go_e_charger, gen24, influxdb2)

def on_connect(client, userdata, flags, rc):
    print("Connection returned result: " + str(rc))
    client.subscribe("pentling/ev_golf/change_mode", 1)
    client.subscribe("pentling/ev_golf/max_charge_power", 1)
    client.subscribe("pentling/ev_golf/min_charge_power", 1)
    client.subscribe("pentling/ev_golf/charge_below_price", 1)

# The callback for when a PUBLISH message is received from the server.
def on_message(client, userdata, msg):
    # print(msg.topic+": {0}".format(int(msg.payload)) )
    if msg.topic == "pentling/ev_golf/change_mode":
        if int(msg.payload) >= 0 and int(msg.payload) <= 99:
            print("MQTT Change state {0}".format(msg.payload))
            golfonso.change_mode(int(msg.payload))
    elif msg.topic == "pentling/ev_golf/max_charge_power":
        if int(msg.payload) >= 0 and int(msg.payload) <= 8000:
            print("MQTT max charge power {0}".format(msg.payload))
            golfonso.max_charge_power = int(msg.payload)
            golfonso.write_setup_to_db('max_charge_power', golfonso.max_charge_power)
    elif msg.topic == "pentling/ev_golf/min_charge_power":
        if int(msg.payload) >= 0 and int(msg.payload) <= 8000:
            print("MQTT min charge power {0}".format(msg.payload))
            golfonso.min_charge_power = int(msg.payload)
            golfonso.write_setup_to_db('min_charge_power', golfonso.min_charge_power)
    elif msg.topic == "pentling/ev_golf/charge_below_price":
        if float(msg.payload) >= 0.0 and float(msg.payload) <= 2.0:
            print("MQTT charge_below_price {0}".format(msg.payload))
            golfonso.charge_below_price = float(msg.payload)
            print(golfonso.charge_below_price)

mqtt= paho.Client()
mqtt.on_connect = on_connect
mqtt.on_message = on_message
mqtt.connect(mqtt_ip, mqtt_port)
mqtt.loop_start()


while True:
    
    golfonso.opmode()

    time.sleep(10)

