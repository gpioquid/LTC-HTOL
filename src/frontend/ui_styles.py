from PySide6.QtGui import QFont

C = {
    "bg": "#080b10",
    "panel": "#0f141b",
    "card": "#141b24",
    "card_hover": "#18222e",
    "border": "#202b38",
    "border2": "#2b3a4a",
    "text": "#d8e5f0",
    "dim": "#708598",
    "green": "#21d07a",
    "yellow": "#f5c451",
    "red": "#ff5d6c",
    "cyan": "#35c8ff",
    "orange": "#ff9e57",
    "purple": "#b693ff",
    "white": "#ffffff",
    "tile_bg": "#0c1219",
}

ACCENTS = [
    C["cyan"],
    C["green"],
    C["yellow"],
    C["orange"],
    C["purple"],
    C["red"],
]

FM = ("Consolas", 10)
FMS = ("Consolas", 9)
FMB = ("Consolas", 11, True)
FML = ("Consolas", 13, True)

PLOT_BG = C["tile_bg"]
PLOT_GRID = "#233142"
PLOT_TEXT = C["dim"]


def font(spec):
    result = QFont(spec[0], spec[1])

    if len(spec) > 2:
        result.setBold(bool(spec[2]))

    return result


APP_STYLESHEET = f"""
QWidget {{
    background: {C["bg"]};
    color: {C["text"]};
    font-family: "Consolas";
    font-size: 10pt;
}}

QMainWindow {{
    background: {C["bg"]};
}}

QFrame#panel {{
    background: {C["panel"]};
    border: 1px solid {C["border"]};
    border-radius: 8px;
}}

QFrame#card {{
    background: {C["card"]};
    border: 1px solid {C["border"]};
    border-radius: 8px;
}}

QFrame#card:hover {{
    border-color: {C["border2"]};
}}

QFrame#metricCard {{
    background: {C["tile_bg"]};
    border: 1px solid {C["border"]};
    border-radius: 7px;
}}

QLabel {{
    background: transparent;
    border: none;
}}

QLabel#headerMetric {{
    background: {C["tile_bg"]};
    border: 1px solid {C["border"]};
    border-radius: 5px;
    padding: 7px 10px;
}}

QLineEdit,
QPlainTextEdit {{
    background: {C["tile_bg"]};
    color: {C["text"]};
    border: 1px solid {C["border2"]};
    border-radius: 5px;
    padding: 6px 8px;
    selection-background-color: {C["cyan"]};
    selection-color: {C["bg"]};
}}

QLineEdit:hover,
QPlainTextEdit:hover {{
    border-color: {C["dim"]};
}}

QLineEdit:focus,
QPlainTextEdit:focus {{
    border: 1px solid {C["cyan"]};
}}

QLineEdit:disabled {{
    color: {C["dim"]};
    background: {C["panel"]};
}}

QPushButton {{
    background: {C["card"]};
    color: {C["text"]};
    border: 1px solid {C["border2"]};
    border-radius: 5px;
    padding: 6px 10px;
    min-height: 22px;
}}

QPushButton:hover {{
    background: {C["card_hover"]};
    border-color: {C["cyan"]};
}}

QPushButton:pressed {{
    background: {C["border2"]};
}}

QPushButton:disabled {{
    color: {C["dim"]};
    border-color: {C["border"]};
}}

QProgressBar {{
    background: {C["tile_bg"]};
    color: {C["text"]};
    border: 1px solid {C["border2"]};
    border-radius: 4px;
    text-align: center;
}}

QProgressBar::chunk {{
    background: {C["cyan"]};
    border-radius: 3px;
}}

QScrollArea {{
    border: none;
    background: transparent;
}}

QScrollArea > QWidget > QWidget {{
    background: {C["bg"]};
}}

QScrollBar:vertical {{
    background: {C["panel"]};
    width: 10px;
    margin: 0;
}}

QScrollBar::handle:vertical {{
    background: {C["border2"]};
    min-height: 28px;
    border-radius: 5px;
}}

QScrollBar::handle:vertical:hover {{
    background: {C["dim"]};
}}

QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical {{
    height: 0;
}}

QScrollBar:horizontal {{
    background: {C["panel"]};
    height: 10px;
}}

QScrollBar::handle:horizontal {{
    background: {C["border2"]};
    min-width: 28px;
    border-radius: 5px;
}}

QScrollBar::add-line:horizontal,
QScrollBar::sub-line:horizontal {{
    width: 0;
}}

QSplitter::handle {{
    background: {C["border"]};
    width: 3px;
}}

QSplitter::handle:hover {{
    background: {C["cyan"]};
}}

QToolTip {{
    background: {C["card"]};
    color: {C["text"]};
    border: 1px solid {C["cyan"]};
    padding: 5px;
}}

QMessageBox {{
    background: {C["panel"]};
}}

QInputDialog {{
    background: {C["panel"]};
}}
"""


def button_style(color, filled=False):
    background = color if filled else C["card"]
    foreground = C["bg"] if filled else color

    if filled:
        hover_background = C["border2"]
        hover_foreground = C["white"]
    else:
        hover_background = color
        hover_foreground = C["bg"]

    return f"""
    QPushButton {{
        background: {background};
        color: {foreground};
        border: 1px solid {color};
        border-radius: 5px;
        padding: 6px 10px;
        font-weight: 700;
    }}

    QPushButton:hover {{
        background: {hover_background};
        color: {hover_foreground};
        border-color: {color};
    }}

    QPushButton:pressed {{
        background: {C["border2"]};
        color: {C["white"]};
    }}
    """
