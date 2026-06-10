from __future__ import annotations
import math
import numpy as np
import pyqtgraph as pg
import pyqtgraph.opengl as gl
from PySide6.QtCore import Qt, QEvent
from PySide6.QtGui import QEventPoint
from PySide6.QtWidgets import QWidget, QVBoxLayout, QPushButton
from ..app_state import AppState

PIN_SIZE = 40
PIN_GAP = 1
CELL = PIN_SIZE + PIN_GAP
MIN_VISUAL_H = 1.0
GRID_EXTENT = 8 * CELL - PIN_GAP

# ── Box geometry ───────────────────────────────────────────────────────────────
# Unit box: top verts at z=1, bottom at z=0. Height is baked per-update by
# scaling the z column of a copy of _BASE_VERTS.

_HALF = PIN_SIZE / 2.0

_BASE_VERTS = np.array([
    [ _HALF,  _HALF, 1.0],  # 0  top  NE
    [ _HALF, -_HALF, 1.0],  # 1  top  SE
    [-_HALF, -_HALF, 1.0],  # 2  top  SW
    [-_HALF,  _HALF, 1.0],  # 3  top  NW
    [ _HALF,  _HALF, 0.0],  # 4  bot  NE
    [ _HALF, -_HALF, 0.0],  # 5  bot  SE
    [-_HALF, -_HALF, 0.0],  # 6  bot  SW
    [-_HALF,  _HALF, 0.0],  # 7  bot  NW
], dtype=np.float32)

_BASE_FACES = np.array([
    [0, 1, 2], [0, 2, 3],   # top     (z+)
    [4, 6, 5], [4, 7, 6],   # bottom  (z-)
    [0, 4, 5], [0, 5, 1],   # east    (x+)
    [1, 5, 6], [1, 6, 2],   # south   (y-)
    [2, 6, 7], [2, 7, 3],   # west    (x-)
    [3, 7, 4], [3, 4, 0],   # north   (y+)
], dtype=np.int32)

# ── Per-face brightness ────────────────────────────────────────────────────────
# Camera: elevation=30°, azimuth=-45° → sits in the +x, −y, +z direction.
# Faces pointing toward the camera receive higher brightness.
#   top:   fully lit from above
#   east:  primary lit side (normal +x, camera is +x)
#   south: secondary lit side (normal −y, camera is −y)
#   north: partially shadowed (away from camera)
#   west:  most shadowed (away from camera)
#   bottom: nearly black (ground plane, never seen)

_FACE_BRIGHTNESS = np.array([
    1.00, 1.00,  # top
    0.15, 0.15,  # bottom
    0.72, 0.72,  # east   (x+)  lit
    0.62, 0.62,  # south  (y-)  lit
    0.36, 0.36,  # west   (x-)  shadow
    0.44, 0.44,  # north  (y+)  shadow
], dtype=np.float32)


def _make_face_colors(r: int, g: int, b: int) -> np.ndarray:
    base = np.array([r / 255.0, g / 255.0, b / 255.0], dtype=np.float32)
    rgb = _FACE_BRIGHTNESS[:, np.newaxis] * base        # (12, 3)
    return np.hstack([rgb, np.ones((12, 1), dtype=np.float32)])  # (12, 4)


def _make_mesh_data(h: float, r: int, g: int, b: int) -> gl.MeshData:
    verts = _BASE_VERTS.copy()
    verts[:, 2] *= h    # scale z: top verts 1→h, bottom verts 0→0
    return gl.MeshData(vertexes=verts, faces=_BASE_FACES.copy(),
                       faceColors=_make_face_colors(r, g, b))


class TouchGLViewWidget(gl.GLViewWidget):
    """GLViewWidget with touch support.

    1 finger  → orbit   (same as left-mouse drag)
    2 fingers → pinch to zoom + two-finger pan
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setAttribute(Qt.WidgetAttribute.WA_AcceptTouchEvents, True)

    def event(self, ev):
        t = ev.type()
        if t in (QEvent.Type.TouchBegin, QEvent.Type.TouchUpdate, QEvent.Type.TouchEnd):
            ev.accept()
            if t == QEvent.Type.TouchUpdate:
                self._on_touch_update(ev)
            return True
        return super().event(ev)

    def _on_touch_update(self, ev):
        active = [p for p in ev.points()
                  if p.state() != QEventPoint.State.Released]

        if len(active) >= 2:
            p0, p1 = active[0], active[1]
            c0, c1 = p0.position(), p1.position()
            l0, l1 = p0.lastPosition(), p1.lastPosition()

            # pinch-to-zoom: scale distance by change in finger span
            cur_span = math.hypot(c1.x() - c0.x(), c1.y() - c0.y())
            prv_span = math.hypot(l1.x() - l0.x(), l1.y() - l0.y())
            if prv_span > 1.0:
                self.opts['distance'] *= prv_span / cur_span

        elif len(active) == 1:
            p = active[0]
            diff = p.position() - p.lastPosition()
            self.orbit(-diff.x() * 0.1, diff.y() * 0.1)

        self.update()


class View3D(QWidget):
    def __init__(self, app_state: AppState, parent=None):
        super().__init__(parent)
        self.app_state = app_state

        self._setup_ui()
        self._init_3d_scene()

        self.app_state.design_changed.connect(self._on_design_changed)
        self.app_state.pin_changed.connect(self._on_pin_changed)

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.gl_widget = TouchGLViewWidget()
        self.gl_widget.setBackgroundColor((20, 20, 20, 255))
        layout.addWidget(self.gl_widget)

        self.reset_btn = QPushButton("Reset Camera", self.gl_widget)
        self.reset_btn.clicked.connect(self._reset_camera)
        self.reset_btn.move(10, 10)

    def _init_3d_scene(self):
        self._reset_camera()

        grid = gl.GLGridItem()
        grid.setSize(GRID_EXTENT, GRID_EXTENT)
        grid.setSpacing(CELL, CELL)
        grid.setColor((60, 60, 60, 120))
        grid.translate(GRID_EXTENT / 2, GRID_EXTENT / 2, 0)
        self.gl_widget.addItem(grid)

        self.pin_items: list[tuple] = []  # (x, y, mesh)

        for row in range(8):
            for col in range(8):
                x = col * CELL + _HALF
                y = (7 - row) * CELL + _HALF

                md = _make_mesh_data(MIN_VISUAL_H, 0, 0, 0)
                mesh = gl.GLMeshItem(meshdata=md, smooth=False,
                                     shader=None, glOptions='opaque')
                mesh.translate(x, y, 0)
                self.gl_widget.addItem(mesh)
                self.pin_items.append((x, y, mesh))

        self._on_design_changed()

    def _reset_camera(self):
        centre = GRID_EXTENT / 2
        self.gl_widget.setCameraPosition(distance=700, elevation=30, azimuth=-45)
        self.gl_widget.opts['center'] = pg.Vector(centre, centre, 0)

    def _update_pin_visuals(self, index: int):
        pin = self.app_state.design.pins[index]
        _, _, mesh = self.pin_items[index]

        h = max(float(pin.height), MIN_VISUAL_H)
        mesh.setMeshData(meshdata=_make_mesh_data(h, pin.r, pin.g, pin.b))

    def _on_design_changed(self):
        for i in range(64):
            self._update_pin_visuals(i)

    def _on_pin_changed(self, index: int):
        self._update_pin_visuals(index)
