#!/usr/bin/env python3

import unittest
from unittest import mock

from go_e_charger import open_charger
from go_e_charger.go_e_charger_modbus import (
    ENERGY_CHARGE_TO_WH,
    GoeChargerModbus,
    REG_AMPERE_EEPROM,
    REG_AMPERE_VOLATILE,
    REG_FORCE_STATE,
    REG_PHASE_SWITCH_MODE,
)


def put_u32(store, addr, value):
    store[addr] = (int(value) >> 16) & 0xffff
    store[addr + 1] = int(value) & 0xffff


class FakeModbus:
    def __init__(self):
        self.inputs = {}
        self.holdings = {}
        self.writes = []
        self.fail_reads = False

    def open(self):
        return True

    def close(self):
        return None

    def read_input_registers(self, addr, count):
        if self.fail_reads:
            return None
        return [self.inputs.get(addr + i, 0) for i in range(count)]

    def read_holding_registers(self, addr, count):
        if self.fail_reads:
            return None
        return [self.holdings.get(addr + i, 0) for i in range(count)]

    def write_multiple_registers(self, addr, values):
        for offset, value in enumerate(values):
            self.holdings[addr + offset] = value
        self.writes.append((addr, list(values)))
        return True


def loaded_charger(storage='volatile'):
    fake = FakeModbus()
    # Gemini firmware 59.4, car finished and still connected, 3.6 kW example.
    fake.inputs[100] = 4
    put_u32(fake.inputs, 108, 230)
    put_u32(fake.inputs, 110, 228)
    put_u32(fake.inputs, 112, 229)
    put_u32(fake.inputs, 114, 123)  # 12.3 A
    put_u32(fake.inputs, 116, 0)
    put_u32(fake.inputs, 118, 0)
    put_u32(fake.inputs, 120, 360000)  # 3.6 kW in the v2 map
    put_u32(fake.inputs, 128, 78161)  # 7816.1 kWh
    put_u32(fake.inputs, 132, 2715668)  # 7543.522 Wh
    put_u32(fake.inputs, 144, 2)
    put_u32(fake.inputs, 146, 36)  # 3.6 kW at 0.1 kW per count
    fake.holdings[REG_AMPERE_VOLATILE] = 24
    fake.holdings[REG_AMPERE_EEPROM] = 10
    fake.holdings[REG_PHASE_SWITCH_MODE] = 0
    fake.holdings[REG_FORCE_STATE] = 0
    charger = GoeChargerModbus('127.0.0.1', ampere_storage=storage, client=fake)
    return charger, fake


class ModbusTransportTest(unittest.TestCase):

    def test_scales_match_the_v2_map_and_the_http_names(self):
        charger, _fake = loaded_charger()
        status = charger.GetStatusAll()

        self.assertEqual(status['car_status'], 'charging finished, vehicle still connected')
        self.assertEqual(status['cable_unlock_status'], 3)
        self.assertTrue(charger.CableLocked())
        self.assertEqual(status['u_l1'], 230.0)
        self.assertEqual(status['i_l1'], 12.3)
        self.assertEqual(status['p_all'], 3600.0)
        self.assertEqual(status['p_l1'], 3600.0)
        self.assertEqual(status['energy_total'], 7816.1)
        self.assertAlmostEqual(
            status['energy_since_connect'], 2715668 * ENERGY_CHARGE_TO_WH)
        self.assertEqual(status['charger_max_current'], 24)
        self.assertEqual(charger.P_All, 3600.0)
        self.assertEqual(charger.ForceOn, -1)

    def test_no_vehicle_is_not_a_locked_cable(self):
        charger, fake = loaded_charger()
        fake.inputs[100] = 1
        self.assertFalse(charger.CableLocked())
        self.assertEqual(charger.GetStatusParam('cable_unlock_status'), 1)
        self.assertEqual(
            charger.GetStatusParam('car_status'), 'Charger ready, no vehicle')

    def test_volatile_write_uses_function_16_on_register_299(self):
        charger, fake = loaded_charger('volatile')
        self.assertTrue(charger.SetStatusParam('charger_max_current', 8))
        self.assertEqual(fake.writes, [(REG_AMPERE_VOLATILE, [8])])
        self.assertEqual(charger.ChargerMaxCurrent, 8)
        self.assertEqual(fake.holdings[REG_AMPERE_EEPROM], 10)

    def test_eeprom_storage_writes_register_300(self):
        charger, fake = loaded_charger('eeprom')
        charger.ChargerMaxCurrent = 12
        self.assertEqual(fake.writes[-1], (REG_AMPERE_EEPROM, [12]))

    def test_force_and_phase_follow_the_http_mapping(self):
        charger, fake = loaded_charger()
        charger.ForceOn = 1
        self.assertEqual(fake.writes[-1], (REG_FORCE_STATE, [2]))
        charger.ForceOn = 1
        self.assertEqual(len(fake.writes), 1)

        charger.SetPhaseMode = 3
        self.assertEqual(fake.writes[-1], (REG_PHASE_SWITCH_MODE, [2]))
        self.assertEqual(charger.SetPhaseMode, 3)
        charger.SetPhaseMode = 1
        self.assertEqual(fake.writes[-1], (REG_PHASE_SWITCH_MODE, [1]))

    def test_set_charging_power_uses_the_two_phase_car_rules(self):
        charger, fake = loaded_charger()
        with mock.patch('go_e_charger.common.time.sleep'):
            charger.setChargingP(4000)
        self.assertEqual(
            fake.writes, [(REG_PHASE_SWITCH_MODE, [2]), (REG_AMPERE_VOLATILE, [8])])

        fake.writes.clear()
        with mock.patch('go_e_charger.common.time.sleep'):
            charger.setChargingP(2000)
        self.assertEqual(
            fake.writes, [(REG_PHASE_SWITCH_MODE, [1]), (REG_AMPERE_VOLATILE, [8])])

    def test_failed_read_returns_an_empty_status(self):
        charger, fake = loaded_charger()
        fake.fail_reads = True
        self.assertEqual(charger.GetStatusAll(), {})
        self.assertIsNone(charger.GetStatusParam('energy_array'))

    def test_factory_selects_the_transport(self):
        http = open_charger('127.0.0.1', protocol='http')
        modbus = open_charger('127.0.0.1', protocol='modbus')
        self.assertEqual(type(http).__name__, 'GoeCharger')
        self.assertEqual(type(modbus).__name__, 'GoeChargerModbus')
        self.assertEqual(modbus._ampere_register, REG_AMPERE_VOLATILE)
        with self.assertRaises(ValueError):
            open_charger('127.0.0.1', protocol='mqtt')

    def test_http_class_still_exposes_the_shared_api(self):
        from go_e_charger.go_e_charger_httpv2 import GoeCharger
        self.assertTrue(callable(GoeCharger.setChargingP))
        self.assertTrue(callable(GoeCharger.CableLocked))


if __name__ == '__main__':
    unittest.main()
