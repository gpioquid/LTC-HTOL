import datetime
import os
import threading
import traceback
from pathlib import Path

from dotenv import load_dotenv
from PySide6.QtCore import QObject, Qt, QTimer, Signal
from PySide6.QtWidgets import (
    QInputDialog,
    QMainWindow,
    QMessageBox,
    QSizePolicy,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from src.backend.data_repository import DataRepository
from src.backend.instrument_drivers import (
    disconnect_psus,
    psu_read,
    psu_set_power,
    thermocouple_read,
)
from src.backend.state_models import (
    ChamberState,
    PSUState,
)
from src.frontend.dialogs import (
    CompleteTestDialog,
    OpenFuseRecoveryDialog,
    PSUCalibrationPopup,
    PSUDetailPopup,
    PSUSetupPopup,
    TestHistoryPopup,
)
from src.frontend.widgets import (
    ChamberWidget,
    EventLogWidget,
    HeaderWidget,
    PSUPanelWidget,
    StatusBarWidget,
)

PROJECT_DIR = Path(__file__).resolve().parents[2]
load_dotenv(
    PROJECT_DIR / ".env",
    override=True,
)

UI_TEST_MODE = (
    os.getenv("UI_TEST_MODE", "false")
    .strip()
    .lower()
    == "true"
)

NUM_PSU = int(os.environ["NUM_PSU"])
POLL_MS = int(os.environ["POLL_MS"])
AUTO_SAVE_INTERVAL = int(os.environ["AUTO_SAVE_INTERVAL"])

_database_file = Path(
    os.getenv(
        "SQLITE_DATABASE_PATH",
        "data/htol_monitor.db",
    )
)

if not _database_file.is_absolute():
    _database_file = (
        PROJECT_DIR / _database_file
    )

DATABASE_FILE = str(
    _database_file.resolve()
)

PSU_OUTPUT_RAMP_SECONDS = float(
    os.getenv(
        "PSU_OUTPUT_RAMP_SECONDS",
        "4.0",
    )
)

DB_SAMPLE_INTERVAL_SECONDS = float(
    os.getenv(
        "DB_SAMPLE_INTERVAL_SECONDS",
        "10",
    )
)

DB_BATCH_FLUSH_SECONDS = float(
    os.getenv(
        "DB_BATCH_FLUSH_SECONDS",
        "30",
    )
)

class Bus(QObject):
    fetched = Signal(object)
    error = Signal(str)

    # Sends the completed open-fuse event back to
    # the main Qt UI thread.
    open_fuse_detected = Signal(object)

class HTOLMonitor(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("HTOL MONITOR v3.0 | HIGH TEMPERATURE OPERATING LIFE TEST")
        self.resize(1680, 960)
        self.setMinimumSize(1180, 720)
        self.setObjectName("HTOLMonitor")
        self._main_splitter_sizes = [1000, 650]
        self._right_splitter_sizes = [560, 240]

        self.psus = [
            PSUState(index)
            for index in range(NUM_PSU)
        ]

        # Open-fuse detection runtime state.
        self._open_fuse_low_current_counts = {
            psu.idx: 0
            for psu in self.psus
        }

        self._open_fuse_monitor_started_at = {
            psu.idx: None
            for psu in self.psus
        }

        self._open_fuse_handling: set[int] = set()

        self._restore_message = None
        self.chamber = ChamberState()
        self.store = DataRepository()


        self._restore_message = None
        self.chamber = ChamberState()
        self.store = DataRepository()
        self._last_db_flush_dt = (datetime.datetime.now())

        self._closing = False
        self._fetch_thread = None
        self._fetch_lock = threading.Lock()

        self.poll_timer = QTimer(self)
        self.poll_timer.timeout.connect(
            self._start_fetch
        )
        self.poll_timer.start(POLL_MS)

        self.running = True
        self._poll_in_progress = False
        self._last_save = datetime.datetime.now()

        # Keep non-modal dialogs alive.
        self._dialogs = []

        self.bus = Bus()
        self.bus.fetched.connect(self.update_ui)
        self.bus.error.connect(self._handle_polling_error)

        self.bus.open_fuse_detected.connect(
            self._on_open_fuse_detected
        )

        #self._restore_live_state()
        self._build_ui()
        self._connect_widget_signals()
        self._initialize_log()
        self._start_timers()

    # ==========================================================
    # Initialization
    # ==========================================================

    def _on_test_started(
        self,
        index: int,
    ) -> None:
        psu = self.psus[index]

        psu.calibration_active = False
        psu.calibration_complete = True
        psu.test_active = True
        psu.power_on = True

        # Arm open-fuse monitoring for this test.
        self._open_fuse_low_current_counts[index] = 0

        self._open_fuse_monitor_started_at[index] = (
            datetime.datetime.now()
        )

        self._open_fuse_handling.discard(index)


        if psu.test_start_dt is None:
            psu.test_start_dt = (
                datetime.datetime.now()
            )

        try:
            self.store.save_live_state(
                self.psus
            )

        except Exception as error:
            psu.test_active = False

            self._open_fuse_low_current_counts[index] = 0
            self._open_fuse_monitor_started_at[index] = None
            self._open_fuse_handling.discard(index)

            QMessageBox.critical(
                self,
                "Database Error",
                (
                    "The test could not be started because "
                    "the ongoing test record was not saved."
                    f"\n\n{error}"
                ),
            )
            return

        channel = (
            self.psu_panel_widget
            .channel_widgets[index]
        )
        channel.update_state(psu)

        self._log(
            f"TEST STARTED  "
            f"PSU{index + 1}  "
            f"ETR:{psu.etr_number}  "
            f"Required:"
            f"{psu.set_voltage:.3f} V / "
            f"{psu.set_current:.3f} A  "
            f"Calibrated:"
            f"{psu.calibrated_voltage:.3f} V / "
            f"{psu.calibrated_current:.3f} A"
        )

    def _restore_live_state(self) -> None:
        try:
            saved_states = self.store.load_live_state()

        except Exception as error:
            self._restore_message = (
                f"Unable to restore ongoing tests: {error}"
            )
            return

        restored_channels = []

        for saved_state in saved_states:
            index = int(saved_state["psu_idx"])

            if not 0 <= index < len(self.psus):
                continue

            psu = self.psus[index]
            psu.restore(saved_state)

            psu.power_on = bool(
                saved_state.get("power_on", False)
            )
            psu.online = bool(
                saved_state.get("online", False)
            )

            restored_channels.append(
                f"PSU{index + 1}/{psu.etr_number}"
            )

        if restored_channels:
            self._restore_message = (
                "Restored ongoing tests: "
                + ", ".join(restored_channels)
            )
        else:
            self._restore_message = None

    def _build_ui(self):
        central_widget = QWidget()
        central_widget.setObjectName("centralWidget")

        self.setCentralWidget(central_widget)

        root_layout = QVBoxLayout(central_widget)
        root_layout.setContentsMargins(8, 8, 8, 5)
        root_layout.setSpacing(6)

        # ----------------------------------------------------------
        # Header
        # ----------------------------------------------------------

        self.header_widget = HeaderWidget(NUM_PSU)
        self.header_widget.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Fixed,
        )

        root_layout.addWidget(self.header_widget)

        # ----------------------------------------------------------
        # Main horizontal splitter
        # ----------------------------------------------------------

        self.main_splitter = QSplitter(
            Qt.Orientation.Horizontal,
            self,
        )
        self.main_splitter.setObjectName("mainSplitter")
        self.main_splitter.setChildrenCollapsible(False)
        self.main_splitter.setHandleWidth(5)
        self.main_splitter.setOpaqueResize(True)

        # ----------------------------------------------------------
        # Left side: PSU channels
        # ----------------------------------------------------------

        self.psu_panel_widget = PSUPanelWidget(self.psus)
        self.psu_panel_widget.setMinimumWidth(650)
        self.psu_panel_widget.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding,
        )

        self.main_splitter.addWidget(self.psu_panel_widget)

        # ----------------------------------------------------------
        # Right side: vertical splitter
        # ----------------------------------------------------------

        self.right_splitter = QSplitter(
            Qt.Orientation.Vertical,
            self,
        )
        self.right_splitter.setObjectName("rightSplitter")
        self.right_splitter.setChildrenCollapsible(False)
        self.right_splitter.setHandleWidth(5)
        self.right_splitter.setOpaqueResize(True)
        self.right_splitter.setMinimumWidth(440)

        self.chamber_widget = ChamberWidget()
        self.chamber_widget.setMinimumHeight(330)
        self.chamber_widget.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding,
        )

        self.event_log_widget = EventLogWidget()
        self.event_log_widget.setMinimumHeight(150)
        self.event_log_widget.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding,
        )

        self.right_splitter.addWidget(self.chamber_widget)
        self.right_splitter.addWidget(self.event_log_widget)

        # Give the chamber area more space than the event log.
        self.right_splitter.setStretchFactor(0, 7)
        self.right_splitter.setStretchFactor(1, 3)
        self.right_splitter.setSizes(self._right_splitter_sizes)

        self.main_splitter.addWidget(self.right_splitter)

        # PSU panel receives approximately 60% of the width.
        self.main_splitter.setStretchFactor(0, 3)
        self.main_splitter.setStretchFactor(1, 2)
        self.main_splitter.setSizes(self._main_splitter_sizes)

        root_layout.addWidget(
            self.main_splitter,
            1,
        )

        # ----------------------------------------------------------
        # Bottom status bar
        # ----------------------------------------------------------

        self.status_bar_widget = StatusBarWidget(DATABASE_FILE)
        self.status_bar_widget.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Fixed,
        )

        root_layout.addWidget(self.status_bar_widget)
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        root_layout = QVBoxLayout(central_widget)
        root_layout.setContentsMargins(
            10,
            10,
            10,
            6,
        )
        root_layout.setSpacing(7)

        # Header
        self.header_widget = HeaderWidget(NUM_PSU)
        root_layout.addWidget(self.header_widget)

        # Main content splitter
        splitter = QSplitter()
        splitter.setChildrenCollapsible(False)
        splitter.setHandleWidth(3)

        # Left side
        self.psu_panel_widget = PSUPanelWidget(self.psus)

        # Right side
        right_widget = QWidget()

        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(
            4,
            0,
            0,
            0,
        )
        right_layout.setSpacing(6)

        self.chamber_widget = ChamberWidget()
        self.event_log_widget = EventLogWidget()

        right_layout.addWidget(
            self.chamber_widget,
            3,
        )
        right_layout.addWidget(
            self.event_log_widget,
            2,
        )

        splitter.addWidget(self.psu_panel_widget)
        splitter.addWidget(right_widget)

        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)
        splitter.setSizes([980, 650])

        root_layout.addWidget(splitter, 1)

        # Bottom status bar
        self.status_bar_widget = StatusBarWidget(DATABASE_FILE)

        root_layout.addWidget(self.status_bar_widget)

    def _connect_widget_signals(self):
        # Header
        self.header_widget.history_requested.connect(self._open_history)

        # PSU actions
        self.psu_panel_widget.test_toggled.connect(self._toggle_test)
        self.psu_panel_widget.control_requested.connect(self._open_control)
        self.psu_panel_widget.trend_requested.connect(self._open_detail)
        self.psu_panel_widget.complete_requested.connect(self._complete_test)
        self.psu_panel_widget.notes_requested.connect(self._edit_notes)
        self.psu_panel_widget.machine_selected.connect(self._open_detail)

        # PSU input changes
        self.psu_panel_widget.etr_changed.connect(self._set_etr)
        self.psu_panel_widget.technician_changed.connect(self._set_technician)
        self.psu_panel_widget.target_changed.connect(self._set_target)

        # Persist every event added to the log widget.
        self.event_log_widget.event_added.connect(self._persist_event)

    def _initialize_log(self):
        self._log("HTOL Monitor v3.0 initialized. Continuous monitoring active.")
        self._log(
                f"Database: {DATABASE_FILE}"
            )

        if self._restore_message:
            self._log(self._restore_message)

    def _start_timers(self) -> None:
        self.poll_timer = QTimer(self)

        self.poll_timer.timeout.connect(
            self._start_fetch
        )

        self.poll_timer.start(POLL_MS)

        # Run the first polling cycle immediately.
        self._start_fetch()

    # ==========================================================
    # Logging
    # ==========================================================

    def _log(self, message):
        self.event_log_widget.append_event(message)

    def _persist_event(self, event) -> None:
        def save_event() -> None:
            try:
                self.store.append_event(event)

            except Exception as error:
                print(
                    f"Unable to persist event: {error}"
                )

        threading.Thread(
            target=save_event,
            daemon=True,
        ).start()

    def _update_clock(self):
        current_time = datetime.datetime.now().strftime("%H:%M:%S")

        self.header_widget.set_clock(current_time)

    # ==========================================================
    # PSU input updates
    # ==========================================================

    def _set_etr(self, index, value):
        self.psus[index].etr_number = value.strip()

    def _set_technician(
        self,
        index,
        value,
    ):
        self.psus[index].technician = value.strip()

    def _set_target(
        self,
        index,
        value,
    ):
        psu = self.psus[index]
        channel_widget = self.psu_panel_widget.channel_widgets[index]

        try:
            target_hours = float(value)

            if target_hours <= 0:
                raise ValueError

            psu.target_hrs = target_hours

        except ValueError:
            channel_widget.target_input.setText(str(psu.target_hrs))

            QMessageBox.warning(
                self,
                "Invalid Target",
                "Target hours must be a number greater than zero.",
            )

    # ==========================================================
    # Test actions
    # ==========================================================

    def _toggle_test(self, index):
        psu = self.psus[index]

        channel_widget = self.psu_panel_widget.channel_widgets[index]

        # Read the current values before starting.
        psu.etr_number = channel_widget.etr_input.text().strip()
        psu.technician = channel_widget.technician_input.text().strip()

        try:
            target_hours = float(channel_widget.target_input.text())

            if target_hours <= 0:
                raise ValueError

            psu.target_hrs = target_hours

        except ValueError:
            channel_widget.target_input.setText(str(psu.target_hrs))

            QMessageBox.warning(
                self,
                "Invalid Target",
                "Target hours must be a number greater than zero.",
            )
            return

        if not psu.test_active:
            if psu.etr_number in ("", "—"):
                QMessageBox.warning(
                    self,
                    "Missing Information",
                    f"Enter an ETR number for PSU{index + 1} before starting.",
                )
                return

            psu.test_active = True

            if psu.test_start_dt is None:
                psu.test_start_dt = datetime.datetime.now()

            self._log(
                f"TEST STARTED  "
                f"PSU{index + 1}  "
                f"ETR:{psu.etr_number}  "
                f"Tech:{psu.technician}"
            )

        else:
            psu.test_active = False

            self._log(
                f"TEST PAUSED  "
                f"PSU{index + 1}  "
                f"ETR:{psu.etr_number}  "
                f"({psu.hours_elapsed:.2f} "
                "h elapsed)"
            )

        channel_widget.update_state(psu)
        self._auto_save()

    def _ui_test_complete_test(
        self,
        index: int,
    ) -> None:
        if not UI_TEST_MODE:
            return

        psu = self.psus[index]

        if not psu.test_active:
            QMessageBox.information(
                self,
                "UI Test Mode",
                f"PSU{index + 1} has no active test.",
            )
            return

        # Fast-forward the software state to 100%.
        psu.hours_elapsed = float(psu.target_hrs)

        # Keep the test active until CompleteTestDialog
        # confirms and archives it.
        psu.test_active = True
        psu.online = True
        psu.power_on = True

        channel = (
            self.psu_panel_widget
            .channel_widgets[index]
        )
        channel.update_state(psu)

        self._log(
            f"UI TEST MODE: PSU{index + 1} "
            f"fast-forwarded to "
            f"{psu.target_hrs:g} h."
        )

        self._auto_save()

        # Open your existing CompleteTestDialog.
        QTimer.singleShot(
            0,
            lambda: self._complete_test(index),
        )

    def _complete_test(self, index):
        psu = self.psus[index]

        if psu.hours_elapsed < 0.001 and not psu.test_active:
            QMessageBox.information(
                self,
                "Nothing to Archive",
                f"PSU{index + 1} has no active test to complete.",
            )
            return

        dialog = CompleteTestDialog(
            self,
            psu,
            self.chamber,
            self.store,
            self._on_test_completed,
        )

        self._show_dialog(dialog)

    def _on_test_completed(
        self,
        index: int,
        record: dict,
    ) -> None:
        psu = self.psus[index]

        self._log(
            f"TEST ENDED  "
            f"PSU{index + 1}  "
            f"ETR:{record.get('etr_number', '—')}  "
            f"Tech:{record.get('technician', '—')}  "
            f"Duration:{record.get('hours_elapsed', 0.0):.2f} h"
        )

        # Reset the completed PSU channel.
        psu.test_active = False
        psu.calibration_active = False
        psu.calibration_complete = False
        psu.test_start_dt = None

        psu.power_on = False
        psu.hours_elapsed = 0.0

        psu.calibrated_voltage = None
        psu.calibrated_current = None

        # Reset open-fuse monitoring for the completed test.
        self._open_fuse_low_current_counts[index] = 0
        self._open_fuse_monitor_started_at[index] = None
        self._open_fuse_handling.discard(index)

        # Keep the required configuration if you want the completed
        # values visible until the next test setup.
        #
        # To clear them instead, uncomment:
        # psu.etr_number = ""
        # psu.technician = "—"
        # psu.target_hrs = 1000
        # psu.set_voltage = None
        # psu.set_current = None
        # psu.notes = ""

        channel = self.psu_panel_widget.channel_widgets[index]
        channel.update_state(psu)

        self._auto_save()

    def _sample_active_test(
        self,
        psu,
        now: datetime.datetime,
    ) -> None:
        """Buffer one sample at the configured database interval."""

        if not psu.test_active:
            return

        last_sample = psu.last_db_sample_dt

        if last_sample is not None:
            elapsed_seconds = (
                now - last_sample
            ).total_seconds()

            if (
                elapsed_seconds
                < DB_SAMPLE_INTERVAL_SECONDS
            ):
                return

        self.store.buffer_live_measurement(
            psu=psu,
            chamber=self.chamber,
            measured_at=now,
        )

        psu.last_db_sample_dt = now


    def _edit_notes(self, index):
        psu = self.psus[index]

        text, accepted = QInputDialog.getMultiLineText(
            self,
            f"Notes - PSU{index + 1}",
            "Enter test notes:",
            psu.notes,
        )

        if not accepted:
            return

        psu.notes = text.strip()

        self._log(f"PSU{index + 1} notes updated.")

        self._auto_save()

    def _on_detail_settings_applied(
        self,
        index,
        etr_number,
        technician,
        target_hours,
        voltage,
        current,
    ):
        psu = self.psus[index]

        psu.etr_number = etr_number
        psu.technician = technician
        psu.target_hrs = target_hours
        psu.set_voltage = voltage
        psu.set_current = current

        channel = self.psu_panel_widget.channel_widgets[index]

        channel.update_state(psu)

        self._log(
            f"PSU{index + 1} settings applied: "
            f"ETR: {etr_number} "
            f"Tech: {technician}"
            f"Target: {target_hours:g} h"
            f"{voltage:.3f} V and {current:.3f} A"
        )

        self._auto_save()

    # ==========================================================
    # Dialogs
    # ==========================================================

    def _open_control(self, index):
        dialog = PSUControlPopup(
            self,
            self.psus[index],
            self._on_setpoints_applied,
        )

        self._show_dialog(dialog)

    def _on_setpoints_applied(
        self,
        index,
        voltage,
        current,
    ):
        self._log(
            f"PSU{index + 1} setpoints updated: {voltage:.3f} V / {current:.3f} A"
        )

    def _open_detail(self, index: int) -> None:
        try:
            psu = self.psus[index]

            if psu.test_active:
                dialog = PSUDetailPopup(
                    self,
                    psu,
                    self.chamber,
                    self._on_detail_settings_applied,
                    on_ui_test_complete=(
                        self._ui_test_complete_test
                        if UI_TEST_MODE
                        else None
                    ),
                )
            else:
                dialog = PSUSetupPopup(
                    self,
                    psu,
                    self._open_calibration,
                )

            self._show_dialog(dialog)

        except Exception:
            traceback.print_exc()

    def _open_calibration(self, index: int) -> None:
        print(
            f"Opening PSU {index + 1} calibration: "
            f"UI_TEST_MODE={UI_TEST_MODE}"
        )

        dialog = PSUCalibrationPopup(
            self,
            self.psus[index],
            self._on_test_started,
            ui_test_mode=UI_TEST_MODE,
        )

        self._show_dialog(dialog)

    def _open_history(self):
        dialog = TestHistoryPopup(
            self,
            self.store,
        )

        self._show_dialog(dialog)

    def _show_dialog(self, dialog):
        self._dialogs.append(dialog)

        # QDialog provides finished. This removes
        # the retained reference when it closes.
        dialog.finished.connect(
            lambda result, current=dialog: self._release_dialog(current)
        )

        dialog.show()
        dialog.raise_()
        dialog.activateWindow()

    def _release_dialog(self, dialog):
        if dialog in self._dialogs:
            self._dialogs.remove(dialog)

        dialog.deleteLater()

    # ==========================================================
    # Export and persistence
    # ==========================================================

    def _auto_save(self):
        threading.Thread(
            target=self.store.save_live_state,
            args=(self.psus,),
            daemon=True,
        ).start()

    # ==========================================================
    # Polling
    # ==========================================================

    def _start_fetch(self) -> None:
        if self._closing:
            return

        if (
            self._fetch_thread is not None
            and self._fetch_thread.is_alive()
        ):
            return

        self._fetch_thread = threading.Thread(
            target=self._fetch,
            daemon=True,
            name="htol-polling",
        )
        self._fetch_thread.start()

    def _fetch(self) -> None:
        if self._closing:
            return

        if not self._fetch_lock.acquire(blocking=False):
            return

        try:
            if self._closing:
                return

            now = datetime.datetime.now()

            self._fetch_psu_readings(now)

            if self._closing:
                return

            self._fetch_chamber_reading(now)

            if self._closing:
                return

            self._perform_periodic_save(now)

            if self._closing:
                return

            try:
                self.bus.fetched.emit(now)

            except RuntimeError:
                if not self._closing:
                    raise

        except Exception as error:
            if self._closing:
                return

            try:
                self.bus.error.emit(
                    f"Polling error: {error}"
                )

            except RuntimeError:
                # The signal bus may already be deleted
                # while the application is closing.
                pass

        finally:
            self._fetch_lock.release()


    def _fetch_psu_readings(
        self,
        now: datetime.datetime,
    ) -> None:
        for index, psu in enumerate(self.psus):
            if self._closing:
                return

            reading = psu_read(index)

            if self._closing:
                return

            psu.online = bool(
                reading["online"]
            )

            psu.power_on = bool(
                reading["power_on"]
            )

            psu.voltage_v = float(
                reading["voltage_v"]
            )

            psu.current_a = float(
                reading["current_a"]
            )

            psu.current_hist.append(
                psu.current_a
            )

            psu.voltage_hist.append(
                psu.voltage_v
            )

            psu.time_hist.append(now)

            # Check the latest measured current for a
            # sustained open-fuse condition.
            self._check_open_fuse(
                psu,
                now,
            )

            # The open-fuse handler may have stopped the test.
            # Buffer the measurement only if the test remains active.
            if psu.test_active:
                self._sample_active_test(
                    psu,
                    now,
                )



    def _fetch_chamber_reading(self, now):
        reading = thermocouple_read()

        self.chamber.online = reading["online"]
        self.chamber.temp_c = reading["temp_c"]

        self.chamber.temp_hist.append(self.chamber.temp_c)
        self.chamber.time_hist.append(now)

    def _perform_periodic_save(
        self,
        now: datetime.datetime,
    ) -> None:
        """Save ongoing sessions and flush buffered measurements."""

        try:
            self.store.save_live_state(
                self.psus
            )

        except Exception as error:
            self._log(
                f"Unable to save live test state: "
                f"{error}"
            )

        elapsed_since_flush = (
            now - self._last_db_flush_dt
        ).total_seconds()

        if (
            elapsed_since_flush
            < DB_BATCH_FLUSH_SECONDS
        ):
            return

        try:
            inserted_count = (
                self.store.flush_measurement_buffer()
            )

            self._last_db_flush_dt = now

            if inserted_count:
                print(
                    "SQLite measurement flush: "
                    f"{inserted_count} row(s)"
                )

        except Exception as error:
            self._log(
                f"Unable to flush test measurements: "
                f"{error}"
            )

    def _handle_polling_error(
        self,
        message,
    ):
        self._log(message)

        self.status_bar_widget.set_warning()

    # ==========================================================
    # UI update
    # ==========================================================

    def update_ui(self, now):
        active_count= self.psu_panel_widget.update_channels(self.psus)

        self.header_widget.set_active_count(
            active_count,
            NUM_PSU,
        )

        self.chamber_widget.update_state(
            self.chamber,
            max_points=600,
        )

        self.status_bar_widget.set_last_poll(now.strftime("%H:%M:%S"))
        self.status_bar_widget.set_monitoring()

    # ==========================================================
    # Shutdown
    # ==========================================================

    def closeEvent(self, event) -> None:
        self._closing = True

        # Stop scheduling new polling threads.
        if hasattr(self, "poll_timer"):
            self.poll_timer.stop()

        # If your timer has a different name, stop it too.
        if hasattr(self, "timer"):
            self.timer.stop()

        fetch_thread = self._fetch_thread

        if (
            fetch_thread is not None
            and fetch_thread.is_alive()
            and fetch_thread
            is not threading.current_thread()
        ):
            fetch_thread.join(timeout=12.0)

        try:
            self.store.save_live_state(
                self.psus
            )

            self.store.flush_measurement_buffer()

        except Exception as error:
            print(
                f"Final database save failed: {error}"
            )

        disconnect_psus()

        event.accept()

    def _check_open_fuse(
        self,
        psu,
        now: datetime.datetime,
    ) -> None:
        """
        Detect sustained near-zero measured current during testing.

        The detector is disabled:
        - When no test is active
        - When the PSU is offline
        - When the PSU output is off
        - During the startup grace period
        """

        index = psu.idx

        if not psu.test_active:
            self._open_fuse_low_current_counts[index] = 0
            self._open_fuse_monitor_started_at[index] = None
            self._open_fuse_handling.discard(index)
            return

        if not psu.online or not psu.power_on:
            self._open_fuse_low_current_counts[index] = 0
            return

        if index in self._open_fuse_handling:
            return

        monitor_started_at = (
            self._open_fuse_monitor_started_at[index]
        )

        if monitor_started_at is None:
            self._open_fuse_monitor_started_at[index] = now
            self._open_fuse_low_current_counts[index] = 0
            return

        elapsed_seconds = (
            now - monitor_started_at
        ).total_seconds()

        if (
            elapsed_seconds
            < OPEN_FUSE_STARTUP_GRACE_SECONDS
        ):
            self._open_fuse_low_current_counts[index] = 0
            return

        try:
            measured_current = float(
                psu.current_a
            )

        except (TypeError, ValueError):
            self._open_fuse_low_current_counts[index] = 0
            return

        is_low_current = (
            abs(measured_current)
            <= OPEN_FUSE_CURRENT_THRESHOLD_A
        )

        if not is_low_current:
            self._open_fuse_low_current_counts[index] = 0
            return

        self._open_fuse_low_current_counts[index] += 1

        low_current_count = (
            self._open_fuse_low_current_counts[index]
        )

        print(
            f"PSU {index + 1}: possible open fuse, "
            f"measured current="
            f"{measured_current * 1000:.3f} mA, "
            f"confirmation "
            f"{low_current_count}/"
            f"{OPEN_FUSE_CONSECUTIVE_POLLS}"
        )

        if (
            low_current_count
            < OPEN_FUSE_CONSECUTIVE_POLLS
        ):
            return

        # Prevent another polling cycle from handling the
        # same open-fuse condition again.
        self._open_fuse_handling.add(index)

        self._handle_open_fuse(
            psu=psu,
            measured_current=measured_current,
            detected_at=now,
        )

    def _handle_open_fuse(
        self,
        psu,
        measured_current: float,
        detected_at: datetime.datetime,
    ) -> None:
        """
        Immediately disable the PSU after a confirmed open-fuse
        condition, but preserve the live test for recovery.

        This method runs in the polling worker thread.
        """

        index = psu.idx
        shutdown_error = None

        print(
            f"PSU {index + 1}: OPEN FUSE DETECTED, "
            f"measured current="
            f"{measured_current * 1000:.3f} mA"
        )

        try:
            psu_set_power(
                index,
                False,
            )

        except Exception as error:
            shutdown_error = str(error)

            print(
                f"PSU {index + 1}: output shutdown "
                f"could not be confirmed: {error}"
            )

        # Keep test_active True so the live database session
        # remains recoverable and can be continued.
        psu.power_on = False

        event_note = (
            "OPEN FUSE DETECTED. "
            f"Measured current remained within "
            f"+/-"
            f"{OPEN_FUSE_CURRENT_THRESHOLD_A * 1000:.0f} mA "
            f"for {OPEN_FUSE_CONSECUTIVE_POLLS} consecutive "
            "polling cycles. "
            f"Detected at "
            f"{detected_at.strftime('%Y-%m-%d %H:%M:%S')}. "
            f"Measured current: "
            f"{measured_current * 1000:.3f} mA. "
            "PSU output disabled while waiting for operator action."
        )

        if psu.notes:
            psu.notes = (
                f"{psu.notes}\n\n{event_note}"
            )
        else:
            psu.notes = event_note

        if shutdown_error:
            psu.notes += (
                "\nWarning: physical output shutdown "
                "could not be confirmed: "
                f"{shutdown_error}"
            )

        try:
            # Preserve the latest interrupted state.
            self.store.save_live_state(
                self.psus
            )

            self.store.flush_measurement_buffer()

        except Exception as error:
            print(
                f"PSU {index + 1}: unable to save "
                f"the interrupted live test: {error}"
            )

        event_data = {
            "psu_idx": index,
            "etr_number": psu.etr_number,
            "measured_current": measured_current,
            "detected_at": detected_at,
            "shutdown_error": shutdown_error,
        }

        try:
            self.bus.open_fuse_detected.emit(
                event_data
            )

        except RuntimeError:
            if not self._closing:
                raise

    def _on_open_fuse_detected(
        self,
        event_data: dict,
    ) -> None:
        """
        Open the recovery dialog on the Qt UI thread.
        """

        index = int(
            event_data["psu_idx"]
        )

        psu = self.psus[index]

        measured_current = float(
            event_data["measured_current"]
        )

        psu.power_on = False

        channel = (
            self.psu_panel_widget
            .channel_widgets[index]
        )
        channel.update_state(psu)

        self._log(
            f"OPEN FUSE DETECTED  "
            f"PSU{index + 1}  "
            f"ETR:{psu.etr_number}  "
            f"Current:"
            f"{measured_current * 1000:.3f} mA  "
            "OUTPUT OFF  WAITING FOR OPERATOR"
        )

        dialog = OpenFuseRecoveryDialog(
            parent=self,
            psu=psu,
            measured_current=measured_current,
            on_continue=(
                self._continue_after_open_fuse
            ),
            on_end_test=self._complete_test,
        )

        self._show_dialog(dialog)

    def _continue_after_open_fuse(
        self,
        index: int,
    ) -> None:
        """
        Resume an interrupted test after operator acknowledgement.

        The existing ramp-enabled psu_set_power() is used so the
        PSU never turns on abruptly.
        """

        psu = self.psus[index]

        if not psu.test_active:
            raise RuntimeError(
                "The interrupted test is no longer active."
            )

        if (
            psu.calibrated_voltage is None
            or psu.calibrated_current is None
        ):
            raise RuntimeError(
                "The calibrated voltage or current "
                "is no longer available."
            )

        if UI_TEST_MODE:
            actual_power_state = True

            psu.voltage_v = float(
                psu.calibrated_voltage
            )
            psu.current_a = float(
                psu.calibrated_current
            )

        else:
            actual_power_state = psu_set_power(
                index,
                True,
                target_voltage=float(
                    psu.calibrated_voltage
                ),
                target_current=float(
                    psu.calibrated_current
                ),
                ramp_seconds=(
                    PSU_OUTPUT_RAMP_SECONDS
                ),
            )

        if not actual_power_state:
            raise RuntimeError(
                "The PSU did not confirm that "
                "the output is ON."
            )

        psu.power_on = True

        # Restart the grace period so the current ramp itself
        # cannot retrigger the open-fuse detector.
        restart_time = datetime.datetime.now()

        self._open_fuse_low_current_counts[index] = 0

        self._open_fuse_monitor_started_at[index] = (
            restart_time
        )

        self._open_fuse_handling.discard(index)

        self.store.save_live_state(
            self.psus
        )

        channel = (
            self.psu_panel_widget
            .channel_widgets[index]
        )
        channel.update_state(psu)

        self._log(
            f"TEST CONTINUED  "
            f"PSU{index + 1}  "
            f"ETR:{psu.etr_number}  "
            "OPEN FUSE CONDITION CLEARED  "
            "OUTPUT RAMPED ON"
        )

    @staticmethod
    def _log_open_fuse_to_terminal(
        index: int,
        measured_current: float,
    ) -> None:
        print(
            f"PSU {index + 1}: OPEN FUSE DETECTED, "
            f"measured current="
            f"{measured_current * 1000:.3f} mA"
        )