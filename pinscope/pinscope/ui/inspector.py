from __future__ import annotations
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QLabel, QSlider, 
                               QSpinBox, QPushButton, QColorDialog, QHBoxLayout, QGroupBox)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from ..app_state import AppState
from ..model.pin import Pin

class InspectorPanel(QWidget):
    def __init__(self, app_state: AppState, parent=None):
        super().__init__(parent)
        self.app_state = app_state
        self._updating_ui = False
        
        self._setup_ui()
        self.app_state.selection_changed.connect(self._on_selection_changed)
        self.app_state.pin_changed.connect(self._on_pin_changed)

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        
        # Height Group
        height_group = QGroupBox("Height")
        height_layout = QHBoxLayout(height_group)
        
        self.height_slider = QSlider(Qt.Orientation.Horizontal)
        self.height_slider.setRange(0, 200)
        self.height_spinbox = QSpinBox()
        self.height_spinbox.setRange(0, 200)
        self.height_spinbox.setSuffix(" mm")
        
        self.height_slider.valueChanged.connect(self.height_spinbox.setValue)
        self.height_spinbox.valueChanged.connect(self.height_slider.setValue)
        self.height_slider.valueChanged.connect(self._on_value_changed)
        
        height_layout.addWidget(self.height_slider)
        height_layout.addWidget(self.height_spinbox)
        layout.addWidget(height_group)
        
        # Color Group
        color_group = QGroupBox("Color")
        color_layout = QVBoxLayout(color_group)
        
        self.color_btn = QPushButton("Select Color")
        self.color_btn.clicked.connect(self._on_color_clicked)
        
        self.color_preview = QLabel()
        self.color_preview.setFixedSize(50, 20)
        self.color_preview.setAutoFillBackground(True)
        self.color_preview.setStyleSheet("background-color: black; border: 1px solid gray;")
        
        color_row = QHBoxLayout()
        color_row.addWidget(self.color_btn)
        color_row.addWidget(self.color_preview)
        
        color_layout.addLayout(color_row)
        layout.addWidget(color_group)
        
        layout.addStretch()
        
        self.setEnabled(False) # Disable until selection exists
        self.current_color = QColor(0, 0, 0)

    def _on_selection_changed(self):
        indices = self.app_state.selected_indices
        if not indices:
            self.setEnabled(False)
            return
            
        self.setEnabled(True)
        
        # Use the first selected pin to populate UI
        first_idx = next(iter(indices))
        pin = self.app_state.design.pins[first_idx]
        
        self._updating_ui = True
        self.height_slider.setValue(pin.height)
        self.current_color = QColor(pin.r, pin.g, pin.b)
        self._update_color_preview()
        self._updating_ui = False

    def _on_pin_changed(self, index: int):
        if index in self.app_state.selected_indices and not self._updating_ui:
            self._on_selection_changed()

    def _on_value_changed(self):
        if self._updating_ui:
            return
            
        height = self.height_slider.value()
        r, g, b = self.current_color.red(), self.current_color.green(), self.current_color.blue()
        
        pin = Pin(height, r, g, b)
        self.app_state.set_pins(self.app_state.selected_indices, pin)

    def _on_color_clicked(self):
        color = QColorDialog.getColor(self.current_color, self, "Select Pin Color")
        if color.isValid():
            self.current_color = color
            self._update_color_preview()
            self._on_value_changed()
            
    def _update_color_preview(self):
        self.color_preview.setStyleSheet(f"background-color: {self.current_color.name()}; border: 1px solid gray;")
