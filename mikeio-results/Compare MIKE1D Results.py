from mikeio1d.res1d import Res1D, QueryDataNode
import arcpy
import os
import numpy as np

# res1d_file = r"C:\Users\ELNN\OneDrive - Ramboll\Documents\Aarhus Vand\Kongelund og Marselistunnel\MIKE\KOM_Plan_027\KOM_CDS_5_sc3Base.res1d"
res1d_files = [r"C:\Users\ELNN\OneDrive - Ramboll\Documents\Aarhus Vand\Kongelund og Marselistunnel\MIKE\KOM_012\KOM_12_CDS_20Base.res1d",
               r"C:\Users\ELNN\OneDrive - Ramboll\Documents\Aarhus Vand\Kongelund og Marselistunnel\MIKE\KOM_STATUS_001\KOM_STATUS_CDS20Base.res1d"]

flood_depths_status = {}
flood_depths_plan = {}
nodes_geometry = {}

for res1d_file in res1d_files:
# res1d_file = r"C:\Users\ELNN\OneDrive - Ramboll\Documents\Aarhus Vand\Kongelund og Marselistunnel\MIKE\KOM_Plan_017_sc2\KOM_Plan_017_sc2_CDS_5Base.res1d"
    print(res1d_file)
    queries = []
    res1d = Res1D(res1d_file)
    for node in res1d.data.Nodes:
        queries.append(QueryDataNode("WaterLevel", node, validate = False))

    df = Res1D(res1d_file, queries)
    arcpy.env.overwriteOutput = True

    for node in df.data.Nodes:
        nodes_geometry[node.ID] = arcpy.Point(node.XCoordinate, node.YCoordinate)
        if "STATUS" in res1d_file:
            flood_depths_status[node.ID] = max(np.max(df.get_node_values(node.ID, "WaterLevel")) - node.GroundLevel, 0)
        else:
            flood_depths_plan[node.ID] = max(np.max(df.get_node_values(node.ID, "WaterLevel")) - node.GroundLevel, 0)

intersecting_nodes = np.intersect1d(list(flood_depths_status.keys()), list(flood_depths_plan.keys()))

output_folder = r"C:\Papirkurv\Resultater"# r"C:\Users\ELNN\OneDrive - Ramboll\Documents\ArcGIS\scratch.gdb"
new_filename = "Comparison.shp"
try:
    output_filepath = arcpy.CreateFeatureclass_management(output_folder, new_filename, "POINT")[0]
    arcpy.management.AddField(output_filepath, "MUID", "TEXT")
    arcpy.management.AddField(output_filepath, "FloodDiff", "FLOAT", 6, 3)
except Exception as e:
    print(e)
    output_filepath = os.path.join(output_folder, new_filename)
    with arcpy.da.UpdateCursor(output_filepath, ["MUID"]) as cursor:
        for row in cursor:
            cursor.deleteRow()

with arcpy.da.InsertCursor(output_filepath, ["SHAPE@", "MUID", "FloodDiff"]) as cursor:
    for node in intersecting_nodes:
        muid = node
        flood_diff = flood_depths_status[node] - flood_depths_plan[node]

        cursor.insertRow([nodes_geometry[node], muid, flood_diff])