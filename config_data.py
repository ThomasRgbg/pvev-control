
#
# Device Database and registry
#

# Need to be adapted to your local devices.
# And these values here are just default values, not my ones... ;)

mqtt_ip = "192.168.0.100"
mqtt_port = 1883

influxdb_url = 'http://192.168.0.100:8086'
influxdb_token = "mytokenblalala=="
influxdb_org = 'home'
influxdb_bucket = 'home/autogen'

influxdb_price_location = 'grid_tibber'
influxdb_price_measurement = 'price_total'

symo_ip = ["192.168.0.10", "192.168.0.11"]
symo_table = ["pv_first", "pv_second"]

go_e_charger_ip = "192.168.0.12"
go_e_table = "ev_car"
