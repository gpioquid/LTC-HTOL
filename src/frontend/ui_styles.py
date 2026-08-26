from PySide6.QtGui import QFont

C = {
    "bg": "#080b10",
    "panel": "#0f141b",
    "card": "#202c38",
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

MONITOR_BG = "#111C27"
MONITOR_BORDER = "#344B5E"
MONITOR_HEADING = "#7095AC"

PROGRESS_BG = "#0D161F"
PROGRESS_TEXT = "#E6F1F8"


def font(spec):
    result = QFont(spec[0], spec[1])

    if len(spec) > 2:
        result.setBold(bool(spec[2]))

    return result


APP_STYLESHEET = f"""

QFrame[machineState="openFuse"] {{
    border: 2px solid #FF9F43;
    background-color: #2B2118;
}}

QLabel[status="openFuse"] {{
    color: #FF9F43;
    font-weight: bold;
}}

QFrame#monitoringContainer {{
    background-color: #111C27;
    border: 1px solid #344B5E;
    border-radius: 7px;
}}

QFrame#monitoringContainer QLabel {{
    border: none;
    background-color: transparent;
}}

QLabel#monitoringHeading {{
    color: #7095AC;
    border: none;
    background-color: transparent;
}}

QProgressBar#machineProgressBar {{
    color: #E6F1F8;
    background-color: #0D161F;
    border: 1px solid #344B5E;
    border-radius: 4px;
    text-align: center;
    font-size: 10px;
    padding: 0;
}}

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

QFrame#machineCard {{
    background: {C["card"]};
    border: 1px solid {C["border"]};
    border-radius: 10px;
    }}

    QFrame#machineCard[hovered="true"] {{
        background: {C["card_hover"]};
        border-color: {C["cyan"]};
    }}

    QFrame#machineCard[state="idle"] {{
        border: 1px solid {C["border2"]};
    }}

    QFrame#machineCard[state="running"] {{
        border: 2px solid {C["green"]};
    }}

    QFrame#machineCard[state="paused"] {{
        border: 2px solid {C["yellow"]};
    }}

    QFrame#machineCard[state="offline"] {{
        border: 1px solid {C["red"]};
    }}

    QFrame#machineCard {{
        background: #1f242b;
        border: 1px solid #303844;
        border-left: 5px solid #4f8cff;
        border-radius: 14px;
    }}

    QFrame#machineCard[hovered="true"] {{
        background: #272f39;
        border: 1px solid #4f8cff;
        border-left: 5px solid #4f8cff;
    }}

    QFrame#machineCard[state="running"] QFrame#machineCardContent {{
    border: 2px solid #21d07a;
}}

QFrame#machineCard[state="paused"] QFrame#machineCardContent {{
    border: 2px solid #f5c451;
}}



QFrame#machineCard[state="offline"] QFrame#machineCardContent {{
    border: 2px solid #708598;
}}
    QFrame#metricCard {{
        background: #161b22;
        border: 1px solid #303844;
        border-radius: 8px;
    }}
    QFrame#machineCard {{
    background: #111923;
    border: 1px solid #263444;
    border-radius: 18px;
}}

QFrame#machineCardContent {{
    background: #141d28;
    border: 1px solid #314050;
    border-radius: 14px;
}}
QFrame#machineCard[hovered="true"] {{
    background: #10161d;
}}

QFrame#machineCard[hovered="true"] QFrame#machineCardContent {{
    border: 1px solid #35c8ff;
    background: #1b2734;
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
