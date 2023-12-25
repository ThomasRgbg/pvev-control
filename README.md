# pvev-control
Control of Fronius Gen24, Go-E Charger and some stuff in the middle

Drivers
-------

* pv_fronius/fronius_symo.py - ModbusTCP based control/readout of Fronius Symo and Symo-Gen24 inverters. Beside of a lot of data readback, there is also a bit of comfort functions implemented, like suspend based on PV Voltage or direct control of the charge/discharge of the attached battery. And a bit of calculation of data which can be not directly read back.

* go_e_charger/go_e_charger_httpv2.py - (Local) http API based access to a Go-E Wallbox. Beside of the usual stuff a bit of more comfortable control of the charging power (currently a bit hardcoded for 1/2 phase operation and would need some rework for 1/3 phases... however there is not really a good way to detect if a car supports only 2 like my eGolf or 3 phases)

* influxdb_cli2/influxdb_cli2.py - just some boring Influx DB access for reading and writing data


Applications
------------

* fronius_influxdb.py - Just some periodic readback of registers and write into the influxdb, supporting multiple inverters.

* go_e_charger_control.py - First rule of control theory: Afterwards you always know more... so this is a highly complex, confusing and heavily developed statemachine to tame the charging of a eGolf on a Go-E charger based on the available power coming down from the PV syste with some additional consideration of the house-battery state, electricity price and a lot of quirks of the car (like you can not switch on/off to often in short time, only limited steps of charging amps etc). I make it more for general entertainment available here. If somebody ever uses this, please send me a message. 

* simple_batterycontrol.py - Control of the house-battery attached to a Symo Gen24, based on electricity price (Tibber) and some beginnging tries of enlonging the battery lifetme by reducing charging/discharging cases.
