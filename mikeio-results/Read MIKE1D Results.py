from mikeio1d.res1d import Res1D, QueryDataNode, QueryDataReach
import arcpy
import os
import numpy as np
import mousereader
import traceback

# res1d_file = r"C:\Users\ELNN\OneDrive - Ramboll\Documents\Aarhus Vand\Kongelund og Marselistunnel\MIKE\KOM_Plan_027\KOM_CDS_5_sc3Base.res1d"
res1d_file = r"C:\Users\ELNN\OneDrive - Ramboll\Documents\Aarhus Vand\Soenderhoej\MIKE\MIKE_URBAN\SON_017\SON_017_N_CDS5_156_ARF_127Base.res1d"
MU_model = r"C:\Users\ELNN\OneDrive - Ramboll\Documents\Aarhus Vand\Soenderhoej\MIKE\MIKE_URBAN\SON_017\SON_017.mdb"
# res1d_file = r"C:\Users\ELNN\OneDrive - Ramboll\Documents\Aarhus Vand\Soenderhoej\MIKE\MIKE_URBAN\SON_013\SON_013_N_CDS5_156_ARF_127Base.res1d"
# MU_model = r"C:\Users\ELNN\OneDrive - Ramboll\Documents\Aarhus Vand\Soenderhoej\MIKE\MIKE_URBAN\SON_013\SON_013.mdb"
# MU_model= "C:\Users\ELNN\OneDrive - Ramboll\Documents\Aarhus Vand\Soenderhoej\MIKE\MIKE_URBAN\SON_014\SON_014.mdb"
# res1d_file = r"C:\Users\ELNN\OneDrive - Ramboll\Documents\Aarhus Vand\Kongelund og Marselistunnel\MIKE\KOM_STATUS_001\KOM_STATUS_CDS20Base.res1d"
# MU_model = r"C:\Users\ELNN\OneDrive - Ramboll\Documents\Aarhus Vand\Kongelund og Marselistunnel\MIKE\KOM_STATUS_001\KOM_STATUS_001.mdb"

nodes = {}
reaches = {}
class Node:
    def __init__(self, muid):
        self.diameter = None
        self.net_type_no = 0
        self.ground_level = 0
        self.invert_level = 0
        self.max_level = 0
        self.id = muid
        self.max_headloss = 0
        self.inlet_waterlevel = 0
        self.outlet_waterlevel = 0
        self.max_inlet_velocity = 0

    @property
    def flood_depth(self):
        return max(self.max_level - self.ground_level,0)

    @property
    def flood_volume(self):
        return self.diameter*1000*min(1, self.flood_depth)*self.flood_depth if self.diameter and self.flood_depth else 0

    @property
    def flow_area(self):
        return self.diameter * (self.max_level - self.invert_level) if self.max_level > 0 and self.diameter and self.invert_level else 0

    @property
    def flow_area_diameter(self):
        return np.sqrt(self.flow_area*4/np.pi) if self.flow_area > 0 else 0

class Reach:
    def __init__(self, muid):
        self.muid = muid
        self.net_type_no = 0
        self.diameter = 0
        # self.start_coordinate = None
        # self.end_coordinate = None
        self.shape = None
        self.max_discharge = None
        self.sum_discharge = None
        self.end_discharge = None
        self.min_discharge = None
        self.fromnode = None
        self.tonode = None
        self.type = "Link"
        self.max_flow_velocity = None

    # @property
    # def shape(self):
    #     return arcpy.Polyline(arcpy.Array([arcpy.Point(*self.start_coordinate), arcpy.Point(*self.end_coordinate)]))


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
    queries.append(QueryDataReach("Discharge", reach, validate = False))

