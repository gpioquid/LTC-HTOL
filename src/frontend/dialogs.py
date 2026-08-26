import datetime
import threading
import csv

import matplotlib.dates as mdates
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QButtonGroup,
    QFileDialog,
    QDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QRadioButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from src.backend.instrument_drivers import psu_set_output, psu_set_power
from src.frontend.ui_styles import (
    ACCENTS,
    FM,
    FMB,
    FML,
    FMS,
    PLOT_BG,
    PLOT_GRID,
    PLOT_TEXT,
    C,
    button_style,
    font,
)


def panel():
    w = QFrame()
    w.setObjectName("panel")
    return w


def label(text, spec=FM, color=None):
    w = QLabel(text)
    w.setFont(font(spec))
    if color:
        w.setStyleSheet(f"color:{color};border:0")
    return w


def style_ax(ax):
    ax.set_facecolor(PLOT_BG)
    [s.set_color(PLOT_GRID) for s in ax.spines.values()]
    ax.tick_params(colors=PLOT_TEXT, labelsize=7)
    ax.grid(True, color=PLOT_GRID, linewidth=0.4, alpha=0.7)


class PSUSetupPopup(QDialog):
    def __init__(
        self,
        parent,
        psu,
        on_continue,
    ):
        super().__init__(parent)

        self.psu = psu
        self.on_continue = on_continue
        self.accent = ACCENTS[psu.idx % len(ACCENTS)]

        self.setWindowTitle(f"PSU{psu.idx + 1} New Test Setup")
        self.resize(550, 430)
        self.setMinimumSize(500, 400)

        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)

        self._build_header(root)
        self._build_inputs(root)
        self._build_buttons(root)

    def _build_header(self, root):
        header = panel()
        layout = QVBoxLayout(header)
        layout.setContentsMargins(12, 10, 12, 10)

        layout.addWidget(
            label(
                f"◈ PSU{self.psu.idx + 1} TEST SETUP",
                FML,
                self.accent,
            )
        )

        description = label(
            "Enter the required test parameters before proceeding to PSU calibration.",
            FMS,
            C["dim"],
        )
        description.setWordWrap(True)

        layout.addWidget(description)
        root.addWidget(header)

    def _build_inputs(self, root):
        input_panel = panel()
        layout = QGridLayout(input_panel)

        layout.setContentsMargins(12, 12, 12, 12)
        layout.setHorizontalSpacing(10)
        layout.setVerticalSpacing(10)

        self.etr_input = QLineEdit()
        self.etr_input.setPlaceholderText("Enter ETR number")

        self.technician_input = QLineEdit()
        self.technician_input.setPlaceholderText("Enter technician name")

        self.target_input = QLineEdit(f"{float(self.psu.target_hrs):g}")

        self.required_voltage_input = QLineEdit()
        self.required_voltage_input.setPlaceholderText("Enter Voltage Rating")

        self.required_current_input = QLineEdit()
        self.required_current_input.setPlaceholderText("Enter Current Rating")

        layout.addWidget(
            label("ETR NUMBER:", FMS, C["dim"]),
            0,
            0,
        )
        layout.addWidget(self.etr_input, 0, 1)

        layout.addWidget(
            label("TECHNICIAN:", FMS, C["dim"]),
            1,
            0,
        )
        layout.addWidget(self.technician_input, 1, 1)

        layout.addWidget(
            label("TARGET HOURS:", FMS, C["dim"]),
            2,
            0,
        )
        layout.addWidget(self.target_input, 2, 1)

        layout.addWidget(
            label("REQUIRED VOLTAGE:", FMS, C["dim"]),
            3,
            0,
        )
        layout.addWidget(self.required_voltage_input, 3, 1)
        layout.addWidget(label("V"), 3, 2)

        layout.addWidget(
            label("REQUIRED CURRENT:", FMS, C["dim"]),
            4,
            0,
        )
        layout.addWidget(self.required_current_input, 4, 1)
        layout.addWidget(label("A"), 4, 2)

        root.addWidget(input_panel)

    def _build_buttons(self, root):
        layout = QHBoxLayout()

        continue_button = QPushButton("CONTINUE TO CALIBRATION")
        continue_button.setStyleSheet(button_style(self.accent))
        continue_button.clicked.connect(self._continue_to_calibration)

        cancel_button = QPushButton("CANCEL")
        cancel_button.clicked.connect(self.reject)

        layout.addStretch()
        layout.addWidget(continue_button)
        layout.addWidget(cancel_button)

        root.addLayout(layout)

    def _continue_to_calibration(self):
        try:
            etr_number = self.etr_input.text().strip()
            technician = self.technician_input.text().strip()

            target_hours = float(self.target_input.text())
            required_voltage = float(self.required_voltage_input.text())
            required_current = float(self.required_current_input.text())

            if not etr_number:
                raise ValueError("Enter an ETR number.")

            if not technician:
                raise ValueError("Enter the technician name.")

            if target_hours <= 0:
                raise ValueError("Target hours must be greater than zero.")

            if required_voltage < 0:
                raise ValueError("Required voltage cannot be negative.")

            if required_current < 0:
                raise ValueError("Required current cannot be negative.")

        except ValueError as error:
            QMessageBox.warning(
                self,
                "Invalid Test Setup",
                str(error),
            )
            return

        # Save the original required test parameters.
        self.psu.etr_number = etr_number
        self.psu.technician = technician
        self.psu.target_hrs = target_hours
        self.psu.set_voltage = required_voltage
        self.psu.set_current = required_current

        self.on_continue(self.psu.idx)
        self.accept()


