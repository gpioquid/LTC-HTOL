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
    def __init__(self, parent, psu, chamber):
        super().__init__(parent)
        self.psu = psu
        self.chamber = chamber
        self.accent = ACCENTS[psu.idx]
        self.setWindowTitle(f"PSU{psu.idx + 1} · {psu.etr_number} — Detail / History")
        self.resize(920, 640)
        self.setMinimumSize(700, 500)
        root = QVBoxLayout(self)
        hdr = panel()
        h = QHBoxLayout(hdr)
        h.addWidget(label(f"◈  PSU{psu.idx + 1} · {psu.etr_number}", FML, self.accent))
        h.addWidget(label(f"TECH: {psu.technician}", FM, C["dim"]))
        h.addStretch()
        h.addWidget(label("RANGE:", FMS, C["dim"]))
        self.group = QButtonGroup(self)
        self.ranges = {}
        for opt in ("Live", "1h", "6h", "24h", "All"):
            b = QRadioButton(opt)
            self.group.addButton(b)
            self.ranges[opt] = b
            h.addWidget(b)
            b.toggled.connect(self.refresh)
        self.ranges["Live"].setChecked(True)
        root.addWidget(hdr)
        stats = panel()
        sg = QGridLayout(stats)
        self.stat = {}
        vals = [
            ("HOURS ON", f"{psu.hours_elapsed:.2f} h"),
            ("TARGET", f"{psu.target_hrs} h"),
            ("PROGRESS", f"{psu.progress_pct:.1f}%"),
            ("CURRENT", f"{psu.current_a:.3f} A"),
            ("VOLTAGE", f"{psu.voltage_v:.3f} V"),
            ("STATUS", psu.status_str),
        ]
        for i, (k, v) in enumerate(vals):
            sg.addWidget(label(k, FMS, C["dim"]), 0, i)
            self.stat[k] = label(v, FMB, self.accent)
            sg.addWidget(self.stat[k], 1, i)
        self.on_range = label("ON-TIME IN RANGE: — h", FM, C["cyan"])
        sg.addWidget(self.on_range, 2, 0, 1, 6)
        root.addWidget(stats)
        self.notes = label(psu.notes or "—", FMS, C["text"])
        self.notes.setWordWrap(True)
        root.addWidget(self.notes)
        self.fig = Figure(figsize=(7, 4), dpi=96, facecolor=PLOT_BG)
        self.a1 = self.fig.add_subplot(211)
        self.a2 = self.fig.add_subplot(212)
        for ax in (self.a1, self.a2):
            style_ax(ax)
        (self.l1,) = self.a1.plot([], [], color=self.accent)
        (self.l2,) = self.a2.plot([], [], color=C["orange"])
        self.canvas = FigureCanvasQTAgg(self.fig)
        root.addWidget(self.canvas, 1)
        b = QPushButton("↻ REFRESH")
        b.clicked.connect(self.refresh)
        b.setStyleSheet(button_style(self.accent))
        root.addWidget(b, 0, Qt.AlignHCenter)
        self.refresh()

    def refresh(self):
        p = self.psu
        self.stat["HOURS ON"].setText(f"{p.hours_elapsed:.2f} h")
        self.stat["PROGRESS"].setText(f"{p.progress_pct:.1f}%")
        self.stat["CURRENT"].setText(f"{p.current_a:.3f} A")
        self.stat["VOLTAGE"].setText(f"{p.voltage_v:.3f} V")
        self.stat["STATUS"].setText(p.status_str)
        self.notes.setText(p.notes or "—")
        choice = next((k for k, v in self.ranges.items() if v.isChecked()), "Live")
        now = datetime.datetime.now().astimezone()
        cutoff = {
            "Live": now - datetime.timedelta(minutes=15),
            "1h": now - datetime.timedelta(hours=1),
            "6h": now - datetime.timedelta(hours=6),
            "24h": now - datetime.timedelta(hours=24),
            "All": datetime.datetime.min,
        }[choice]

        def f(t, v):
            return [(x, y) for x, y in zip(t, v) if x >= cutoff]

        a = f(p.time_hist, p.current_hist)
        t = f(self.chamber.time_hist, self.chamber.temp_hist)
        self.l1.set_data([x for x, y in a], [y for x, y in a])
        self.l2.set_data([x for x, y in t], [y for x, y in t])
        for ax in (self.a1, self.a2):
            ax.relim()
            ax.autoscale_view()
            ax.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))
        self.on_range.setText(
            f"ON-TIME IN RANGE: {sum(1 for x, y in a if y > 0) * 0.001:.2f} h"
        )
        self.canvas.draw_idle()


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
