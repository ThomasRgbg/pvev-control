"""go-e Charger transports. The control script picks one with protocol=."""


def open_charger(ipaddr, protocol='http', port=502, unit_id=1,
                 ampere_storage='volatile', debug=False):
    """Return a charger object for the HTTP API or for Modbus TCP.

    Both objects implement the same read and write methods. protocol=http
    is the historical default.
    """
    name = str(protocol).strip().lower().replace('_', '-')
    if name in ('http', 'http-api', 'api'):
        from go_e_charger.go_e_charger_httpv2 import GoeCharger
        return GoeCharger(ipaddr=ipaddr, debug=debug)
    if name in ('modbus', 'modbus-tcp'):
        from go_e_charger.go_e_charger_modbus import GoeChargerModbus
        return GoeChargerModbus(
            ipaddr,
            port=port,
            unit_id=unit_id,
            ampere_storage=ampere_storage,
            debug=debug,
        )
    raise ValueError(
        "go-e protocol must be 'http' or 'modbus', got {0!r}".format(protocol))
