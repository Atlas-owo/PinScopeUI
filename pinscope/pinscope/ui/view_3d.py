from __future__ import annotations
import numpy as np
import pyqtgraph as pg
import pyqtgraph.opengl as gl
from PySide6.QtWidgets import QWidget, QVBoxLayout, QPushButton
from ..app_state import AppState

PIN_SIZE = 40
PIN_GAP = 1
CELL = PIN_SIZE + PIN_GAP   # 41 mm per cell
MIN_VISUAL_H = 1.0
GRID_EXTENT = 8 * CELL - PIN_GAP  # 327 mm (no trailing gap)


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

        self.gl_widget = gl.GLViewWidget()
        self.gl_widget.setBackgroundColor((80, 80, 80, 255))
        layout.addWidget(self.gl_widget)

        self.reset_btn = QPushButton("Reset Camera", self.gl_widget)
        self.reset_btn.clicked.connect(self._reset_camera)
        self.reset_btn.move(10, 10)

    def _init_3d_scene(self):
        self._reset_camera()

        grid = gl.GLGridItem()
        grid.setSize(GRID_EXTENT, GRID_EXTENT)
        grid.setSpacing(CELL, CELL)
        grid.setColor((200, 200, 200, 80))
        grid.translate(GRID_EXTENT / 2, GRID_EXTENT / 2, 0)
        self.gl_widget.addItem(grid)

        self.pin_items = []  # (x, y, mesh, edges)

        half = PIN_SIZE / 2

        verts = np.array([
            [ half,  half, 1.0], [ half, -half, 1.0], [-half, -half, 1.0], [-half,  half, 1.0],
            [ half,  half, 0.0], [ half, -half, 0.0], [-half, -half, 0.0], [-half,  half, 0.0],
        ], dtype=float)
        faces = np.array([
            [0, 1, 2], [0, 2, 3],
            [4, 6, 5], [4, 7, 6],
            [0, 4, 5], [0, 5, 1],
            [1, 5, 6], [1, 6, 2],
            [2, 6, 7], [2, 7, 3],
            [3, 7, 4], [3, 4, 0],
        ])
        md = gl.MeshData(vertexes=verts, faces=faces)

        edge_pairs = [
            (0,1),(1,2),(2,3),(3,0),
            (4,5),(5,6),(6,7),(7,4),
            (0,4),(1,5),(2,6),(3,7),
        ]
        edge_pts = np.array(
            [pt for a, b in edge_pairs for pt in (verts[a], verts[b])],
            dtype=float,
        )

        for row in range(8):
            for col in range(8):
                x = col * CELL + half
                y = (7 - row) * CELL + half

                mesh = gl.GLMeshItem(meshdata=md, smooth=False, shader='shaded',
                                     glOptions='opaque')
                self.gl_widget.addItem(mesh)

                edges = gl.GLLinePlotItem(
                    pos=edge_pts.copy(),
                    color=(0.2, 0.2, 0.2, 1.0),
                    width=1.2,
                    mode='lines',
                    antialias=True,
                )
                edges.setGLOptions('opaque')
                self.gl_widget.addItem(edges)

                self.pin_items.append((x, y, mesh, edges))

        self._on_design_changed()

    def _reset_camera(self):
        centre = GRID_EXTENT / 2
        self.gl_widget.setCameraPosition(distance=700, elevation=30, azimuth=-45)
        self.gl_widget.opts['center'] = pg.Vector(centre, centre, 0)

    def _update_pin_visuals(self, index: int):
        pin = self.app_state.design.pins[index]
        x, y, mesh, edges = self.pin_items[index]

        h = max(float(pin.height), MIN_VISUAL_H)

        mesh.setColor((pin.r / 255.0, pin.g / 255.0, pin.b / 255.0, 1.0))
        mesh.resetTransform()
        mesh.scale(1, 1, h)
        mesh.translate(x, y, 0)

        edges.resetTransform()
        edges.scale(1, 1, h)
        edges.translate(x, y, 0)

    def _on_design_changed(self):
        for i in range(64):
            self._update_pin_visuals(i)

    def _on_pin_changed(self, index: int):
        self._update_pin_visuals(index)
