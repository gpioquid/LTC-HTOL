from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from src.frontend.ui_styles import (
    ACCENTS,
    FML,
    FMS,
    C,
)
from src.frontend.widgets.common import (
    create_label,
    create_panel,
)
from src.frontend.widgets.psu_channel_widget import (
    PSUChannelWidget,
)


class PSUPanelWidget(QWidget):
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
        psus,
        parent=None,
    ):
        super().__init__(parent)

        self.channel_widgets = []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 4, 0)
        layout.setSpacing(6)

        section_header = create_panel()
        header_layout = QHBoxLayout(section_header)
        header_layout.setContentsMargins(
            12,
            7,
            12,
            7,
        )

        header_layout.addWidget(
            create_label(
                f"◈ POWER SUPPLY UNITS  ·  {len(psus)}-CHANNEL MONITOR AND CONTROL",
                FML,
                C["cyan"],
            )
        )
        header_layout.addStretch()

        self.summary_label = create_label(
            f"{len(psus)} CHANNELS",
            FMS,
            C["dim"],
        )

        header_layout.addWidget(self.summary_label)
        layout.addWidget(section_header)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        rows_widget = QWidget()
        rows_layout = QVBoxLayout(rows_widget)
        rows_layout.setContentsMargins(0, 0, 2, 0)
        rows_layout.setSpacing(6)

        for index, psu in enumerate(psus):
            widget = PSUChannelWidget(
                index,
                psu,
                ACCENTS[index % len(ACCENTS)],
            )

            self._connect_channel(widget)

            self.channel_widgets.append(widget)
            rows_layout.addWidget(widget)

        rows_layout.addStretch()

        scroll_area.setWidget(rows_widget)
        layout.addWidget(scroll_area, 1)

    def _connect_channel(self, widget):
        widget.test_toggled.connect(self.test_toggled.emit)
        widget.control_requested.connect(self.control_requested.emit)
        widget.trend_requested.connect(self.trend_requested.emit)
        widget.complete_requested.connect(self.complete_requested.emit)
        widget.notes_requested.connect(self.notes_requested.emit)
        widget.etr_changed.connect(self.etr_changed.emit)
        widget.technician_changed.connect(self.technician_changed.emit)
        widget.target_changed.connect(self.target_changed.emit)

    def update_channels(self, psus):
        active_count = 0
        fault_count = 0

        for widget, psu in zip(
            self.channel_widgets,
            psus,
        ):
            widget.update_state(psu)

            active_count += int(psu.power_on)
            fault_count += int(psu.fault)

        suffix = "" if fault_count == 1 else "S"

        self.summary_label.setText(
            f"{active_count} ACTIVE  ·  {fault_count} FAULT{suffix}"
        )

        return active_count, fault_count

    def reset_channel(
        self,
        index,
        etr_number,
        technician,
    ):
        self.channel_widgets[index].reset_test(
            etr_number,
            technician,
        )
