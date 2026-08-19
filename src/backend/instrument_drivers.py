import os
from pathlib import Path

from dotenv import load_dotenv

PROJECT_DIR = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_DIR / ".env")
import random

NUM_PSU = int(os.environ["NUM_PSU"])

_sim_power = [False] * NUM_PSU
_sim_v_set = [12.0, 5.0, 24.0, 15.0, 9.0, 3.3]
_sim_a_set = [5.0, 3.2, 7.5, 4.8, 6.1, 2.9]


def psu_read(idx: int) -> dict:
    """TODO: Replace with Ethernet/SCPI query.  Returns readback values."""
    online = random.random() > 0.04
    on = _sim_power[idx] and online
    return {
        "online": online,
        "power_on": on,
        "voltage_v": round(_sim_v_set[idx] + random.uniform(-0.04, 0.04), 3)
        if on
        else 0.0,
        "current_a": round(_sim_a_set[idx] + random.uniform(-0.10, 0.10), 3)
        if on
        else 0.0,
        "fault": random.random() > 0.98,
    }


def psu_set_output(idx: int, voltage: float, current: float):
    """TODO: Send SCPI  VOLT {voltage}; CURR {current}  to PSU at idx."""
    _sim_v_set[idx] = voltage
    _sim_a_set[idx] = current


def psu_set_power(idx: int, on: bool):
    """TODO: Send SCPI  OUTPUT ON/OFF  to PSU at idx."""
    _sim_power[idx] = on


def thermocouple_read() -> dict:
    """TODO: Replace with serial read from MCU."""
    return {
        "temp_c": round(125.0 + random.uniform(-2.5, 2.5), 1),
        "online": random.random() > 0.02,
    }
