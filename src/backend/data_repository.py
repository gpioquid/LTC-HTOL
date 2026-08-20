import os
from pathlib import Path

from dotenv import load_dotenv

PROJECT_DIR = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_DIR / ".env")
import datetime
import json
import threading

_data_file = Path(os.environ["DATA_FILE"])
if not _data_file.is_absolute():
    _data_file = PROJECT_DIR / _data_file
DATA_FILE = str(_data_file.resolve())


class DataStore:
    """
    Single JSON file  htol_data.json  with three sections:
      live_state        — PSU states saved periodically so tests survive restarts
      completed_tests   — Archived records of finished tests
      event_log         — Time-stamped event strings
    """

    _lock = threading.Lock()

    def __init__(self, path=DATA_FILE):
        self.path = path
        self._ensure_file()

    def _ensure_file(self):
        if not os.path.exists(self.path):
            self._write({"live_state": {}, "completed_tests": [], "event_log": []})

    def _read(self) -> dict:
        try:
            with open(self.path, "r") as f:
                return json.load(f)
        except Exception:
            return {"live_state": {}, "completed_tests": [], "event_log": []}

    def _write(self, data: dict):
        with self._lock, open(self.path, "w") as f:
            json.dump(data, f, indent=2, default=str)

    # ── Live state (auto-save / resume) ──────────────────────────

    def save_live_state(self, psus: list):
        """Persist in-progress test state so it can be resumed after restart."""
        data = self._read()
        for psu in psus:
            data["live_state"][str(psu.idx)] = {
                "etr_number": psu.etr_number,
                "technician": psu.technician,
                "target_hrs": psu.target_hrs,
                "hours_elapsed": psu.hours_elapsed,
                "notes": psu.notes,
                "test_start_dt": psu.test_start_dt.isoformat()
                if psu.test_start_dt
                else None,
                "set_voltage": psu.set_voltage,
                "set_current": psu.set_current,
                "calibrated_voltage": psu.calibrated_voltage,
                "calibrated_current": psu.calibrated_current,
                "calibration_complete": psu.calibration_complete,
                "test_active": psu.test_active,
                # Keep a compact snapshot (last 200 pts) for the history plot
                "current_snap": list(psu.current_hist)[-200:],
                "temp_snap": [],  # filled by caller
            }
        self._write(data)

    def load_live_state(self) -> dict:
        return self._read().get("live_state", {})

    # ── Completed tests ───────────────────────────────────────────

    def complete_test(self, record: dict):
        data = self._read()
        data.setdefault("completed_tests", []).append(record)
        # Clear the live slot for this PSU
        data["live_state"].pop(str(record.get("psu_idx", "")), None)
        self._write(data)

    def get_completed_tests(self) -> list:
        return self._read().get("completed_tests", [])

    # ── Events ───────────────────────────────────────────────────

    def append_event(self, msg: str):
        data = self._read()
        data.setdefault("event_log", []).append(
            {
                "ts": datetime.datetime.now().isoformat(timespec="seconds"),
                "msg": msg,
            }
        )
        data["event_log"] = data["event_log"][-2000:]
        self._write(data)

    # ── Snapshot export ───────────────────────────────────────────

    def export_snapshot(self, psus: list, chamber_temp: float) -> str:
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        fpath = os.path.join(os.path.dirname(self.path), f"htol_snapshot_{ts}.json")
        snap = {
            "snapshot_time": ts,
            "chamber_temp_c": chamber_temp,
            "psus": [
                {
                    "psu": f"PSU{p.idx + 1}",
                    "etr": p.etr_number,
                    "technician": p.technician,
                    "hours": round(p.hours_elapsed, 4),
                    "target_hrs": p.target_hrs,
                    "voltage_v": p.voltage_v,
                    "current_a": p.current_a,
                    "status": p.status_str,
                    "notes": p.notes,
                }
                for p in psus
            ],
        }
        with open(fpath, "w") as f:
            json.dump(snap, f, indent=2, default=str)
        return fpath


# ══════════════════════════════════════════════════════════════════
#  DATA MODEL
# ══════════════════════════════════════════════════════════════════
