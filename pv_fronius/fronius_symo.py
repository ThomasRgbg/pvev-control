#!/usr/bin/env python3

# Version history:
# V1: Baseline
# V2: Add Enable function, argparse for testprogram

# References:
# https://stoborblog.wordpress.com/2017/03/11/sunspec-solar-viewer-fronius-modbus/

from pyModbusTCP.client import ModbusClient
from pyModbusTCP import utils

import time
import math
import logging

logging.basicConfig(format='fronius_symo: %(message)s', level=logging.INFO)


class Symo:
    def __init__(self, ipaddr, model="autodetect"):
        self.ipaddr = ipaddr
        self.modbus = ModbusClient(host=ipaddr, port=502, auto_open=True, auto_close=True)
        self.model = model
        self.name = "Unkown"
        # self.modbus.debug(True)

        # Format:
        # "name : [register address, data type, unit 1]
        registers_gen24 = {
        # Common Block Register   
            "Sunspec_SID" : [40001, "uint32", 1],
            "Sunspec_Common_ID" : [40003, "uint16", 1],
            "Sunspec_Common_L" : [40004, "uint16", 1],
            "Sunspec_Devicename" : [40021, "string16", 1],
            "Sunspec_Software Version" : [40045, "string8", 1],
            "Sunspec_Inverter_ID" : [40070, "uint16", 1],
            "Sunspec_Inverter_L" : [40071, "uint16", 1],
            "AC_Phase-A_Current" : [40074, "float", 1],
            "AC_Phase-B_Current" : [40076, "float", 1],
            "AC_Phase-C_Current" : [40078, "float", 1],
            "AC_Voltage_Phase-AB" : [40080, "float", 1],
            "AC_Voltage_Phase-BC" : [40082, "float", 1],
            "AC_Voltage_Phase-CA" : [40084, "float", 1],
            "AC_Voltage_Phase-A-N" : [40086, "float", 1],
            "AC_Voltage_Phase-B-N" : [40088, "float", 1],
            "AC_Voltage_Phase-C-N" : [40090, "float", 1],
            "AC_Output_Power" : [40092, "float", 1],
            "AC_Frequency" : [40094, "float", 1],
            "AC_Energy" : [40102, "float", 1],
            "DC_Power" : [40108, "float", 1],
            
            "Cabinet_Temperature" : [40110, "float", 1],
            "Operating_State" : [40118, "uint16", 1],
        # Nameplate model
            "Nameplate_Continous_AC_Power" : [[40135,40136], "uint16_sunssf", 1],
            "Nameplate_Battery_Capacity" : [[40151,40152], "uint16_sunssf", 1],
            "Nameplate_Battery_Charge_Power" : [[40155,40156], "uint16_sunssf", 1],
            "Nameplate_Battery_Discharge_Power" : [[40157,40158], "uint16_sunssf", 1],
        # control model
            "Control_conn" : [40242, "uint16", 1],
        # Status model
            "Isolation_resistance" : [[40236,40237], "uint16_sunssf", 1],
        # Storage device (Battery)
            "Sunspec_Battery_ID" : [40354, "uint16", 1],
            "Sunspec_Battery_L" : [40355, "uint16", 1],
            "Battery_Max_Charge_Power" : [[40356,40372], "uint16_sunssf", 1],
            "Battery_WChaGra" : [40357, "uint16", 1],
            "Battery_WDisChaGra" : [40358, "uint16", 1],
            "Battery_StorCtl_Mod" : [40359, "uint16", 1],
            "Battery_Min_Reserve" : [[40361,40375], "uint16_sunssf", 1],
            "Battery_SoC" : [[40362,40376], "uint16_sunssf", 1],
            "Battery_Status" : [40365, "uint16", 1],
            "Battery_OutWRte" : [[40366,40379], "int16_sunssf", 1],
            "Battery_InWRte" : [[40367,40379], "int16_sunssf", 1],
            "Battery_InOutWRte_RvrtTm" : [40369, "uint16", 1],
            "Battery_ChaGriSet" : [40371, "uint16", 1],
        # Multiple MPPT
            "Sunspec_MPPT_ID" : [40264, "uint16", 1],
            "MPPT_1_DC_Current" : [[40283,40266], "uint16_sunssf", 1],
            "MPPT_1_DC_Voltage" : [[40284,40267], "uint16_sunssf", 1],
            "MPPT_1_DC_Power" : [[40285,40268], "uint16_sunssf", 1],
            "MPPT_1_DC_Energy" : [[40286,40269], "acc32_sunssf", 1],
            "MPPT_2_DC_Current" : [[40303,40266], "uint16_sunssf", 1],
            "MPPT_2_DC_Voltage" : [[40304,40267], "uint16_sunssf", 1],
            "MPPT_2_DC_Power" : [[40305,40268], "uint16_sunssf", 1],
            "MPPT_2_DC_Energy" : [[40306,40269], "acc32_sunssf", 1],
            "MPPT_3_DC_Current" : [[40323,40266], "uint16_sunssf", 1],
            "MPPT_3_DC_Voltage" : [[40324,40267], "uint16_sunssf", 1],
            "MPPT_3_DC_Power" : [[40325,40268], "uint16_sunssf", 1],
            "MPPT_3_DC_Energy" : [[40326,40269], "acc32_sunssf", 1],
            "MPPT_4_DC_Current" : [[40343,40266], "uint16_sunssf", 1],
            "MPPT_4_DC_Voltage" : [[40344,40267], "uint16_sunssf", 1],
            "MPPT_4_DC_Power" : [[40345,40268], "uint16_sunssf", 1],
            "MPPT_4_DC_Energy" : [[40346,40269], "acc32_sunssf", 1],
        # Power Meter
            "Sunspec_Meter_ID" : [40070, "uint16", 200],
            "Meter_Frequency" : [40096, "float", 200],
            "Meter_Power_Total" : [40098, "float", 200],
            "Meter_Power_L1" : [40100, "float", 200],
            "Meter_Power_L2" : [40102, "float", 200],
            "Meter_Power_L3" : [40104, "float", 200],
            "Meter_Real_Energy_Exported" : [40130, "float", 200],
            "Meter_Real_Energy_Exported_L1" : [40132, "float", 200],
            "Meter_Real_Energy_Exported_L2" : [40134, "float", 200],
            "Meter_Real_Energy_Exported_L3" : [40136, "float", 200],
            "Meter_Real_Energy_Imported" : [40138, "float", 200],
            "Meter_Real_Energy_Imported_L1" : [40140, "float", 200],
            "Meter_Real_Energy_Imported_L2" : [40142, "float", 200],
            "Meter_Real_Energy_Imported_L3" : [40144, "float", 200],
        }

        registers_symo = {
        # Common Block Register   
            "Sunspec_SID" : [40001, "uint32", 1],
            "Sunspec_Common_ID" : [40003, "uint16", 1],
            "Sunspec_Common_L" : [40004, "uint16", 1],
            "Sunspec_Devicename" : [40021, "string16", 1],
            "Sunspec_Software Version" : [40045, "string8", 1],
            "Sunspec_Inverter_ID" : [40070, "uint16", 1],
            "Sunspec_Inverter_L" : [40071, "uint16", 1],
            "AC_Phase-A_Current" : [40074, "float", 1],
            "AC_Phase-B_Current" : [40076, "float", 1],
            "AC_Phase-C_Current" : [40078, "float", 1],
            "AC_Voltage_Phase-AB" : [40080, "float", 1],
            "AC_Voltage_Phase-BC" : [40082, "float", 1],
            "AC_Voltage_Phase-CA" : [40084, "float", 1],
            "AC_Voltage_Phase-A-N" : [40086, "float", 1],
            "AC_Voltage_Phase-B-N" : [40088, "float", 1],
            "AC_Voltage_Phase-C-N" : [40090, "float", 1],
            "AC_Output_Power" : [40092, "float", 1],
            "AC_Frequency" : [40094, "float", 1],
            "AC_Energy" : [40102, "float", 1],
            "DC_Power" : [40108, "float", 1],
            "Operating_State" : [40118, "uint16", 1],
        # Nameplate model
            "Nameplate_Continous_AC_Power" : [[40135,40136], "uint16_sunssf", 1],
        # control model
            "Control_conn" : [40242, "uint16", 1],
        # Multiple MPPT
            "Sunspec_MPPT_ID" : [40264, "uint16", 1],
            "MPPT_1_DC_Current" : [[40283,40266], "uint16_sunssf", 1],
            "MPPT_1_DC_Voltage" : [[40284,40267], "uint16_sunssf", 1],
            "MPPT_1_DC_Power" : [[40285,40268], "uint16_sunssf", 1],
            "MPPT_2_DC_Current" : [[40303,40266], "uint16_sunssf", 1],
            "MPPT_2_DC_Voltage" : [[40304,40267], "uint16_sunssf", 1],
            "MPPT_2_DC_Power" : [[40305,40268], "uint16_sunssf", 1],
        }
        
        calculated_parameters_gen24 = {
            "Consumption_Sum" : ['AC_Output_Power', 'Meter_Power_Total', '+'],
            "Battery_Power" : ['MPPT_4_DC_Power', 'MPPT_3_DC_Power', '-'],
            "Battery_Current" : ['MPPT_4_DC_Current', 'MPPT_3_DC_Current', '-'],
            "PV_Power" : ['MPPT_1_DC_Power', 'MPPT_2_DC_Power', '+'],
            "AC_Output_L1" : ['AC_Voltage_Phase-A-N', 'AC_Phase-A_Current', '*'],
            "AC_Output_L2" : ['AC_Voltage_Phase-B-N', 'AC_Phase-B_Current', '*'],
            "AC_Output_L3" : ['AC_Voltage_Phase-C-N', 'AC_Phase-C_Current', '*'],
            }

        calculated_parameters_symo = {
            "PV_Power" : ['MPPT_1_DC_Power', 'MPPT_2_DC_Power', '+'],
            "AC_Output_L1" : ['AC_Voltage_Phase-A-N', 'AC_Phase-A_Current', '*'],
            "AC_Output_L2" : ['AC_Voltage_Phase-B-N', 'AC_Phase-B_Current', '*'],
            "AC_Output_L3" : ['AC_Voltage_Phase-C-N', 'AC_Phase-C_Current', '*'],
            }

        self.modbus.unit_id = 1
        sunspecid = self.read_uint16(40070)
        if sunspecid != 113:
            logging.warning("Warning: Invalid SunspecID, wrong device ?")

        if self.model == "autodetect":
            self.name = self.read_string(40021, 16)
            if self.name == None:
                logging.error("Error, could not identify Fronius device")
            elif "GEN24" in self.name:
                self.registers = registers_gen24
                self.calculated_parameters = calculated_parameters_gen24
            else:
                self.registers = registers_symo
                self.calculated_parameters = calculated_parameters_symo
        elif self.model == "symo_gen24":
            self.name = "Symo GEN24 forced"
            self.registers = registers_gen24
            self.calculated_parameters = calculated_parameters_gen24
        elif self.model == "symo":
            self.name = "Symo forced"
            self.registers = registers_symo
            self.calculated_parameters = calculated_parameters_symo
        else:
            logging.error("Error: Unkown symo model")
                                      
    def read_uint16(self, addr):
        regs = self.modbus.read_holding_registers(addr-1, 2)
        if regs:
            if regs[0] == 0xffff:
                logging.error("read_uint16() - invalid value/no data - addr: {0}".format(addr))
                return None
            else:
                return int(regs[0])
        else:
            logging.error("read_uint16() - error")
            return False
      
    def read_uint32(self, addr):
        regs = self.modbus.read_holding_registers(addr-1, 2)
        if regs:
            if regs[0] == 0xffff and regs[1] == 0xffff:
                logging.error("read_uint32() - invalid value/no data - addr: {0}".format(addr))
                return None
            else:
                return int(utils.word_list_to_long(regs, big_endian=True)[0])
        else:
            logging.error("read_uint32() - error - addr: {0}".format(addr))
            return False
        
    def read_float(self, addr):
        regs = self.modbus.read_holding_registers(addr-1, 2)
        if not regs:
            logging.error("read_float() - error - addr: {0}".format(addr))
            return False

        list_32_bits = utils.word_list_to_long(regs, big_endian=True)
        value = float(utils.decode_ieee(list_32_bits[0]))
        if math.isnan(value):
            return None
        else:
            return value

    def read_uint16_sunssf(self, addrs):
        value = self.modbus.read_holding_registers(addrs[0]-1, 1)
        scalereg = self.modbus.read_holding_registers(addrs[1]-1, 1)
        # logging.info(value[0],scalereg[0])
        if value and scalereg:
            if scalereg[0] == 0x8000:
                logging.error("read_uint16_sunssf() - invalid value/no data - addr: {0}".format(addrs[0]))
                return None
            elif value[0] == 0xffff:
                logging.error("read_uint16_sunssf() - invalid value/no data - addr: {0}".format(addrs[0]))
                return None
            elif scalereg[0] > 32768:   # Bad hack for int16 conversion
                scalef = 10**(scalereg[0]-65536)
            else:
                scalef = 10**(scalereg[0])
            return float(value[0] * scalef)
        else:
            logging.error("read_uint16_sunssf() - error - addr: {0}".format(addrs[0]))
            return False

    def read_int16_sunssf(self, addrs):
        value = self.modbus.read_holding_registers(addrs[0]-1, 1)
        scalereg = self.modbus.read_holding_registers(addrs[1]-1, 1)
        # logging.info(value[0],scalereg[0])
        if value and scalereg:
            if scalereg[0] == 0x8000:
                logging.error("read_uint16_sunssf() - invalid value/no data - addr: {0}".format(addrs[0]))
                return None
            elif value[0] == 0xffff:
                logging.error("read_uint16_sunssf() - invalid value/no data - addr: {0}".format(addrs[0]))
                return None
            elif scalereg[0] > 32768:   # Bad hack for int16 conversion
                scalef = 10**(scalereg[0]-65536)
            else:
                scalef = 10**(scalereg[0])
            if value[0] > 0x8000:
                value[0] = value[0] - 0xffff
            return float(value[0] * scalef)
        else:
            logging.error("read_int16_sunssf() - error - addr: {0}".format(addrs[0]))
            return False

    def read_acc32_sunssf(self, addrs):
        regs = self.modbus.read_holding_registers(addrs[0]-1, 2)
        value = int(utils.word_list_to_long(regs, big_endian=True)[0])
        scalereg = self.modbus.read_holding_registers(addrs[1]-1, 1)
        # logging.info(regs,scalereg[0])
        if regs and scalereg:
            if scalereg[0] == 0x8000:
                logging.error("read_acc32_sunssf() - invalid value/no data - addr: {0}".format(addrs[0]))
                return None
            elif value == 0xffffffff:
                logging.error("read_acc32_sunssf() - invalid value/no data - addr: {0}".format(addrs[0]))
                return None
            elif scalereg[0] > 32768:   # Bad hack for int16 conversion
                scalef = 10**(scalereg[0]-65536)
            else:
                scalef = 10**(scalereg[0])
            return float(value * scalef)
        else:
            logging.error("read_acc32_sunssf() - error - addr: {0}".format(addrs[0]))
            return False

    def read_string(self, addr, size):
        regs = self.modbus.read_holding_registers(addr-1, size)
        if regs:
            result = ''
            for i in range(size):
                if regs[i] == 0:
                    break
                result += (chr((regs[i]>>8) & 0xff))
                result += (chr(regs[i] & 0xff))
            if result == '':
                return False
            else:
                return result

    def read_data(self, parameter):
        [register, datatype, unit_id] = self.registers[parameter]
        
        self.modbus.unit_id = unit_id
        if datatype == "float":
            return self.read_float(register)
        elif datatype == "uint32":
            return self.read_uint32(register)
        elif datatype == "uint16":
            return self.read_uint16(register)
        elif datatype == 'uint16_sunssf':
            return self.read_uint16_sunssf(register)
        elif datatype == 'int16_sunssf':
            return self.read_int16_sunssf(register)
        elif datatype == 'acc32_sunssf':
            return self.read_acc32_sunssf(register)
        elif datatype == 'string8':
            return self.read_string(register, 8)
        elif datatype == 'string16':
            return self.read_string(register, 16)
        else:
            return False
        
    def read_calculated_value(self, parameter):
        [param1, param2, operant] = self.calculated_parameters[parameter]

        try:
            if operant == '+':
                value = self.read_data(param1) + self.read_data(param2)
            elif operant == '-':
                value = self.read_data(param1) - self.read_data(param2)
            elif operant == '*':
                value = self.read_data(param1) * self.read_data(param2)
            elif operant == '/':
                value = self.read_data(param1) / self.read_data(param2)
            else:
                return False
        except TypeError:
            return False

        return value

    def write_float(self, addr, value):
        floats_list = [value]
        b32_l = [utils.encode_ieee(f) for f in floats_list] 
        b16_l = utils.long_list_to_word(b32_l, big_endian=False)
        return self.modbus.write_multiple_registers(addr-1, b16_l)

    def write_uint16(self, addr, value):
        return self.modbus.write_single_register(addr-1, value)

    def write_uint16_sunssf(self, addrs, value):
        scalereg = self.modbus.read_holding_registers(addrs[1]-1, 1)
        if scalereg[0] > 32768:   # Bad hack for int16 conversion
            scalef = 10**(scalereg[0]-65536)
        else:
            scalef = 10**(scalereg[0])
        value = int(value / scalef)
        return self.modbus.write_single_register(addrs[0]-1, value)

    def write_int16_sunssf(self, addrs, value):
        scalereg = self.modbus.read_holding_registers(addrs[1]-1, 1)
        if scalereg[0] > 32768:   # Bad hack for int16 conversion
            scalef = 10**(scalereg[0]-65536)
        else:
            scalef = 10**(scalereg[0])
        value = int(value / scalef)
        if value >= 0:
            return self.modbus.write_single_register(addrs[0]-1, value)
        else:
            return self.modbus.write_single_register(addrs[0]-1, (0xffff+value) )
   
    def write_data(self, parameter, value):
        [register, datatype, unit_id] = self.registers[parameter]
        
        self.modbus.unit_id = unit_id
        if datatype == "float":
            return self.write_float(register, value)
        elif datatype == "uint16":
            return self.write_uint16(register, value)
        elif datatype == 'uint16_sunssf':
            return self.write_uint16_sunssf(register, value)
        elif datatype == 'int16_sunssf':
            return self.write_int16_sunssf(register, value)
        else:
            return False

    def print_all(self):
        logging.info("Show all registers:")
        for name, params in self.registers.items():
            value = self.read_data(name)
            if value is not None:
                if type(params[0]) is list:
                    logging.info("{0:d}: {1:s} - {2:2.1f}".format(params[0][0], name, value))
                elif type(value) is str:
                    logging.info("{0:d}: {1:s} - {2:s} ".format(params[0], name, value))
                else:
                    logging.info("{0:d}: {1:s} - {2:2.1f}".format(params[0], name, value))
                
    def print_all_calculated(self):
        logging.info("Show all calculated values:")
        for name, params in self.calculated_parameters.items():
            value = self.read_calculated_value(name)
            logging.info("{0:s} - {1:2.1f}".format(name, value))
        
    def get_all_parameters(self):
        return list(self.registers.keys())

    def get_all_calculated(self):
        return list(self.calculated_parameters.keys())
    
    # To search for undocument registers.... 
    def print_raw(self):
        logging.info("Raw read 1000-2000:")
        for i in range(40000,40200,1):
            value = self.read_uint16(i)
            if value:
