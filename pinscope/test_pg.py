import pyqtgraph.opengl as gl
md = gl.MeshData.cylinder(rows=10, cols=20, radius=[4.0, 4.0], length=1.0)
print(md.vertexes().shape)