for reach in [r for r in res1d.data.Reaches if r.Name.replace("Weir:","") in reaches]:
    muid = reach.Name.replace("Weir:","")
    reach.type = "Weir"
    res1d_nodes = [node for node in res1d.data.Nodes]
    reaches[muid].shape = arcpy.Polyline(arcpy.Array([arcpy.Point(coordinate.X, coordinate.Y) for coordinate in reach.DigiPoints]))
    # reaches[muid].start_coordinate = [res1d_nodes[reach.StartNodeIndex].XCoordinate, res1d_nodes[reach.StartNodeIndex].YCoordinate]
    # reaches[muid].end_coordinate = [res1d_nodes[reach.EndNodeIndex].XCoordinate,
                                      # res1d_nodes[reach.EndNodeIndex].YCoordinate]
    reaches[muid].fromnode = res1d_nodes[reach.StartNodeIndex].ID
    reaches[muid].tonode = res1d_nodes[reach.EndNodeIndex].ID


df = Res1D(res1d_file, queries)
arcpy.env.overwriteOutput = True
output_folder = r"C:\Papirkurv\Resultater"# r"C:\Users\ELNN\OneDrive - Ramboll\Documents\ArcGIS\scratch.gdb"
new_filename = os.path.basename(res1d_file).replace(".res1d",".shp")
# weirs_new_filename = os.path.basename(res1d_file).replace(".res1d","_weirs.shp")
links_new_filename = os.path.basename(res1d_file).replace(".res1d","_discharge.shp")
try:
    output_filepath = arcpy.CreateFeatureclass_management(output_folder, new_filename, "POINT")[0]
    arcpy.management.AddField(output_filepath, "MUID", "TEXT")
    arcpy.management.AddField(output_filepath, "Diameter", "FLOAT", 8, 2)
    arcpy.management.AddField(output_filepath, "NetTypeNo", "SHORT")
    arcpy.management.AddField(output_filepath, "Invert_lev", "FLOAT", 8, 2)
    arcpy.management.AddField(output_filepath, "Max_elev", "FLOAT", 8, 2)
    arcpy.management.AddField(output_filepath, "Flood_dep", "FLOAT", 8, 2)
    arcpy.management.AddField(output_filepath, "Flood_vol", "FLOAT", 8, 2)
    arcpy.management.AddField(output_filepath, "max_hl", "FLOAT", 8, 2)
    arcpy.management.AddField(output_filepath, "max_I_V", "FLOAT", 8, 2)
    arcpy.management.AddField(output_filepath, "flow_area", "FLOAT", 8, 2)
    arcpy.management.AddField(output_filepath, "flow_diam", "FLOAT", 8, 2)


    # weirs_output_filepath = arcpy.CreateFeatureclass_management(output_folder, weirs_new_filename, "POLYLINE")[0]
    # arcpy.management.AddField(weirs_output_filepath, "MUID", "TEXT")
    # arcpy.management.AddField(weirs_output_filepath, "NetTypeNo", "SHORT")
    # arcpy.management.AddField(weirs_output_filepath, "Discharge", "FLOAT", 8, 2)

    links_output_filepath = arcpy.CreateFeatureclass_management(output_folder, links_new_filename, "POLYLINE")[0]
    arcpy.management.AddField(links_output_filepath, "MUID", "TEXT")
    arcpy.management.AddField(links_output_filepath, "NetTypeNo", "SHORT")
    arcpy.management.AddField(links_output_filepath, "MaxQ", "FLOAT", 8, 2)
    arcpy.management.AddField(links_output_filepath, "SumQ", "FLOAT", 8, 2)
    arcpy.management.AddField(links_output_filepath, "EndQ", "FLOAT", 8, 2)
    arcpy.management.AddField(links_output_filepath, "MinQ", "FLOAT", 8, 2)
    arcpy.management.AddField(links_output_filepath, "MaxV", "FLOAT", 8, 2)
except Exception as e:
    print(e)
    for filepath in [os.path.join(output_folder, new_filename)]:
        with arcpy.da.UpdateCursor(output_filepath, ["MUID"]) as cursor:
            for row in cursor:
                cursor.deleteRow()

