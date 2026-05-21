from __future__ import annotations
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
    QLabel, QSpinBox, QComboBox, QPushButton, QColorDialog, QFormLayout,
)
from PySide6.QtGui import QColor
from ..app_state import AppState
from ..model.gesture import GestureConfig


class _GestureWidget(QWidget):
    """Controls for a single push or pull gesture (s:8 fields)."""

    def __init__(self, label: str, app_state: AppState, is_push: bool, parent=None):
        super().__init__(parent)
        self.app_state = app_state
        self.is_push = is_push
        self._updating = False

        group = QGroupBox(label)
        form = QFormLayout(group)
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)

        # Direction
        self.direction_combo = QComboBox()
        self.direction_combo.addItem("Extend", userData=1)
        self.direction_combo.addItem("Retract", userData=0)
        form.addRow("Direction:", self.direction_combo)

        # Step height
        step_row = QWidget()
        step_layout = QHBoxLayout(step_row)
        step_layout.setContentsMargins(0, 0, 0, 0)
        self.step_spin = QSpinBox()
        self.step_spin.setRange(0, 200)
        self.step_spin.setSuffix(" mm")
        step_layout.addWidget(self.step_spin)
        form.addRow("Step Height:", step_row)

        # LED color
        color_row = QWidget()
        color_layout = QHBoxLayout(color_row)
        color_layout.setContentsMargins(0, 0, 0, 0)
        self.color_btn = QPushButton("Select Color")
        self.color_btn.clicked.connect(self._on_color_clicked)
        self.color_preview = QLabel()
        self.color_preview.setFixedSize(50, 20)
        self.color_preview.setAutoFillBackground(True)
        color_layout.addWidget(self.color_btn)
        color_layout.addWidget(self.color_preview)
        form.addRow("LED Color:", color_row)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(group)

        self.direction_combo.currentIndexChanged.connect(self._on_changed)
        self.step_spin.valueChanged.connect(self._on_changed)

        self._color = QColor(255, 255, 255)
        self._refresh_preview()

    def load(self, cfg: GestureConfig) -> None:
        self._updating = True
        idx = self.direction_combo.findData(cfg.direction)
        self.direction_combo.setCurrentIndex(idx if idx >= 0 else 0)
        self.step_spin.setValue(cfg.step_height)
        self._color = QColor(cfg.r, cfg.g, cfg.b)
        self._refresh_preview()
        self._updating = False

    def _current_config(self) -> GestureConfig:
        direction = self.direction_combo.currentData()
        return GestureConfig(
            direction=direction,
            step_height=self.step_spin.value(),
            r=self._color.red(),
            g=self._color.green(),
            b=self._color.blue(),
        )

    def _on_changed(self) -> None:
        if self._updating:
            return
        cfg = self._current_config()
        if self.is_push:
            self.app_state.set_push_config(cfg)
        else:
            self.app_state.set_pull_config(cfg)

    def _on_color_clicked(self) -> None:
        color = QColorDialog.getColor(self._color, self, "Select LED Color")
        if color.isValid():
            self._color = color
            self._refresh_preview()
            self._on_changed()

    def _refresh_preview(self) -> None:
        self.color_preview.setStyleSheet(
            f"background-color: {self._color.name()}; border: 1px solid gray;"
        )


class GlobalsPanel(QWidget):
    def __init__(self, app_state: AppState, parent=None):
        super().__init__(parent)
        self.app_state = app_state
        self._updating = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)

        # Motor speed
        motor_group = QGroupBox("Motor Speed")
        motor_form = QFormLayout(motor_group)
        motor_form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)

        self.start_speed_spin = QSpinBox()
        self.start_speed_spin.setRange(1, 9999)
        self.start_speed_spin.setSuffix(" steps/s")
        motor_form.addRow("Start Speed:", self.start_speed_spin)

        self.end_speed_spin = QSpinBox()
        self.end_speed_spin.setRange(1, 9999)
        self.end_speed_spin.setSuffix(" steps/s")
        motor_form.addRow("End Speed:", self.end_speed_spin)

        layout.addWidget(motor_group)

        # Gesture configs
        self.push_widget = _GestureWidget("Push Gesture (UP)", app_state, is_push=True)
        self.pull_widget = _GestureWidget("Pull Gesture (DOWN)", app_state, is_push=False)
        layout.addWidget(self.push_widget)
        layout.addWidget(self.pull_widget)

        layout.addStretch()

        self.start_speed_spin.valueChanged.connect(self._on_speed_changed)
        self.end_speed_spin.valueChanged.connect(self._on_speed_changed)

        self.app_state.design_changed.connect(self._load_from_design)
        self.app_state.globals_changed.connect(self._load_from_design)
        self._load_from_design()

    def _load_from_design(self) -> None:
        self._updating = True
        d = self.app_state.design
        self.start_speed_spin.setValue(d.motor_start_speed)
        self.end_speed_spin.setValue(d.motor_end_speed)
        self.push_widget.load(d.push_config)
        self.pull_widget.load(d.pull_config)
        self._updating = False

    def _on_speed_changed(self) -> None:
        if self._updating:
            return
        self.app_state.set_motor_speed(
            self.start_speed_spin.value(),
            self.end_speed_spin.value(),
        )
