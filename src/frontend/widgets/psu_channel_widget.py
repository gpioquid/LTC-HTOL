from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLineEdit,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
)

from src.frontend.ui_styles import (
    FMB,
    FMS,
    C,
    button_style,
)
from src.frontend.widgets.common import (
    create_label,
)


class PSUChannelWidget(QFrame):
    test_toggled = Signal(int)
    control_requested = Signal(int)
    trend_requested = Signal(int)
    complete_requested = Signal(int)
    notes_requested = Signal(int)

    etr_changed = Signal(int, str)
    technician_changed = Signal(int, str)
    target_changed = Signal(int, str)

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

        self.setObjectName("card")
        self.setMinimumHeight(118)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(
            10,
            8,
            10,
            8,
        )
        main_layout.setSpacing(7)

        self._build_readback_row(main_layout)
        self._build_information_row(
            main_layout,
            psu,
        )
        self._build_control_row(main_layout)

    def _build_readback_row(self, parent_layout):
        layout = QHBoxLayout()
        layout.setSpacing(8)

        channel_label = create_label(
            f"PSU {self.index + 1}",
            ("Consolas", 12, True),
            self.accent,
        )
        channel_label.setMinimumWidth(66)

        self.status_label = create_label(
            "IDLE",
            FMB,
            C["dim"],
        )
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setMinimumWidth(84)

        self.voltage_label = create_label(
            "0.000 V",
            FMB,
            C["text"],
        )
        self.current_label = create_label(
            "0.000 A",
            FMB,
            self.accent,
        )
        self.hours_label = create_label(
            "0.00 h",
            FMB,
            self.accent,
        )

        layout.addWidget(channel_label)
        layout.addWidget(self.status_label)
        layout.addStretch()

        layout.addWidget(
            create_label(
                "VOLTAGE",
                FMS,
                C["dim"],
            )
        )
        layout.addWidget(self.voltage_label)
        layout.addSpacing(8)

        layout.addWidget(
            create_label(
                "CURRENT",
                FMS,
                C["dim"],
            )
        )
        layout.addWidget(self.current_label)
        layout.addSpacing(8)

        layout.addWidget(
            create_label(
                "ELAPSED",
                FMS,
                C["dim"],
            )
        )
        layout.addWidget(self.hours_label)

        parent_layout.addLayout(layout)

    def _build_information_row(
        self,
        parent_layout,
        psu,
    ):
        layout = QGridLayout()
        layout.setHorizontalSpacing(8)
        layout.setVerticalSpacing(4)

        self.etr_input = QLineEdit(psu.etr_number)
        self.etr_input.setPlaceholderText("ETR number")

        self.technician_input = QLineEdit(psu.technician)
        self.technician_input.setPlaceholderText("Technician")

        self.target_input = QLineEdit(str(psu.target_hrs))
        self.target_input.setMaximumWidth(76)
        self.target_input.setAlignment(Qt.AlignmentFlag.AlignRight)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 1000)
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat("0.0%")
        self.progress_bar.setMinimumWidth(130)
        self.progress_bar.setMinimumHeight(18)

        headers = (
            ("ETR NUMBER", 0),
            ("TECHNICIAN", 1),
            ("TARGET", 2),
            ("PROGRESS", 3),
        )

        for text, column in headers:
            layout.addWidget(
                create_label(
                    text,
                    FMS,
                    C["dim"],
                ),
                0,
                column,
            )

        layout.addWidget(
            self.etr_input,
            1,
            0,
        )
        layout.addWidget(
            self.technician_input,
            1,
            1,
        )
        layout.addWidget(
            self.target_input,
            1,
            2,
        )
        layout.addWidget(
            self.progress_bar,
            1,
            3,
        )

        layout.setColumnStretch(0, 2)
        layout.setColumnStretch(1, 2)
        layout.setColumnStretch(2, 1)
        layout.setColumnStretch(3, 3)

        self.etr_input.editingFinished.connect(
            lambda: self.etr_changed.emit(
                self.index,
                self.etr_input.text().strip(),
            )
        )
        self.technician_input.editingFinished.connect(
            lambda: self.technician_changed.emit(
                self.index,
                self.technician_input.text().strip(),
            )
        )
        self.target_input.editingFinished.connect(
            lambda: self.target_changed.emit(
                self.index,
                self.target_input.text().strip(),
            )
        )

        parent_layout.addLayout(layout)

    def _build_control_row(self, parent_layout):
        layout = QHBoxLayout()
        layout.setSpacing(6)

        self.start_button = QPushButton("START")
        self.start_button.setMinimumWidth(90)
        self.start_button.setStyleSheet(button_style(C["green"], True))

        control_button = QPushButton("CONTROL")
        control_button.setStyleSheet(button_style(self.accent))

        trend_button = QPushButton("TREND")
        trend_button.setStyleSheet(button_style(self.accent))

        complete_button = QPushButton("COMPLETE")
        complete_button.setStyleSheet(button_style(C["green"]))

        notes_button = QPushButton("NOTES")

        self.start_button.clicked.connect(lambda: self.test_toggled.emit(self.index))
        control_button.clicked.connect(lambda: self.control_requested.emit(self.index))
        trend_button.clicked.connect(lambda: self.trend_requested.emit(self.index))
        complete_button.clicked.connect(
            lambda: self.complete_requested.emit(self.index)
        )
        notes_button.clicked.connect(lambda: self.notes_requested.emit(self.index))

        layout.addWidget(self.start_button)
        layout.addWidget(control_button)
        layout.addWidget(trend_button)
        layout.addWidget(complete_button)
        layout.addWidget(notes_button)
        layout.addStretch()

        parent_layout.addLayout(layout)

    def update_state(self, psu):
        self.hours_label.setText(f"{psu.hours_elapsed:.2f} h")
        self.voltage_label.setText(f"{psu.voltage_v:.3f} V")
        self.current_label.setText(f"{psu.current_a:.3f} A")

        self.status_label.setText(psu.status_str)
        self.status_label.setStyleSheet(
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

        progress = max(
            0.0,
            min(
                float(psu.progress_pct),
                100.0,
            ),
        )

        self.progress_bar.setValue(round(progress * 10))
        self.progress_bar.setFormat(f"{progress:.1f}%")
        self.progress_bar.setStyleSheet(
            f"""
            QProgressBar {{
                background: {C["tile_bg"]};
                color: {C["text"]};
                border: 1px solid
                    {C["border2"]};
                border-radius: 4px;
                text-align: center;
            }}

            QProgressBar::chunk {{
                background: {self.accent};
                border-radius: 3px;
            }}
            """
        )

        if psu.test_active:
            self.start_button.setText("STOP")
            self.start_button.setStyleSheet(button_style(C["red"], True))

        elif psu.hours_elapsed > 0:
            self.start_button.setText("RESUME")
            self.start_button.setStyleSheet(button_style(C["yellow"], True))

        else:
            self.start_button.setText("START")
            self.start_button.setStyleSheet(button_style(C["green"], True))

    def reset_test(
        self,
        etr_number,
        technician,
    ):
        self.etr_input.setText(etr_number)
        self.technician_input.setText(technician)
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat("0.0%")