class PSUCalibrationPopup(QDialog):
    def __init__(
        self,
        parent,
        psu,
        on_test_started,
        ui_test_mode: bool = False,
    ):
        super().__init__(parent)

        self.psu = psu
        self.on_test_started = on_test_started
        self.ui_test_mode = ui_test_mode
        self.accent = ACCENTS[psu.idx % len(ACCENTS)]

        self.setWindowTitle(f"PSU{psu.idx + 1} Calibration")
        self.resize(620, 520)
        self.setMinimumSize(560, 470)

        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)

        self._build_header(root)
        self._build_required_values(root)
        self._build_calibration_controls(root)
        self._build_readback(root)
        self._build_actions(root)

        self.refresh_timer = QTimer(self)
        self.refresh_timer.timeout.connect(self._refresh_readback)
        self.refresh_timer.start(500)

        self._refresh_readback()

    def _build_header(self, root):
        header = panel()
        layout = QVBoxLayout(header)
        layout.setContentsMargins(12, 10, 12, 10)

        layout.addWidget(
            label(
                f"◈ PSU{self.psu.idx + 1} CALIBRATION",
                FML,
                self.accent,
            )
        )

        description = label(
            "Adjust the PSU command values and enable the output. "
            "Verify the actual electronic parameters before starting.",
            FMS,
            C["dim"],
        )
        description.setWordWrap(True)

        layout.addWidget(description)
        root.addWidget(header)

    def _build_required_values(self, root):
        required_panel = panel()
        layout = QGridLayout(required_panel)

        layout.setContentsMargins(12, 10, 12, 10)
        layout.setHorizontalSpacing(20)
        layout.setVerticalSpacing(6)

        layout.addWidget(
            label("ETR NUMBER", FMS, C["dim"]),
            0,
            0,
        )
        layout.addWidget(
            label("TECHNICIAN", FMS, C["dim"]),
            0,
            1,
        )
        layout.addWidget(
            label("REQUIRED PARAMETERS", FMS, C["dim"]),
            0,
            2,
        )

        layout.addWidget(
            label(self.psu.etr_number, FMB, self.accent),
            1,
            0,
        )
        layout.addWidget(
            label(self.psu.technician, FMB, self.accent),
            1,
            1,
        )
        layout.addWidget(
            label(
                f"{self.psu.set_voltage:.2f} V / {self.psu.set_current:.2f} A",
                FMB,
                self.accent,
            ),
            1,
            2,
        )

        root.addWidget(required_panel)

    def _build_calibration_controls(self, root):
        controls_panel = panel()
        layout = QGridLayout(controls_panel)

        layout.setContentsMargins(12, 12, 12, 12)
        layout.setHorizontalSpacing(10)
        layout.setVerticalSpacing(10)

        initial_voltage = (
            self.psu.calibrated_voltage
            if self.psu.calibrated_voltage is not None
            else self.psu.set_voltage
        )

        initial_current = (
            self.psu.calibrated_current
            if self.psu.calibrated_current is not None
            else self.psu.set_current
        )

        self.voltage_input = QLineEdit()
        self.voltage_input.setPlaceholderText("Enter Voltage")

        self.current_input = QLineEdit()
        self.current_input.setPlaceholderText("Enter Current")

        layout.addWidget(
            label("PSU VOLTAGE COMMAND:", FMS, C["dim"]),
            0,
            0,
        )
        layout.addWidget(self.voltage_input, 0, 1)
        layout.addWidget(label("V"), 0, 2)

        layout.addWidget(
            label("PSU CURRENT COMMAND:", FMS, C["dim"]),
            1,
            0,
        )
        layout.addWidget(self.current_input, 1, 1)
        layout.addWidget(label("A"), 1, 2)

        self.apply_button = QPushButton("APPLY CALIBRATION VALUES")
        self.apply_button.setStyleSheet(button_style(self.accent))
        self.apply_button.clicked.connect(self._apply_calibration_values)

        layout.addWidget(
            self.apply_button,
            2,
            0,
            1,
            3,
        )

        root.addWidget(controls_panel)

    def _build_readback(self, root):
        readback_panel = panel()
        layout = QGridLayout(readback_panel)

        layout.setContentsMargins(12, 10, 12, 10)
        layout.setHorizontalSpacing(20)
        layout.setVerticalSpacing(6)

        layout.addWidget(
            label("MEASURED VOLTAGE", FMS, C["dim"]),
            0,
            0,
        )
        layout.addWidget(
            label("MEASURED CURRENT", FMS, C["dim"]),
            0,
            1,
        )
        layout.addWidget(
            label("OUTPUT STATE", FMS, C["dim"]),
            0,
            2,
        )

        self.voltage_readback = label(
            "0.00 V",
            FMB,
            self.accent,
        )
        self.current_readback = label(
            "0.00 A",
            FMB,
            self.accent,
        )
        self.output_readback = label(
            "OFF",
            FMB,
            C["dim"],
        )

        layout.addWidget(self.voltage_readback, 1, 0)
        layout.addWidget(self.current_readback, 1, 1)
        layout.addWidget(self.output_readback, 1, 2)

        self.status_label = label(
            "Apply calibration values before enabling the output.",
            FMS,
            C["dim"],
        )

        layout.addWidget(
            self.status_label,
            2,
            0,
            1,
            3,
        )

        root.addWidget(readback_panel)

    def _build_actions(self, root):
        layout = QHBoxLayout()

        self.output_button = QPushButton("TURN OUTPUT ON")
        self.output_button.clicked.connect(self._toggle_output)

        self.start_button = QPushButton("START TEST")
        self.start_button.setStyleSheet(button_style(C["green"]))
        self.start_button.clicked.connect(self._start_test)

        cancel_button = QPushButton("CANCEL")
        cancel_button.clicked.connect(self.reject)

        layout.addWidget(self.output_button)
        layout.addStretch()
        layout.addWidget(self.start_button)
        layout.addWidget(cancel_button)

        root.addLayout(layout)

    def _apply_calibration_values(self) -> None:
        try:
            voltage_text = self.voltage_input.text().strip()
            current_text = self.current_input.text().strip()

            if not voltage_text:
                raise ValueError(
                    "Enter a calibration voltage."
                )

            if not current_text:
                raise ValueError(
                    "Enter a calibration current."
                )

            voltage = float(voltage_text)
            current = float(current_text)

            if voltage < 0:
                raise ValueError(
                    "Calibration voltage cannot be negative."
                )

            if current < 0:
                raise ValueError(
                    "Calibration current cannot be negative."
                )

            print(
                f"PSU {self.psu.idx + 1}: "
                f"UI Test Mode = {self.ui_test_mode}"
            )

            print(
                f"PSU {self.psu.idx + 1}: "
                f"applying calibration values "
                f"{voltage:.3f} V / {current:.3f} A"
            )

            if self.ui_test_mode:
                result = {
                    "success": True,
                    "voltage": voltage,
                    "current": current,
                }
            else:
                result = psu_set_output(
                    self.psu.idx,
                    voltage,
                    current,
                )

        except ValueError as error:
            QMessageBox.warning(
                self,
                "Invalid Calibration Values",
                str(error),
            )
            return

        except Exception as error:
            print(
                f"PSU {self.psu.idx + 1} "
                f"calibration failed: {error!r}"
            )

            QMessageBox.critical(
                self,
                "Calibration Error",
                (
                    "Unable to apply calibration values.\n\n"
                    f"{type(error).__name__}: {error}"
                ),
            )
            return

        self.psu.calibrated_voltage = float(
            result["voltage"]
        )
        self.psu.calibrated_current = float(
            result["current"]
        )

        self.psu.calibration_active = True
        self.psu.calibration_complete = False

        self.status_label.setText(
            "Calibration values applied: "
            f"{self.psu.calibrated_voltage:.3f} V / "
            f"{self.psu.calibrated_current:.3f} A"
        )

        self.status_label.setStyleSheet(
            f"color: {C['green']}; border: 0;"
        )

        print(
            f"PSU {self.psu.idx + 1}: "
            "calibration values applied successfully"
        )

    def _toggle_output(self):
        if self.psu.calibrated_voltage is None or self.psu.calibrated_current is None:
            QMessageBox.warning(
                self,
                "Calibration Values Not Applied",
                "Apply the calibration voltage and current first.",
            )
            return

        requested_state = not self.psu.power_on

        try:
            if self.ui_test_mode:
                actual_state = requested_state
            else:
                actual_state = psu_set_power(
                    self.psu.idx,
                    requested_state,
                )

        except Exception as error:
            QMessageBox.critical(
                self,
                "Output Control Error",
                f"Unable to control the PSU output:\n{error}",
            )
            return

        self.psu.power_on = actual_state

        if self.ui_test_mode and actual_state:
            self.psu.voltage_v = float(self.psu.calibrated_voltage)
            self.psu.current_a = float(self.psu.calibrated_current)

        elif self.ui_test_mode:
            self.psu.voltage_v = 0.0
            self.psu.current_a = 0.0

        self.output_button.setText(
            "TURN OUTPUT OFF" if actual_state else "TURN OUTPUT ON"
        )

        self._refresh_readback()

    def _refresh_readback(self):
        self.voltage_readback.setText(f"{self.psu.voltage_v:.2f} V")
        self.current_readback.setText(f"{self.psu.current_a:.2f} A")

        if self.psu.power_on:
            self.output_readback.setText("ON")
            self.output_readback.setStyleSheet(f"color: {C['green']}; border: 0;")
            self.output_button.setText("TURN OUTPUT OFF")
        else:
            self.output_readback.setText("OFF")
            self.output_readback.setStyleSheet(f"color: {C['dim']}; border: 0;")
            self.output_button.setText("TURN OUTPUT ON")

    def _start_test(self) -> None:
        if (
            self.psu.calibrated_voltage is None
            or self.psu.calibrated_current is None
        ):
            QMessageBox.warning(
                self,
                "Calibration Incomplete",
                "Apply the final calibration values before starting the test.",
            )
            return

        calibrated_voltage = float(
            self.psu.calibrated_voltage
        )
        calibrated_current = float(
            self.psu.calibrated_current
        )

        try:
            if self.ui_test_mode:
                # Simulate reapplying the final calibrated values.
                self.psu.voltage_v = calibrated_voltage
                self.psu.current_a = calibrated_current

                actual_power_state = True

            else:
                # Reapply the final calibrated values even if the
                # output was turned OFF after calibration.
                result = psu_set_output(
                    self.psu.idx,
                    calibrated_voltage,
                    calibrated_current,
                )

                self.psu.calibrated_voltage = float(
                    result["voltage"]
                )
                self.psu.calibrated_current = float(
                    result["current"]
                )

                # START TEST must always turn the output back ON.
                actual_power_state = psu_set_power(
                    self.psu.idx,
                    True,
                )

                if not actual_power_state:
                    raise RuntimeError(
                        "The PSU output could not be turned ON."
                    )

        except Exception as error:
            QMessageBox.critical(
                self,
                "Test Startup Error",
                (
                    "Unable to start the test with the "
                    "PSU output enabled.\n\n"
                    f"{error}"
                ),
            )
            return

        # Update the application state only after the PSU
        # commands have completed successfully.
        self.psu.online = True
        self.psu.power_on = True
        self.psu.fault = False

        self.psu.calibration_active = False
        self.psu.calibration_complete = True

        self.psu.test_active = True
        self.psu.test_start_dt = datetime.datetime.now()
        self.psu.hours_elapsed = 0.0
        self.psu.last_db_sample_dt = None

        self.output_readback.setText("ON")
        self.output_button.setText("TURN OUTPUT OFF")

        self.on_test_started(
            self.psu.idx
        )

        self.accept()

    def reject(self) -> None:
        if (
            self.psu.calibration_active
            and not self.psu.test_active
        ):
            try:
                if self.ui_test_mode:
                    self.psu.power_on = False
                    self.psu.voltage_v = 0.0
                    self.psu.current_a = 0.0
                else:
                    self.psu.power_on = psu_set_power(
                        self.psu.idx,
                        False,
                    )

            except Exception as error:
                QMessageBox.critical(
                    self,
                    "Output Shutdown Error",
                    (
                        "Unable to turn off the calibration "
                        f"output.\n\n{error}"
                    ),
                )
                return

            self.psu.calibration_active = False

        super().reject()


