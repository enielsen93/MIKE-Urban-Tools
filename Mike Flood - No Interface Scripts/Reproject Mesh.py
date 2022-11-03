import mikeio
from pyproj import Proj, transform
import arcpy

mesh = mikeio.dfsu.Mesh(r"C:\Users\ELNN\Downloads\Mesh.mesh")
reference_mesh = mikeio.dfsu.Mesh(r"C:\Offline\VOR_Status\Mesh\Mesh_test_interp.mesh")

node_coordinates = mesh.geometry.node_coordinates

inproj = Proj(mesh.geometry.projection)
outproj = Proj(reference_mesh.geometry.projection)
node_coordinates[:,0], node_coordinates[:,1] = transform(inproj, outproj, node_coordinates[:,1], node_coordinates[:,0])
# for node in node_coordinates:
#     arcpy.Point()

dir(mesh)
mesh.geometry._set_nodes(node_coordinates,
                         mesh.geometry.codes,
                         mesh.geometry._node_ids,
                         projection_string = reference_mesh.geometry.projection)

mesh.write(r"C:\Users\ELNN\Downloads\Mesh_UTM32_2.mesh")