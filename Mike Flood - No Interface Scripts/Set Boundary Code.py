import mikeio
import matplotlib.pyplot as plt
mesh_filepath = r"C:\Offline\VOR_Status\Mesh\Mesh_v1.1_status.mesh"

mesh = mikeio.dfsu.Mesh(mesh_filepath)

polylines = mesh.geometry.boundary_polylines[1][0]
mesh.geometry.codes[polylines.nodes] = 2

mesh.write(mesh_filepath)
# plt.scatter(mesh.geometry.boundary_polylines[1][0].xy[:,0], mesh.geometry.boundary_polylines[1][0].xy[:,1])
# plt.show()
# print("Break")
