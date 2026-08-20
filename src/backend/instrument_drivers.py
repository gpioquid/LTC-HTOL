import os
from pathlib import Path
from typing import Any

import pyvisa
from dotenv import load_dotenv

PROJECT_DIR = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_DIR / ".env")
import random

NUM_PSU = int(os.environ["NUM_PSU"])

_resource_manager: pyvisa.ResourceManager | None = None
_psu_connection: list[Any | None] = [None] * NUM_PSU



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
            _psu_connection[idx] = instrument

            print(f"PSU {psu_number} connected at"
                  f" {ip_address} : {identity}")

        except pyvisa.Error as exc:
            _psu_connection[idx] = None
            print(f"PSU {psu_number} connection failed at"
                  f"{ip_address}: {exc}")

        return _psu_connection


def disconnect_psus() -> None:
    """Close all PSU connections and the VISA resource manager"""

    global _resource_manager

    for idx, instrument in enumerate(_psu_connection):
        if instrument is None:
            continue

        try:
            #for safety behavior

            instrument.close()
            print(f"PSU {idx +1} disconnected")

        except pyvisa.Error as exc:
            print(f" PSU {idx +1} disconnect error: {exc}")

        finally:
            _psu_connection[idx] = None

    if _resource_manager is not None:
        try:
            _resource_manager.close()
            print("VISA resource manager closed")

        except pyvisa.Error as exc:
            print(f"VISA reousce manager close error: {exc}")

        finally:
            _resource_manager = None
                                                


def psu_read(idx: int) -> dict:

    instrument = _psu_connection[idx]

    if instrument is None:
        return{
            "online": False,
            "power_on": False,
            "voltage_v": 0.0,
            "current_a": 0.0,
            "fault": False,
        }

    try:
        voltage = float(instrument.query('MEASure:VOLTage?').strip())
        current = float(instrument.query('MEASure:CURRent?').strip())

        output_reponse = instrument.query("OUTPut?").strip().upper()
        power_on = output_reponse in {"1", "ON"}

        return {
            "online": True,
            "power_on": power_on,
            "voltage_v": round(voltage, 3),
            "current_a": round(current, 3),
            "fault": False,
        }
    except (pyvisa.Error, ValueError) as exc:
        print(f"PSU {idx +1} read failed: {exc}")

        return{
            "online": False,
            "power_on": False,
            "voltage_v": 0.0,
            "current_a": 0.0,
            "fault": False,
        }

def psu_set_output(idx: int, voltage: float, current: float) -> dict:
    """Set the voltage and current setpoints for one PSU"""

    if not 0 <= idx < NUM_PSU:
        raise IndexError(f"Invalid PSU Index: {idx}")

    instrument = _psu_connection[idx]

    if instrument is None:
        raise RuntimeError(f"PSU {idx+1} is not connected")

    if voltage < 0:
        raise ValueError("Voltage cannot be negative")

    if current <0:
        raise ValueError("Current cannot be negative")

    try:
        instrument.write("*CLS")

        instrument.write("SOURce:VOLTage {voltage:.3f}")
        instrument.write("SOURce:CURRent {current:.3f}")

        instrument.query("*OPC?")
        
        programmed_voltage = float(instrument.query("SOURce:VOLTage?"))
        programmed_current = float(instrument.query("SOURce:CURRent?"))

        print(
            f"PSI {idx +1} setpoints applied:"
            f"{programmed_voltage:.3f} V "
            f"{programmed_current:.3f} A"
        )

        return{
            "succes": True,
            "voltage": programmed_voltage,
            "current": programmed_current,
        }

    except (pyvisa.Error, ValueError) as exc:
        raise RuntimeError(
            f"Unable to set PSU {idx+1} output: {exc}"
        ) from exc



def psu_set_power(idx: int, on: bool) -> bool:
    """Enable or disable the output of the selected PSU."""

    if not 0 <= idx < NUM_PSU:
        raise IndexError(f"Invalid PSU index: {idx}")

    instrument = _psu_connection[idx]

    if instrument is None:
        raise RuntimeError(f"PSU {idx +1 } is not connected")

    try:
        instrument.write("*CLS")
        instrument.write("OUTP ON" if on else "OUTP OFF")
        instrument.query("*OPC?")

        response = instrument.query("OUTP?").strip().upper()
        actual_state = response in {"1", "ON"}

        if actual_state != on:
            requested = "ON" if on else "OFF"
            actual = "ON" if actual_state else "OFF"

            raise RuntimeError(
                f"PSU {idx +1} output verification failed. "
                f"Requested {requested}, but read back {actual}."
            )

        print(
            f"PSU {idx +1} output"
            f"{'enabled' if actual_state else 'disabled'}"
        )

        return actual_state

    except pyvisa.Error as exc:
        raise RuntimeError(
            f"Unable to control PSU {idx+1} output: {exc}"
        )

    


def thermocouple_read() -> dict:
    """TODO: Replace with serial read from MCU."""
    return {
        "temp_c": round(125.0 + random.uniform(-2.5, 2.5), 1),
        "online": random.random() > 0.02,
    }
