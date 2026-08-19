from PySide6.QtWidgets import (
    QHBoxLayout,
    QWidget,
)

from src.frontend.ui_styles import FMS, C
from src.frontend.widgets.common import (
    create_label,
    create_panel,
)


class StatusBarWidget(QWidget):
    def __init__(
        self,
        data_file,
        parent=None,
    ):
        super().__init__(parent)

        root_layout = QHBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)

        panel = create_panel()

        layout = QHBoxLayout(panel)
        layout.setContentsMargins(
            12,
            4,
            12,
            4,
        )
        layout.setSpacing(12)

        self.monitoring_label = create_label(
            "● MONITORING",
            FMS,
            C["green"],
        )

        self.poll_label = create_label(
            "LAST POLL: —",
            FMS,
            C["dim"],
        )

        data_label = create_label(
            f"DATA: {data_file}",
            FMS,
            C["dim"],
        )
        data_label.setToolTip(data_file)

        layout.addWidget(self.monitoring_label)
        layout.addStretch()
        layout.addWidget(data_label)
        layout.addWidget(self.poll_label)

        root_layout.addWidget(panel)

    def set_last_poll(self, value):
        self.poll_label.setText(f"LAST POLL: {value}")

    def set_monitoring(self):
        self.monitoring_label.setText("● MONITORING")
        self.monitoring_label.setStyleSheet(f"color: {C['green']};")

    def set_warning(self):
        self.monitoring_label.setText("● MONITORING WARNING")
        self.monitoring_label.setStyleSheet(f"color: {C['yellow']};")
