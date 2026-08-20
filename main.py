import sys

from PySide6.QtWidgets import QApplication

from src.frontend.main_window import HTOLMonitor
from src.frontend.ui_styles import APP_STYLESHEET
from src.backend.instrument_drivers import connect_psus, disconnect_psus


def main():
    app = QApplication(sys.argv)
    app.setStyleSheet(APP_STYLESHEET)

    #connect the PSUs before monitoring starts
    connect_psus()

    #Automatically close PSU and VISA resources when the app exits
    app.aboutToQuit.connect(disconnect_psus)

    window = HTOLMonitor()
    window.show()

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
