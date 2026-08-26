import os
from pathlib import Path

from dotenv import load_dotenv

PROJECT_DIR = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_DIR / ".env")
import datetime
from collections import deque

C = {"green": "#00ff88", "yellow": "#ffcc00", "red": "#ff4455", "dim": "#4a6070"}
MAX_HIST = int(os.environ["MAX_HIST"])


class PSUState:
    def __init__(self, idx):
        
        self.idx = idx
        self.etr_number = f"ETR-{1000 + idx + 1}"
        self.technician = "—"
        
        self.target_hrs = 1000
        self.hours_elapsed = 0.0

        self.online = False
        self.power_on = False
        self.fault = False

        self.voltage_v = 0  # readback
        self.current_a = 0  # readback

        # Original required test parameters
        self.set_voltage = None
        self.set_current = None

        # Final PSU values determined during calibration
        self.calibrated_voltage = None
        self.calibrated_current = None

        self.calibrated_active = False
        self.calibration_complete = False

        self.notes = ""
        self.test_start_dt = None
        self.test_active = False

        self.last_db_sample_dt = None

        self.current_hist = deque(maxlen=MAX_HIST)
        self.voltage_hist = deque(maxlen=MAX_HIST)
        self.time_hist = deque(maxlen=MAX_HIST)

    @property
    def progress_pct(self):
        return min(100.0, (self.hours_elapsed / max(self.target_hrs, 1)) * 100)

    @property
    def status_str(self):
        if not self.test_active:
            return "IDLE"
        if self.fault:
            return "FAULT"
        if not self.online:
            return "OFFLINE"
        if self.power_on:
            return "ON"
        return "STANDBY"

    @property
    def status_color(self):
        return {
            "ON": C["green"],
            "STANDBY": C["yellow"],
            "OFFLINE": C["red"],
            "FAULT": C["red"],
            "IDLE": C["dim"],
        }.get(self.status_str, C["dim"])

    def restore(self, saved: dict):
        """Load persisted state back into this PSU object."""
        self.etr_number = saved.get("etr_number", self.etr_number)
        self.technician = saved.get("technician", self.technician)
        self.target_hrs = saved.get("target_hrs", self.target_hrs)
        self.hours_elapsed = saved.get("hours_elapsed", 0.0)
        self.notes = saved.get("notes", "")
        saved_set_voltage = saved.get("set_voltage")
        saved_set_current = saved.get("set_current")
        saved_cal_voltage = saved.get("calibrated_voltage")
        saved_cal_current = saved.get("calibrated_current")

        if saved_set_voltage is not None:
            self.set_voltage = float(saved_set_voltage)

        if saved_set_current is not None:
            self.set_current = float(saved_set_current)

        if saved_cal_voltage is not None:
            self.calibrated_voltage = float(saved_cal_voltage)

        if saved_cal_current is not None:
            self.calibrated_current = float(saved_cal_current)

        self.calibration_complete = saved.get(
            "calibration_complete",
            False,
        )
        self.test_active = saved.get("test_active", False)
        raw_dt = saved.get("test_start_dt")
        if raw_dt:
            try:
                self.test_start_dt = datetime.datetime.fromisoformat(raw_dt)
            except Exception:
                self.test_start_dt = None


class ChamberState:
    def __init__(self):
        self.temp_c = 0.0
        self.online = False
        self.temp_hist = deque(maxlen=MAX_HIST)
        self.time_hist = deque(maxlen=MAX_HIST)


# ══════════════════════════════════════════════════════════════════
#  POPUP: PSU Detail  (Current + Temp vs Time, range selectable)
# ══════════════════════════════════════════════════════════════════
