import datetime

import pyqtgraph as pg
from PySide6.QtWidgets import QFrame, QLabel

from src.frontend.ui_styles import FM, font


def create_label(text, font_spec=FM, color=None):
    label = QLabel(text)
    label.setFont(font(font_spec))

    if color:
        label.setStyleSheet(
            f"""
            QLabel {{
                color: {color};
                background: transparent;
                border: none;
            }}
            """
        )

    return label


def create_panel(object_name="panel"):
    frame = QFrame()
    frame.setObjectName(object_name)
    return frame


class TimeAxisItem(pg.AxisItem):
    def tickStrings(
        self,
        values,
        scale,
        spacing,
    ):
        labels = []

        for value in values:
            try:
                timestamp = datetime.datetime.fromtimestamp(value)
                labels.append(timestamp.strftime("%H:%M:%S"))

            except (
                ValueError,
                OSError,
                OverflowError,
            ):
                labels.append("")

        return labels
