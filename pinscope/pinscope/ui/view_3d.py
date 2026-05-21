from __future__ import annotations
import pyqtgraph as pg
import pyqtgraph.opengl as gl
from PySide6.QtWidgets import QWidget, QVBoxLayout, QPushButton, QHBoxLayout
from PySide6.QtCore import Qt
from ..app_state import AppState

class View3D(QWidget):
    def __init__(self, app_state: AppState, parent=None):
        super().__init__(parent)
        self.app_state = app_state
        self.glow_enabled = False
        
        self._setup_ui()
        self._init_3d_scene()
        
        self.app_state.design_changed.connect(self._on_design_changed)
        self.app_state.pin_changed.connect(self._on_pin_changed)

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.gl_widget = gl.GLViewWidget()
        layout.addWidget(self.gl_widget)
        
        # Overlay reset camera button
        self.reset_btn = QPushButton("Reset Camera", self.gl_widget)
        self.reset_btn.clicked.connect(self._reset_camera)
        self.reset_btn.move(10, 10) # Absolute position to overlay on top of GLViewWidget

    def _init_3d_scene(self):
        self._reset_camera()
        
        import numpy as np
        
        # Add a grid/base plate
        grid = gl.GLGridItem()
        grid.setSize(350, 350)
        grid.setSpacing(42, 42)
        grid.setColor((255, 255, 255, 150)) # Brighter grid
        # Center the 8x8 grid: pins go from 0 to 7*42 = 294. Center is 147.
        grid.translate(147, 147, 0)
        self.gl_widget.addItem(grid)
        
        self.pin_items = []
        self.glow_items = []
        
        # Create solid rectangular pins
        verts = np.array([
            [ 20,  20,  0.5], [ 20, -20,  0.5], [-20, -20,  0.5], [-20,  20,  0.5],
            [ 20,  20, -0.5], [ 20, -20, -0.5], [-20, -20, -0.5], [-20,  20, -0.5]
        ])
        faces = np.array([
            [0, 1, 2], [0, 2, 3], # Top
            [4, 6, 5], [4, 7, 6], # Bottom
            [0, 4, 5], [0, 5, 1], # +X side
            [1, 5, 6], [1, 6, 2], # -Y side
            [2, 6, 7], [2, 7, 3], # -X side
            [3, 7, 4], [3, 4, 0]  # +Y side
        ])
        md = gl.MeshData(vertexes=verts, faces=faces)
        
        verts_glow = np.array([
            [ 22,  22,  0.5], [ 22, -22,  0.5], [-22, -22,  0.5], [-22,  22,  0.5],
            [ 22,  22, -0.5], [ 22, -22, -0.5], [-22, -22, -0.5], [-22,  22, -0.5]
        ])
        glow_md = gl.MeshData(vertexes=verts_glow, faces=faces)
        
        for row in range(8):
            for col in range(8):
                idx = row * 8 + col
                x = col * 42.0
                y = row * 42.0
                
                # Solid pin
                mesh = gl.GLMeshItem(meshdata=md, smooth=True, shader='shaded')
                self.gl_widget.addItem(mesh)
                self.pin_items.append((x, y, mesh))
                
                # Glow shell
                glow = gl.GLMeshItem(meshdata=glow_md, smooth=True, shader='balloon', glOptions='additive')
                glow.setVisible(False)
                self.gl_widget.addItem(glow)
                self.glow_items.append((x, y, glow))
                
        self._on_design_changed()

    def _reset_camera(self):
        self.gl_widget.setCameraPosition(distance=400, elevation=30, azimuth=-45)
        self.gl_widget.opts['center'] = pg.Vector(147, 147, 0)
        
    def set_glow_enabled(self, enabled: bool):
        self.glow_enabled = enabled
        for _, _, glow in self.glow_items:
            glow.setVisible(enabled)
        # Trigger an update to make sure alphas are correct
        self._on_design_changed()

    def _update_pin_visuals(self, index: int):
        pin = self.app_state.design.pins[index]
        x, y, mesh = self.pin_items[index]
        _, _, glow = self.glow_items[index]
        
        # Map 0-255 height to real 3D units (e.g., 0 to 50)
        h = (pin.height / 255.0) * 50.0
        # If height is 0, give it a tiny height so it's visible as a base
        h = max(h, 0.5)
        
        # Colors (R, G, B, A) in 0.0 - 1.0
        r, g, b = pin.r / 255.0, pin.g / 255.0, pin.b / 255.0
        
        # Pyqtgraph GLMeshItem color
        mesh.setColor((r, g, b, 1.0))
        
        # Apply transforms: scale Z by h, translate to x, y, h/2
        mesh.resetTransform()
        mesh.scale(1, 1, h)
        mesh.translate(x, y, h/2)
        
        if self.glow_enabled:
            # We want the glow to be additive and slightly transparent
            glow.setColor((r, g, b, 0.15))
            glow.resetTransform()
            glow.scale(1, 1, h * 1.1)
            glow.translate(x, y, (h * 1.1)/2)

    def _on_design_changed(self):
        for i in range(64):
            self._update_pin_visuals(i)

    def _on_pin_changed(self, index: int):
        self._update_pin_visuals(index)
