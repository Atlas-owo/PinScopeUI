import pyqtgraph.opengl as gl
md = gl.MeshData.cylinder(rows=1, cols=4, radius=[28.284, 28.284], length=1.0)
print(md.vertexes().shape)
