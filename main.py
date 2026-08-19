import sys

from PySide6.QtWidgets import QApplication

from src.frontend.main_window import HTOLMonitor
from src.frontend.ui_styles import APP_STYLESHEET


def main():
    app = QApplication(sys.argv)
    app.setStyleSheet(APP_STYLESHEET)

    window = HTOLMonitor()
    window.show()

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
