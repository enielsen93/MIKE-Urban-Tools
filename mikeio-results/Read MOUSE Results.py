# -*- coding: utf-8 -*-
# from mikeio1d.res1d import Res1D, QueryDataNode
import arcpy
import os
import numpy as np
import mousereader
import traceback

# res1d_file = r"C:\Users\ELNN\OneDrive - Ramboll\Documents\Aarhus Vand\Kongelund og Marselistunnel\MIKE\KOM_Plan_027\KOM_CDS_5_sc3Base.res1d"
result_file = r"C:\Users\ELNN\OneDrive - Ramboll\Documents\MOL\MOL_055Base.PRF"
MU_model = r"C:\Users\ELNN\OneDrive - Ramboll\Documents\MOL\MOL_055.mdb"
msm_Node = os.path.join(MU_model, "msm_Node")
# res1d_file = r"C:\Users\ELNN\OneDrive - Ramboll\Documents\Aarhus Vand\Kongelund og Marselistunnel\MIKE\KOM_STATUS_001\KOM_STATUS_CDS20Base.res1d"
# MU_model = r"C:\Users\ELNN\OneDrive - Ramboll\Documents\Aarhus Vand\Kongelund og Marselistunnel\MIKE\KOM_STATUS_001\KOM_STATUS_001.mdb"

nodes = {}
class Node:
    def __init__(self):
        self.diameter = None
        self.net_type_no = 0
        self.ground_level = 0
        self.max_level = 0
        self.shape = None

    @property
    def flood_depth(self):
        return self.max_level - self.ground_level

    @property
    def flood_volume(self):
        return self.diameter*1000*min(1, self.flood_depth)*self.flood_depth if self.diameter and self.flood_depth else 0

with arcpy.da.SearchCursor(msm_Node, ["SHAPE@", "MUID", "GroundLevel", "Diameter", "NetTypeNo"]) as cursor:
    for row in cursor:
        nodes[row[1]] = Node()
        nodes[row[1]].shape = row[0]
        nodes[row[1]].ground_level = row[2]
        nodes[row[1]].diameter = row[3]
        nodes[row[1]].net_type_no = row[4]


# res1d_file = r"C:\Users\ELNN\OneDrive - Ramboll\Documents\Aarhus Vand\Kongelund og Marselistunnel\MIKE\KOM_Plan_017_sc2\KOM_Plan_017_sc2_CDS_5Base.res1d"
print(result_file)
mouse_result = mousereader.MouseResult(result_file, list(nodes.keys()), "Node_WL")

arcpy.env.overwriteOutput = True
output_folder = r"C:\Papirkurv\Resultater"# r"C:\Users\ELNN\OneDrive - Ramboll\Documents\ArcGIS\scratch.gdb"
new_filename = os.path.basename(result_file).replace(".prf",".shp")
try:
    output_filepath = arcpy.CreateFeatureclass_management(output_folder, new_filename, "POINT")[0]
    arcpy.management.AddField(output_filepath, "MUID", "TEXT")
    arcpy.management.AddField(output_filepath, "NetTypeNo", "SHORT")
    arcpy.management.AddField(output_filepath, "Flood_dep", "FLOAT", 8, 2)
    arcpy.management.AddField(output_filepath, "Flood_vol", "FLOAT", 8, 2)
except Exception as e:
    print(e)
    output_filepath = os.path.join(output_folder, new_filename)
    with arcpy.da.UpdateCursor(output_filepath, ["MUID"]) as cursor:
        for row in cursor:
            cursor.deleteRow()

with arcpy.da.InsertCursor(output_filepath, ["SHAPE@", "MUID", "Flood_dep", "Flood_vol", "NetTypeNo"]) as cursor:
    for node in nodes.keys():
        muid = node
        if muid in nodes or not MU_model:
            nodes[muid].max_level = np.max(mouse_result.query(row[1]))

            if nodes[muid].flood_depth>0:
                cursor.insertRow([node.shape, muid, nodes[muid].flood_depth, nodes[muid].flood_volume, nodes[muid].net_type_no if nodes[muid].net_type_no is not None else 0])