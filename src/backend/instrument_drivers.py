import os
import random
import threading
from pathlib import Path
from typing import Any

import pyvisa
from dotenv import load_dotenv

PROJECT_DIR = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_DIR / ".env")

NUM_PSU = int(os.environ["NUM_PSU"])
PSU_TIMEOUT_MS = int(os.getenv("PSU_TIMEOUT_MS", "10000"))

_resource_manager: pyvisa.ResourceManager | None = None

# One VISA connection per PSU.
_psu_connections: list[Any | None] = [None] * NUM_PSU

# Prevent simultaneous polling and control commands on the same PSU.
_psu_locks = [
    threading.RLock()
    for _ in range(NUM_PSU)
]


def connect_psus() -> list:
    """Connect to all configured PSUs."""

    global _resource_manager

    _resource_manager = pyvisa.ResourceManager()

    for idx in range(NUM_PSU):
        psu_number = idx + 1
        ip_address = os.getenv(f"PSU_{psu_number}_IP_ADDRESS")

        if not ip_address:
            print(f"PSU {psu_number}: IP adress is not configured")
            _psu_connections[idx] = None
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
                  f" {ip_address} : {identity}")

        except pyvisa.Error as exc:
            _psu_connections[idx] = None
            print(f"PSU {psu_number} connection failed at"
                  f"{ip_address}: {exc}")

        return _psu_connections


def disconnect_psus() -> None:
    """Close all PSU connections and the VISA resource manager"""

    global _resource_manager

    for idx, instrument in enumerate(_psu_connections):
        if instrument is None:
            continue

        try:
            #for safety behavior

            instrument.close()
            print(f"PSU {idx +1} disconnected")

        except pyvisa.Error as exc:
            print(f" PSU {idx +1} disconnect error: {exc}")

        finally:
            _psu_connections[idx] = None

    if _resource_manager is not None:
        try:
            _resource_manager.close()
            print("VISA resource manager closed")

        except pyvisa.Error as exc:
            print(f"VISA reousce manager close error: {exc}")

        finally:
            _resource_manager = None
                                                


def psu_read(idx: int) -> dict:
    """Read actual PSU measurements and output state."""

    if not 0 <= idx < NUM_PSU:
        raise IndexError(f"Invalid PSU index: {idx}")

    instrument = _psu_connections[idx]

    if instrument is None:
        return {
            "online": False,
            "power_on": False,
            "voltage_v": 0.0,
            "current_a": 0.0,
            "fault": False,
        }

    psu_lock = _psu_locks[idx]

    try:
        with psu_lock:
            voltage_response = instrument.query(
                "MEASure:VOLTage?"
            ).strip()

            current_response = instrument.query(
                "MEASure:CURRent?"
            ).strip()

            output_response = instrument.query(
                "OUTPut:STATe?"
            ).strip().upper()

        return {
            "online": True,
            "power_on": output_response in {"1", "ON"},
            "voltage_v": round(
                float(voltage_response),
                3,
            ),
            "current_a": round(
                float(current_response),
                3,
            ),
            "fault": False,
        }

    except (pyvisa.Error, ValueError) as error:
        print(
            f"PSU {idx + 1} read failed: {error}"
        )

        return {
            "online": False,
            "power_on": False,
            "voltage_v": 0.0,
            "current_a": 0.0,
            "fault": True,
        }



def psu_set_output(
    idx: int,
    voltage: float,
    current: float,
) -> dict:
    """Apply calibration voltage and current to one PSU."""

    if not 0 <= idx < NUM_PSU:
        raise IndexError(f"Invalid PSU index: {idx}")

    if voltage < 0:
        raise ValueError("Voltage cannot be negative")

    if current < 0:
        raise ValueError("Current cannot be negative")

    instrument = _psu_connections[idx]

    if instrument is None:
        raise RuntimeError(
            f"PSU {idx + 1} is not connected"
        )

    psu_lock = _psu_locks[idx]

    try:
        with psu_lock:
            print(
                f"PSU {idx + 1}: setting current "
                f"to {current:.3f} A"
            )
            instrument.write(
                f"SOURce:CURRent {current:.6f}"
            )

            print(
                f"PSU {idx + 1}: setting voltage "
                f"to {voltage:.3f} V"
            )
            instrument.write(
                f"SOURce:VOLTage {voltage:.6f}"
            )

        print(
            f"PSU {idx + 1}: calibration values sent "
            f"successfully"
        )

        return {
            "success": True,
            "voltage": voltage,
            "current": current,
        }

    except pyvisa.errors.VisaIOError as error:
        raise RuntimeError(
            f"Unable to apply calibration values to "
            f"PSU {idx + 1}: {error}"
        ) from error



def psu_set_power(idx: int, on: bool) -> bool:
    """Send the output ON or OFF command to one PSU."""

    if not 0 <= idx < NUM_PSU:
        raise IndexError(f"Invalid PSU index: {idx}")

    instrument = _psu_connections[idx]

    if instrument is None:
        raise RuntimeError(
            f"PSU {idx + 1} is not connected"
        )

    requested_state = 1 if on else 0
    psu_lock = _psu_locks[idx]

    try:
        with psu_lock:
            instrument.write(
                f"OUTPut:STATe {requested_state}"
            )

        print(
            f"PSU {idx + 1}: output command sent: "
            f"{'ON' if on else 'OFF'}"
        )

        return on

    except pyvisa.errors.VisaIOError as error:
        raise RuntimeError(
            f"Unable to control PSU {idx + 1} output: "
            f"{error}"
        ) from error
    


def thermocouple_read() -> dict:
    """TODO: Replace with serial read from MCU."""
    return {
        "temp_c": round(125.0 + random.uniform(-2.5, 2.5), 1),
        "online": random.random() > 0.02,
    }
