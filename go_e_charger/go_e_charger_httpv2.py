#!/usr/bin/env python3

# -*- coding: utf-8 -*-

# Version history:
# V1: Baseline

# Based on https://github.com/cathiele/goecharger/blob/main/goecharger/goecharger.py
# API-documentation: https://go-e.co/app/api.pdf
# API keys https://github.com/goecharger/go-eCharger-API-v2/blob/main/apikeys-de.md
# controlling https://www.goingelectric.de/forum/viewtopic.php?t=71547
# http://192.168.0.12/api/status

import requests
from enum import Enum
from json.decoder import JSONDecodeError
import time

class GoeCharger:
    
    def __init__(self, ipaddr = '192.168.0.82'):
        self.ipaddr = ipaddr
        self.parameters = {
            # Format:
            # 'code' : ['Name', convertread, convertwrite]
            
            'car' : ['car_status', self.rpc_car_status, None], 
            'modelStatus' : ['model_status', self.rpc_model_status, None],
            'amp' : ['charger_max_current', None, None],
            'acu' : ['charger_target_current', None, None],
            'nrg' : ['energy_array', self.rpc_nrg, None],
            'frc' : ['force_state', None, None],
            'eto' : ['energy_total', lambda x: x/1000, None],
            'wh'  : ['energy_since_connect', lambda x: x/1, None],
            'psm' : ['phase_switch_mode', None, None],
            'cus' : ['cable_unlock_status', None, None],
            }

    def __ReadStatusAPI(self, params = 'all'):
        try:
            if 'all' == params:
                statusRequest = requests.get("http://%s/api/status" % self.ipaddr, timeout=5)
            else:
                # TODO: Does not really work
                # print("http://{0}/api/status?filter={1}".format( self.ipaddr, params))
                statusRequest = requests.get("http://{0}/api/status?filter={1}".format( self.ipaddr, params), timeout=5)
                # print(statusRequest.json())

            status = statusRequest.json()
            return status
        except (requests.exceptions.ConnectTimeout, requests.exceptions.ConnectionError):
            return {}

    def __WriteStatusAPI(self, parameter, value):
        setRequest = requests.get("http://%s/api/set?%s=%s" % (self.ipaddr, parameter, value))
        #return GoeChargerStatusMapper().mapApiStatusResponse(setRequest.json())
        
    def convert_incomming_dict(self, data, raw = False):
        results = {}
        for key, value in dict(data).items():
            # print("{0} = {1}".format(key, value))
            if key in self.parameters.keys():
                if self.parameters[key][1]:
                    if not raw:
                        convt_value = self.parameters[key][1](value)
                    else:
                        convt_value = value
                        
                    if isinstance(convt_value, dict):
                        results = results | convt_value
                    else:
                        results[ self.parameters[key][0] ] = convt_value
                else:
                    results[ self.parameters[key][0] ] = value
            
        return results
            
    def convert_outgoing_param(self, name, value):
        for code, params in self.parameters:
            if params[0] == name:
                return [code, value]
            
        return [None, None]

    # pcr = read parameter convert 
    def rpc_car_status(self,value):
        car_status = {
            1 : 'Charger ready, no vehicle',
            2 : 'charging',
            3 : 'Waiting for vehicle',
            4 : 'charging finished, vehicle still connected'
        }
        return car_status[value]

    def rpc_model_status(self,value):
        model_status = {
            0 : 'NotChargingBecauseNoChargeCtrlData',
            1 : 'NotChargingBecauseOvertemperature', 
            2 : 'NotChargingBecauseAccessControlWait', 
            3 : 'ChargingBecauseForceStateOn', 
            4 : 'NotChargingBecauseForceStateOff', 
            5 : 'NotChargingBecauseScheduler',
            6 : 'NotChargingBecauseEnergyLimit', 
            7 : 'ChargingBecauseAwattarPriceLow', 
            8 : 'ChargingBecauseAutomaticStopTestLadung',
            9 : 'ChargingBecauseAutomaticStopNotEnoughTime',
            10 : 'ChargingBecauseAutomaticStop', 
            11 : 'ChargingBecauseAutomaticStopNoClock', 
            12 : 'ChargingBecausePvSurplus',
            13 : 'ChargingBecauseFallbackGoEDefault',
            14 : 'ChargingBecauseFallbackGoEScheduler', 
            15 : 'ChargingBecauseFallbackDefault', 
            16 : 'NotChargingBecauseFallbackGoEAwattar',
            17 : 'NotChargingBecauseFallbackAwattar',
            18 : 'NotChargingBecauseFallbackAutomaticStop',
            19 : 'ChargingBecauseCarCompatibilityKeepAlive', 
            20 : 'ChargingBecauseChargePauseNotAllowed',
            22 : 'NotChargingBecauseSimulateUnplugging', 
            23 : 'NotChargingBecausePhaseSwitch', 
            24 : 'NotChargingBecauseMinPauseDuration'
        }
        return model_status[value]

    def rpc_nrg(self, values):
        results = {}
        results['u_l1'] = values[0]
        results['u_l2'] = values[1]
        results['u_l3'] = values[2]
        results['u_n']  = values[3]
        results['i_l1'] = values[4]
        results['i_l2'] = values[5]
        results['i_l3'] = values[6]
        results['p_l1'] = values[7]
        results['p_l2'] = values[8]
        results['p_l3'] = values[9]
        results['p_n']  = values[10]
        results['p_all'] = values[11]
        results['pf_l1'] = values[12]
        results['pf_l2'] = values[13]
        results['pf_l3'] = values[14]
        results['pf_n']  = values[15]

        return results

    def GetStatusAll(self, filtered=False):
        response = {}
        try:
            status = self.__ReadStatusAPI()
            
            response = self.convert_incomming_dict(status)
            if filtered:
                for key, value in dict(response).items():
                    if value is None:
                        del response[key]
            
        except JSONDecodeError:
            response = {}
        return response

    def GetStatusNums(self, filtered=False):
        response = {}
        try:
            status = self.__ReadStatusAPI()
            
            response = self.convert_incomming_dict(status, raw = True)
            if filtered:
                for key, value in dict(response).items():
                    if value is None:
                        del response[key]
                    if isinstance(value, str):
                        del response[key]
                    if isinstance(value, list):
                        del response[key]
            
        except JSONDecodeError:
            response = {}
        return response

    def GetStatusParam(self, statusparam):
        code = None
        try:
            for key, param in dict(self.parameters).items():
                if param[0] == statusparam:
                    code = key
                    break
            
            if code:
                status = self.__ReadStatusAPI(params = code)
                response = self.convert_incomming_dict(status)
            else:
                return None
            
        except JSONDecodeError:
            return None
        
        if len(list(response.values())) == 1:
            return list(response.values())[0]
        elif len(list(response.values())) > 1:
            return response
        else:
            return None
        
    def SetStatusParam(self, statusparam, value):
        code = None
        try:
            for key, param in dict(self.parameters).items():
                if param[0] == statusparam:
                    code = key
                    break
            
            if code:
                status = self.__WriteStatusAPI(parameter = code, value = value)
