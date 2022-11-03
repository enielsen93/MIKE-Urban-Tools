from mikeio1d.res1d import Res1D, QueryDataNode
import arcpy
import os
import numpy as np
import mousereader

# res1d_file = r"C:\Users\ELNN\OneDrive - Ramboll\Documents\Aarhus Vand\Kongelund og Marselistunnel\MIKE\KOM_Plan_027\KOM_CDS_5_sc3Base.res1d"
res1d_file = r"C:\Users\ELNN\OneDrive - Ramboll\Documents\MOL\MOL_055_opdimBase.res1d"
MU_model = r"C:\Users\ELNN\OneDrive - Ramboll\Documents\MOL\MOL_055_opdim.mdb"
# res1d_file = r"C:\Users\ELNN\OneDrive - Ramboll\Documents\Aarhus Vand\Kongelund og Marselistunnel\MIKE\KOM_STATUS_001\KOM_STATUS_CDS20Base.res1d"
# MU_model = r"C:\Users\ELNN\OneDrive - Ramboll\Documents\Aarhus Vand\Kongelund og Marselistunnel\MIKE\KOM_STATUS_001\KOM_STATUS_001.mdb"

nodes = {}
class Node:
    def __init__(self, muid):
        self.diameter = None
        self.net_type_no = 0
        self.ground_level = 0
        self.max_level = 0
        self.id = muid

    @property
    def flood_depth(self):
        return max(self.max_level - self.ground_level,0)

    @property
    def flood_volume(self):
        return self.diameter*1000*min(1, self.flood_depth)*self.flood_depth if self.diameter and self.flood_depth else 0

if MU_model:
    import pyodbc
    conn = pyodbc.connect(
        r'Driver={Microsoft Access Driver (*.mdb, *.accdb)};DBQ=%s;' % (MU_model))
    cursor = conn.cursor()
    cursor.execute('select MUID, Diameter, NetTypeNo from msm_Node')
    rows = cursor.fetchall()
    for row in rows:
        nodes[row[0]] = Node(row[0])
        nodes[row[0]].diameter = row[1]
        nodes[row[0]].net_type_no = row[2]


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
    for query_node in df.data.Nodes:
        muid = query_node.ID
        if muid not in nodes:
            nodes[muid] = Node(muid)
        node = nodes[muid]
        node.ground_level = query_node.GroundLevel
        node.max_level = np.max(df.get_node_values(muid, "WaterLevel"))
        # print((node.max_level, node.ground_level))
        if node.flood_depth>0:
            cursor.insertRow([arcpy.Point(query_node.XCoordinate, query_node.YCoordinate), muid, node.flood_depth, node.flood_volume, node.net_type_no if node.net_type_no is not None else 0])