#                logging.info("{0:d}: {1:2.1f}".format(i, value))
                logging.info("{0:d}: {1:d} (0x{2:x}),".format(i, value,value))
            #else:
            #    logging.info("{0:d}: error".format(i))
        
    # See https://loxwiki.atlassian.net/wiki/spaces/LOXEN/pages/1316061809/Fronius+Hybrid+with+Modbus+TCP
    # Positive = Limit Charge Power (Not more than X*100W Charge, depdend on Sun)
    # Negative = Discharge Battery (X * 100W Discharge, House + Grid)
    def set_battery_charge_rate(self, power):
        if power == None:
            logging.info("Disable Battery Charge Limit")
            reg = self.read_data('Battery_StorCtl_Mod')
            reg = reg & 0xfffe # clear bit 0
            self.write_data('Battery_StorCtl_Mod',reg)
        else:
            logging.info("Setting Charge limit to {0}".format(power))
            reg = self.read_data('Battery_StorCtl_Mod')
            reg = reg | 0x1 # set bit 0
            self.write_data('Battery_StorCtl_Mod',reg)
            self.write_data('Battery_InWRte', power)
            
    # Positive = Limit Discharge Power (Not more than X*100W Discharge, depend on need)
    # Negative = Force Loading of Battery (Charge X*100W into Battery)
    def set_battery_discharge_rate(self, power):
        if power == None:
            logging.info("Disable Battery discharge Limit")
            reg = self.read_data('Battery_StorCtl_Mod')
            reg = reg & 0xfffd # clear bit 0
            self.write_data('Battery_StorCtl_Mod',reg)
        else:
            logging.info("Setting discharge limit to {0}".format(power))
            reg = self.read_data('Battery_StorCtl_Mod')
            reg = reg | 0x2 # set bit 1
            self.write_data('Battery_StorCtl_Mod',reg)
            self.write_data('Battery_OutWRte', power)

    #
    def enable(self, enable=True, auto=False):
        if auto==True:
            if self.read_data("MPPT_1_DC_Voltage") < 70 and self.read_data("MPPT_2_DC_Voltage") < 70:
                logging.info("Low voltage on Gen24, switch off")
                self.write_data("Control_conn",0)

            elif self.read_data("MPPT_1_DC_Voltage") > 120 or self.read_data("MPPT_2_DC_Voltage") > 120:
                logging.info("minimal voltage on Gen24 reached, switch on")
                self.write_data("Control_conn",1)
        else:
            if enable == True:
                self.write_data("Control_conn",1)
            else:
                self.write_data("Control_conn",0)

    # Does not really work?
    def trigger_isolation_measurement(self):
        logging.info("Trigger isolation measurement")
        logging.info(self.read_uint16(40246))
        logging.info(self.read_uint16(40240))
        logging.info(self.read_uint16(40241))
        logging.info(self.read_uint16(40242))
        logging.info(self.read_uint16(40243))
        self.write_uint16(40230,300)
        self.write_uint16(40242,0)
        time.sleep(90)
        self.write_uint16(40242,1)
        logging.info(self.read_uint16(40246))

    
