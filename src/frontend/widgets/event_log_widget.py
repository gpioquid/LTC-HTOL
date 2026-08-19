import datetime

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from src.frontend.ui_styles import FML, C
from src.frontend.widgets.common import (
    create_label,
    create_panel,
)


class EventLogWidget(QWidget):
    event_added = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        panel = create_panel()

        panel_layout = QVBoxLayout(panel)
        panel_layout.setContentsMargins(
            10,
            8,
            10,
            8,
        )
        panel_layout.setSpacing(4)

        header_layout = QHBoxLayout()

        header_layout.addWidget(
            create_label(
                "◈ EVENT LOG",
                FML,
                C["purple"],
            )
        )
        header_layout.addStretch()

        clear_button = QPushButton("CLEAR VIEW")
        clear_button.clicked.connect(self.clear_view)

        header_layout.addWidget(clear_button)

        panel_layout.addLayout(header_layout)

        self.text_box = QPlainTextEdit()
        self.text_box.setReadOnly(True)
        self.text_box.setMaximumBlockCount(1000)
        self.text_box.setPlaceholderText("System events will appear here...")

        panel_layout.addWidget(self.text_box)
        layout.addWidget(panel)

    def append_event(self, message):
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")

        self.text_box.appendPlainText(f"[{timestamp}]  {message}")

        self.event_added.emit(message)

    def clear_view(self):
        self.text_box.clear()

        timestamp = datetime.datetime.now().strftime("%H:%M:%S")

        self.text_box.appendPlainText(f"[{timestamp}]  Event log view cleared.")
