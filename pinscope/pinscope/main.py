import sys
from PySide6.QtWidgets import QApplication
from .app_state import AppState
from .ui.main_window import MainWindow

def main():
    app = QApplication(sys.argv)
    
    app_state = AppState()
    window = MainWindow(app_state)
    window.show()
    
    # Trigger initial render
    app_state.design_changed.emit()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
