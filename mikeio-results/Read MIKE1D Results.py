from mikeio1d.res1d import Res1D, QueryDataNode, QueryDataReach
import arcpy
import os
import numpy as np
import mousereader

# res1d_file = r"C:\Users\ELNN\OneDrive - Ramboll\Documents\Aarhus Vand\Kongelund og Marselistunnel\MIKE\KOM_Plan_027\KOM_CDS_5_sc3Base.res1d"
res1d_file = r"C:\Users\ELNN\OneDrive - Ramboll\Documents\Aarhus Vand\Kongelund og Marselistunnel\MIKE\KOM_Plan_103\KOM_103_CDS_10Base.res1d"
MU_model = r"C:\Users\ELNN\OneDrive - Ramboll\Documents\Aarhus Vand\Kongelund og Marselistunnel\MIKE\KOM_Plan_103\KOM_103_aabnet_op.mdb"
# res1d_file = r"C:\Users\ELNN\OneDrive - Ramboll\Documents\Aarhus Vand\Kongelund og Marselistunnel\MIKE\KOM_STATUS_001\KOM_STATUS_CDS20Base.res1d"
# MU_model = r"C:\Users\ELNN\OneDrive - Ramboll\Documents\Aarhus Vand\Kongelund og Marselistunnel\MIKE\KOM_STATUS_001\KOM_STATUS_001.mdb"

nodes = {}
reaches = {}
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

class Reach:
    def __init__(self, muid):
        self.muid = muid
        self.net_type_no = 0
        self.start_coordinate = None
        self.end_coordinate = None
        self.max_discharge = None
        self.sum_discharge = None


    @property
    def shape(self):
        return arcpy.Polyline(arcpy.Array([arcpy.Point(*self.start_coordinate), arcpy.Point(*self.end_coordinate)]))


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

    cursor.execute('select MUID, NetTypeNo from msm_Weir')
    rows = cursor.fetchall()
    for row in rows:
        reaches[row[0]] = Reach(row[0])
        reaches[row[0]].net_type_no = row[1]

    cursor.execute('select MUID, NetTypeNo from msm_Link')
    rows = cursor.fetchall()
    for row in rows:
        reaches[row[0]] = Reach(row[0])
        reaches[row[0]].net_type_no = row[1]

# res1d_file = r"C:\Users\ELNN\OneDrive - Ramboll\Documents\Aarhus Vand\Kongelund og Marselistunnel\MIKE\KOM_Plan_017_sc2\KOM_Plan_017_sc2_CDS_5Base.res1d"
print(res1d_file)
queries = []
res1d = Res1D(res1d_file)
for node in res1d.data.Nodes:
    queries.append(QueryDataNode("WaterLevel", node, validate = False))

for reach in res1d.data.Reaches:
    queries.append(QueryDataReach("Discharge", reach, validate=False))

for reach in [r for r in res1d.data.Reaches if r.Name.replace("Weir:","") in reaches]:
    muid = reach.Name.replace("Weir:","")
    res1d_nodes = [node for node in res1d.data.Nodes]
    reaches[muid].start_coordinate = [res1d_nodes[reach.StartNodeIndex].XCoordinate, res1d_nodes[reach.StartNodeIndex].YCoordinate]
    reaches[muid].end_coordinate = [res1d_nodes[reach.EndNodeIndex].XCoordinate,
                                      res1d_nodes[reach.EndNodeIndex].YCoordinate]


