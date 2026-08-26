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
_psu_locks = [threading.RLock() for _ in range(NUM_PSU)]

_psu_driver_closing = False

def connect_psus() -> list:
    """Connect to all configured PSUs."""

    global _resource_manager
    global _psu_driver_closing

    _psu_driver_closing = False

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

            print(f"PSU {psu_number} connected at {ip_address} : {identity}")

        except pyvisa.Error as exc:
            _psu_connections[idx] = None
            print(f"PSU {psu_number} connection failed at{ip_address}: {exc}")

        return _psu_connections


def disconnect_psus() -> None:
    global _resource_manager
    global _psu_driver_closing

    # Prevent new reads before closing any sessions.
    _psu_driver_closing = True

    for idx in range(NUM_PSU):
        psu_lock = _psu_locks[idx]

        with psu_lock:
            instrument = _psu_connections[idx]

            if instrument is None:
                continue

            try:
                instrument.close()

                print(
                    f"PSU {idx + 1} disconnected"
                )

            except pyvisa.Error as error:
                print(
                    f"PSU {idx + 1} disconnect "
                    f"error: {error}"
                )

            finally:
                _psu_connections[idx] = None

    if _resource_manager is not None:
        try:
            _resource_manager.close()

            print(
                "VISA resource manager closed"
            )

        except pyvisa.Error as error:
            print(
                "VISA resource manager close "
                f"error: {error}"
            )

        finally:
            _resource_manager = None

