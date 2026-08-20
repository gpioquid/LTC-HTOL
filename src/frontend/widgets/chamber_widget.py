from datetime import timedelta

import pyqtgraph as pg
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QVBoxLayout,
    QWidget,
)

from src.frontend.ui_styles import (
    FMB,
    FML,
    FMS,
    PLOT_BG,
    PLOT_GRID,
    C,
)
from src.frontend.widgets.common import (
    TimeAxisItem,
    create_label,
    create_panel,
)


class ChamberWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        self._build_status_panel(layout)
        self._build_chart(layout)

    
    def _make_plot_non_interactive(self, plot_widget) -> None:
        plot_item = plot_widget.getPlotItem()
        view_box = plot_item.getViewBox()

        view_box.setMouseEnabled(x=False, y=False)
        plot_item.setMenuEnabled(False)
        plot_item.hideButtons()

        plot_widget.viewport().setAttribute(
            Qt.WidgetAttribute.WA_TransparentForMouseEvents,
            True,
        )
        plot_widget.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        plot_widget.setContextMenuPolicy(Qt.ContextMenuPolicy.NoContextMenu)

    def _build_status_panel(self, layout):
        panel = create_panel()

        panel_layout = QHBoxLayout(panel)
        panel_layout.setContentsMargins(
            12,
            8,
            12,
            8,
        )

        title_layout = QVBoxLayout()
        title_layout.setSpacing(2)

        title_layout.addWidget(
            create_label(
                "ENVIRONMENTAL CHAMBER",
                FML,
                C["orange"],
            )
        )

        self.status_label = create_label(
            "● OFFLINE",
            FMB,
            C["red"],
        )
        title_layout.addWidget(self.status_label)

        panel_layout.addLayout(title_layout)
        panel_layout.addStretch()

        temperature_card = create_panel("metricCard")

        temperature_layout = QVBoxLayout(temperature_card)
        temperature_layout.setContentsMargins(
            16,
            6,
            16,
            6,
        )
        temperature_layout.setSpacing(0)

        title = create_label(
            "CHAMBER TEMPERATURE",
            FMS,
            C["dim"],
        )
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.temperature_label = create_label(
            "—— °C",
            ("Consolas", 23, True),
            C["orange"],
        )
        self.temperature_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        temperature_layout.addWidget(title)
        temperature_layout.addWidget(self.temperature_label)

        panel_layout.addWidget(temperature_card)

        layout.addWidget(panel)

    def _build_chart(self, layout):
        panel = create_panel()

        chart_layout = QVBoxLayout(panel)
        chart_layout.setContentsMargins(
            10,
            8,
            10,
            8,
        )
        chart_layout.setSpacing(4)

        chart_layout.addWidget(
            create_label(
                "CHAMBER TEMPERATURE TREND",
                FML,
                C["orange"],
            )
        )

        time_axis = TimeAxisItem(orientation="bottom")

        self.plot = pg.PlotWidget(
            axisItems={
                "bottom": time_axis,
            }
        )
        self._make_plot_non_interactive(self.plot)
        self.plot.setBackground(PLOT_BG)
        self.plot.showGrid(
            x=True,
            y=True,
            alpha=0.25,
        )

        self.plot.setLabel(
            "left",
            "Temperature",
            units="°C",
            color=C["dim"],
        )
        self.plot.setLabel(
            "bottom",
            "Time",
            color=C["dim"],
        )

        for axis_name in ("left", "bottom"):
            axis = self.plot.getAxis(axis_name)
            axis.setTextPen(pg.mkPen(C["dim"]))
            axis.setPen(pg.mkPen(PLOT_GRID))

        self.plot.setMouseEnabled(
            x=True,
            y=True,
        )

        self.line = self.plot.plot(
            [],
            [],
            pen=pg.mkPen(
                color=C["orange"],
                width=2,
            ),
        )

        chart_layout.addWidget(self.plot)
        layout.addWidget(panel, 3)

    def update_state(
        self,
        chamber,
        max_points=600,
    ):
        if chamber.online:
            self.temperature_label.setText(f"{chamber.temp_c:.1f} °C")
            self.temperature_label.setStyleSheet(f"color: {C['orange']};")

            self.status_label.setText("● ONLINE")
            self.status_label.setStyleSheet(f"color: {C['green']};")

        else:
            self.temperature_label.setText("—— °C")
            self.temperature_label.setStyleSheet(f"color: {C['dim']};")

            self.status_label.setText("● OFFLINE")
            self.status_label.setStyleSheet(f"color: {C['red']};")

            return

        if len(chamber.time_hist) < 2:
            return

        end_time = chamber.time_hist[-1]
        start_time = end_time - timedelta(minutes=1)

        filtered = [
            (t, temp)
            for t, temp in zip(chamber.time_hist, chamber.temp_hist)
            if t >= start_time
        ]

        if not filtered:
            return

        recent_times, temperatures = zip(*filtered)

        timestamps = [t.timestamp() for t in recent_times]

        self.line.setData(
            timestamps,
            temperatures,
        )

        self.plot.setXRange(
            start_time.timestamp(),
            end_time.timestamp(),
            padding=0,
        )
