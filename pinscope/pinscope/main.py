import sys
import argparse
from PySide6.QtWidgets import QApplication
from .app_state import AppState
from .ui.main_window import MainWindow


def main():
    parser = argparse.ArgumentParser(prog="pinscope")
    parser.add_argument("--touch", action="store_true", help="Launch touchscreen mode")
    args, qt_args = parser.parse_known_args()

    app = QApplication(sys.argv[:1] + qt_args)
    app_state = AppState()

    if args.touch:
        from .ui.touch_window import TouchWindow
        window = TouchWindow(app_state)  # calls showFullScreen() internally
    else:
        window = MainWindow(app_state)
        window.show()

    app_state.design_changed.emit()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
