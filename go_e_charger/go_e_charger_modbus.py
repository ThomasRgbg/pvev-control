#!/usr/bin/env python3

# Modbus TCP transport for a go-e Charger (HOME / Gemini, API v2).
#
# Register map:
# https://github.com/goecharger/go-eCharger-API-v2/blob/main/modbus-en.md
#
# The charger must have the Modbus slave enabled (app, or HTTP key men=true).
# It listens on port 502, unit id 1, and only accepts write function 16.
# Leave the charger byte/register swap (msb, msr) at the factory default.
#
# Ampere writes go to AMPERE_VOLATILE unless ampere_storage=eeprom. That
# register is the one go-e documents for energy control: it is not stored in
# EEPROM (about 100,000 write cycles) and is restored from EEPROM at boot.

import logging

from pyModbusTCP.client import ModbusClient
from pyModbusTCP import utils

try:
    from go_e_charger.common import GoeChargerApi
except ImportError:
    from common import GoeChargerApi


logger = logging.getLogger('go_e_charger.modbus')

# Addresses are the 0-based register numbers from the go-e map.
# pyModbusTCP uses the same numbering. Do not add 1.
REG_CAR_STATE = 100
REG_VOLT_L1 = 108
REG_AMP_L1 = 114
REG_POWER_TOTAL = 120
REG_ENERGY_TOTAL = 128
REG_ENERGY_CHARGE = 132
REG_VOLT_N = 144
REG_POWER_L1 = 146
REG_POWER_FACTOR_L1 = 152
REG_PHASES = 205
REG_AMPERE_VOLATILE = 299
REG_AMPERE_EEPROM = 300
REG_PHASE_SWITCH_MODE = 332
REG_FORCE_STATE = 337

# Input-register scales from the v2 map. Checked on a Gemini, firmware 59.4,
# against the HTTP API: volts, 0.1 A, lifetime energy in 0.1 kWh, and session
# energy in deka-watt-seconds. Total power follows the v2 example
# (360000 -> 3.6 kW). A charging session was not running, so that factor was
# not compared with a live load.
POWER_TOTAL_TO_W = 0.01
PHASE_POWER_TO_W = 100.0
CURRENT_TO_A = 0.1
ENERGY_TOTAL_TO_KWH = 0.1
# deka-watt-seconds to Wh: raw * 10 Ws / 3600
ENERGY_CHARGE_TO_WH = 10.0 / 3600.0

CAR_STATUS = {
    1: 'Charger ready, no vehicle',
    2: 'charging',
    3: 'Waiting for vehicle',
    4: 'charging finished, vehicle still connected',
}

# Vehicle present. There is no Modbus register for HTTP key cus.
CONNECTED_CAR_STATES = (2, 3, 4)


def _u32(words):
    return int(utils.word_list_to_long(list(words), big_endian=True)[0])


