from __future__ import annotations
from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QDockWidget,
                               QFileDialog, QMessageBox, QSplitter)
from PySide6.QtCore import Qt, QSettings
from PySide6.QtGui import QKeySequence
import os
from .grid_2d import Grid2D
from .view_3d import View3D
from .inspector import InspectorPanel
from .globals_panel import GlobalsPanel
from .connection_panel import ConnectionPanel
from ..app_state import AppState
from ..io import design_io
from ..io.tcp_client import TcpClient


class MainWindow(QMainWindow):
    def __init__(self, app_state: AppState, parent=None):
        super().__init__(parent)
        self.app_state = app_state
        self.current_file = None
        self.settings = QSettings("MIT", "PinScope")
        self.tcp = TcpClient(self)

        self.setWindowTitle("PinScope Control Panel - Untitled")
        self.resize(1100, 700)

        self._setup_ui()
        self._setup_menus()
        self._update_recent_files_menu()

    def _make_dock(self, title: str, widget: QWidget, area: Qt.DockWidgetArea) -> QDockWidget:
        dock = QDockWidget(title, self)
        dock.setFeatures(QDockWidget.DockWidgetFeature.NoDockWidgetFeatures)
        dock.setAllowedAreas(area)
        dock.setWidget(widget)
        self.addDockWidget(area, dock)
        return dock

    def _setup_ui(self) -> None:
        central_widget = QWidget()
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        splitter = QSplitter(Qt.Orientation.Vertical)

        self.grid_2d = Grid2D(self.app_state)
        self.view_3d = View3D(self.app_state)

        splitter.addWidget(self.grid_2d)
        splitter.addWidget(self.view_3d)
        splitter.setSizes([300, 400])

        layout.addWidget(splitter)

        # Connection bar pinned to the bottom of the central widget
        self.connection_panel = ConnectionPanel(self.app_state, self.tcp)
        layout.addWidget(self.connection_panel)

        self.setCentralWidget(central_widget)

        # Right docks
        self.inspector_panel = InspectorPanel(self.app_state)
        self._make_dock("Inspector", self.inspector_panel, Qt.DockWidgetArea.RightDockWidgetArea)

        self.globals_panel = GlobalsPanel(self.app_state)
        self._make_dock("Globals", self.globals_panel, Qt.DockWidgetArea.RightDockWidgetArea)

    def _setup_menus(self) -> None:
        menu_bar = self.menuBar()
        menu_bar.setNativeMenuBar(False)

        file_menu = menu_bar.addMenu("File")

        open_action = file_menu.addAction("Open...")
        open_action.setShortcut(QKeySequence.StandardKey.Open)
        open_action.triggered.connect(self._on_open)

        self.recent_menu = file_menu.addMenu("Recent Files")

        file_menu.addSeparator()

        save_action = file_menu.addAction("Save")
        save_action.setShortcut(QKeySequence.StandardKey.Save)
        save_action.triggered.connect(self._on_save)

        save_as_action = file_menu.addAction("Save As...")
        save_as_action.setShortcut(QKeySequence.StandardKey.SaveAs)
        save_as_action.triggered.connect(self._on_save_as)

        menu_bar.addMenu("Edit")
        menu_bar.addMenu("View")
        menu_bar.addMenu("Deploy")
        menu_bar.addMenu("Help")

    def _on_open(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Open Design", "", "PinScope Design (*.pinscope.json);;All Files (*)"
        )
        if file_path:
            self._load_file(file_path)

    def _load_file(self, file_path: str):
        try:
            design = design_io.load(file_path)
            self.app_state.set_design(design)
            self.current_file = file_path
            self._add_recent_file(file_path)
            name = os.path.basename(file_path)
            self.setWindowTitle(f"PinScope Control Panel - {name}")
        except Exception as e:
            QMessageBox.critical(self, "Error Loading File", str(e))

    def _on_save(self):
        if self.current_file:
            self._save_file(self.current_file)
        else:
            self._on_save_as()

    def _on_save_as(self):
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save Design", "", "PinScope Design (*.pinscope.json)"
        )
        if file_path:
            if not file_path.endswith(".pinscope.json"):
                if file_path.endswith(".json"):
                    file_path = file_path[:-5] + ".pinscope.json"
                else:
                    file_path += ".pinscope.json"
            self._save_file(file_path)

    def _save_file(self, file_path: str):
        try:
            self.app_state.design.name = os.path.splitext(os.path.basename(file_path))[0]
            design_io.save(file_path, self.app_state.design)
            self.current_file = file_path
            self._add_recent_file(file_path)
            name = os.path.basename(file_path)
            self.setWindowTitle(f"PinScope Control Panel - {name}")
        except Exception as e:
            QMessageBox.critical(self, "Error Saving File", str(e))

    def _add_recent_file(self, file_path: str):
        recent_files = self.settings.value("recent_files", [])
        if file_path in recent_files:
            recent_files.remove(file_path)
        recent_files.insert(0, file_path)
        recent_files = recent_files[:10]
        self.settings.setValue("recent_files", recent_files)
        self._update_recent_files_menu()

    def _update_recent_files_menu(self):
        self.recent_menu.clear()
        recent_files = self.settings.value("recent_files", [])
        if not recent_files:
            action = self.recent_menu.addAction("No Recent Files")
            action.setEnabled(False)
        else:
            for file_path in recent_files:
                action = self.recent_menu.addAction(os.path.basename(file_path))
                action.triggered.connect(lambda checked=False, p=file_path: self._load_file(p))
