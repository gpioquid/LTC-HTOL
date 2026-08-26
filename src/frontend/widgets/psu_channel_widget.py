from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QSizePolicy,
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

    def _build_ui(self) -> None:
        self.setMinimumHeight(245)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(5, 5, 5, 5)
        main_layout.setSpacing(0)

        content_frame = QFrame()
        content_frame.setObjectName("machineCardContent")

        main_layout.addWidget(content_frame)

        content_layout = QVBoxLayout(content_frame)
        content_layout.setContentsMargins(14, 10, 14, 10)
        content_layout.setSpacing(5)

        # ==========================================================
        # Header
        # ==========================================================

        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(8)

        self.channel_label = create_label(
            f"PSU {self.index + 1}",
            FML,
            self.accent,
        )

        self.status_dot = QLabel("●")
        self.status_dot.setStyleSheet(
            f"""
            QLabel {{
                color: {self.accent};
                font-size: 18px;
                border: none;
                background: transparent;
            }}
            """
        )

        self.status_label = create_label(
            "IDLE",
            FMB,
            C["dim"],
        )
        self.status_label.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )
        self.status_label.setMinimumWidth(90)
        self.status_label.setFixedHeight(23)

        header_layout.addWidget(self.channel_label)
        header_layout.addStretch()
        header_layout.addWidget(self.status_dot)
        header_layout.addWidget(self.status_label)

        content_layout.addLayout(header_layout)

        # ==========================================================
        # ETR number and technician
        # ==========================================================

        information_layout = QHBoxLayout()
        information_layout.setContentsMargins(0, 0, 0, 0)
        information_layout.setSpacing(10)

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

        self.etr_label.setMinimumHeight(18)
        self.technician_label.setMinimumHeight(18)

        information_layout.addWidget(self.etr_label)
        information_layout.addStretch()
        information_layout.addWidget(self.technician_label)

        content_layout.addLayout(information_layout)

        # ==========================================================
        # Live measurements and progress container
        # ==========================================================

        monitoring_container = QFrame()
        monitoring_container.setObjectName("monitoringContainer")
        monitoring_container.setMinimumHeight(112)
        monitoring_container.setMaximumHeight(112)
        monitoring_container.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Fixed,
        )


        monitoring_layout = QVBoxLayout(monitoring_container)
        monitoring_layout.setContentsMargins(12, 6, 12, 7)
        monitoring_layout.setSpacing(3)

        # ----------------------------------------------------------
        # Live voltage and current
        # ----------------------------------------------------------

        measurements_layout = QGridLayout()
        measurements_layout.setContentsMargins(0, 0, 0, 0)
        measurements_layout.setHorizontalSpacing(30)
        measurements_layout.setVerticalSpacing(1)

        voltage_title = self._metric_title("VOLTAGE")
        current_title = self._metric_title("CURRENT")
        voltage_title.setObjectName("monitoringHeading")
        current_title.setObjectName("monitoringHeading")    

        voltage_title.setAlignment(
            Qt.AlignmentFlag.AlignHCenter
            | Qt.AlignmentFlag.AlignVCenter
        )
        current_title.setAlignment(
            Qt.AlignmentFlag.AlignHCenter
            | Qt.AlignmentFlag.AlignVCenter
        )

        voltage_title.setFixedHeight(15)
        current_title.setFixedHeight(15)

        self.voltage_label = self._metric_value(
            "0.000 V",
            C["text"],
        )
        self.current_label = self._metric_value(
            "0.000 A",
            C["text"],
        )

        self.voltage_label.setAlignment(
            Qt.AlignmentFlag.AlignHCenter
            | Qt.AlignmentFlag.AlignVCenter
        )
        self.current_label.setAlignment(
            Qt.AlignmentFlag.AlignHCenter
            | Qt.AlignmentFlag.AlignVCenter
        )

        self.voltage_label.setFixedHeight(19)
        self.current_label.setFixedHeight(19)

        measurements_layout.addWidget(
            voltage_title,
            0,
            0,
        )
        measurements_layout.addWidget(
            current_title,
            0,
            1,
        )
        measurements_layout.addWidget(
            self.voltage_label,
            1,
            0,
        )
        measurements_layout.addWidget(
            self.current_label,
            1,
            1,
        )

        measurements_layout.setColumnStretch(0, 1)
        measurements_layout.setColumnStretch(1, 1)

        monitoring_layout.addLayout(measurements_layout)

        # ----------------------------------------------------------
        # Separator
        # ----------------------------------------------------------

        monitoring_separator = QFrame()
        monitoring_separator.setObjectName(
            "monitoringSeparator"
        )
        monitoring_separator.setFrameShape(
            QFrame.Shape.HLine
        )
        monitoring_separator.setFixedHeight(1)
        monitoring_separator.setStyleSheet(
            f"""
            QFrame#monitoringSeparator {{
                border: none;
                background-color: {C["border2"]};
            }}
            """
        )

        monitoring_layout.addWidget(monitoring_separator)

        # ----------------------------------------------------------
        # Test progress
        # ----------------------------------------------------------

        progress_header = QHBoxLayout()
        progress_header.setContentsMargins(0, 0, 0, 0)
        progress_header.setSpacing(8)

        progress_title = create_label(
            "TEST PROGRESS",
            FMS,
            C["dim"],
        )
        progress_title.setObjectName("monitoringHeading")
        progress_title.setFixedHeight(15)
        progress_title.setAlignment(
            Qt.AlignmentFlag.AlignLeft
            | Qt.AlignmentFlag.AlignVCenter
        )

        
        

        progress_header.addWidget(progress_title)
        progress_header.addStretch()

        monitoring_layout.addLayout(progress_header)

        self.progress_bar = QProgressBar()
        self.progress_bar.setObjectName("machineProgressBar")
        self.progress_bar.setRange(0, 1000)
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat("0 / 1000 h")
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )
        self.progress_bar.setFixedHeight(21)

        
        self.progress_bar.setStyleSheet(
                f"""
                QProgressBar#machineProgressBar::chunk {{
                    background-color: {self.accent};
                    border-radius: 3px;
                }}
                """
            )
        

        monitoring_layout.addWidget(self.progress_bar)

        content_layout.addWidget(monitoring_container)

        
        # ==========================================================
        # Required test parameters
        # ==========================================================

        required_layout = QHBoxLayout()
        required_layout.setContentsMargins(0, 0, 0, 0)
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
        required_layout.addWidget(
            self.required_voltage_label
        )
        required_layout.addWidget(required_separator)
        required_layout.addWidget(
            self.required_current_label
        )
        required_layout.addStretch()

        required_title.setFixedHeight(16)
        self.required_voltage_label.setFixedHeight(16)
        required_separator.setFixedHeight(16)
        self.required_current_label.setFixedHeight(16)

        content_layout.addLayout(required_layout)


        # ==========================================================
        # Footer
        # ==========================================================

        footer_layout = QHBoxLayout()
        footer_layout.setContentsMargins(0, 0, 0, 0)
        footer_layout.setSpacing(8)

        self.last_update_label = create_label(
            "Waiting for data...",
            FMS,
            C["dim"],
        )

        self.click_hint = create_label(
            "Details →",
            FMS,
            C["text"],
        )
        self.click_hint.setAlignment(
            Qt.AlignmentFlag.AlignRight
            | Qt.AlignmentFlag.AlignVCenter
        )

        footer_layout.addWidget(self.last_update_label)
        footer_layout.addStretch()
        footer_layout.addWidget(self.click_hint)

        self.last_update_label.setFixedHeight(16)
        self.click_hint.setFixedHeight(16)



        content_layout.addLayout(footer_layout)


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

        self.voltage_label.setText(f"{psu.voltage_v:.2f} V")
        self.current_label.setText(f"{psu.current_a:.2f} A")

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
                f"{psu.set_voltage:.2f} V"
            )

        if psu.set_current is None:
            self.required_current_label.setText("— A")
        else:
            self.required_current_label.setText(
                f"{psu.set_current:.2f} A"
            )

    def reset_test(
        self,
        etr_number,
        technician,
    ):
        self.etr_label.setText(etr_number)
        self.technician_label.setText(technician)
        self.progress_bar.setValue(0)