class GoeChargerModbus(GoeChargerApi):

    def __init__(self, ipaddr, port=502, unit_id=1, ampere_storage='volatile',
                 timeout=5.0, debug=False, client=None):
        self.ipaddr = ipaddr
        self.debug = debug
        storage = str(ampere_storage).strip().lower()
        if storage in ('volatile', 'amx', 'ram'):
            self._ampere_register = REG_AMPERE_VOLATILE
        elif storage in ('eeprom', 'amp'):
            self._ampere_register = REG_AMPERE_EEPROM
        else:
            raise ValueError(
                "ampere_storage must be 'volatile' or 'eeprom', got {0!r}".format(
                    ampere_storage))
        self.ampere_storage = storage

        if client is not None:
            self.modbus = client
        else:
            self.modbus = ModbusClient(
                host=ipaddr,
                port=int(port),
                unit_id=int(unit_id),
                timeout=float(timeout),
                auto_open=True,
                auto_close=False,
            )

    def _drop(self):
        try:
            self.modbus.close()
        except Exception:
            logger.warning("closing Modbus connection to %s failed", self.ipaddr)

    def _read(self, kind, addr, count):
        if kind == 'input':
            regs = self.modbus.read_input_registers(addr, count)
        else:
            regs = self.modbus.read_holding_registers(addr, count)
        if not regs or len(regs) < count:
            logger.warning(
                "Modbus read failed (%s %s x %s) from %s: %s",
                kind, addr, count, self.ipaddr, getattr(self.modbus, 'last_error_as_txt', ''))
            self._drop()
            return None
        return regs

    def _write_u16(self, addr, value):
        # Function 6 is not implemented. A single register still uses function 16.
        value = int(value)
        if value < 0 or value > 0xffff:
            logger.warning("refuse Modbus write of %s to register %s", value, addr)
            return None
        ok = self.modbus.write_multiple_registers(addr, [value])
        if not ok:
            logger.warning(
                "Modbus write failed (register %s) to %s: %s",
                addr, self.ipaddr, getattr(self.modbus, 'last_error_as_txt', ''))
            self._drop()
            return None
        return True

    def _read_status(self):
        # Stop on the first failed block. A dead socket would otherwise burn
        # one timeout per register group.
        car = self._read('input', REG_CAR_STATE, 1)
        if not car:
            return {}
        electrical = self._read('input', REG_VOLT_L1, 14)
        if not electrical:
            return {}
        energy = self._read('input', REG_ENERGY_TOTAL, 6)
        if not energy:
            return {}
        neutral = self._read('input', REG_VOLT_N, 16)
        if not neutral:
            return {}
        amps = self._read('holding', self._ampere_register, 1)
        if not amps:
            return {}
        phase = self._read('holding', REG_PHASE_SWITCH_MODE, 1)
        if not phase:
            return {}
        force = self._read('holding', REG_FORCE_STATE, 1)
        if not force:
            return {}

        car_state = int(car[0])
        # cus == 3 is what CableLocked() treats as locked. Modbus has no cus
        # register; a connected vehicle is locked with the default cable mode.
        if car_state in CONNECTED_CAR_STATES:
            cable_unlock_status = 3
        else:
            cable_unlock_status = 1

        status = {
            'car_state': car_state,
            'car_status': CAR_STATUS.get(car_state, 'unknown ({0})'.format(car_state)),
            'cable_unlock_status': cable_unlock_status,
            'charger_max_current': int(amps[0]),
            'phase_switch_mode': int(phase[0]),
            'force_state': int(force[0]),
            'u_l1': float(_u32(electrical[0:2])),
            'u_l2': float(_u32(electrical[2:4])),
            'u_l3': float(_u32(electrical[4:6])),
            'i_l1': _u32(electrical[6:8]) * CURRENT_TO_A,
            'i_l2': _u32(electrical[8:10]) * CURRENT_TO_A,
            'i_l3': _u32(electrical[10:12]) * CURRENT_TO_A,
            'p_all': _u32(electrical[12:14]) * POWER_TOTAL_TO_W,
            'energy_total': _u32(energy[0:2]) * ENERGY_TOTAL_TO_KWH,
            'energy_since_connect': _u32(energy[4:6]) * ENERGY_CHARGE_TO_WH,
            'u_n': float(_u32(neutral[0:2])),
            'p_l1': _u32(neutral[2:4]) * PHASE_POWER_TO_W,
            'p_l2': _u32(neutral[4:6]) * PHASE_POWER_TO_W,
            'p_l3': _u32(neutral[6:8]) * PHASE_POWER_TO_W,
            'pf_l1': float(_u32(neutral[8:10])),
            'pf_l2': float(_u32(neutral[10:12])),
            'pf_l3': float(_u32(neutral[12:14])),
            'pf_n': float(_u32(neutral[14:16])),
        }
        return status

    def GetStatusAll(self, filtered=False):
        response = self._read_status()
        if filtered:
            for key, value in list(response.items()):
                if value is None:
                    del response[key]
        return response

    def GetStatusNums(self, filtered=False):
        response = {}
        for key, value in self._read_status().items():
            if isinstance(value, str):
                continue
            if isinstance(value, (list, dict)):
                continue
            if filtered and value is None:
                continue
            response[key] = value
        return response

    def GetStatusParam(self, statusparam):
        status = self._read_status()
        if not status:
            return None
        if statusparam == 'energy_array':
            keys = (
                'u_l1', 'u_l2', 'u_l3', 'u_n',
                'i_l1', 'i_l2', 'i_l3',
                'p_l1', 'p_l2', 'p_l3', 'p_all',
                'pf_l1', 'pf_l2', 'pf_l3', 'pf_n',
            )
            return dict((key, status[key]) for key in keys)
        return status.get(statusparam)

    def SetStatusParam(self, statusparam, value):
        if statusparam == 'charger_max_current':
            return self._write_u16(self._ampere_register, value)
        if statusparam == 'phase_switch_mode':
            return self._write_u16(REG_PHASE_SWITCH_MODE, value)
        if statusparam == 'force_state':
            return self._write_u16(REG_FORCE_STATE, value)
        logger.warning("Modbus transport cannot write %s", statusparam)
        return None


if __name__ == "__main__":
    import argparse
    import time

    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s')

    argparser = argparse.ArgumentParser()
    argparser.add_argument("-a", "--address", default='192.168.0.12')
    argparser.add_argument("--port", type=int, default=502)
    argparser.add_argument("--unit-id", type=int, default=1)
    argparser.add_argument(
        "--ampere-storage", choices=('volatile', 'eeprom'), default='volatile')
    argparser.add_argument("-p", "--set-charging-p", action='store')
    argparser.add_argument("-e", "--enable-charging", action='store')
    argparser.add_argument("-w", "--wait", action='store_true')
    args = argparser.parse_args()

    charger = GoeChargerModbus(
        args.address,
        port=args.port,
        unit_id=args.unit_id,
        ampere_storage=args.ampere_storage,
    )

    if args.set_charging_p:
        charger.setChargingP(int(args.set_charging_p))

    if args.enable_charging:
        charger.ForceOn = int(args.enable_charging)

    if args.wait or not (args.set_charging_p or args.enable_charging):
        while True:
            print(charger.GetStatusAll())
            print(charger.ChargerMaxCurrent, charger.P_All, charger.CableLocked())
            if not args.wait:
                break
            time.sleep(10)
