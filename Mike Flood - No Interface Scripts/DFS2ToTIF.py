# -*- coding: utf-8 -*-
"""
Created on Fri Jun  3 10:16:41 2022

@author: ELNN
"""

import mikeio
import numpy as np
import arcpy

dfs2_filepath = r"C:\Offline\VOR_Status\VOR_Status_CDS5_2dCDS5.m21 - Result Files\VOR_Status_CDS20_maxA01.dfs2"
dfs2 = mikeio.dfs2.Dfs2(dfs2_filepath)

item = dfs2.items[0].name

data = np.nan_to_num(dfs2.read(items = item).data[0],nan=-999)

arcpy.env.overwriteOutput = True

lower_left_corner = arcpy.PointGeometry(arcpy.Point(dfs2.longitude, dfs2.latitude),"GCS_WGS_1984").projectAs("ETRS_1989_UTM_Zone_32N")[0]
raster = arcpy.NumPyArrayToRaster(np.flip(data, axis=1), lower_left_corner = lower_left_corner,
                                     x_cell_size = dfs2.dx,
                                     y_cell_size = dfs2.dy,
                                     value_to_nodata = -999)

raster.save(dfs2_filepath.replace(".dfs2","1.tif"))