#                response = self.convert_incomming_dict(status)
            else:
                return None
            
        except JSONDecodeError:
            return None
        
#        if len(list(response.values())) > 0:
#            return list(response.values())[0]
#        else:
#            return None

    def CableLocked(self):
        if int(self.GetStatusParam('cable_unlock_status')) == 3:
            print("Cable locked")
            return True
        else:
            print("Cable not locked")
            return False

    @property
    def ChargerMaxCurrent(self):
        return self.GetStatusParam('charger_max_current')
    
    @ChargerMaxCurrent.setter
    def ChargerMaxCurrent(self, value):
        return self.SetStatusParam('charger_max_current', value)
        
    @property
    def ForceOn(self):
        return self.GetStatusParam('force_state') - 1
    
    @ForceOn.setter
    def ForceOn(self, value):
        if self.ForceOn == value:
            return None
        else:
            return self.SetStatusParam('force_state', value +1)

    @property
    def SetPhaseMode(self):
        psm = self.GetStatusParam('phase_switch_mode')
        if psm == 2:
            return 3
        else:
            return 1
    
    @SetPhaseMode.setter
    def SetPhaseMode(self, value):
        if value == 3:
            self.SetStatusParam('phase_switch_mode', 2)
        else:
            self.SetStatusParam('phase_switch_mode', 1)

    @property
    def P_All(self):
        values = self.GetStatusParam('energy_array')
        print(values)
        return values['p_all']

    def setChargingP(self, power):
        if power <= 5*230:
            power = 5*230
        elif power >= 16*3*230:
            power = 16*3*230
        
        max_1p = 230*16*1
        car_phases = 2
        min_3p = 230*5*car_phases
                
        if (power < min_3p):
            self.SetPhaseMode = 1
        elif (power > max_1p):
            self.SetPhaseMode = 3

        if self.SetPhaseMode == 3:
            power = power / car_phases
        
        amps = int(power / 230)
        if amps > 16:
            amps = 16
        print("set_charging_p to {0} A".format(amps))
        # if self.values['i_charge_cur_set'] != amps:
        self.ChargerMaxCurrent = amps
        time.sleep(10)




if __name__ == "__main__":
    import argparse
    import time

    argparser = argparse.ArgumentParser()
    argparser.add_argument("-a", "--address", help="IP address of go e", 
                           default='192.168.0.12', action='store')

    argparser.add_argument("--debug", help="Enable debug output",
                           action='store_true')
    
    argparser.add_argument("-w", "--wait", help="Wait for messages",
                           action='store_true')
    
    argparser.add_argument("-p", "--set-charging-p", help="Set Charging Power", 
                           action='store')
    
    argparser.add_argument("-e", "--enable-charging", help="Enable Charging", 
                           action='store')
        
    argparser.add_argument("-t", "--test", help="Enable Test functions",
                           action='store_true')

    args = argparser.parse_args()
    
    # print(args)

    go_e_charger = GoeCharger(args.address)

    if args.set_charging_p:
        go_e_charger.setChargingP(int(args.set_charging_p))

    if args.enable_charging:
        go_e_charger.ForceOn = int(args.enable_charging)

    if args.wait:
        while True:
            response =  go_e_charger.GetStatusAll(filtered=False)
            print("----")
            print(response)
            # go_e_charger.setChargingP(1380)
            print(go_e_charger.ChargerMaxCurrent)
            print(go_e_charger.P_All)
            # print(response['car_status'])
            # print(response['model_status'])
            time.sleep(10)
 

