from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
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


class HeaderWidget(QFrame):
    history_requested = Signal()

    def __init__(self, num_psu, parent=None):
        super().__init__(parent)

        self.setObjectName("panel")
        self.setMinimumHeight(82)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(
            16,
            10,
            16,
            10,
        )
        layout.setSpacing(10)

        title_layout = QVBoxLayout()
        title_layout.setSpacing(1)

        title_layout.addWidget(
            create_label(
                "■ HTOL MONITOR",
                ("Consolas", 20, True),
                C["cyan"],
            )
        )
        title_layout.addWidget(
            create_label(
                "HIGH TEMPERATURE OPERATING LIFE TEST  ·  CONTINUOUS MONITOR  ·  v3.0",
                FMS,
                C["dim"],
            )
        )

        layout.addLayout(title_layout)
        layout.addStretch()

        history_button = QPushButton("TEST HISTORY")
        history_button.setToolTip("Open completed HTOL test records")
        history_button.setStyleSheet(button_style(C["purple"]))
        history_button.clicked.connect(self.history_requested.emit)

        self.active_label = create_label(
            f"ACTIVE  0/{num_psu}",
            FMB,
            C["green"],
        )
        self.active_label.setObjectName("headerMetric")

        self.fault_label = create_label(
            "FAULTS  0",
            FMB,
            C["dim"],
        )
        self.fault_label.setObjectName("headerMetric")

        self.clock_label = create_label(
            "--:--:--",
            ("Consolas", 16, True),
            C["text"],
        )

        layout.addWidget(history_button)
        layout.addSpacing(8)
        layout.addWidget(self.active_label)
        layout.addWidget(self.fault_label)
        layout.addSpacing(8)
        layout.addWidget(self.clock_label)

    def set_clock(self, value):
        self.clock_label.setText(value)

    def set_active_count(
        self,
        active_count,
        total_count,
    ):
        self.active_label.setText(f"ACTIVE  {active_count}/{total_count}")

    def set_fault_count(self, fault_count):
        self.fault_label.setText(f"FAULTS  {fault_count}")

        color = C["red"] if fault_count else C["dim"]

        self.fault_label.setStyleSheet(f"color: {color};")
