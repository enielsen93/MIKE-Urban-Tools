# -*- coding: utf-8 -*-
"""
Created on Tue Nov  9 11:25:43 2021

@author: mu
"""

import mikeio
import numpy as np
import arcpy
filename = r"C:\Users\ELNN\Downloads\Mesh_UTM32.mesh"

dfsu = mikeio.dfsu.Mesh(filename)

node_coordinates = dfsu.node_coordinates

element_table = dfsu.element_table

fc = r"C:\Papirkurv\Mesh_Z.shp"

with arcpy.da.InsertCursor(fc, ["SHAPE@"]) as cursor:
    for element_i, element in enumerate(element_table):
        if element_i > len(element_table)/8:
            print((element_i, len(element_table)/8))
            break
        cursor.insertRow([arcpy.Polygon(arcpy.Array([arcpy.Point(node[0], node[1])
                                                     for node in node_coordinates[
                                                         np.array([element[0], element[1], element[2]])]]))])
        # cursor.insertRow([arcpy.Polygon(arcpy.Array([arcpy.Point(node[0], node[1])
        #                            for node in node_coordinates[np.array([element[0], element[1], element[2]])]])),
        #                   np.mean(node_coordinates[np.array([element[0], element[1], element[2]]),2])])
        # print(element)