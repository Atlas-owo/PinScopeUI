import pyqtgraph.opengl as gl
box = gl.GLBoxItem()
print(isinstance(box, gl.GLMeshItem))
print(hasattr(box, 'setGLOptions'))
