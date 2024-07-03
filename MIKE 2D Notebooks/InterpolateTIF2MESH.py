# -*- coding: utf-8 -*-
import os
import arcpy
import numpy as np
import re
from arcpy import env
arcpy.env.addOutputsToMap = False
import sys
import time
import mikeio
import bisect
from scipy.spatial import cKDTree
from datetime import timedelta
from scipy.interpolate import RegularGridInterpolator

DHMFile = r"C:\Users\ELNN\OneDrive - Ramboll\Documents\Aarhus Vand\Vesterbro Torv\MIKE_URBAN\04_DTM\Løsningsforslag 2023-12-11.tif"
mesh_files = [
                r"C:\Users\ELNN\OneDrive - Ramboll\Documents\Aarhus Vand\Vesterbro Torv\MIKE_URBAN\07_MESH\VBT_Mesh_2023_11_29.mesh"
            ]
mesh_files = np.flip(mesh_files)
for MeshFile in mesh_files:
    print(MeshFile)

    MeshFileOutput = os.path.join(r"C:\Users\ELNN\OneDrive - Ramboll\Documents\Aarhus Vand\Vesterbro Torv\MIKE_URBAN\07_MESH\Nødoverløb med jordbassiner", os.path.basename(MeshFile).replace(".mesh", "_interp.mesh"))

    dfs = mikeio.dfsu.Mesh(MeshFile)

    data = dfs.node_coordinates

    DHMRaster = np.flip(arcpy.RasterToNumPyArray(DHMFile, nodata_to_value=0), axis=0)

    DHMRasterInfo = np.array([float(arcpy.GetRasterProperties_management(DHMFile, "LEFT")[0].replace(",", ".")),
                              float(arcpy.GetRasterProperties_management(DHMFile, "BOTTOM")[0].replace(",", ".")),
                              float(arcpy.GetRasterProperties_management(DHMFile, "CELLSIZEX")[0].replace(",", ".")),
                              float(arcpy.GetRasterProperties_management(DHMFile, "CELLSIZEY")[0].replace(",", "."))])

    raster = arcpy.Raster(DHMFile)
    lower_left_corner = arcpy.Point(raster.extent.XMin, raster.extent.YMin)
    DHMRasterXs = lower_left_corner.X + np.arange(raster.width) * raster.meanCellWidth + raster.meanCellWidth/2
    DHMRasterYs = lower_left_corner.Y + np.arange(raster.height) * raster.meanCellHeight + raster.meanCellHeight/2

    # DHMRasterXs = np.arange(DHMRasterInfo[0],DHMRasterInfo[0]+DHMRaster.shape[1]*DHMRasterInfo[2],float(DHMRasterInfo[2])).astype(np.float32)
    # DHMRasterYs = np.arange(DHMRasterInfo[1],DHMRasterInfo[1]+DHMRaster.shape[0]*DHMRasterInfo[3],float(DHMRasterInfo[3])).astype(np.float32 )

    interp = RegularGridInterpolator((DHMRasterYs, DHMRasterXs),
                                     DHMRaster)

    # DHMRasterX, DHMRasterY = np.meshgrid(DHMRasterXs,DHMRasterYs)
    # DHMRasterXsFlat = DHMRasterX.flatten()
    # DHMRasterYsFlat = DHMRasterY.flatten()
    # DHMRasterFlat = DHMRaster.flatten()

    # idx = np.where(DHMRasterFlat!=0)
    # DHMRasterXsFlatSparse = DHMRasterXsFlat[idx]
    # DHMRasterYsFlatSparse = DHMRasterYsFlat[idx]
    # DHMRasterFlatSparse = DHMRasterFlat[idx]

    tic = time.time()
    bedLevelFlat = np.zeros((data.shape[0]), dtype=np.float64)

    bedLevelFlat = interp(data[:, [1, 0]])
    # for row in range(int(len(bedLevelFlat))):
    #     try:
    #         bedLevelFlat[row] = interp([bisect.bisect_left(DHMRasterYs, data[row,1]),bisect.bisect_left(DHMRasterXs, data[row,0])]
    #     except Exception as e:
    #         bedLevelFlat[row] = 0

    dfs.zn = bedLevelFlat
    dfs.write(MeshFileOutput)