class PSUDetailPopup(QDialog):
    def __init__(self, parent, psu, chamber, on_apply, on_ui_test_complete=None):
        super().__init__(parent)

        self.psu = psu
        self.chamber = chamber
        self.on_apply = on_apply
        self.on_ui_test_complete = on_ui_test_complete
        self.configuration_unlocked = False
        self.accent = ACCENTS[psu.idx % len(ACCENTS)]

        self.setWindowTitle(f"PSU{psu.idx + 1} Test Session")
        self.resize(920, 700)
        self.setMinimumSize(700, 500)

        root = QVBoxLayout(self)
        root.setContentsMargins(10, 10, 10, 10)
        root.setSpacing(6)

        self._build_header(root)
        self._build_settings(root)
        self._build_statistics(root)
        self._build_notes(root)
        self._build_charts(root)
        self._build_action_buttons(root)

        # Connect range buttons only after every UI element exists.
        for button in self.ranges.values():
            button.toggled.connect(self._on_range_changed)

        self.ranges["Live"].setChecked(True)
        self.refresh()

        # Refresh the ongoing-test dialog using the latest PSUState values.
        self.refresh_timer = QTimer(self)
        self.refresh_timer.timeout.connect(self.refresh)
        self.refresh_timer.start(1000)

    def closeEvent(self, event) -> None:
        if hasattr(self, "refresh_timer"):
            self.refresh_timer.stop()

        super().closeEvent(event)

    def accept(self) -> None:
        if hasattr(self, "refresh_timer"):
            self.refresh_timer.stop()

        super().accept()

    def _build_settings(self, root) -> None:
        settings_panel = panel()

        layout = QGridLayout(settings_panel)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setHorizontalSpacing(10)
        layout.setVerticalSpacing(8)

        # Section heading and lock status
        settings_title = label(
            "TEST CONFIGURATION",
            FMS,
            C["dim"],
        )

        self.configuration_lock_label = label(
            "LOCKED",
            FMS,
            C["green"],
        )
        self.configuration_lock_label.setAlignment(
            Qt.AlignmentFlag.AlignRight
            | Qt.AlignmentFlag.AlignVCenter
        )

        layout.addWidget(settings_title, 0, 0, 1, 2)
        layout.addWidget(
            self.configuration_lock_label,
            0,
            2,
            1,
            3,
        )

        # Configuration fields
        self.etr_input = QLineEdit(
            self.psu.etr_number
        )

        self.technician_input = QLineEdit(
            self.psu.technician
        )

        self.target_input = QLineEdit(
            f"{self.psu.target_hrs:g}"
        )

        self.voltage_input = QLineEdit(
            f"{float(self.psu.set_voltage or 0.0):.3f}"
        )

        self.current_input = QLineEdit(
            f"{float(self.psu.set_current or 0.0):.3f}"
        )

        layout.addWidget(
            label("ETR NUMBER:", FMS, C["dim"]),
            1,
            0,
        )
        layout.addWidget(
            self.etr_input,
            1,
            1,
        )

        layout.addWidget(
            label("TECHNICIAN:", FMS, C["dim"]),
            1,
            2,
        )
        layout.addWidget(
            self.technician_input,
            1,
            3,
            1,
            2,
        )

        layout.addWidget(
            label("TARGET HOURS:", FMS, C["dim"]),
            2,
            0,
        )
        layout.addWidget(
            self.target_input,
            2,
            1,
        )

        layout.addWidget(
            label("REQUIRED VOLTAGE:", FMS, C["dim"]),
            2,
            2,
        )
        layout.addWidget(
            self.voltage_input,
            2,
            3,
        )
        layout.addWidget(
            label("V", FMS, C["dim"]),
            2,
            4,
        )

        layout.addWidget(
            label("REQUIRED CURRENT:", FMS, C["dim"]),
            3,
            2,
        )
        layout.addWidget(
            self.current_input,
            3,
            3,
        )
        layout.addWidget(
            label("A", FMS, C["dim"]),
            3,
            4,
        )

        self.configuration_fields = [
            self.etr_input,
            self.technician_input,
            self.target_input,
            self.voltage_input,
            self.current_input,
        ]

        self.apply_status = label(
            "The active test configuration is locked.",
            FMS,
            C["dim"],
        )

        layout.addWidget(
            self.apply_status,
            4,
            0,
            1,
            5,
        )

        root.addWidget(settings_panel)

        # Lock fields after every widget has been created.
        self._set_configuration_locked(True)

    def _build_action_buttons(self, root) -> None:
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # Available only when UI Test Mode supplies a callback.
        self.ui_test_complete_button = QPushButton(
            "UI TEST MODE: COMPLETE TEST"
        )
        self.ui_test_complete_button.clicked.connect(
            self._ui_test_complete_test
        )
        self.ui_test_complete_button.setVisible(
            self.on_ui_test_complete is not None
        )

        self.lock_button = QPushButton(
            "EDIT TEST PARAMETERS"
        )
        self.lock_button.clicked.connect(
            self._toggle_configuration_lock
        )

        self.apply_button = QPushButton(
            "APPLY CHANGES"
        )
        self.apply_button.setStyleSheet(
            button_style(self.accent)
        )
        self.apply_button.clicked.connect(
            self._apply_settings
        )
        self.apply_button.setEnabled(False)

        refresh_button = QPushButton("REFRESH")
        refresh_button.clicked.connect(
            self.refresh
        )

        close_button = QPushButton("CLOSE")
        close_button.clicked.connect(
            self.close
        )

        # UI Test Mode action stays on the left.
        layout.addWidget(
            self.ui_test_complete_button
        )

        layout.addStretch()

        layout.addWidget(self.lock_button)
        layout.addWidget(self.apply_button)
        layout.addWidget(refresh_button)
        layout.addWidget(close_button)

        root.addLayout(layout)


    def _ui_test_complete_test(self) -> None:
        if self.on_ui_test_complete is None:
            return

        response = QMessageBox.warning(
            self,
            "UI Test Mode: Complete Test",
            (
                "UI Test Mode will fast-forward this test "
                "to its configured target duration.\n\n"
                "The normal test completion dialog will "
                "open afterward.\n\n"
                "No command will be sent to a physical PSU.\n\n"
                "Continue?"
            ),
            QMessageBox.StandardButton.Yes
            | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if response != QMessageBox.StandardButton.Yes:
            return

        psu_index = self.psu.idx

        # Close the test-session dialog first.
        self.accept()

        # Ask the main window to fast-forward and open
        # the normal completion dialog.
        self.on_ui_test_complete(psu_index)

    def _set_configuration_locked(
        self,
        locked: bool,
    ) -> None:
        self.configuration_unlocked = not locked

        for field in self.configuration_fields:
            field.setReadOnly(locked)

        if locked:
            self.configuration_lock_label.setText(
                "LOCKED"
            )
            self.configuration_lock_label.setStyleSheet(
                f"color: {C['green']}; border: none;"
            )

            if hasattr(self, "lock_button"):
                self.lock_button.setText(
                    "EDIT TEST PARAMETERS"
                )

            if hasattr(self, "apply_button"):
                self.apply_button.setEnabled(False)

        else:
            self.configuration_lock_label.setText(
                "EDITING ENABLED"
            )
            self.configuration_lock_label.setStyleSheet(
                f"color: {C['yellow']}; border: none;"
            )

            self.lock_button.setText(
                "CANCEL EDITING"
            )
            self.apply_button.setEnabled(True)

    def _toggle_configuration_lock(self) -> None:
        if self.configuration_unlocked:
            self._restore_configuration_fields()
            self._set_configuration_locked(True)

            self.apply_status.setText(
                "Changes discarded. Configuration locked."
            )
            self.apply_status.setStyleSheet(
                f"color: {C['dim']}; border: none;"
            )
            return

        response = QMessageBox.warning(
            self,
            "Unlock Active Test Configuration",
            (
                "This test is currently active.\n\n"
                "Editing the ETR number, technician, target hours, "
                "required voltage, or required current will modify "
                "the stored test record.\n\n"
                "This action will not change the calibrated PSU "
                "voltage/current or the physical PSU output.\n\n"
                "Do you want to unlock the configuration?"
            ),
            QMessageBox.StandardButton.Yes
            | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if response != QMessageBox.StandardButton.Yes:
            return

        self._set_configuration_locked(False)

        self.apply_status.setText(
            "Editing enabled. Review all values before applying."
        )
        self.apply_status.setStyleSheet(
            f"color: {C['yellow']}; border: none;"
        )

    def _restore_configuration_fields(self) -> None:
        self.etr_input.setText(
            self.psu.etr_number
        )

        self.technician_input.setText(
            self.psu.technician
        )

        self.target_input.setText(
            f"{self.psu.target_hrs:g}"
        )

        self.voltage_input.setText(
            f"{float(self.psu.set_voltage or 0.0):.3f}"
        )

        self.current_input.setText(
            f"{float(self.psu.set_current or 0.0):.3f}"
        )

    def _apply_settings(self) -> None:
        if not self.configuration_unlocked:
            QMessageBox.information(
                self,
                "Configuration Locked",
                "Unlock the configuration before making changes.",
            )
            return

        etr_number = self.etr_input.text().strip()
        technician = self.technician_input.text().strip()

        try:
            if not etr_number:
                raise ValueError(
                    "ETR number cannot be empty."
                )

            if not technician or technician == "—":
                raise ValueError(
                    "Technician cannot be empty."
                )

            target_hours = float(
                self.target_input.text().strip()
            )

            required_voltage = float(
                self.voltage_input.text().strip()
            )

            required_current = float(
                self.current_input.text().strip()
            )

            if target_hours <= 0:
                raise ValueError(
                    "Target hours must be greater than zero."
                )

            if required_voltage < 0:
                raise ValueError(
                    "Required voltage cannot be negative."
                )

            if required_current < 0:
                raise ValueError(
                    "Required current cannot be negative."
                )

        except ValueError as error:
            QMessageBox.warning(
                self,
                "Invalid Test Configuration",
                str(error),
            )
            return

        response = QMessageBox.warning(
            self,
            "Apply Active Test Changes",
            (
                "The following active test configuration will be "
                "updated:\n\n"
                f"ETR: {etr_number}\n"
                f"Technician: {technician}\n"
                f"Target: {target_hours:g} h\n"
                f"Required voltage: {required_voltage:.3f} V\n"
                f"Required current: {required_current:.3f} A\n\n"
                "The calibrated PSU values and physical output will "
                "remain unchanged.\n\n"
                "Apply these changes?"
            ),
            QMessageBox.StandardButton.Yes
            | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if response != QMessageBox.StandardButton.Yes:
            return

        # Update the active test state.
        self.psu.etr_number = etr_number
        self.psu.technician = technician
        self.psu.target_hrs = target_hours
        self.psu.set_voltage = required_voltage
        self.psu.set_current = required_current

        # Notify the main window so the machine card and saved
        # state are updated.
        self.on_apply(
            self.psu.idx,
            etr_number,
            technician,
            target_hours,
            required_voltage,
            required_current,
        )

        self._set_configuration_locked(True)

        self.apply_status.setText(
            "Configuration updated and locked."
        )
        self.apply_status.setStyleSheet(
            f"color: {C['green']}; border: none;"
        )

        self.setWindowTitle(
            f"PSU{self.psu.idx + 1} · "
            f"{self.psu.etr_number} · Test Session"
        )

        self.refresh()

    def _build_header(self, root):
        header = panel()

        layout = QHBoxLayout(header)
        layout.setContentsMargins(
            12,
            8,
            12,
            8,
        )
        layout.setSpacing(8)

        layout.addWidget(
            label(
                f"◈ PSU{self.psu.idx + 1} · {self.psu.etr_number}",
                FML,
                self.accent,
            )
        )

        layout.addWidget(
            label(
                f"TECH: {self.psu.technician}",
                FM,
                C["dim"],
            )
        )

        layout.addStretch()

        layout.addWidget(
            label(
                "RANGE:",
                FMS,
                C["dim"],
            )
        )

        self.group = QButtonGroup(self)
        self.group.setExclusive(True)

        self.ranges = {}

        for option in (
            "Live",
            "1h",
            "6h",
            "24h",
            "All",
        ):
            button = QRadioButton(option)

            self.group.addButton(button)
            self.ranges[option] = button

            layout.addWidget(button)

        root.addWidget(header)

    def _build_statistics(self, root):
        statistics_panel = panel()

        layout = QGridLayout(statistics_panel)
        layout.setContentsMargins(
            12,
            8,
            12,
            8,
        )
        layout.setHorizontalSpacing(12)
        layout.setVerticalSpacing(6)

        self.stat = {}

        statistics = [
            (
                "HOURS ON",
                f"{self.psu.hours_elapsed:.2f} h",
                self.accent,
            ),
            (
                "TARGET",
                f"{self.psu.target_hrs} h",
                C["yellow"],
            ),
            (
                "PROGRESS",
                f"{self.psu.progress_pct:.1f}%",
                self.accent,
            ),
            (
                "CURRENT",
                f"{self.psu.current_a:.3f} A",
                self.accent,
            ),
            (
                "VOLTAGE",
                f"{self.psu.voltage_v:.3f} V",
                C["text"],
            ),
            (
                "STATUS",
                self.psu.status_str,
                self.psu.status_color,
            ),
        ]

        for column, (
            name,
            value,
            value_color,
        ) in enumerate(statistics):
            heading = label(
                name,
                FMS,
                C["dim"],
            )
            heading.setAlignment(Qt.AlignmentFlag.AlignCenter)

            value_label = label(
                value,
                FMB,
                value_color,
            )
            value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

            layout.addWidget(
                heading,
                0,
                column,
            )
            layout.addWidget(
                value_label,
                1,
                column,
            )

            self.stat[name] = value_label

        self.on_range = label(
            "ON-TIME IN RANGE: — h",
            FM,
            C["cyan"],
        )

        layout.addWidget(
            self.on_range,
            2,
            0,
            1,
            len(statistics),
        )

        root.addWidget(statistics_panel)

    def _build_notes(self, root):
        notes_panel = panel()

        layout = QHBoxLayout(notes_panel)
        layout.setContentsMargins(
            12,
            6,
            12,
            6,
        )
        layout.setSpacing(8)

        layout.addWidget(
            label(
                "NOTES:",
                FMS,
                C["dim"],
            )
        )

        self.notes = label(
            self.psu.notes or "—",
            FMS,
            C["text"],
        )
        self.notes.setWordWrap(True)

        layout.addWidget(self.notes, 1)

        root.addWidget(notes_panel)

    def _build_charts(self, root):
        self.fig = Figure(
            figsize=(7, 4),
            dpi=96,
            facecolor=PLOT_BG,
        )

        self.fig.subplots_adjust(
            left=0.09,
            right=0.97,
            top=0.94,
            bottom=0.11,
            hspace=0.42,
        )

        self.a1 = self.fig.add_subplot(211)
        self.a2 = self.fig.add_subplot(212)

        style_ax(self.a1)
        style_ax(self.a2)

        self.a1.set_title(
            f"PSU{self.psu.idx + 1} Current",
            color=self.accent,
            fontsize=9,
            loc="left",
        )
        self.a1.set_ylabel(
            "Current (A)",
            color=PLOT_TEXT,
            fontsize=8,
        )

        self.a2.set_title(
            "Chamber Temperature",
            color=C["orange"],
            fontsize=9,
            loc="left",
        )
        self.a2.set_ylabel(
            "Temperature (°C)",
            color=PLOT_TEXT,
            fontsize=8,
        )

        (self.l1,) = self.a1.plot(
            [],
            [],
            color=self.accent,
            linewidth=1.5,
        )

        (self.l2,) = self.a2.plot(
            [],
            [],
            color=C["orange"],
            linewidth=1.5,
        )

        self.canvas = FigureCanvasQTAgg(self.fig)

        root.addWidget(self.canvas, 1)

    def _build_refresh_button(self, root):
        refresh_button = QPushButton("↻ REFRESH")
        refresh_button.setStyleSheet(button_style(self.accent))
        refresh_button.clicked.connect(self.refresh)

        root.addWidget(
            refresh_button,
            0,
            Qt.AlignmentFlag.AlignHCenter,
        )

    def _on_range_changed(self, checked):
        """
        Refresh only when a range button becomes checked.

        Switching radio buttons emits one false signal for the
        previous button and one true signal for the new button.
        """
        if checked:
            self.refresh()

    @staticmethod
    def _normalize_datetime(value):
        """
        Convert an aware datetime to a naive datetime.

        Current application history uses naive local datetime
        objects. This also supports aware datetime objects that
        may remain in memory from an earlier application version.
        """
        if not isinstance(
            value,
            datetime.datetime,
        ):
            return None

        if value.tzinfo is not None:
            return value.replace(tzinfo=None)

        return value

    def _selected_range(self):
        for name, button in self.ranges.items():
            if button.isChecked():
                return name

        return "Live"

    def _range_cutoff(self):
        now = datetime.datetime.now()
        selected_range = self._selected_range()

        cutoff_by_range = {
            "Live": (now - datetime.timedelta(minutes=15)),
            "1h": (now - datetime.timedelta(hours=1)),
            "6h": (now - datetime.timedelta(hours=6)),
            "24h": (now - datetime.timedelta(hours=24)),
            "All": datetime.datetime.min,
        }

        return cutoff_by_range[selected_range]

    def _filter_history(
        self,
        times,
        values,
        cutoff,
    ):
        filtered_points = []

        for timestamp, value in zip(
            times,
            values,
            strict=False,
        ):
            normalized_timestamp = self._normalize_datetime(timestamp)

            if normalized_timestamp is None:
                continue

            if normalized_timestamp >= cutoff:
                filtered_points.append(
                    (
                        normalized_timestamp,
                        value,
                    )
                )

        return filtered_points

    def _get_poll_seconds(self):
        times = list(self.psu.time_hist)

        if len(times) < 2:
            return 1.0

        first = self._normalize_datetime(times[-2])
        second = self._normalize_datetime(times[-1])

        if first is None or second is None:
            return 1.0

        interval = (second - first).total_seconds()

        if interval <= 0:
            return 1.0

        return interval

    @staticmethod
    def _calculate_on_time_hours(
        current_points,
        default_interval,
    ):
        if not current_points:
            return 0.0

        on_time_seconds = 0.0

        for index, (
            timestamp,
            current,
        ) in enumerate(current_points):
            if current <= 0:
                continue

            if index == 0:
                interval_seconds = default_interval
            else:
                previous_timestamp = current_points[index - 1][0]

                interval_seconds = (timestamp - previous_timestamp).total_seconds()

                if interval_seconds <= 0:
                    interval_seconds = default_interval

            on_time_seconds += interval_seconds

        return on_time_seconds / 3600

    def _update_statistics(self):
        psu = self.psu

        self.stat["HOURS ON"].setText(f"{psu.hours_elapsed:.2f} h")
        self.stat["TARGET"].setText(f"{psu.target_hrs} h")
        self.stat["PROGRESS"].setText(f"{psu.progress_pct:.1f}%")
        self.stat["CURRENT"].setText(f"{psu.current_a:.3f} A")
        self.stat["VOLTAGE"].setText(f"{psu.voltage_v:.3f} V")

        self.stat["STATUS"].setText(psu.status_str)
        self.stat["STATUS"].setStyleSheet(
            f"""
            QLabel {{
                color: {psu.status_color};
                background: {C["tile_bg"]};
                border: 1px solid
                    {psu.status_color};
                border-radius: 4px;
                padding: 3px 7px;
            }}
            """
        )

        self.notes.setText(psu.notes or "—")

    def _update_charts(
        self,
        current_points,
        temperature_points,
    ):
        current_times = [timestamp for timestamp, _ in current_points]
        current_values = [value for _, value in current_points]

        temperature_times = [timestamp for timestamp, _ in temperature_points]
        temperature_values = [value for _, value in temperature_points]

        self.l1.set_data(
            current_times,
            current_values,
        )
        self.l2.set_data(
            temperature_times,
            temperature_values,
        )

        for axis in (self.a1, self.a2):
            axis.relim()
            axis.autoscale_view()

            axis.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M:%S"))

        self.canvas.draw_idle()

    def refresh(self):
        self._update_statistics()

        cutoff = self._range_cutoff()

        current_points = self._filter_history(
            self.psu.time_hist,
            self.psu.current_hist,
            cutoff,
        )

        temperature_points = self._filter_history(
            self.chamber.time_hist,
            self.chamber.temp_hist,
            cutoff,
        )

        self._update_charts(
            current_points,
            temperature_points,
        )

        poll_seconds = self._get_poll_seconds()

        on_time_hours = self._calculate_on_time_hours(
            current_points,
            poll_seconds,
        )

        self.on_range.setText(f"ON-TIME IN RANGE: {on_time_hours:.3f} h")


class CompleteTestDialog(QDialog):
    def __init__(
        self,
        parent,
        psu,
        chamber,
        store,
        on_complete,
    ):
        super().__init__(parent)

        self.psu = psu
        self.chamber = chamber
        self.store = store
        self.on_complete = on_complete
        self.accent = ACCENTS[
            psu.idx % len(ACCENTS)
        ]

        self.setWindowTitle(
            f"Complete Test - "
            f"PSU{psu.idx + 1} / "
            f"{psu.etr_number}"
        )
        self.resize(520, 520)
        self.setMinimumSize(480, 460)

        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)

        # Header
        root.addWidget(
            label(
                "◈  COMPLETE TEST SESSION",
                FML,
                self.accent,
            )
        )

        # High-level test summary
        summary_panel = panel()
        summary_layout = QGridLayout(summary_panel)
        summary_layout.setContentsMargins(
            12,
            10,
            12,
            10,
        )
        summary_layout.setHorizontalSpacing(18)
        summary_layout.setVerticalSpacing(7)

        average_current = (
            sum(psu.current_hist)
            / len(psu.current_hist)
            if psu.current_hist
            else 0.0
        )

        average_voltage = (
            sum(psu.voltage_hist)
            / len(psu.voltage_hist)
            if psu.voltage_hist
            else 0.0
        )

        average_temperature = (
            sum(chamber.temp_hist)
            / len(chamber.temp_hist)
            if chamber.temp_hist
            else 0.0
        )

        started_at = (
            psu.test_start_dt.strftime(
                "%Y-%m-%d %H:%M:%S"
            )
            if psu.test_start_dt
            else "—"
        )

        calibrated_voltage = (
            f"{psu.calibrated_voltage:.3f} V"
            if psu.calibrated_voltage is not None
            else "—"
        )

        calibrated_current = (
            f"{psu.calibrated_current:.3f} A"
            if psu.calibrated_current is not None
            else "—"
        )

        rows = [
            (
                "ETR Number",
                psu.etr_number or "—",
            ),
            (
                "Technician",
                psu.technician or "—",
            ),
            (
                "Started At",
                started_at,
            ),
            (
                "Test Duration",
                f"{psu.hours_elapsed:.2f} h",
            ),
            (
                "Target Duration",
                f"{psu.target_hrs:g} h",
            ),
            (
                "Completion",
                f"{psu.progress_pct:.1f}%",
            ),
            (
                "Required Parameters",
                f"{float(psu.set_voltage or 0.0):.3f} V / "
                f"{float(psu.set_current or 0.0):.3f} A",
            ),
            (
                "Calibrated Parameters",
                f"{calibrated_voltage} / "
                f"{calibrated_current}",
            ),
            (
                "Average Measurements",
                f"{average_voltage:.3f} V / "
                f"{average_current:.3f} A",
            ),
            (
                "Average Chamber Temp",
                (
                    f"{average_temperature:.1f} °C"
                    if chamber.temp_hist
                    else "—"
                ),
            ),
        ]

        for row, (name, value) in enumerate(rows):
            name_label = label(
                f"{name}:",
                FMS,
                C["dim"],
            )

            value_label = label(
                value,
                FM,
                C["text"],
            )

            value_label.setTextInteractionFlags(
                Qt.TextInteractionFlag.TextSelectableByMouse
            )

            summary_layout.addWidget(
                name_label,
                row,
                0,
            )
            summary_layout.addWidget(
                value_label,
                row,
                1,
            )

        summary_layout.setColumnStretch(0, 0)
        summary_layout.setColumnStretch(1, 1)

        root.addWidget(summary_panel)

        # Final notes
        root.addWidget(
            label(
                "FINAL NOTES:",
                FMS,
                C["dim"],
            )
        )

        self.notes = QPlainTextEdit(
            psu.notes or ""
        )
        self.notes.setPlaceholderText(
            "Enter final observations, test findings, "
            "or completion remarks..."
        )
        self.notes.setMinimumHeight(140)

        root.addWidget(self.notes, 1)

        # Action buttons
        button_layout = QHBoxLayout()
        button_layout.setSpacing(8)

        end_test_button = QPushButton(
            "END TEST"
        )
        end_test_button.setStyleSheet(
            button_style(self.accent)
        )
        end_test_button.clicked.connect(
            self.confirm
        )


        button_layout.addWidget(end_test_button)
        root.addLayout(button_layout)

    def confirm(self) -> None:
        final_notes = self.notes.toPlainText().strip()

        try:
            # Save the latest elapsed time, configuration,
            # PSU status, and notes before finalizing.
            self.psu.notes = final_notes

            self.store.save_live_state(
                [self.psu]
            )

            # Atomically move the ongoing test and all its
            # measurements into permanent Test History.
            test_session_id = (
                self.store.finalize_live_test(
                    psu_idx=self.psu.idx,
                    final_notes=final_notes,
                )
            )

        except Exception as error:
            QMessageBox.critical(
                self,
                "Database Error",
                (
                    "The test could not be moved into "
                    "Test History.\n\n"
                    f"{error}"
                ),
            )
            return

        record = {
            "id": test_session_id,
            "psu_idx": self.psu.idx,
            "psu_label": f"PSU{self.psu.idx + 1}",
            "etr_number": self.psu.etr_number,
            "technician": self.psu.technician,
            "hours_elapsed": self.psu.hours_elapsed,
            "target_hrs": self.psu.target_hrs,
            "notes": final_notes,
        }

        self.on_complete(
            self.psu.idx,
            record,
        )

        self.accept()


class CompletedTestDetailDialog(QDialog):
    def __init__(
        self,
        parent,
        store,
        record: dict,
    ):
        super().__init__(parent)

        self.store = store
        self.record = record

        psu_idx = int(
            record.get("psu_idx", 0)
        )

        self.accent = ACCENTS[
            psu_idx % len(ACCENTS)
        ]

        self.measurements = []

        self.setWindowTitle(
            "Completed Test History - "
            f"{record.get('etr_number', '—')}"
        )

        self.resize(1000, 760)
        self.setMinimumSize(800, 600)

        root = QVBoxLayout(self)
        root.setContentsMargins(10, 10, 10, 10)
        root.setSpacing(8)

        self._build_header(root)
        self._build_summary(root)
        self._build_charts(root)
        self._build_actions(root)

        self._load_measurements()
        self._update_charts()

    def _build_header(
        self,
        root,
    ) -> None:
        header_panel = panel()

        layout = QHBoxLayout(header_panel)
        layout.setContentsMargins(
            12,
            8,
            12,
            8,
        )
        layout.setSpacing(8)

        layout.addWidget(
            label(
                "◈ COMPLETED TEST",
                FML,
                self.accent,
            )
        )

        layout.addWidget(
            label(
                str(
                    self.record.get(
                        "etr_number",
                        "—",
                    )
                ),
                FMB,
                C["text"],
            )
        )

        layout.addStretch()

        layout.addWidget(
            label(
                str(
                    self.record.get(
                        "completed_at",
                        "—",
                    )
                ),
                FMS,
                C["dim"],
            )
        )

        root.addWidget(header_panel)

    def _format_number(
        self,
        key: str,
        decimals: int,
        unit: str,
    ) -> str:
        value = self.record.get(key)

        if value is None:
            return "—"

        try:
            return (
                f"{float(value):.{decimals}f} "
                f"{unit}"
            )
        except (TypeError, ValueError):
            return "—"

    def _build_summary(
        self,
        root,
    ) -> None:
        summary_panel = panel()

        layout = QGridLayout(summary_panel)
        layout.setContentsMargins(
            12,
            10,
            12,
            10,
        )
        layout.setHorizontalSpacing(20)
        layout.setVerticalSpacing(6)

        required_parameters = (
            f"{self._format_number('required_voltage', 3, 'V')} / "
            f"{self._format_number('required_current', 3, 'A')}"
        )

        calibrated_parameters = (
            f"{self._format_number('calibrated_voltage', 3, 'V')} / "
            f"{self._format_number('calibrated_current', 3, 'A')}"
        )

        average_measurements = (
            f"{self._format_number('avg_voltage_v', 3, 'V')} / "
            f"{self._format_number('avg_current_a', 3, 'A')}"
        )

        summary_rows = [
            (
                "PSU",
                self.record.get(
                    "psu_label",
                    "—",
                ),
            ),
            (
                "ETR Number",
                self.record.get(
                    "etr_number",
                    "—",
                ),
            ),
            (
                "Technician",
                self.record.get(
                    "technician",
                    "—",
                ),
            ),
            (
                "Started",
                self.record.get(
                    "started_at",
                    "—",
                ),
            ),
            (
                "Completed",
                self.record.get(
                    "completed_at",
                    "—",
                ),
            ),
            (
                "Duration",
                self._format_number(
                    "hours_elapsed",
                    2,
                    "h",
                ),
            ),
            (
                "Target",
                self._format_number(
                    "target_hrs",
                    2,
                    "h",
                ),
            ),
            (
                "Required",
                required_parameters,
            ),
            (
                "Calibrated",
                calibrated_parameters,
            ),
            (
                "Average",
                average_measurements,
            ),
            (
                "Average Chamber Temp",
                self._format_number(
                    "avg_temp_c",
                    2,
                    "°C",
                ),
            ),
        ]

        column_count = 2

        for index, (
            heading_text,
            value_text,
        ) in enumerate(summary_rows):
            group_column = (
                index % column_count
            )
            group_row = (
                index // column_count
            )

            label_column = (
                group_column * 2
            )
            value_column = (
                label_column + 1
            )

            layout.addWidget(
                label(
                    f"{heading_text}:",
                    FMS,
                    C["dim"],
                ),
                group_row,
                label_column,
            )

            value_label = label(
                str(value_text or "—"),
                FM,
                C["text"],
            )

            value_label.setTextInteractionFlags(
                Qt.TextInteractionFlag.TextSelectableByMouse
            )

            layout.addWidget(
                value_label,
                group_row,
                value_column,
            )

        layout.setColumnStretch(1, 1)
        layout.setColumnStretch(3, 1)

        notes_row = (
            len(summary_rows)
            + column_count
            - 1
        ) // column_count

        layout.addWidget(
            label(
                "FINAL NOTES:",
                FMS,
                C["dim"],
            ),
            notes_row,
            0,
        )

        notes_label = label(
            str(
                self.record.get(
                    "notes",
                    "",
                )
                or "—"
            ),
            FM,
            C["text"],
        )
        notes_label.setWordWrap(True)
        notes_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )

        layout.addWidget(
            notes_label,
            notes_row,
            1,
            1,
            3,
        )

        root.addWidget(summary_panel)

    def _build_charts(
        self,
        root,
    ) -> None:
        self.fig = Figure(
            figsize=(8, 6),
            dpi=96,
            facecolor=PLOT_BG,
        )

        self.fig.subplots_adjust(
            left=0.08,
            right=0.97,
            top=0.95,
            bottom=0.09,
            hspace=0.50,
        )

        self.current_axis = (
            self.fig.add_subplot(311)
        )
        self.voltage_axis = (
            self.fig.add_subplot(312)
        )
        self.temperature_axis = (
            self.fig.add_subplot(313)
        )

        for axis in (
            self.current_axis,
            self.voltage_axis,
            self.temperature_axis,
        ):
            style_ax(axis)

            axis.xaxis.set_major_formatter(
                mdates.DateFormatter(
                    "%H:%M:%S"
                )
            )

        self.current_axis.set_title(
            "Current History",
            color=self.accent,
            fontsize=9,
            loc="left",
        )
        self.current_axis.set_ylabel(
            "Current (A)",
            color=PLOT_TEXT,
            fontsize=8,
        )

        self.voltage_axis.set_title(
            "Voltage History",
            color=C["cyan"],
            fontsize=9,
            loc="left",
        )
        self.voltage_axis.set_ylabel(
            "Voltage (V)",
            color=PLOT_TEXT,
            fontsize=8,
        )

        self.temperature_axis.set_title(
            "Chamber Temperature History",
            color=C["orange"],
            fontsize=9,
            loc="left",
        )
        self.temperature_axis.set_ylabel(
            "Temperature (°C)",
            color=PLOT_TEXT,
            fontsize=8,
        )
        self.temperature_axis.set_xlabel(
            "Time",
            color=PLOT_TEXT,
            fontsize=8,
        )

        (self.current_line,) = (
            self.current_axis.plot(
                [],
                [],
                color=self.accent,
                linewidth=1.4,
            )
        )

        (self.voltage_line,) = (
            self.voltage_axis.plot(
                [],
                [],
                color=C["cyan"],
                linewidth=1.4,
            )
        )

        (self.temperature_line,) = (
            self.temperature_axis.plot(
                [],
                [],
                color=C["orange"],
                linewidth=1.4,
            )
        )

        self.canvas = FigureCanvasQTAgg(
            self.fig
        )

        root.addWidget(
            self.canvas,
            1,
        )

    def _build_actions(
        self,
        root,
    ) -> None:
        layout = QHBoxLayout()
        layout.setContentsMargins(
            0,
            0,
            0,
            0,
        )
        layout.setSpacing(8)

        self.measurement_count_label = label(
            "0 measurement samples",
            FMS,
            C["dim"],
        )

        export_button = QPushButton(
            "EXPORT TEST DATA"
        )
        export_button.setStyleSheet(
            button_style(self.accent)
        )
        export_button.clicked.connect(
            self._export_test_data
        )

        close_button = QPushButton(
            "CLOSE"
        )
        close_button.clicked.connect(
            self.accept
        )

        layout.addWidget(
            self.measurement_count_label
        )
        layout.addStretch()
        layout.addWidget(export_button)
        layout.addWidget(close_button)

        root.addLayout(layout)

    def _load_measurements(self) -> None:
        test_session_id = self.record.get(
            "id"
        )

        if test_session_id is None:
            QMessageBox.warning(
                self,
                "Missing Test Record",
                (
                    "The selected test does not have "
                    "a database session ID."
                ),
            )
            return

        try:
            self.measurements = (
                self.store.get_test_measurements(
                    int(test_session_id)
                )
            )

        except Exception as error:
            QMessageBox.critical(
                self,
                "Database Error",
                (
                    "Unable to load the test "
                    f"measurements.\n\n{error}"
                ),
            )
            self.measurements = []

        sample_count = len(
            self.measurements
        )

        self.measurement_count_label.setText(
            f"{sample_count:,} measurement "
            f"sample{'s' if sample_count != 1 else ''}"
        )

    def _update_charts(self) -> None:
        times = []
        voltage_values = []
        current_values = []
        temperature_times = []
        temperature_values = []

        for measurement in self.measurements:
            measured_at = measurement.get(
                "measured_at"
            )

            if not isinstance(
                measured_at,
                datetime.datetime,
            ):
                continue

            voltage = measurement.get(
                "voltage_v"
            )
            current = measurement.get(
                "current_a"
            )
            temperature = measurement.get(
                "chamber_temp_c"
            )

            times.append(measured_at)
            voltage_values.append(
                float(voltage)
                if voltage is not None
                else float("nan")
            )
            current_values.append(
                float(current)
                if current is not None
                else float("nan")
            )

            if temperature is not None:
                temperature_times.append(
                    measured_at
                )
                temperature_values.append(
                    float(temperature)
                )

        self.current_line.set_data(
            times,
            current_values,
        )

        self.voltage_line.set_data(
            times,
            voltage_values,
        )

        self.temperature_line.set_data(
            temperature_times,
            temperature_values,
        )

        for axis in (
            self.current_axis,
            self.voltage_axis,
            self.temperature_axis,
        ):
            axis.relim()
            axis.autoscale_view()

        self.fig.autofmt_xdate(
            rotation=0,
        )

        self.canvas.draw_idle()

    def _export_test_data(self) -> None:
        etr_number = str(
            self.record.get(
                "etr_number",
                "test",
            )
        )

        safe_etr = "".join(
            character
            if character.isalnum()
            or character in ("-", "_")
            else "_"
            for character in etr_number
        )

        default_filename = (
            f"{safe_etr}_test_history.csv"
        )

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Test Data",
            default_filename,
            "CSV Files (*.csv)",
        )

        if not file_path:
            return

        if not file_path.lower().endswith(
            ".csv"
        ):
            file_path += ".csv"

        try:
            with open(
                file_path,
                "w",
                newline="",
                encoding="utf-8-sig",
            ) as csv_file:
                writer = csv.writer(csv_file)

                writer.writerow(
                    [
                        "HTOL COMPLETED TEST SUMMARY",
                    ]
                )

                summary_fields = (
                    ("Database ID", "id"),
                    ("PSU", "psu_label"),
                    ("ETR Number", "etr_number"),
                    ("Technician", "technician"),
                    ("Started At", "started_at"),
                    ("Completed At", "completed_at"),
                    ("Target Hours", "target_hrs"),
                    ("Hours Elapsed", "hours_elapsed"),
                    ("Progress Percent", "progress_pct"),
                    (
                        "Required Voltage",
                        "required_voltage",
                    ),
                    (
                        "Required Current",
                        "required_current",
                    ),
                    (
                        "Calibrated Voltage",
                        "calibrated_voltage",
                    ),
                    (
                        "Calibrated Current",
                        "calibrated_current",
                    ),
                    (
                        "Average Voltage",
                        "avg_voltage_v",
                    ),
                    (
                        "Average Current",
                        "avg_current_a",
                    ),
                    (
                        "Average Chamber Temperature",
                        "avg_temp_c",
                    ),
                    ("Final Notes", "notes"),
                )

                for heading, key in summary_fields:
                    writer.writerow(
                        [
                            heading,
                            self.record.get(
                                key,
                                "",
                            ),
                        ]
                    )

                writer.writerow([])
                writer.writerow(
                    [
                        "TIMESTAMP",
                        "VOLTAGE_V",
                        "CURRENT_A",
                        "CHAMBER_TEMP_C",
                        "OUTPUT_ON",
                        "PSU_ONLINE",
                        "PSU_FAULT",
                    ]
                )

                for measurement in self.measurements:
                    measured_at = (
                        measurement.get(
                            "measured_at"
                        )
                    )

                    if isinstance(
                        measured_at,
                        datetime.datetime,
                    ):
                        timestamp_text = (
                            measured_at.isoformat(
                                timespec="milliseconds"
                            )
                        )
                    else:
                        timestamp_text = str(
                            measured_at or ""
                        )

                    writer.writerow(
                        [
                            timestamp_text,
                            measurement.get(
                                "voltage_v",
                                "",
                            ),
                            measurement.get(
                                "current_a",
                                "",
                            ),
                            measurement.get(
                                "chamber_temp_c",
                                "",
                            ),
                            int(
                                bool(
                                    measurement.get(
                                        "output_on",
                                        False,
                                    )
                                )
                            ),
                            int(
                                bool(
                                    measurement.get(
                                        "psu_online",
                                        False,
                                    )
                                )
                            ),
                            int(
                                bool(
                                    measurement.get(
                                        "psu_fault",
                                        False,
                                    )
                                )
                            ),
                        ]
                    )

        except OSError as error:
            QMessageBox.critical(
                self,
                "Export Error",
                (
                    "Unable to export the test data."
                    f"\n\n{error}"
                ),
            )
            return

        QMessageBox.information(
            self,
            "Export Complete",
            (
                "The completed test data was exported "
                f"successfully.\n\n{file_path}"
            ),
        )