with arcpy.da.InsertCursor(output_filepath, ["SHAPE@", "MUID", "Diameter", "Invert_lev", "Max_elev", "Flood_dep", "Flood_vol", "NetTypeNo", "max_hl", "max_I_V", "flow_area", "flow_diam"]) as cursor:
    for query_node in df.data.Nodes:
        muid = query_node.ID
        if muid not in nodes:
            nodes[muid] = Node(muid)
        node = nodes[muid]
        node.ground_level = query_node.CriticalLevel if hasattr(query_node, 'CriticalLevel') and query_node.CriticalLevel else query_node.GroundLevel
        node.invert_level = query_node.BottomLevel
        node.max_level = np.max(df.get_node_values(muid, "WaterLevel"))
        if muid in [reach.tonode for reach in reaches.values()] and muid in [reach.fromnode for reach in reaches.values()]:
            try:
                water_levels = [np.max(df.get_reach_end_values(reach.muid, "WaterLevel")) for reach in reaches.values() if reach.tonode == muid and reach.type == "Link"]
                node.inlet_waterlevel = np.max(water_levels) if water_levels else 0
                water_levels = [np.max(df.get_reach_start_values(reach.muid, "WaterLevel")) for reach in reaches.values() if reach.fromnode == muid and reach.type == "Link"]
                node.outlet_waterlevel = np.max(water_levels) if water_levels else 0
                node.max_headloss = node.inlet_waterlevel - node.outlet_waterlevel
                inlet_velocities = [np.max(df.get_reach_end_values(reach.muid, "FlowVelocity")) for reach in reaches.values() if reach.tonode == muid and reach.type == "Link"]
                node.max_inlet_velocity = np.max(inlet_velocities)
                if node.id == "D08089XR":
                    print([np.max(df.get_reach_end_values(reach.muid, "WaterLevel")) for reach in reaches.values() if reach.tonode == muid and reach.type == "Link"])
                    print(muid, node.max_headloss, node.outlet_waterlevel, node.inlet_waterlevel)
            except Exception as e:
                print(muid)
                print(traceback.format_exc())
                print(e)
        # print(node.max_headloss)
        # print((node.max_level, node.ground_level))
        # if node.flood_depth>0:
        cursor.insertRow([arcpy.Point(query_node.XCoordinate, query_node.YCoordinate), muid, node.diameter if node.diameter else 0, node.invert_level, node.max_level, node.flood_depth, node.flood_volume, node.net_type_no if node.net_type_no is not None else 0, node.max_headloss if node.max_headloss else 0, node.max_inlet_velocity if node.max_inlet_velocity else 0, node.flow_area, node.flow_area_diameter])

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
with arcpy.da.InsertCursor(links_output_filepath, ["SHAPE@", "MUID", "MaxQ", "SumQ", "NetTypeNo", "EndQ", "MinQ", "MaxV"]) as cursor:
    for muid in reaches.keys():
        reach = reaches[muid]
        try:
            reach.max_discharge = np.max(abs(df.get_reach_end_values(muid, "Discharge")))
            reach.min_discharge = np.min(df.get_reach_end_values(muid, "Discharge"))
            reach.sum_discharge = np.trapz(abs(df.get_reach_end_values(muid, "Discharge")), timeseries)
            reach.end_discharge = abs(df.get_reach_end_values(muid, "Discharge"))[-1]
            reach.max_flow_velocity = np.max(abs(df.get_reach_end_values(muid, "FlowVelocity")))
        except:
            pass
            # reach.max_discharge = np.max(abs(df.get_reach_end_values("Weir:"+muid, "Discharge")))
            # reach.sum_discharge = np.trapz(abs(df.get_reach_end_values("Weir:" + muid, "Discharge")), timeseries)
        try:
            cursor.insertRow([reach.shape, muid, reach.max_discharge if reach.max_discharge else 0, reach.sum_discharge if reach.sum_discharge else 0,
                          reach.net_type_no if reach.net_type_no is not None else 0, reach.end_discharge if reach.end_discharge else 0, reach.min_discharge if reach.min_discharge else 0, reach.max_flow_velocity if reach.max_flow_velocity else 0])
        except Exception as e:
            print(e)