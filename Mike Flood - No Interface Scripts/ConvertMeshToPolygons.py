# -*- coding: utf-8 -*-
"""
Created on Tue Nov  9 11:25:43 2021

@author: mu
"""

import mikeio
import numpy as np
import arcpy
filename = r"C:\Offline\VOR_Status\Mesh\Mesh_v1.1_lf_v1.2.mesh"

dfsu = mikeio.dfsu.Mesh(filename)

node_coordinates = dfsu.node_coordinates
element_coordinates = dfsu.element_coordinates

element_table = dfsu.element_table

fc = r"C:\Papirkurv\Mesh_Z_2.shp"
distance_vector = np.sum(element_coordinates[:,:2]-[525251, 6255830], axis=1)
with arcpy.da.InsertCursor(fc, ["SHAPE@",'Z']) as cursor:
    for element_i, element in enumerate(element_table):
        if distance_vector[element_i] < 150:
            cursor.insertRow([arcpy.Polygon(arcpy.Array([arcpy.Point(node[0], node[1])
                                                         for node in node_coordinates[
                                                             np.array([element[0], element[1], element[2]])]])), element_coordinates[element_i,2]])
        # cursor.insertRow([arcpy.Polygon(arcpy.Array([arcpy.Point(node[0], node[1])
        #                            for node in node_coordinates[np.array([element[0], element[1], element[2]])]])),
        #                   np.mean(node_coordinates[np.array([element[0], element[1], element[2]]),2])])
        # print(element)