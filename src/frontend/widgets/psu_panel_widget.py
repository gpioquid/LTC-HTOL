from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QGridLayout,
    QHBoxLayout,
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
    # Existing signals retained for compatibility.
    test_toggled = Signal(int)
    control_requested = Signal(int)
    trend_requested = Signal(int)
    complete_requested = Signal(int)
    notes_requested = Signal(int)

    etr_changed = Signal(int, str)
    technician_changed = Signal(int, str)
    target_changed = Signal(int, str)

    # New card-click signal.
    machine_selected = Signal(int)

    def __init__(
        self,
        psus,
        parent=None,
    ):
        super().__init__(parent)

        self.channel_widgets = []

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(
            0,
            0,
            4,
            0,
        )
        root_layout.setSpacing(6)

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
                f"◈ POWER SUPPLY UNITS  ·  {len(psus)}-CHANNEL MONITOR",
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

        root_layout.addWidget(section_header)

        self.card_grid = QGridLayout()
        self.card_grid.setContentsMargins(
            0,
            0,
            0,
            0,
        )
        self.card_grid.setHorizontalSpacing(8)
        self.card_grid.setVerticalSpacing(8)

        for index, psu in enumerate(psus):
            card = PSUChannelWidget(
                index,
                psu,
                ACCENTS[index % len(ACCENTS)],
            )

            card.selected.connect(self.machine_selected.emit)

            # Keep existing signal forwarding.
            card.test_toggled.connect(self.test_toggled.emit)
            card.control_requested.connect(self.control_requested.emit)
            card.trend_requested.connect(self.trend_requested.emit)
            card.complete_requested.connect(self.complete_requested.emit)
            card.notes_requested.connect(self.notes_requested.emit)
            card.etr_changed.connect(self.etr_changed.emit)
            card.technician_changed.connect(self.technician_changed.emit)
            card.target_changed.connect(self.target_changed.emit)

            row = index // 2
            column = index % 2

            self.card_grid.addWidget(
                card,
                row,
                column,
            )

            self.channel_widgets.append(card)

        row_count = (len(psus) + 1) // 2

        for row in range(row_count):
            self.card_grid.setRowStretch(
                row,
                1,
            )

        self.card_grid.setColumnStretch(0, 1)
        self.card_grid.setColumnStretch(1, 1)

        root_layout.addLayout(
            self.card_grid,
            1,
        )

    def update_channels(self, psus):
        active_count = 0

        for card, psu in zip(
            self.channel_widgets,
            psus,
            strict=False,
        ):
            card.update_state(psu)

            active_count += int(psu.power_on)


      

        return active_count

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
