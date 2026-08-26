import datetime

from PySide6.QtCore import Signal, QTimer
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
    psu_network_requested = Signal()

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
                "HTOL MONITOR",
                ("Consolas", 20, True),
                C["cyan"],
            )
        )
        title_layout.addWidget(
            create_label(
                "LTC HIGH TEMPERATURE OPERATING LIFE TEST CONTROL SYSTEM",
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

        network_button = QPushButton(
            "PSU NETWORK SETTINGS"
        )

        network_button.setToolTip(
            "View or edit the configured "
            "Sorensen PSU IP addresses"
        )

        network_button.setStyleSheet(
            button_style(C["cyan"])
        )

        network_button.clicked.connect(
            self.psu_network_requested.emit
        )

        self.active_label = create_label(
            f"ACTIVE  0/{num_psu}",
            FMB,
            C["green"],
        )
        self.active_label.setObjectName("headerMetric")


        self.clock_label = create_label(
            "",
            ("Consolas", 14, True),
            C["text"],
        )
        self.clock_label.setObjectName("headerClock")
        self.clock_label.setMinimumWidth(185)

        layout.addWidget(history_button)
        layout.addWidget(network_button)
        layout.addSpacing(8)
        layout.addWidget(self.active_label)
        layout.addSpacing(8)
        layout.addWidget(self.clock_label)
        # Display the date and time immediately.
        self._update_clock()

        # Continue updating once per second.
        self.clock_timer = QTimer(self)
        self.clock_timer.setInterval(1000)
        self.clock_timer.timeout.connect(
            self._update_clock
        )
        self.clock_timer.start()



    def _update_clock(self) -> None:
        current_datetime = (
            datetime.datetime.now().strftime(
                "%Y-%m-%d  %H:%M:%S"
            )
        )

        self.clock_label.setText(
            current_datetime
        )

    def set_active_count(
        self,
        active_count,
        total_count,
    ):
        self.active_label.setText(f"ACTIVE  {active_count}/{total_count}")

