from __future__ import annotations
from PySide6.QtWidgets import QGraphicsView, QGraphicsScene, QGraphicsRectItem, QGraphicsTextItem
from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QColor, QBrush, QPen, QPainter, QFont
from ..app_state import AppState

# One distinct color per module border
_MODULE_COLORS = [
    QColor(255,  80,  80),  # 1 red
    QColor( 80, 160, 255),  # 2 blue
    QColor( 80, 220,  80),  # 3 green
    QColor(255, 180,  40),  # 4 orange
    QColor(200,  80, 255),  # 5 purple
    QColor( 40, 220, 220),  # 6 cyan
    QColor(255, 255,  60),  # 7 yellow
    QColor(255, 120, 200),  # 8 pink
]

class PinItem(QGraphicsRectItem):
    def __init__(self, index: int, x: float, y: float, size: float):
        super().__init__(QRectF(x, y, size, size))
        self.index = index
        self.setFlag(QGraphicsRectItem.GraphicsItemFlag.ItemIsSelectable, True)
        self.setBrush(QBrush(QColor(255, 255, 255)))
        self.setPen(QPen(QColor(90, 90, 90), 1))

    def itemChange(self, change, value):
        if change == QGraphicsRectItem.GraphicsItemChange.ItemSelectedChange:
            if value:
                self.setPen(QPen(QColor(255, 200, 0), 3))  # High-contrast yellow outline
            else:
                self.setPen(QPen(QColor(50, 50, 50), 1))
        return super().itemChange(change, value)

    def update_from_pin(self, pin):
        self.setBrush(QBrush(QColor(pin.r, pin.g, pin.b)))

class Grid2D(QGraphicsView):
    def __init__(self, app_state: AppState, parent=None):
        super().__init__(parent)
        self.app_state = app_state
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)

        self.cell_size = 36.0
        self.padding = 3.0

        self.setDragMode(QGraphicsView.DragMode.RubberBandDrag)
        self.setBackgroundBrush(QBrush(QColor(60, 60, 60)))

        self.pin_items: list[PinItem] = []
        self._updating_selection = False
        self._init_grid()

        self.scene.selectionChanged.connect(self._on_scene_selection_changed)
        self.app_state.design_changed.connect(self._on_design_changed)
        self.app_state.pin_changed.connect(self._on_pin_changed)
        self.app_state.selection_changed.connect(self._on_app_state_selection_changed)

    def _init_grid(self) -> None:
        MARGIN = 4.0  # gap between module border and pin cells

        # Draw module borders first (behind pins)
        for mod_row in range(4):       # 4 rows of modules
            for mod_col in range(2):   # 2 columns of modules
                board_i = mod_row * 2 + mod_col + 1    # 1..8 (0 is broadcast)
                color = _MODULE_COLORS[board_i - 1]

                # Pin grid coords covered by this module
                pin_row_start = mod_row * 2
                pin_col_start = mod_col * 4

                x = pin_col_start * (self.cell_size + self.padding) - MARGIN
                y = pin_row_start * (self.cell_size + self.padding) - MARGIN
                w = 4 * self.cell_size + 3 * self.padding + 2 * MARGIN
                h = 2 * self.cell_size + 1 * self.padding + 2 * MARGIN

                border = QGraphicsRectItem(QRectF(x, y, w, h))
                pen = QPen(color, 2)
                border.setPen(pen)
                border.setBrush(QBrush(Qt.BrushStyle.NoBrush))
                border.setZValue(-1)
                self.scene.addItem(border)

                label = QGraphicsTextItem(f"B{board_i}")
                label.setDefaultTextColor(color)
                font = QFont()
                font.setPointSize(7)
                font.setBold(True)
                label.setFont(font)
                label.setPos(x + 2, y + 1)
                label.setZValue(-1)
                self.scene.addItem(label)

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
