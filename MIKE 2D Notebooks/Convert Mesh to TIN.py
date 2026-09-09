# -*- coding: utf-8 -*-
"""
Created on Tue Sep  1 15:17:40 2020

@author: eni
"""


#import arcpy
import os
import numpy as np
import mikeio
import arcpy
import traceback
arcpy.env.overwriteOutput = True


arcpy.CheckOutExtension("3D")

mesh_files = [r"C:\Users\ELNN.RAMBOLL.000\OneDrive - Ramboll\Documents\Mosagergroeften\MIKE\07_FM\Mesh\20260728 Mesh_5m2_Z.mesh"]

for mesh_file in mesh_files:
    print(mesh_file)
    dfs = mikeio.dfsu.Mesh(mesh_file)
    node_coordinates = dfs.node_coordinates
    arcpy.env.overwriteOutput = True
    clip = True

    nodesPath = r"in_memory"
    nodesName = "nodes_Z"
    arcpy.CreateFeatureclass_management(nodesPath, nodesName, "POINT", has_z = "Enabled", spatial_reference = dfs.geometry.projection_string)
    # arcpy.AddField_management(os.path.join(nodesPath, nodesName), "Z", "DOUBLE")
    print("Creating point class")
    with arcpy.da.InsertCursor(os.path.join(nodesPath,nodesName), ["SHAPE@"]) as cursor:
        for node in node_coordinates:
            cursor.insertRow([arcpy.Point(node[0], node[1], node[2])])

    if clip:
        print("Preparing clip")
        arcpy.CreateFeatureclass_management("in_memory", "ClipPolygon", "POLYGON")
        boundary_xy_table = dfs.geometry.boundary_polylines.lines[0].xy
        polygons = arcpy.Polygon(arcpy.Array([arcpy.Point(xy[0], xy[1]) for xy in boundary_xy_table]))
        with arcpy.da.InsertCursor("in_memory\ClipPolygon", "SHAPE@") as cursor:
            cursor.insertRow([polygons])

        # try:
        arcpy.CreateFeatureclass_management("in_memory", "CutPolygon", "POLYGON")
        cut_polygons = dfs.geometry.boundary_polylines.lines[3:]
        polygons = []

        if not isinstance(cut_polygons, (list, tuple)):
            cut_polygons = [cut_polygons]

        for cut_polygon in cut_polygons:
            boundary_xy_table = cut_polygon.xy
            polygons.append(arcpy.Polygon(arcpy.Array([arcpy.Point(xy[0], xy[1]) for xy in boundary_xy_table])))

        with arcpy.da.InsertCursor("in_memory\CutPolygon", "SHAPE@") as cursor:
            for polygon in polygons:
                cursor.insertRow([polygon])

        arcpy.management.RepairGeometry(
            "in_memory\CutPolygon",
            "DELETE_NULL"
        )


        # # Export to shapefile
        # out_shp = r"C:\Papirkurv\CutPolygon.shp"
        #
        # if arcpy.Exists(out_shp):
        #     arcpy.Delete_management(out_shp)
        #
        # arcpy.CopyFeatures_management(r"in_memory\CutPolygon", out_shp)

        print("Creating TIN")
        arcpy.ddd.CreateTin(mesh_file.replace(".mesh", "TIN"), dfs.geometry.projection_string,
                r"in_memory\nodes_Z Shape.Z Mass_Points; in_memory\ClipPolygon <None> Hard_Clip; in_memory\CutPolygon <None> Hard_Erase")
        # except Exception as e:
        #     arcpy.AddWarning("CutPolygon creation failed:\n" + traceback.format_exc())
        #     print("Continuing without Cut polygon")
        #
        #     arcpy.ddd.CreateTin(mesh_file.replace(".mesh", "TIN"), dfs.geometry.projection_string,
        #                         r"in_memory\nodes_Z Shape.Z Mass_Points; in_memory\ClipPolygon <None> Hard_Clip")


    else:
        print("Creating TIN")
        arcpy.ddd.CreateTin(mesh_file.replace(".mesh","TIN"), dfs.geometry.projection_string,
                       "%s Shape.Z Mass_Points")