df = Res1D(res1d_file, queries)
arcpy.env.overwriteOutput = True
output_folder = r"C:\Papirkurv\Resultater"# r"C:\Users\ELNN\OneDrive - Ramboll\Documents\ArcGIS\scratch.gdb"
new_filename = os.path.basename(res1d_file).replace(".res1d",".shp")
# weirs_new_filename = os.path.basename(res1d_file).replace(".res1d","_weirs.shp")
links_new_filename = os.path.basename(res1d_file).replace(".res1d","_discharge.shp")
try:
    output_filepath = arcpy.CreateFeatureclass_management(output_folder, new_filename, "POINT")[0]
    arcpy.management.AddField(output_filepath, "MUID", "TEXT")
    arcpy.management.AddField(output_filepath, "NetTypeNo", "SHORT")
    arcpy.management.AddField(output_filepath, "Flood_dep", "FLOAT", 8, 2)
    arcpy.management.AddField(output_filepath, "Flood_vol", "FLOAT", 8, 2)

    # weirs_output_filepath = arcpy.CreateFeatureclass_management(output_folder, weirs_new_filename, "POLYLINE")[0]
    # arcpy.management.AddField(weirs_output_filepath, "MUID", "TEXT")
    # arcpy.management.AddField(weirs_output_filepath, "NetTypeNo", "SHORT")
    # arcpy.management.AddField(weirs_output_filepath, "Discharge", "FLOAT", 8, 2)

    links_output_filepath = arcpy.CreateFeatureclass_management(output_folder, links_new_filename, "POLYLINE")[0]
    arcpy.management.AddField(links_output_filepath, "MUID", "TEXT")
    arcpy.management.AddField(links_output_filepath, "NetTypeNo", "SHORT")
    arcpy.management.AddField(links_output_filepath, "MaxQ", "FLOAT", 8, 2)
    arcpy.management.AddField(links_output_filepath, "SumQ", "FLOAT", 8, 2)
except Exception as e:
    print(e)
    for filepath in [os.path.join(output_folder, new_filename)]:
        with arcpy.da.UpdateCursor(output_filepath, ["MUID"]) as cursor:
            for row in cursor:
                cursor.deleteRow()


with arcpy.da.InsertCursor(output_filepath, ["SHAPE@", "MUID", "Flood_dep", "Flood_vol", "NetTypeNo"]) as cursor:
    for query_node in df.data.Nodes:
        muid = query_node.ID
        if muid not in nodes:
            nodes[muid] = Node(muid)
        node = nodes[muid]
        node.ground_level = query_node.CriticalLevel if hasattr(query_node, 'CriticalLevel') and query_node.CriticalLevel else query_node.GroundLevel
        node.max_level = np.max(df.get_node_values(muid, "WaterLevel"))
        # print((node.max_level, node.ground_level))
        if node.flood_depth>0:
            cursor.insertRow([arcpy.Point(query_node.XCoordinate, query_node.YCoordinate), muid, node.flood_depth, node.flood_volume, node.net_type_no if node.net_type_no is not None else 0])

# with arcpy.da.InsertCursor(weirs_output_filepath, ["SHAPE@", "MUID", "Discharge", "NetTypeNo"]) as cursor:
#     for muid in reaches.keys():
#         reach = reaches[muid]
#         try:
#             reach.discharge = np.sum(df.get_reach_end_values("Weir:"+muid, "Discharge"))
#             # print((node.max_level, node.ground_level))
#             cursor.insertRow([reach.shape, muid, reach.discharge/1e3, reach.net_type_no if reach.net_type_no is not None else 0])
#         except Exception as e:
#             pass
timeseries = [time.timestamp() for time in df.time_index]
with arcpy.da.InsertCursor(links_output_filepath, ["SHAPE@", "MUID", "MaxQ", "SumQ", "NetTypeNo"]) as cursor:
    for muid in reaches.keys():
        reach = reaches[muid]
        try:
            reach.max_discharge = np.max(abs(df.get_reach_end_values(muid, "Discharge")))
            reach.sum_discharge = np.trapz(abs(df.get_reach_end_values(muid, "Discharge")), timeseries)
        except:
            pass
            # reach.max_discharge = np.max(abs(df.get_reach_end_values("Weir:"+muid, "Discharge")))
            # reach.sum_discharge = np.trapz(abs(df.get_reach_end_values("Weir:" + muid, "Discharge")), timeseries)
        try:
            cursor.insertRow([reach.shape, muid, reach.max_discharge, reach.sum_discharge,
                          reach.net_type_no if reach.net_type_no is not None else 0])
        except Exception as e:
            print(e)