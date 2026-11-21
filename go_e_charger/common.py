#!/usr/bin/env python3

# High-level go-e operations shared by the HTTP and Modbus transports.
# The e-Golf only accepts coarse ampere steps and is treated as a 1-phase
# or 2-phase car. Both transports must keep this behaviour.

import time


class GoeChargerApi:

    def CableLocked(self):
        if int(self.GetStatusParam('cable_unlock_status')) == 3:
            return True
        else:
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
            return self.SetStatusParam('force_state', value + 1)

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
        return values['p_all']

    def setChargingP(self, power):
        if power <= 5 * 230:
            power = 5 * 230
        elif power >= 16 * 3 * 230:
            power = 16 * 3 * 230

        max_1p = 230 * 16 * 1
        car_phases = 2
        min_3p = 230 * 5 * car_phases

        if (power < min_3p):
            self.SetPhaseMode = 1
        elif (power > max_1p):
            self.SetPhaseMode = 3

        if self.SetPhaseMode == 3:
            power = power / car_phases

        amps = int(power / 230)
        if amps > 16:
            amps = 16
        self.ChargerMaxCurrent = amps
        time.sleep(10)
