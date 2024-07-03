# -*- coding: utf-8 -*-
"""
Created on Mon Jul 30 11:21:31 2018

@author: eni
"""
import os
import arcpy
import numpy as np
import re
import pythonaddins
import hashlib


MU_database = r"C:\Dokumenter\Haarup\Model\Haarup Disp Plan_samlet_purhusvej_udloeb_korrekt_dim.mdb"
catchments = MU_database + "\mu_Geometry\ms_Catchment"
catchCon = MU_database + "\msm_CatchCon"
hModA = MU_database + "\msm_HModA"
msm_Node = MU_database + "\msm_Node"
msm_Link = MU_database + "\msm_Link"
nodesShape = MU_database + "\msm_Node"
hParA = MU_database + "\msm_HParA"

msm_Node_diameter_lossParID = {}
with arcpy.da.SearchCursor(msm_Node, ["MUID","Diameter","LossParID"], where_clause = "TypeNo NOT IN (2,3)") as cursor:
    for row in cursor:
        msm_Node_diameter_lossParID[row[0]] = [row[1], row[2]]

msm_Node_saddle = []
with arcpy.da.SearchCursor(msm_Link, ["FromNode","ToNode", "Diameter"]) as cursor:
    for row in cursor:
        for node in [row[0],row[1]]:
            if (node not in msm_Node_saddle and
                node in msm_Node_diameter_lossParID and 
                row[2] > msm_Node_diameter_lossParID[node][0] 
                and ("Weighted" in msm_Node_diameter_lossParID[node][1] or 
                     "Classic" in msm_Node_diameter_lossParID[node][1])):
                msm_Node_saddle.append(node)
if msm_Node_saddle:
    arcpy.AddWarning("Warning: Manholes found with diameter less than diameter of one more connected links with an outlet head loss defined. Consider removing outlet head loss.")
                