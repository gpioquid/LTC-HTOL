import datetime
import os
import sqlite3
import threading
from contextlib import contextmanager
from pathlib import Path

from dotenv import load_dotenv


PROJECT_DIR = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_DIR / ".env")


def _resolve_database_path() -> Path:
    configured_path = os.getenv(
        "SQLITE_DATABASE_PATH",
        "data/htol_monitor.db",
    )

    database_path = Path(configured_path)

    if not database_path.is_absolute():
        database_path = PROJECT_DIR / database_path

    return database_path.resolve()


DATABASE_PATH = _resolve_database_path()


class DataRepository:
    """SQLite storage for ongoing and completed HTOL tests."""

    def __init__(
        self,
        database_path: Path | None = None,
    ) -> None:
        self.database_path = Path(
            database_path or DATABASE_PATH
        )

        self.database_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        self._write_lock = threading.RLock()
        self._measurement_buffer: list[tuple] = []

        self._initialize_database()

    @contextmanager
    def _connection(self):
        connection = sqlite3.connect(
            self.database_path,
            timeout=10.0,
        )

        connection.row_factory = sqlite3.Row

        try:
            connection.execute(
                "PRAGMA foreign_keys = ON"
            )
            connection.execute(
                "PRAGMA busy_timeout = 10000"
            )

            yield connection
            connection.commit()

        except Exception:
            connection.rollback()
            raise

        finally:
            connection.close()

    def _initialize_database(self) -> None:
        with self._write_lock:
            with self._connection() as connection:
                connection.execute(
                    "PRAGMA journal_mode = WAL"
                )

                connection.execute(
                    "PRAGMA synchronous = NORMAL"
                )

                connection.executescript(
                    """
                    CREATE TABLE IF NOT EXISTS
                        live_test_sessions
                    (
                        psu_idx INTEGER PRIMARY KEY,
                        psu_label TEXT NOT NULL,

                        etr_number TEXT NOT NULL,
                        technician TEXT NOT NULL,

                        started_at_ms INTEGER,

                        target_hrs REAL NOT NULL,
                        hours_elapsed REAL NOT NULL DEFAULT 0,
                        progress_pct REAL NOT NULL DEFAULT 0,

                        required_voltage REAL,
                        required_current REAL,

                        calibrated_voltage REAL,
                        calibrated_current REAL,

                        calibration_complete INTEGER
                            NOT NULL DEFAULT 0,

                        output_on INTEGER NOT NULL DEFAULT 0,
                        psu_online INTEGER NOT NULL DEFAULT 0,
                        psu_fault INTEGER NOT NULL DEFAULT 0,

                        notes TEXT NOT NULL DEFAULT '',
                        updated_at_ms INTEGER NOT NULL
                    );


                    CREATE TABLE IF NOT EXISTS
                        live_test_measurements
                    (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,

                        psu_idx INTEGER NOT NULL,
                        measured_at_ms INTEGER NOT NULL,

                        voltage_v REAL,
                        current_a REAL,
                        chamber_temp_c REAL,

                        output_on INTEGER NOT NULL DEFAULT 0,
                        psu_online INTEGER NOT NULL DEFAULT 0,
                        psu_fault INTEGER NOT NULL DEFAULT 0,

                        FOREIGN KEY (psu_idx)
                            REFERENCES live_test_sessions(psu_idx)
                            ON DELETE CASCADE
                    );

                    CREATE INDEX IF NOT EXISTS
                        idx_live_measurements_psu_time
                    ON live_test_measurements (
                        psu_idx,
                        measured_at_ms
                    );


                    CREATE TABLE IF NOT EXISTS
                        test_sessions
                    (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,

                        psu_idx INTEGER NOT NULL,
                        psu_label TEXT NOT NULL,

                        etr_number TEXT NOT NULL,
                        technician TEXT NOT NULL,

                        started_at_ms INTEGER,
                        completed_at_ms INTEGER NOT NULL,

                        target_hrs REAL NOT NULL,
                        hours_elapsed REAL NOT NULL,
                        progress_pct REAL NOT NULL,

                        required_voltage REAL,
                        required_current REAL,

                        calibrated_voltage REAL,
                        calibrated_current REAL,

                        avg_voltage_v REAL,
                        avg_current_a REAL,
                        avg_temp_c REAL,

                        final_notes TEXT NOT NULL DEFAULT '',
                        created_at_ms INTEGER NOT NULL
                    );

                    CREATE INDEX IF NOT EXISTS
                        idx_test_sessions_completed
                    ON test_sessions (
                        completed_at_ms DESC
                    );

                    CREATE INDEX IF NOT EXISTS
                        idx_test_sessions_etr
                    ON test_sessions (
                        etr_number
                    );

                    CREATE INDEX IF NOT EXISTS
                        idx_test_sessions_technician
                    ON test_sessions (
                        technician
                    );


                    CREATE TABLE IF NOT EXISTS
                        test_measurements
                    (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,

                        test_session_id INTEGER NOT NULL,
                        measured_at_ms INTEGER NOT NULL,

                        voltage_v REAL,
                        current_a REAL,
                        chamber_temp_c REAL,

                        output_on INTEGER NOT NULL DEFAULT 0,
                        psu_online INTEGER NOT NULL DEFAULT 0,
                        psu_fault INTEGER NOT NULL DEFAULT 0,

                        FOREIGN KEY (test_session_id)
                            REFERENCES test_sessions(id)
                            ON DELETE CASCADE
                    );

                    CREATE INDEX IF NOT EXISTS
                        idx_test_measurements_session_time
                    ON test_measurements (
                        test_session_id,
                        measured_at_ms
                    );

                    CREATE TABLE IF NOT EXISTS events (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        created_at_ms INTEGER NOT NULL,
                        severity TEXT NOT NULL DEFAULT 'INFO',
                        message TEXT NOT NULL,
                        psu_idx INTEGER,
                        etr_number TEXT
                    );

                    CREATE INDEX IF NOT EXISTS
                        idx_events_created_at
                    ON events (
                        created_at_ms DESC
                    );

                    CREATE INDEX IF NOT EXISTS
                        idx_events_psu
                    ON events (
                        psu_idx,
                        created_at_ms DESC
                    );

                    """
                )

    @staticmethod
    def _datetime_to_ms(
        value: datetime.datetime | None,
    ) -> int | None:
        if value is None:
            return None

        if not isinstance(
            value,
            datetime.datetime,
        ):
            raise TypeError(
                "Expected datetime.datetime or None."
            )

        return int(value.timestamp() * 1000)

    @staticmethod
    def _ms_to_datetime_text(
        value: int | None,
    ) -> str | None:
        if value is None:
            return None

        return datetime.datetime.fromtimestamp(
            value / 1000
        ).isoformat(
            timespec="seconds"
        )

    def test_connection(self) -> bool:
        """Verify that the SQLite database is accessible."""

        with self._connection() as connection:
            row = connection.execute(
                "SELECT 1 AS result"
            ).fetchone()

        return bool(
            row is not None
            and row["result"] == 1
        )

    def save_live_state(self, psus) -> None:
        """Create or update the database record for every active test."""

        now_ms = int(
            datetime.datetime.now().timestamp() * 1000
        )

        query = """
            INSERT INTO live_test_sessions (
                psu_idx,
                psu_label,
                etr_number,
                technician,
                started_at_ms,
                target_hrs,
                hours_elapsed,
                progress_pct,
                required_voltage,
                required_current,
                calibrated_voltage,
                calibrated_current,
                calibration_complete,
                output_on,
                psu_online,
                psu_fault,
                notes,
                updated_at_ms
            )
            VALUES (
                ?, ?, ?, ?, ?, ?, ?, ?, ?,
                ?, ?, ?, ?, ?, ?, ?, ?, ?
            )
            ON CONFLICT(psu_idx) DO UPDATE SET
                psu_label = excluded.psu_label,
                etr_number = excluded.etr_number,
                technician = excluded.technician,
                started_at_ms = excluded.started_at_ms,
                target_hrs = excluded.target_hrs,
                hours_elapsed = excluded.hours_elapsed,
                progress_pct = excluded.progress_pct,
                required_voltage = excluded.required_voltage,
                required_current = excluded.required_current,
                calibrated_voltage = excluded.calibrated_voltage,
                calibrated_current = excluded.calibrated_current,
                calibration_complete =
                    excluded.calibration_complete,
                output_on = excluded.output_on,
                psu_online = excluded.psu_online,
                psu_fault = excluded.psu_fault,
                notes = excluded.notes,
                updated_at_ms = excluded.updated_at_ms
        """

        rows = []

        for psu in psus:
            if not psu.test_active:
                continue

            rows.append(
                (
                    psu.idx,
                    f"PSU{psu.idx + 1}",
                    psu.etr_number,
                    psu.technician,
                    self._datetime_to_ms(
                        psu.test_start_dt
                    ),
                    float(psu.target_hrs),
                    float(psu.hours_elapsed),
                    float(psu.progress_pct),
                    psu.set_voltage,
                    psu.set_current,
                    psu.calibrated_voltage,
                    psu.calibrated_current,
                    int(psu.calibration_complete),
                    int(psu.power_on),
                    int(psu.online),
                    int(psu.fault),
                    psu.notes or "",
                    now_ms,
                )
            )

        if not rows:
            return

        with self._write_lock:
            with self._connection() as connection:
                connection.executemany(
                    query,
                    rows,
                )

    def load_live_state(self) -> list:
    #Load all ongoing tests for application recovery
        with self._connection() as connection:
            rows = connection.execute(
                """
                SELECT
                    psu_idx,
                    etr_number,
                    technician,
                    started_at_ms,
                    target_hrs,
                    hours_elapsed,
                    required_voltage,
                    required_current,
                    calibrated_voltage,
                    calibrated_current,
                    calibration_complete,
                    output_on,
                    psu_online,
                    psu_fault,
                    notes
                FROM live_test_sessions
                ORDER BY psu_idx
                """
            ).fetchall()

        saved_states = []

        for row in rows:
            test_start_dt = self._ms_to_datetime_text(
                row["started_at_ms"]
            )

            saved_states.append(
                {
                    "psu_idx": row["psu_idx"],
                    "etr_number": row["etr_number"],
                    "technician": row["technician"],
                    "target_hrs": row["target_hrs"],
                    "hours_elapsed": row[
                        "hours_elapsed"
                    ],
                    "set_voltage": row[
                        "required_voltage"
                    ],
                    "set_current": row[
                        "required_current"
                    ],
                    "calibrated_voltage": row[
                        "calibrated_voltage"
                    ],
                    "calibrated_current": row[
                        "calibrated_current"
                    ],
                    "calibration_complete": bool(
                        row["calibration_complete"]
                    ),
                    "test_active": True,
                    "test_start_dt": test_start_dt,
                    "notes": row["notes"] or "",
                    "power_on": bool(row["output_on"]),
                    "online": bool(row["psu_online"]),
                    "fault": bool(row["psu_fault"]),
                }
            )

        return saved_states

    def buffer_live_measurement(
        self,
        psu,
        chamber,
        measured_at: datetime.datetime,
    ) -> None:
        """Buffer one measurement sample for an ongoing test."""

        if not psu.test_active:
            return

        chamber_temperature = None

        if chamber.online:
            chamber_temperature = float(
                chamber.temp_c
            )

        measurement = (
            int(psu.idx),
            self._datetime_to_ms(measured_at),
            float(psu.voltage_v),
            float(psu.current_a),
            chamber_temperature,
            int(bool(psu.power_on)),
            int(bool(psu.online)),
            int(bool(psu.fault)),
        )

        with self._write_lock:
            self._measurement_buffer.append(
                measurement
            )

    def flush_measurement_buffer(self) -> int:
        """Write all buffered measurements in one transaction."""

        with self._write_lock:
            if not self._measurement_buffer:
                return 0

            pending_rows = list(
                self._measurement_buffer
            )

            self._measurement_buffer.clear()

            try:
                with self._connection() as connection:
                    connection.executemany(
                        """
                        INSERT INTO live_test_measurements (
                            psu_idx,
                            measured_at_ms,
                            voltage_v,
                            current_a,
                            chamber_temp_c,
                            output_on,
                            psu_online,
                            psu_fault
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        pending_rows,
                    )

            except Exception:
                # Put the samples back if the database write fails.
                self._measurement_buffer[0:0] = (
                    pending_rows
                )
                raise

        return len(pending_rows)

    def get_live_measurements(
        self,
        psu_idx: int,
        limit: int,
    ) -> list:
        """Return recent live samples in chronological order."""

        with self._connection() as connection:
            rows = connection.execute(
                """
                SELECT
                    measured_at_ms,
                    voltage_v,
                    current_a,
                    chamber_temp_c,
                    output_on,
                    psu_online,
                    psu_fault
                FROM (
                    SELECT
                        measured_at_ms,
                        voltage_v,
                        current_a,
                        chamber_temp_c,
                        output_on,
                        psu_online,
                        psu_fault
                    FROM live_test_measurements
                    WHERE psu_idx = ?
                    ORDER BY measured_at_ms DESC
                    LIMIT ?
                )
                ORDER BY measured_at_ms ASC
                """,
                (
                    int(psu_idx),
                    int(limit),
                ),
            ).fetchall()

        measurements = []

        for row in rows:
            measurements.append(
                {
                    "measured_at": (
                        datetime.datetime.fromtimestamp(
                            row["measured_at_ms"]
                            / 1000
                        )
                    ),
                    "voltage_v": row["voltage_v"],
                    "current_a": row["current_a"],
                    "chamber_temp_c": (
                        row["chamber_temp_c"]
                    ),
                    "output_on": bool(
                        row["output_on"]
                    ),
                    "psu_online": bool(
                        row["psu_online"]
                    ),
                    "psu_fault": bool(
                        row["psu_fault"]
                    ),
                }
            )

        return measurements

    def append_event(self, event) -> int:
        """Store one application event in SQLite."""

        if isinstance(event, dict):
            message = str(
                event.get("message")
                or event.get("text")
                or ""
            )

            severity = str(
                event.get("severity")
                or event.get("level")
                or "INFO"
            ).upper()

            psu_idx = event.get("psu_idx")
            etr_number = event.get("etr_number")

            event_time = (
                event.get("timestamp")
                or event.get("created_at")
                or datetime.datetime.now()
            )

        else:
            message = str(event)
            severity = "INFO"
            psu_idx = None
            etr_number = None
            event_time = datetime.datetime.now()

        if not message:
            raise ValueError(
                "Cannot save an event without a message."
            )

        if isinstance(event_time, datetime.datetime):
            created_at_ms = self._datetime_to_ms(
                event_time
            )

        elif isinstance(event_time, (int, float)):
            created_at_ms = int(event_time)

        elif isinstance(event_time, str):
            try:
                parsed_time = (
                    datetime.datetime.fromisoformat(
                        event_time
                    )
                )
                created_at_ms = self._datetime_to_ms(
                    parsed_time
                )

            except ValueError:
                created_at_ms = self._datetime_to_ms(
                    datetime.datetime.now()
                )

        else:
            created_at_ms = self._datetime_to_ms(
                datetime.datetime.now()
            )

        with self._write_lock:
            with self._connection() as connection:
                cursor = connection.execute(
                    """
                    INSERT INTO events (
                        created_at_ms,
                        severity,
                        message,
                        psu_idx,
                        etr_number
                    )
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        created_at_ms,
                        severity,
                        message,
                        psu_idx,
                        etr_number,
                    ),
                )

                return int(cursor.lastrowid)

    def get_events(
        self,
        limit: int = 500,
    ) -> list:
        """Return the latest application events."""

        with self._connection() as connection:
            rows = connection.execute(
                """
                SELECT
                    id,
                    created_at_ms,
                    severity,
                    message,
                    psu_idx,
                    etr_number
                FROM events
                ORDER BY created_at_ms DESC, id DESC
                LIMIT ?
                """,
                (int(limit),),
            ).fetchall()

        events = []

        for row in reversed(rows):
            events.append(
                {
                    "id": row["id"],
                    "timestamp": (
                        self._ms_to_datetime_text(
                            row["created_at_ms"]
                        )
                    ),
                    "severity": row["severity"],
                    "message": row["message"],
                    "psu_idx": row["psu_idx"],
                    "etr_number": row["etr_number"],
                }
            )

        return events