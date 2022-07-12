# -*- coding: utf-8 -*-
"""
Created on Tue Nov  9 11:25:43 2021

@author: mu
"""

import mikeio
import numpy as np
import arcpy
filename = r"K:\Hydrauliske modeller\Modeller\A265_1 Kapacitetsanalyse Sydbyen\Mesh\Tiltag\A265_1_Mesh_GA_v2_1_cropped_interp_E12_Krydsombygning_Bredgade_Sanatorievej.mesh"

dfsu = mikeio.dfsu.Dfsu(filename)

node_coordinates = dfsu.node_coordinates

element_table = dfsu.element_table

fc = r"K:\Hydrauliske modeller\Papirkurv\Mesh_Z.shp"

with arcpy.da.InsertCursor(fc, ["SHAPE@", "Z"]) as cursor:
    for element in element_table:
        cursor.insertRow([arcpy.Polygon(arcpy.Array([arcpy.Point(node[0], node[1]) 
                                   for node in node_coordinates[np.array([element[0], element[1], element[2]])]])), 
                          np.mean(node_coordinates[np.array([element[0], element[1], element[2]]),2])])
        # print(element)