class TestHistoryPopup(QDialog):
    def __init__(self, parent, store):
        super().__init__(parent)
        self.store = store
        self.records = []
        self.setWindowTitle("TEST HISTORY LOG")
        self.resize(1060, 700)
        root = QVBoxLayout(self)
        h = QHBoxLayout()
        h.addWidget(label("COMPLETED TEST HISTORY", FML, C["purple"]))
        self.search = QLineEdit()
        self.search.setPlaceholderText("ETR #, Technician, or Date…")
        self.search.textChanged.connect(self.apply_filter)
        h.addWidget(self.search)
        root.addLayout(h)
        self.table = QTableWidget(0, 4)
        self.table.setEditTriggers(
            QTableWidget.EditTrigger.NoEditTriggers
        )

        self.table.setSelectionBehavior(
            QTableWidget.SelectionBehavior.SelectRows
        )

        self.table.setSelectionMode(
            QTableWidget.SelectionMode.SingleSelection
        )
        self.table.setHorizontalHeaderLabels(["DATE", "ETR #", "TECHNICIAN", "DURATION"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.itemSelectionChanged.connect(self.show_detail)
        self.table.itemDoubleClicked.connect(
            self.open_test_detail
        )
        root.addWidget(self.table, 2)
        self.detail = QPlainTextEdit()
        self.detail.setReadOnly(True)
        root.addWidget(self.detail, 1)
        self.load()

    def load(self):
        try:
            self.records = (
                self.store.get_completed_tests()
            )

        except Exception as error:
            QMessageBox.critical(
                self,
                "Database Error",
                (
                    "Unable to load completed tests.\n\n"
                    f"{error}"
                ),
            )
            self.records = []

        self.apply_filter()

    def apply_filter(self) -> None:
        query = (
            self.search.text()
            .strip()
            .lower()
        )

        self.filtered = [
            record
            for record in self.records
            if (
                not query
                or any(
                    query in str(
                        record.get(field, "")
                        or ""
                    ).lower()
                    for field in (
                        "etr_number",
                        "technician",
                        "completed_at",
                    )
                )
            )
        ]

        self.table.setRowCount(
            len(self.filtered)
        )

        for row_index, record in enumerate(
            self.filtered
        ):
            completed_at = (
                record.get("completed_at")
                or "—"
            )

            etr_number = (
                record.get("etr_number")
                or "—"
            )

            technician = (
                record.get("technician")
                or "—"
            )

            hours_elapsed = record.get(
                "hours_elapsed",
                0.0,
            )

            try:
                duration_text = (
                    f"{float(hours_elapsed):.2f} h"
                )
            except (TypeError, ValueError):
                duration_text = "—"

            values = (
                str(completed_at)[:10],
                str(etr_number),
                str(technician),
                duration_text,
            )

            for column_index, value in enumerate(
                values
            ):
                item = QTableWidgetItem(value)

                if column_index in (0, 3):
                    item.setTextAlignment(
                        Qt.AlignmentFlag.AlignCenter
                    )

                self.table.setItem(
                    row_index,
                    column_index,
                    item,
                )

    def open_test_detail(
        self,
        _item,
    ) -> None:
        row_index = self.table.currentRow()

        if row_index < 0:
            return

        if row_index >= len(self.filtered):
            return

        record = self.filtered[row_index]

        dialog = CompletedTestDetailDialog(
            self,
            self.store,
            record,
        )

        dialog.exec()

    def show_detail(self) -> None:
        row_index = self.table.currentRow()

        if row_index < 0:
            return

        if row_index >= len(self.filtered):
            return

        record = self.filtered[row_index]

        excluded_fields = {
            "id",
            "psu_idx",
        }

        lines = []

        for key, value in record.items():
            if key in excluded_fields:
                continue

            heading = (
                key.replace("_", " ")
                .title()
            )

            lines.append(
                f"{heading:24}: {value}"
            )

        self.detail.setPlainText(
            "\n".join(lines)
        )


class PSUControlPopup(QDialog):
    def __init__(self, parent, psu, on_apply):
        super().__init__(parent)
        self.psu = psu
        self.on_apply = on_apply
        self.setWindowTitle(f"PSU{psu.idx + 1} Control — {psu.etr_number}")
        self.resize(420, 320)
        root = QVBoxLayout(self)
        root.addWidget(
            label(f"◈ PSU{psu.idx + 1} OUTPUT CONTROL", FML, ACCENTS[psu.idx])
        )
        frm = panel()
        g = QGridLayout(frm)
        self.v = QLineEdit(f"{psu.set_voltage:.3f}")
        self.a = QLineEdit(f"{psu.set_current:.3f}")
        g.addWidget(label("SET VOLTAGE:"), 0, 0)
        g.addWidget(self.v, 0, 1)
        g.addWidget(label("V"), 0, 2)
        g.addWidget(label("SET CURRENT:"), 1, 0)
        g.addWidget(self.a, 1, 1)
        g.addWidget(label("A"), 1, 2)
        self.rb = label(f"{psu.voltage_v:.3f} V / {psu.current_a:.3f} A")
        g.addWidget(self.rb, 2, 0, 1, 3)
        root.addWidget(frm)
        h = QHBoxLayout()
        apply = QPushButton("⬆ APPLY SETPOINTS")
        apply.clicked.connect(self.apply)
        self.power = QPushButton("OUTPUT OFF" if psu.power_on else "OUTPUT ON")
        self.power.clicked.connect(self.toggle_power)
        h.addWidget(apply)
        h.addWidget(self.power)
        root.addLayout(h)

    def apply(self):
        try:
            v = float(self.v.text())
            a = float(self.a.text())
        except ValueError:
            QMessageBox.critical(
                self, "Invalid Input", "Voltage and Current must be numbers."
            )
            return
        self.psu.set_voltage = v
        self.psu.set_current = a
        threading.Thread(
            target=psu_set_output, args=(self.psu.idx, v, a), daemon=True
        ).start()
        self.on_apply(self.psu.idx, v, a)
        self.rb.setText(f"Setpoints sent: {v:.3f} V / {a:.3f} A")

    def toggle_power(self):
        state = not self.psu.power_on
        threading.Thread(
            target=psu_set_power, args=(self.psu.idx, state), daemon=True
        ).start()
        self.power.setText("OUTPUT OFF" if state else "OUTPUT ON")
