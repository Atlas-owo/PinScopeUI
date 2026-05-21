from __future__ import annotations
from PySide6.QtWidgets import QGraphicsView, QGraphicsScene, QGraphicsRectItem
from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QColor, QBrush, QPen, QPainter
from ..app_state import AppState

class PinItem(QGraphicsRectItem):
    def __init__(self, index: int, x: float, y: float, size: float):
        super().__init__(QRectF(x, y, size, size))
        self.index = index
        self.setFlag(QGraphicsRectItem.GraphicsItemFlag.ItemIsSelectable, True)
        self.setBrush(QBrush(QColor(0, 0, 0)))
        self.setPen(QPen(QColor(50, 50, 50)))

    def itemChange(self, change, value):
        if change == QGraphicsRectItem.GraphicsItemChange.ItemSelectedChange:
            if value:
                self.setPen(QPen(QColor(255, 200, 0), 3))  # High-contrast yellow outline
            else:
                self.setPen(QPen(QColor(50, 50, 50), 1))
        return super().itemChange(change, value)

    def update_from_pin(self, pin):
        self.setBrush(QBrush(QColor(pin.r, pin.g, pin.b)))
        # Optional: could visually indicate height later

class Grid2D(QGraphicsView):
    def __init__(self, app_state: AppState, parent=None):
        super().__init__(parent)
        self.app_state = app_state
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)
        
        self.cell_size = 50.0
        self.padding = 5.0
        
        self.setDragMode(QGraphicsView.DragMode.RubberBandDrag)
        
        self.pin_items: list[PinItem] = []
        self._updating_selection = False
        self._init_grid()
        
        # Connect signals
        self.scene.selectionChanged.connect(self._on_scene_selection_changed)
        self.app_state.design_changed.connect(self._on_design_changed)
        self.app_state.pin_changed.connect(self._on_pin_changed)
        self.app_state.selection_changed.connect(self._on_app_state_selection_changed)

    def _init_grid(self) -> None:
        for row in range(8):
            for col in range(8):
                idx = row * 8 + col
                x = col * (self.cell_size + self.padding)
                y = row * (self.cell_size + self.padding)
                item = PinItem(idx, x, y, self.cell_size)
                self.scene.addItem(item)
                self.pin_items.append(item)
        
        self.setSceneRect(self.scene.itemsBoundingRect())
        self.setRenderHint(QPainter.RenderHint.Antialiasing)

    def _on_design_changed(self) -> None:
        design = self.app_state.design
        for i, pin in enumerate(design.pins):
            self.pin_items[i].update_from_pin(pin)

    def _on_pin_changed(self, index: int) -> None:
        pin = self.app_state.design.pins[index]
        self.pin_items[index].update_from_pin(pin)

    def _on_scene_selection_changed(self) -> None:
        if self._updating_selection:
            return
        selected_items = self.scene.selectedItems()
        indices = {item.index for item in selected_items if isinstance(item, PinItem)}
        self._updating_selection = True
        self.app_state.set_selection(indices)
        self._updating_selection = False

    def _on_app_state_selection_changed(self) -> None:
        if self._updating_selection:
            return
        self._updating_selection = True
        indices = self.app_state.selected_indices
        for item in self.pin_items:
            item.setSelected(item.index in indices)
        self._updating_selection = False
