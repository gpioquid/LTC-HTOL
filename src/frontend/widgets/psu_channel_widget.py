from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QVBoxLayout,
)

from src.frontend.ui_styles import (
    FMB,
    FML,
    FMS,
    C,
)
from src.frontend.widgets.common import create_label


class PSUChannelWidget(QFrame):
    # Existing signals remain available.
    test_toggled = Signal(int)
    control_requested = Signal(int)
    trend_requested = Signal(int)
    complete_requested = Signal(int)
    notes_requested = Signal(int)

    etr_changed = Signal(int, str)
    technician_changed = Signal(int, str)
    target_changed = Signal(int, str)

    # New signal emitted when the card is clicked.
    selected = Signal(int)

    def __init__(
        self,
        index,
        psu,
        accent,
        parent=None,
    ):
        super().__init__(parent)

        self.index = index
        self.accent = accent
        self.psu = psu

        self.setObjectName("machineCard")
        self.setProperty("state", "idle")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumHeight(180)

        self._build_ui()
        self.update_state(psu)

    def _build_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(0)

        content_frame = QFrame()
        content_frame.setObjectName("machineCardContent")

        main_layout.addWidget(content_frame)

        content_layout = QVBoxLayout(content_frame)
        content_layout.setContentsMargins(
            20,
            18,
            20,
            18,
        )
        content_layout.setSpacing(12)

        # header_layout
        # information_layout
        # measurements_layout
        # progress_layout
        # footer_layout

        # Header
        header_layout = QHBoxLayout()
        header_layout.setSpacing(8)

        self.channel_label = create_label(
            f"PSU {self.index + 1}",
            FML,
            self.accent,
        )

        self.status_label = create_label(
            "IDLE",
            FMB,
            C["dim"],
        )
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setMinimumWidth(90)

        header_layout.addWidget(self.channel_label)

        header_layout.addStretch()

        self.status_dot = QLabel("●")
        self.status_dot.setStyleSheet(
            f"""
            color: {self.accent};
            font-size: 18px;
            border: none;
            """
        )

        header_layout.addWidget(self.status_dot)
        header_layout.addWidget(self.status_label)

        content_layout.addLayout(header_layout)

        # ETR and technician
        information_layout = QHBoxLayout()

        self.etr_label = create_label(
            self.psu.etr_number or "NO ETR",
            FMB,
            C["text"],
        )

        self.technician_label = create_label(
            self.psu.technician or "—",
            FMS,
            C["dim"],
        )

        information_layout.addWidget(self.etr_label)
        information_layout.addStretch()
        information_layout.addWidget(self.technician_label)

        content_layout.addLayout(information_layout)

        # Measurement values
        measurements_layout = QGridLayout()
        measurements_layout.setHorizontalSpacing(15)
        measurements_layout.setVerticalSpacing(3)

        measurements_layout.addWidget(
            self._metric_title("VOLTAGE"),
            1,
            0,
        )

        measurements_layout.addWidget(
            self._metric_title("CURRENT"),
            1,
            1,
        )
        

        self.voltage_label = self._metric_value(
            "0.000 V",
            C["text"],
        )
        self.current_label = self._metric_value(
            "0.000 A",
            C["text"],
        )


        measurements_layout.addWidget(
                    self.voltage_label,
                    2,
                    0,
                )
        measurements_layout.addWidget(
                    self.current_label,
                    2,
                    1,
                )

        

        for column in range(2):
            measurements_layout.setColumnStretch(
                column,
                1,
            )

        content_layout.addLayout(measurements_layout)

        # Progress
        progress_header = QHBoxLayout()

        progress_header.addWidget(
            create_label(
                "TEST PROGRESS",
                FMS,
                C["dim"],
            )
        )

        self.progress_text = create_label(
            "0.0%",
            FMB,
            self.accent,
        )
        


        progress_header.addStretch()

        progress_header.addWidget(self.progress_text)

        content_layout.addLayout(progress_header)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 1000)
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat("0 / 1000 h")
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.progress_bar.setMinimumHeight(24)
        

        content_layout.addWidget(self.progress_bar)

        # Click hint
        footer_layout = QHBoxLayout()

        self.last_update_label = create_label(
            "Waiting for data...",
            FMS,
            C["dim"],
        )

        self.click_hint = create_label(
            "Details →",
            FMS,
            "white",
        )

        footer_layout.addWidget(self.last_update_label)
        footer_layout.addStretch()
        footer_layout.addWidget(self.click_hint)

        content_layout.addLayout(footer_layout)

        # Required test parameters at the very bottom
        required_layout = QHBoxLayout()
        required_layout.setContentsMargins(0, 2, 0, 0)
        required_layout.setSpacing(6)

        required_title = create_label(
            "REQUIRED:",
            FMS,
            C["dim"],
        )

        self.required_voltage_label = create_label(
            "— V",
            FMS,
            self.accent,
        )

        required_separator = create_label(
            "·",
            FMS,
            C["text"],
        )

        self.required_current_label = create_label(
            "— A",
            FMS,
            self.accent,
        )

        required_layout.addWidget(required_title)
        required_layout.addWidget(self.required_voltage_label)
        required_layout.addWidget(required_separator)
        required_layout.addWidget(self.required_current_label)
        required_layout.addStretch()

        content_layout.addLayout(required_layout)

    def _metric_title(self, text):
        result = create_label(
            text,
            FMS,
            C["dim"],
        )
        result.setAlignment(Qt.AlignmentFlag.AlignCenter)
        return result

    def _metric_value(
        self,
        text,
        color,
    ):
        result = create_label(
            text,
            FMB,
            color,
        )
        result.setAlignment(Qt.AlignmentFlag.AlignCenter)
        return result

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.selected.emit(self.index)

        super().mousePressEvent(event)

    def enterEvent(self, event):
        self.setProperty("hovered", True)
        self._refresh_style()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.setProperty("hovered", False)
        self._refresh_style()
        super().leaveEvent(event)

    def _refresh_style(self):
        self.style().unpolish(self)
        self.style().polish(self)
        self.update()

    def _state_name(self, psu):
        if psu.fault:
            return "fault"

        if not psu.online:
            return "offline"

        if psu.test_active and psu.power_on:
            return "running"

        if psu.hours_elapsed > 0:
            return "paused"

        return "idle"

    def update_state(self, psu):
        self.psu = psu

        self.etr_label.setText(psu.etr_number or "NO ETR")
        self.technician_label.setText(psu.technician or "—")

        self.voltage_label.setText(f"{psu.voltage_v:.3f} V")
        self.current_label.setText(f"{psu.current_a:.3f} A")

        self.status_label.setText(psu.status_str)

        self.status_dot.setStyleSheet(
            f"""
            color: {psu.status_color};
            font-size: 18px;
            border: none;
            """
        )

        self.status_label.setStyleSheet(
            f"""
            QLabel {{
                color: {psu.status_color};
                background: {C["tile_bg"]};
                border: 1px solid
                    {psu.status_color};
                border-radius: 5px;
                padding: 4px 10px;
            }}
            """
        )

        target_hours = getattr(
            psu,
            "target_hrs",
            1000,
        )


        progress = max(
            0.0,
            min(
                float(psu.progress_pct),
                100.0,
            ),
        )

        self.progress_text.setText(
            f"{progress:.1f}%"
        )

        self.progress_bar.setValue(
            round(progress * 10)
        )

        self.progress_bar.setFormat(
            f"{psu.hours_elapsed:.1f} / "
            f"{target_hours:g} h"
        )
        self.progress_bar.setStyleSheet(
            f"""
            QProgressBar {{
                color: {C["text"]};
                background: {C["tile_bg"]};
                border: 1px solid {C["border2"]};
                border-radius: 5px;
                text-align: center;
                padding: 0px;
            }}

            QProgressBar::chunk {{
                background: {self.accent};
                border-radius: 4px;
            }}
            """
        )

        state = self._state_name(psu)

        if self.property("state") != state:
            self.setProperty("state", state)
            self._refresh_style()

        if psu.set_voltage is None:
            self.required_voltage_label.setText("— V")
        else:
            self.required_voltage_label.setText(
                f"{psu.set_voltage:.3f} V"
            )

        if psu.set_current is None:
            self.required_current_label.setText("— A")
        else:
            self.required_current_label.setText(
                f"{psu.set_current:.3f} A"
            )

    def reset_test(
        self,
        etr_number,
        technician,
    ):
        self.etr_label.setText(etr_number)
        self.technician_label.setText(technician)
        self.progress_bar.setValue(0)
        self.progress_text.setText("0.0%")
