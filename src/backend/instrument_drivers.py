import os
import pyvisa
from pathlib import Path

from dotenv import load_dotenv

PROJECT_DIR = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_DIR / ".env")
import random

NUM_PSU = int(os.environ["NUM_PSU"])

_resource_manager: pyvisa.ResourceManager | None = None
_psu_connection: list[Any | None] = [None] * NUM_PSU


"""_sim_power = [False] * NUM_PSU
_sim_v_set = [12.0, 5.0, 24.0, 15.0, 9.0, 3.3]
_sim_a_set = [5.0, 3.2, 7.5, 4.8, 6.1, 2.9]"""

def connect_psus() -> list:
    """Connect to all configured PSUs."""

    global _resource_manager

    _resource_manager = pyvisa.ResourceManager()

    for idx in range(NUM_PSU):
        psu_number = idx + 1
        ip_address = os.getenv(f"PSU_{psu_number}_IP_ADDRESS")

        if not ip_address:
            print(f"PSU {psu_number}: IP adress is not configured")
            _psu_connection[idx] = None
            continue

        resource_address = f"TCPIP0::{ip_address}::INSTR"

        try:
            instrument = _resource_manager.open_resource(resource_address)
            instrument.timeout = 3000
            instrument.read_termination = "\n"
            instrument.write_termination = "\n"

            identity = instrument.query("*IDN?").strip()
            _psu_connections[idx] = instrument

            print(f"PSU {psu_number} connected at"
                  f"{ip_address}:{identity}")

        except pyvisa.Error as exc:
            _psu_connection[idx] = None
            print(f"PSU {psu_number} connection failed at"
                  f"{ip_address}: {exc}")

        return _psu_connections

def psu_read(idx: int) -> dict:
    """TODO: Replace with Ethernet/SCPI query.  Returns readback values."""
    online = random.random() > 0.04
    on = _sim_power[idx] and online

    voltage = test_instrument.query('MEASure:VOLTage?')
    current = test_instrument.query('MEASure:CURRent?')

    return {
        "online": online,
        "power_on": on,
        "voltage_v": round(voltage[idx] + random.uniform(-0.04, 0.04), 3)
        if on
        else 0.0,
        "current_a": round(current[idx] + random.uniform(-0.10, 0.10), 3)
        if on
        else 0.0,
        "fault": random.random() > 0.98,
    }

"""
def psu_set_output(idx: int, voltage: float, current: float):
    """TODO: Send SCPI  VOLT {voltage}; CURR {current}  to PSU at idx."""
    _sim_v_set[idx] = voltage
    _sim_a_set[idx] = current


def psu_set_power(idx: int, on: bool):
    """TODO: Send SCPI  OUTPUT ON/OFF  to PSU at idx."""
    _sim_power[idx] = on
"""

def thermocouple_read() -> dict:
    """TODO: Replace with serial read from MCU."""
    return {
        "temp_c": round(125.0 + random.uniform(-2.5, 2.5), 1),
        "online": random.random() > 0.02,
    }
