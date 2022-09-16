from mikeio1d.res1d import Res1D, QueryDataNode
import arcpy
import os
import numpy as np

# res1d_file = r"C:\Users\ELNN\OneDrive - Ramboll\Documents\Aarhus Vand\Kongelund og Marselistunnel\MIKE\KOM_Plan_027\KOM_CDS_5_sc3Base.res1d"
res1d_files = [r"C:\Users\ELNN\OneDrive - Ramboll\Documents\Aarhus Vand\Kongelund og Marselistunnel\MIKE\KOM_010\KOM_010_sc1_CDS_10Base.res1d"]

for res1d_file in res1d_files:
# res1d_file = r"C:\Users\ELNN\OneDrive - Ramboll\Documents\Aarhus Vand\Kongelund og Marselistunnel\MIKE\KOM_Plan_017_sc2\KOM_Plan_017_sc2_CDS_5Base.res1d"
    print(res1d_file)
    queries = []
    res1d = Res1D(res1d_file)
    for node in res1d.data.Nodes:
        queries.append(QueryDataNode("WaterLevel", node, validate = False))

    df = Res1D(res1d_file, queries)
    arcpy.env.overwriteOutput = True
    output_folder = r"C:\Papirkurv\Resultater"# r"C:\Users\ELNN\OneDrive - Ramboll\Documents\ArcGIS\scratch.gdb"
    new_filename = os.path.basename(res1d_file).replace(".res1d",".shp")
    try:
        output_filepath = arcpy.CreateFeatureclass_management(output_folder, new_filename, "POINT")[0]
        arcpy.management.AddField(output_filepath, "MUID", "TEXT")
        arcpy.management.AddField(output_filepath, "Flood", "FLOAT", 4, 2)
    except Exception as e:
        print(e)
        output_filepath = os.path.join(output_folder, new_filename)
        with arcpy.da.UpdateCursor(output_filepath, ["MUID"]) as cursor:
            for row in cursor:
                cursor.deleteRow()

    with arcpy.da.InsertCursor(output_filepath, ["SHAPE@", "MUID", "Flood"]) as cursor:
        for node in df.data.Nodes:
            muid = node.ID
            flood_depth = np.max(df.get_node_values(muid, "WaterLevel")) - node.GroundLevel
            if flood_depth > 0:
                cursor.insertRow([arcpy.Point(node.XCoordinate, node.YCoordinate), muid, flood_depth])