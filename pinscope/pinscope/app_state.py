from __future__ import annotations
from PySide6.QtCore import QObject, Signal
from .model.design import Design
from .model.pin import Pin
from .model.gesture import GestureConfig

class AppState(QObject):
    design_changed = Signal()
    selection_changed = Signal()
    pin_changed = Signal(int)
    globals_changed = Signal()

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._design = Design()
        self._selected_indices: set[int] = set()

    @property
    def design(self) -> Design:
        return self._design

    @property
    def selected_indices(self) -> set[int]:
        return self._selected_indices

    def set_design(self, design: Design) -> None:
        self._design = design
        self.design_changed.emit()

    def set_pin(self, index: int, pin: Pin) -> None:
        if 0 <= index < 64:
            self._design.pins[index] = pin
            self.pin_changed.emit(index)
            self.design_changed.emit()

    def set_pins(self, indices: set[int], pin: Pin) -> None:
        for index in indices:
            if 0 <= index < 64:
                # Create a new Pin instance to avoid reference sharing
                self._design.pins[index] = Pin(pin.height, pin.r, pin.g, pin.b)
                self.pin_changed.emit(index)
        if indices:
            self.design_changed.emit()

    def set_selection(self, indices: set[int]) -> None:
        if self._selected_indices != indices:
            self._selected_indices = indices
            self.selection_changed.emit()

    def clear_selection(self) -> None:
        if self._selected_indices:
            self._selected_indices.clear()
            self.selection_changed.emit()

    def set_motor_speed(self, start: int, end: int) -> None:
        self._design.motor_start_speed = start
        self._design.motor_end_speed = end
        self.globals_changed.emit()

    def set_push_config(self, config: GestureConfig) -> None:
        self._design.push_config = config
        self.globals_changed.emit()

    def set_pull_config(self, config: GestureConfig) -> None:
        self._design.pull_config = config
        self.globals_changed.emit()