def psu_read(idx: int) -> dict:
    if _psu_driver_closing:
        return {
            "online": False,
            "power_on": False,
            "voltage_v": 0.0,
            "current_a": 0.0,
        }

    if not 0 <= idx < NUM_PSU:
        raise IndexError(
            f"Invalid PSU index: {idx}"
        )

    instrument = _psu_connections[idx]

    if instrument is None:
        return {
            "online": False,
            "power_on": False,
            "voltage_v": 0.0,
            "current_a": 0.0,
        }

    psu_lock = _psu_locks[idx]

    try:
        with psu_lock:
            if _psu_driver_closing:
                return {
                    "online": False,
                    "power_on": False,
                    "voltage_v": 0.0,
                    "current_a": 0.0,
                }

            voltage = float(
                instrument.query(
                    "MEASure:VOLTage?"
                ).strip()
            )

            current = float(
                instrument.query(
                    "MEASure:CURRent?"
                ).strip()
            )

        return {
            "online": True,
            "power_on": voltage > 0.01,
            "voltage_v": round(voltage, 3),
            "current_a": round(current, 3),
        }

    except (pyvisa.Error, ValueError) as error:
        if not _psu_driver_closing:
            print(
                f"PSU {idx + 1} read failed: "
                f"{error}"
            )

        return {
            "online": False,
            "power_on": False,
            "voltage_v": 0.0,
            "current_a": 0.0,
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
        raise RuntimeError(f"PSU {idx + 1} is not connected")

    psu_lock = _psu_locks[idx]

    try:
        with psu_lock:
            print(f"PSU {idx + 1}: setting current to {current:.3f} A")
            instrument.write(f"SOURce:CURRent {current:.6f}")

            print(f"PSU {idx + 1}: setting voltage to {voltage:.3f} V")
            instrument.write(f"SOURce:VOLTage {voltage:.6f}")

        print(f"PSU {idx + 1}: calibration values sent successfully")

        return {
            "success": True,
            "voltage": voltage,
            "current": current,
        }

    except pyvisa.errors.VisaIOError as error:
        raise RuntimeError(
            f"Unable to apply calibration values to PSU {idx + 1}: {error}"
        ) from error


def psu_set_power(
    idx: int,
    on: bool,
    target_voltage: float | None = None,
    target_current: float | None = None,
    ramp_seconds: float = 4.0,
) -> bool:
    """
    Turn the PSU output ON or OFF.

    ON:
        Set the target voltage immediately, enable the output
        with a 0 A current setting, then use the native Sorensen
        current ramp to reach target_current.

    OFF:
        Abort any active current ramp and disable the output.
    """

    if not 0 <= idx < NUM_PSU:
        raise IndexError(
            f"Invalid PSU index: {idx}"
        )

    instrument = _psu_connections[idx]

    if instrument is None:
        raise RuntimeError(
            f"PSU {idx + 1} is not connected."
        )

    psu_lock = _psu_locks[idx]

    try:
        with psu_lock:
            if not on:
                instrument.write(
                    "SOURce:CURRent:RAMP:ABORt"
                )
                instrument.write(
                    "OUTPut:STATe 0"
                )

                print(
                    f"PSU {idx + 1}: output OFF"
                )

                return False

            if target_voltage is None:
                raise ValueError(
                    "Target voltage is required "
                    "when enabling PSU output."
                )

            if target_current is None:
                raise ValueError(
                    "Target current is required "
                    "when enabling PSU output."
                )

            voltage = float(target_voltage)
            current = float(target_current)
            duration = float(ramp_seconds)

            if voltage < 0:
                raise ValueError(
                    "Target voltage cannot be negative."
                )

            if current < 0:
                raise ValueError(
                    "Target current cannot be negative."
                )

            if not 0.1 <= duration <= 99.0:
                raise ValueError(
                    "Ramp duration must be between "
                    "0.1 and 99.0 seconds."
                )

            # Cancel any previous current ramp.
            instrument.write(
                "SOURce:CURRent:RAMP:ABORt"
            )

            # Prepare the PSU while output is disabled.
            instrument.write(
                "OUTPut:STATe 0"
            )

            # Apply the target voltage immediately.
            instrument.write(
                f"SOURce:VOLTage {voltage:.3f}"
            )

            # Establish the current-ramp starting point.
            instrument.write(
                "SOURce:CURRent 0"
            )

            # Enable output at the zero-current setting.
            instrument.write(
                "OUTPut:STATe 1"
            )

            # Start the native Sorensen current ramp.
            instrument.write(
                "SOURce:CURRent:RAMP "
                f"{current:.3f} "
                f"{duration:.1f}"
            )

            # Check whether the SGX accepted the commands.
            error_response = instrument.query(
                "SYSTem:ERRor?"
            ).strip()

            error_code_text = (
                error_response
                .split(",", maxsplit=1)[0]
                .strip()
            )

            try:
                error_code = int(
                    error_code_text
                )
            except ValueError:
                error_code = None

            if error_code != 0:
                instrument.write(
                    "SOURce:CURRent:RAMP:ABORt"
                )
                instrument.write(
                    "OUTPut:STATe 0"
                )

                raise RuntimeError(
                    "SGX rejected the current ramp: "
                    f"{error_response}"
                )

            # Confirm that the physical output is enabled.
            output_response = instrument.query(
                "OUTPut:STATe?"
            ).strip()

            output_on = output_response.upper() in {
                "1",
                "ON",
            }

            if not output_on:
                raise RuntimeError(
                    "The SGX accepted the commands, "
                    "but its output remains OFF."
                )

            # Normally returns 1 while the current ramp
            # is running and 0 when completed.
            ramp_status = instrument.query(
                "SOURce:CURRent:RAMP?"
            ).strip()

        print(
            f"PSU {idx + 1}: native current ramp "
            f"started, status={ramp_status}, "
            f"0.000 A to {current:.3f} A in "
            f"{duration:.1f} s, "
            f"voltage target={voltage:.3f} V"
        )

        return True

    except Exception as error:
        if on:
            try:
                with psu_lock:
                    instrument.write(
                        "SOURce:CURRent:RAMP:ABORt"
                    )
                    instrument.write(
                        "OUTPut:STATe 0"
                    )

            except Exception as shutdown_error:
                print(
                    f"PSU {idx + 1}: emergency "
                    f"shutdown failed: "
                    f"{shutdown_error}"
                )

        if isinstance(error, RuntimeError):
            raise

        raise RuntimeError(
            f"Unable to control PSU {idx + 1} "
            f"output: {error}"
        ) from error
    
def thermocouple_read() -> dict:
    """TODO: Replace with serial read from MCU."""
    return {
        "temp_c": round(125.0 + random.uniform(-2.5, 2.5), 1),
        "online": random.random() > 0.02,
    }
