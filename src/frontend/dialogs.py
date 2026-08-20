import datetime
import threading

import matplotlib.dates as mdates
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QButtonGroup,
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


class PSUDetailPopup(QDialog):
    def __init__(self, parent, psu, chamber, on_apply):
        super().__init__(parent)

        self.psu = psu
        self.chamber = chamber
        self.on_apply = on_apply
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

    def _build_settings(self, root):
        settings_panel = panel()

        layout = QGridLayout(settings_panel)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setHorizontalSpacing(10)
        layout.setVerticalSpacing(8)

        self.etr_input = QLineEdit(self.psu.etr_number)
        self.technician_input = QLineEdit(self.psu.technician)
        self.target_input = QLineEdit(str(self.psu.target_hrs))
        self.voltage_input = QLineEdit(f"{self.psu.set_voltage:.3f}")
        self.current_input = QLineEdit(f"{self.psu.set_current:.3f}")

        layout.addWidget(label("ETR NUMBER:", FMS, C["dim"]), 0, 0)
        layout.addWidget(self.etr_input,0 ,1)

        layout.addWidget(label("TECHNICIAN:", FMS, C["dim"]), 0, 2)
        layout.addWidget(self.technician_input,0 ,3)

        layout.addWidget(label("TARGET HOURS:", FMS, C["dim"]), 1, 0)
        layout.addWidget(self.target_input,1 ,1)

        layout.addWidget(label("SET VOLTAGE:", FMS, C["dim"]), 1, 2)
        layout.addWidget(self.voltage_input,1 ,3)
        layout.addWidget(label("V", FMS, C["dim"]), 1,4)


        layout.addWidget(label("SET CURRENT:", FMS, C["dim"]), 2, 2)
        layout.addWidget(self.current_input,2 ,3)
        layout.addWidget(label("A", FMS, C["dim"]), 2,4)


        self.apply_status = label(
            "Enter the test configuration, then select APPLY.",
            FMS, C["dim"],
        )

        layout.addWidget(self.apply_status, 3, 0, 1, 5)

        root.addWidget(settings_panel)



    def _build_action_buttons(self, root):
        layout = QHBoxLayout()

        apply_button = QPushButton("APPLY SETTINGS")
        apply_button.setStyleSheet(button_style(self.accent))
        apply_button.clicked.connect(self._apply_settings)

        refresh_button = QPushButton("REFRESH")
        refresh_button.clicked.connect(self.refresh)

        close_button = QPushButton("CLOSE")
        close_button.clicked.connect(self.close)

        layout.addStretch()
        layout.addWidget(apply_button)
        layout.addWidget(refresh_button)
        layout.addWidget(close_button)
        layout.addStretch()

        root.addLayout(layout)

    def _apply_settings(self):
        etr_number = self.etr_input.text().strip()
        technician = self.technician_input.text().strip()

        if not etr_number:
            QMessageBox.warning(
                self,
                "Missing ETR Number",
                "Enter an ETR Number."
            )
            return

        if not technician:
            QMessageBox.warning(
                self,
                "Missing Technician",
                "Enter the technician name."
            )
            return

        try:
            target_hours = float(self.target_input.text())
            voltage = float(self.voltage_input.text())
            current = float(self.current_input.text())

            if target_hours <=0:
                raise ValueError("Target hours must be grater than zero.")

            if voltage <0:
                raise ValueError("Voltage cannot be negative.")

            if current < 0:
                raise ValueError("Current cannot be negative.")

        except ValueError as error:
            QMessageBox.warning(
                self,
                "Invalid Settings",
                str(error),
            )
            return

        self.psu.etr_number = etr_number
        self.psu.technician = technician
        self.psu.target_hrs = target_hours
        self.set_voltage = voltage
        self.set_current = current

        try:
            psu_set_output(
                self.psu.idx,
                voltage,
                current,
            )

        except Exception as error:
            QMessageBox.critical(
                self,
                "PSU Communication Error",
                f"Unable to apply the PSU test configurations: \n{error}",
            )
            return

        self.on_apply(
            self.psu.idx,
            etr_number,
            technician,
            target_hours,
            voltage,
            current,
        )

        self.apply_status.setText(
            f"Settings applied: {voltage:.3f} V and {current:.3f} A"
        )

        self.apply_status.setStyleSheet(
            f"color: {C['green']}; border: 0;"
        )

        self.setWindowTitle(
            f"PSU{self.psu.idx + 1}"
            f"{self.psu.etr_number} Configuration and History"
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
    def __init__(self, parent, psu, chamber, store, on_complete):
        super().__init__(parent)
        self.psu = psu
        self.chamber = chamber
        self.store = store
        self.on_complete = on_complete
        self.setWindowTitle(f"Complete Test — PSU{psu.idx + 1} / {psu.etr_number}")
        self.resize(500, 520)
        root = QVBoxLayout(self)
        root.addWidget(label("◈  MARK TEST COMPLETE", FML, ACCENTS[psu.idx]))
        summary = panel()
        g = QGridLayout(summary)
        rows = [
            ("ETR Number", psu.etr_number),
            ("Technician", psu.technician),
            ("Hours Elapsed", f"{psu.hours_elapsed:.2f} h"),
            ("Target Hours", f"{psu.target_hrs} h"),
            ("Progress", f"{psu.progress_pct:.1f}%"),
            ("Chamber Temp", f"{chamber.temp_c:.1f} °C" if chamber.online else "—"),
        ]
        for i, (a, b) in enumerate(rows):
            g.addWidget(label(a + ":", FMS, C["dim"]), i, 0)
            g.addWidget(label(b), i, 1)
        root.addWidget(summary)
        root.addWidget(label("OUTCOME:", FMS, C["dim"]))
        oh = QHBoxLayout()
        self.outcomes = QButtonGroup(self)
        for i, opt in enumerate(("PASS", "FAIL", "ABORT", "ARCHIVE")):
            b = QRadioButton(opt)
            self.outcomes.addButton(b, i)
            oh.addWidget(b)
            b.setChecked(i == 0)
        root.addLayout(oh)
        root.addWidget(label("FINAL NOTES:", FMS, C["dim"]))
        self.notes = QPlainTextEdit(psu.notes)
        root.addWidget(self.notes)
        bh = QHBoxLayout()
        ok = QPushButton("✔ CONFIRM & ARCHIVE")
        ok.clicked.connect(self.confirm)
        cancel = QPushButton("✕ CANCEL")
        cancel.clicked.connect(self.reject)
        bh.addWidget(ok)
        bh.addWidget(cancel)
        root.addLayout(bh)

    def confirm(self):
        p = self.psu
        c = self.chamber
        rec = {
            "psu_idx": p.idx,
            "psu_label": f"PSU{p.idx + 1}",
            "etr_number": p.etr_number,
            "technician": p.technician,
            "started_at": p.test_start_dt.isoformat(timespec="seconds")
            if p.test_start_dt
            else "—",
            "completed_at": datetime.datetime.now().isoformat(timespec="seconds"),
            "hours_elapsed": round(p.hours_elapsed, 4),
            "target_hrs": p.target_hrs,
            "avg_current_a": round(sum(p.current_hist) / len(p.current_hist), 4)
            if p.current_hist
            else 0.0,
            "avg_temp_c": round(sum(c.temp_hist) / len(c.temp_hist), 2)
            if c.temp_hist
            else 0.0,
            "outcome": self.outcomes.checkedButton().text(),
            "notes": self.notes.toPlainText().strip(),
            "current_snapshot": list(p.current_hist)[-300:],
            "temp_snapshot": list(c.temp_hist)[-300:],
        }
        self.store.complete_test(rec)
        self.on_complete(p.idx, rec)
        self.accept()


class TestHistoryPopup(QDialog):
    def __init__(self, parent, store):
        super().__init__(parent)
        self.store = store
        self.records = []
        self.setWindowTitle("TEST HISTORY LOG")
        self.resize(1060, 700)
        root = QVBoxLayout(self)
        h = QHBoxLayout()
        h.addWidget(label("◈ COMPLETED TEST HISTORY", FML, C["purple"]))
        self.search = QLineEdit()
        self.search.setPlaceholderText("ETR #, Technician, or Date…")
        self.search.textChanged.connect(self.apply_filter)
        h.addWidget(self.search)
        root.addLayout(h)
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["DATE", "ETR #", "TECHNICIAN", "OUTCOME"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.itemSelectionChanged.connect(self.show_detail)
        root.addWidget(self.table, 2)
        self.detail = QPlainTextEdit()
        self.detail.setReadOnly(True)
        root.addWidget(self.detail, 1)
        self.load()

    def load(self):
        self.records = list(reversed(self.store.get_completed_tests()))
        self.apply_filter()

    def apply_filter(self):
        q = self.search.text().strip().lower()
        self.filtered = [
            r
            for r in self.records
            if not q
            or any(
                q in str(r.get(k, "")).lower()
                for k in ("etr_number", "technician", "completed_at")
            )
        ]
        self.table.setRowCount(len(self.filtered))
        for i, r in enumerate(self.filtered):
            for j, v in enumerate(
                (
                    r.get("completed_at", "—")[:10],
                    r.get("etr_number", "—"),
                    r.get("technician", "—"),
                    r.get("outcome", "—"),
                )
            ):
                self.table.setItem(i, j, QTableWidgetItem(str(v)))

    def show_detail(self):
        i = self.table.currentRow()
        if i < 0:
            return
        r = self.filtered[i]
        self.detail.setPlainText(
            "\n".join(
                f"{k.replace('_', ' ').title():16}: {v}"
                for k, v in r.items()
                if k not in ("current_snapshot", "temp_snapshot")
            )
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
