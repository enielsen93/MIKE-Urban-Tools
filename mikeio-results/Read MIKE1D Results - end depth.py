from mikeio1d.res1d import Res1D, QueryDataNode
import arcpy
import os
import numpy as np

# res1d_file = r"C:\Users\ELNN\OneDrive - Ramboll\Documents\Aarhus Vand\Kongelund og Marselistunnel\MIKE\KOM_Plan_027\KOM_CDS_5_sc3Base.res1d"
res1d_file = r"C:\Users\ELNN\OneDrive - Ramboll\Documents\Aarhus Vand\Kongelund og Marselistunnel\MIKE\KOM_Plan_038_sc3\KOM_Plan_038_sc3_hotstartBase.res1d"

queries = []
res1d = Res1D(res1d_file)
for node in res1d.data.Nodes:
    queries.append(QueryDataNode("WaterLevel", node, validate = False))

df = Res1D(res1d_file, queries)
arcpy.env.overwriteOutput = True
try:
    output_filepath = arcpy.CreateFeatureclass_management(r"C:\Users\ELNN\OneDrive - Ramboll\Documents\ArcGIS\scratch.gdb", os.path.basename(res1d_file).replace(".res1d","_end_depth"), "POINT")[0]
    arcpy.management.AddField(output_filepath, "MUID", "TEXT")
    arcpy.management.AddField(output_filepath, "enddepth", "FLOAT", 4, 2)
except Exception as e:
    print(e)
    output_filepath = os.path.join(r"C:\Users\ELNN\OneDrive - Ramboll\Documents\ArcGIS\scratch.gdb", os.path.basename(res1d_file).replace(".res1d","_end_depth"))
    with arcpy.da.UpdateCursor(output_filepath, ["MUID"]) as cursor:
        for row in cursor:
            cursor.deleteRow()

with arcpy.da.InsertCursor(output_filepath, ["SHAPE@", "MUID", "enddepth"]) as cursor:
    for node in df.data.Nodes:
        muid = node.ID
        end_depth = (df.get_node_values(muid, "WaterLevel"))[-1] - node.BottomLevel
        cursor.insertRow([arcpy.Point(node.XCoordinate, node.YCoordinate), muid, end_depth])