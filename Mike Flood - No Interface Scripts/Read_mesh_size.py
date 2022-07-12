# -*- coding: utf-8 -*-
"""
Spyder Editor

This is a temporary script file.
"""
import matplotlib.pyplot as plt
import numpy as np
import pickle
from scipy import interpolate
from scipy.interpolate import NearestNDInterpolator
from scipy.interpolate import RectBivariateSpline
from scipy.spatial import cKDTree
import time
import sys
sys.path.append("C:/Program Files/ArcGIS/Pro/Resources/ArcPy")
from matplotlib import cm
import mikeio
tic = time.time()
import arcpy
import os
print("%d seconds: Reading Mesh" % (time.time()-tic))

filename = r"K:\Hydrauliske modeller\Modeller\A265_1 Kapacitetsanalyse Sydbyen\Mesh\A265_1_Mesh_GA_v2_1_cropped_interp_E2.mesh"
#extent_shape_file = r"K:\Hydrauliske modeller\Modeller\Kapacitetsanalyse Aarhusbakken\GIS\Code_2.shp"
dfs = mikeio.dfsu.Mesh(filename)

element_area = dfs.get_element_area()
plt.figure()

plt.hist(element_area, bins=200)