# Test area
if __name__ == "__main__":
    import argparse
    argparser = argparse.ArgumentParser()
    argparser.add_argument("-a", "--address", help="IP address Fronius Symo", 
                           default='192.168.0.123', action='store')

    argparser.add_argument("--debug", help="Enable debug output",
                           action='store_true')    

    argparser.add_argument("--dump", help="Dump all registers",
                           action='store_true')    
        
    argparser.add_argument("-t", "--test", help="Enable Test functions",
                           action='store_true')

    args = argparser.parse_args()
    
    symo = Symo(ipaddr=args.address)
    
    if args.dump:
        symo.print_all()
        symo.print_all_calculated()

    if args.test:
        logging.info("Test results")
        
        # Current AC Output Power
        # logging.info(symo.read_float(40092))
        
        logging.info(symo.read_data("Sunspec_Common_ID"))

    #    logging.info(symo.read_uint32(40286))

    #    symo.set_battery_charge_rate(None)
    #    symo.set_battery_charge_rate(None)
    #    symo.set_battery_discharge_rate(None)
    #    symo.write_uint16(40366,400)
    #    symo.write_uint16(40358,3)

        #symo.trigger_isolation_measurement()

    #    Isolationsmessung triggern ? 
    #    symo.write_uint16(40230,300)
    #    symo.write_uint16(40242,0)
    #    time.sleep(90)
    #    symo.write_uint16(40242,1)

    #    logging.info(symo.read_uint16(40359))
        
        #logging.info(symo.get_all_parameters())

        # logging.info(symo.read_calculated_value('Consumption_Sum'))
                
        # symo.modbus.unit_id = 200
        # symo.print_raw()

        # logging.info(symo.read_uint16(40069))

        # logging.info(symo.modbus.unit_id)
            
        # symo.modbus._unit_id = 200
        # logging.info(symo.modbus.unit_id)

        #logging.info(symo.read_uint16(40100))
        #logging.info(symo.read_uint16(40102))
        #logging.info(symo.read_uint16(40104))
        # logging.info(symo.read_float(40098))
        
        # logging.info(symo.get_mppt_power())
        
        # symo.modbus.unit_id(1)

        symo.enable(1)
