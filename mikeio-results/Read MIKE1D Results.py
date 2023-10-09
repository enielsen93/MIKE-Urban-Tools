from mikeio1d.res1d import Res1D, QueryDataNode, QueryDataReach
import arcpy
import os
import numpy as np
import traceback
import cProfile
from alive_progress import alive_bar
import math

extension = ""

MU_model = r"C:\Users\ELNN\OneDrive - Ramboll\Documents\Aarhus Vand\Vesterbro Torv\MIKE_URBAN\VBT_STATUS\VBT_STATUS.sqlite"
# res1d_file = r"C:\Users\ELNN\OneDrive - Ramboll\Documents\Aarhus Vand\Kongelund og Marselistunnel\MIKE\KOM_Plan_027\KOM_CDS_5_sc3Base.res1d"
res1d_file = r"C:\Users\ELNN\OneDrive - Ramboll\Documents\Aarhus Vand\Vesterbro Torv\MIKE_URBAN\VBT_STATUS\VBT_STATUS_m1d - Result Files\VBT_STATUS_CDS20_120BaseDefault_Network_HD.res1d"
# res1d_files = [r'C:\Users\ELNN\OneDrive - Ramboll\Documents\Aarhus Vand\Soenderhoej\MIKE\MIKE_URBAN\SON_023\SON_023_CDS5_156_ARF_100Base.res1d', r'C:\Users\ELNN\OneDrive - Ramboll\Documents\Aarhus Vand\Soenderhoej\MIKE\MIKE_URBAN\SON_023\SON_023_CDS5_156_ARF_150Base.res1d', r'C:\Users\ELNN\OneDrive - Ramboll\Documents\Aarhus Vand\Soenderhoej\MIKE\MIKE_URBAN\SON_023\SON_023_N_CDS5_156Base.res1d', r'C:\Users\ELNN\OneDrive - Ramboll\Documents\Aarhus Vand\Soenderhoej\MIKE\MIKE_URBAN\SON_023\SON_023_N_CDS5_156_ARF_127Base.res1d']
# MU_model = r"C:\Papirkurv\VBT_STATUS\VBT_STATUS.sqlite"
# res1d_file = r"C:\Users\ELNN\OneDrive - Ramboll\Documents\Aarhus Vand\Soenderhoej\MIKE\MIKE_URBAN\SON_013\SON_013_N_CDS5_156_ARF_127Base.res1d"
# MU_model = r"C:\Users\ELNN\OneDrive - Ramboll\Documents\Aarhus Vand\Soenderhoej\MIKE\MIKE_URBAN\SON_013\SON_013.mdb"
# MU_model= "C:\Users\ELNN\OneDrive - Ramboll\Documents\Aarhus Vand\Soenderhoej\MIKE\MIKE_URBAN\SON_z014\SON_014.mdb"
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
        self.end_depth = 0

    @property
    def flood_depth(self):
        if self.max_level and self.ground_level:
            return max(self.max_level - self.ground_level,0)
        else:
            return 0

    @property
    def flood_volume(self):
        if self.diameter and self.flood_depth:
            node_area = self.diameter**2*np.pi/4
            integral1 = (math.exp(7*min(1,self.flood_depth))/7-math.exp(7*0)/7)*node_area
            integral2 = (max(1, self.flood_depth)-1)*node_area*1000
            return integral1+integral2
        else:
            return 0

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
        self.length = None
        self.uplevel = None
        self.dwlevel = None
        self.max_discharge = None
        self.sum_discharge = None
        self.end_discharge = None
        self.min_discharge = None
        self.fromnode = None
        self.tonode = None
        self.type = "Link"
        self.max_flow_velocity = None
        self.min_start_water_level = None
        self.min_end_water_level = None
        self.max_start_water_level = None
        self.max_end_water_level = None

    @property
    def energy_line_gradient(self):
        return ((self.max_start_water_level - self.max_end_water_level) - (self.min_start_water_level-self.min_end_water_level)) / self.shape.length

    @property
    def friction_loss(self):
        return (self.max_start_water_level - self.max_end_water_level) - (self.min_start_water_level-self.min_end_water_level)

    @property
    def fill_degree(self):
        if all((self.max_start_water_level, self.uplevel, self.diameter)):
            return (self.max_start_water_level-self.uplevel)/self.diameter*1e2
    # @property
    # def shape(self):
    #     return arcpy.Polyline(arcpy.Array([arcpy.Point(*self.start_coordinate), arcpy.Point(*self.end_coordinate)]))


if MU_model and ".mdb" in MU_model:
    import pyodbc
    conn = pyodbc.connect(
        r'Driver={Microsoft Access Driver (*.mdb, *.accdb)};DBQ=%s;' % (MU_model))
    cursor = conn.cursor()
    cursor.execute('select MUID, Diameter, NetTypeNo, groundlevel, criticallevel, invertlevel from msm_Node')
    rows = cursor.fetchall()
    for row in rows:
        nodes[row[0]] = Node(row[0])
        nodes[row[0]].diameter = row[1]
        nodes[row[0]].net_type_no = row[2]
        nodes[row[0]].ground_level = row[3]
        nodes[row[0]].critical_level = row[4]
        nodes[row[0]].invert_level = row[5]

    cursor.execute('select MUID, NetTypeNo from msm_Weir')
    rows = cursor.fetchall()
    for row in rows:
        reaches[row[0]] = Reach(row[0])
        reaches[row[0]].net_type_no = row[1]
        reaches[row[0]].type = "Weir"

    cursor.execute('select MUID, NetTypeNo, Diameter, uplevel, uplevel_c, dwlevel, dwlevel_c from msm_Link')
    rows = cursor.fetchall()
    for row in rows:
        reaches[row[0]] = Reach(row[0])
        reaches[row[0]].net_type_no = row[1]
        reaches[row[0]].diameter = row[2]
        reaches[row[0]].uplevel = row[3] if row[3] else row[4]
        reaches[row[0]].dwlevel = row[5] if row[5] else row[6]

elif MU_model and ".sqlite" in MU_model:
    with arcpy.da.SearchCursor(os.path.join(MU_model, "msm_Node"), ["MUID", "Diameter", "NetTypeNo", "GroundLevel", "CriticalLevel", "InvertLevel"]) as cursor:
        for row in cursor:
            nodes[row[0]] = Node(row[0])
            nodes[row[0]].diameter = row[1]
            nodes[row[0]].net_type_no = row[2]
            nodes[row[0]].ground_level = row[3]
            nodes[row[0]].critical_level = row[4]
            nodes[row[0]].invert_level = row[5]

    with arcpy.da.SearchCursor(os.path.join(MU_model, "msm_Weir"), ["MUID", "NetTypeNo"]) as cursor:
        for row in cursor:
            reaches[row[0]] = Reach(row[0])
            reaches[row[0]].net_type_no = row[1]
            reaches[row[0]].type = "Weir"

    with arcpy.da.SearchCursor(os.path.join(MU_model, "msm_Link"), ["MUID", "NetTypeNo", "Diameter", "uplevel", "uplevel_c", "dwlevel", "dwlevel_c"]) as cursor:
        for row in cursor:
            reaches[row[0]] = Reach(row[0])
            reaches[row[0]].net_type_no = row[1]
            reaches[row[0]].diameter = row[2]
            reaches[row[0]].uplevel = row[3] if row[3] else row[4]
            reaches[row[0]].dwlevel = row[5] if row[5] else row[6]

# res1d_file = r"C:\Users\ELNN\OneDrive - Ramboll\Documents\Aarhus Vand\Kongelund og Marselistunnel\MIKE\KOM_Plan_017_sc2\KOM_Plan_017_sc2_CDS_5Base.res1d"
print(res1d_file)
# queries = []
res1d = Res1D(res1d_file)

for reach in [r for r in res1d.data.Reaches if r.Name.replace("Weir:","") in reaches]:
    muid = reach.Name.replace("Weir:","")
    reach.type = "Weir"
    res1d_nodes = [node for node in res1d.data.Nodes]
    reaches[muid].shape = arcpy.Polyline(arcpy.Array([arcpy.Point(coordinate.X, coordinate.Y) for coordinate in reach.DigiPoints]))
    reaches[muid].fromnode = res1d_nodes[reach.StartNodeIndex].ID
    reaches[muid].tonode = res1d_nodes[reach.EndNodeIndex].ID
    reaches[muid].length = reach.Length

df = Res1D(res1d_file)

# dataframe = df.read()
arcpy.env.overwriteOutput = True
output_folder = r"C:\Papirkurv\Resultater"

def getAvailableFilename(filepath):
    if arcpy.Exists(filepath):
        i = 1
        while arcpy.Exists(filepath + "%d" % i):
            i += 1
        return filepath + "%d" % i
    else:
        return filepath

extension = extension if 'extension' in locals() else ""

nodes_new_filename = getAvailableFilename(os.path.join(output_folder, os.path.basename(res1d_file).replace(".res1d","_nodes%s.shp" % extension)))

links_new_filename = getAvailableFilename(os.path.join(output_folder, os.path.basename(res1d_file).replace(".res1d","_links%s.shp" % extension)))

nodes_output_filepath = arcpy.CreateFeatureclass_management(output_folder, os.path.basename(nodes_new_filename), "POINT")[0]
arcpy.management.AddField(nodes_output_filepath, "MUID", "TEXT")
arcpy.management.AddField(nodes_output_filepath, "NetTypeNo", "SHORT")
for field in ["Diameter", "Invert_lev", "Max_elev", "Flood_dep", "Flood_vol", "max_hl", "max_I_V", "flow_area", "flow_diam", "end_depth"]:
    arcpy.management.AddField(nodes_output_filepath, field, "FLOAT", 8, 2)

links_output_filepath = arcpy.CreateFeatureclass_management(output_folder, os.path.basename(links_new_filename), "POLYLINE")[0]
arcpy.management.AddField(links_output_filepath, "MUID", "TEXT")
arcpy.management.AddField(links_output_filepath, "NetTypeNo", "SHORT")
for field in ["Diameter", "MaxQ", "SumQ", "EndQ", "MinQ", "MaxV", "FillDeg", "EnergyGr", "FrictionLo"]:
    arcpy.management.AddField(links_output_filepath, field, "FLOAT", 8, 2)

timeseries = [time.timestamp() for time in df.time_index]
print("Calculating for reaches")
with alive_bar(len(reaches),force_tty=True) as bar:
    with arcpy.da.InsertCursor(links_output_filepath, ["SHAPE@", "MUID", "Diameter", "MaxQ", "SumQ", "NetTypeNo", "EndQ", "MinQ", "MaxV", "EnergyGr", "FrictionLo", "FillDeg"]) as cursor:
        for muid in reaches.keys():
            reach = reaches[muid]
            try:
                if reach.type == "Link":
                    queries = [QueryDataReach("Discharge", muid, reach.length), QueryDataReach("FlowVelocity", muid, reach.length),
                               QueryDataReach("WaterLevel", muid, 0), QueryDataReach("WaterLevel", muid, reach.length)]
                    query_result = res1d.read(queries)
                    reach_discharge = query_result.iloc[:,0]
                    reach.max_discharge = np.max(abs(reach_discharge))
                    reach.min_discharge = np.min(reach_discharge)
                    reach.sum_discharge = np.trapz(abs(reach_discharge), timeseries)
                    reach.end_discharge = abs(reach_discharge)[-1]
                    reach.max_flow_velocity = np.max(abs(query_result.iloc[:,1]))
                    reach_start_values = query_result.iloc[:,2]
                    reach_end_values = query_result.iloc[:,3]
                    reach.min_start_water_level = np.min(abs(reach_start_values))
                    reach.min_end_water_level = np.min(abs(reach_end_values))
                    reach.max_start_water_level = np.max(abs(reach_start_values))
                    reach.max_end_water_level = np.max(abs(reach_end_values))
            except Exception as e:
                print(e)
                # reach.max_discharge = np.max(abs(df.get_reach_end_values("Weir:"+muid, "Discharge")))
                # reach.sum_discharge = np.trapz(abs(df.get_reach_end_values("Weir:" + muid, "Discharge")), timeseries)
            if True:
                # print((reach.min_start_water_level, reach.min_end_water_level, reach.max_start_water_level, reach.max_end_water_level))
                if all((reach.min_start_water_level, reach.min_end_water_level, reach.max_start_water_level, reach.max_end_water_level)):
                    energy_line_gradient = reach.energy_line_gradient
                    friction_loss = reach.friction_loss
                else:
                    energy_line_gradient = 0
                    friction_loss = 0
                cursor.insertRow([reach.shape, muid, reach.diameter if reach.diameter else 0, reach.max_discharge if reach.max_discharge else 0, reach.sum_discharge if reach.sum_discharge else 0,
                              reach.net_type_no if reach.net_type_no is not None else 0, reach.end_discharge if reach.end_discharge else 0,
                                  reach.min_discharge if reach.min_discharge else 0, reach.max_flow_velocity if reach.max_flow_velocity else 0,
                                  energy_line_gradient, friction_loss, reach.fill_degree if reach.fill_degree else 0])
                bar()
            # except Exception as e:
            #     print(e)

res1d_quantities = res1d.quantities

with arcpy.da.InsertCursor(nodes_output_filepath, ["SHAPE@", "MUID", "Diameter", "Invert_lev", "Max_elev", "Flood_dep", "Flood_vol", "NetTypeNo", "max_hl", "max_I_V", "flow_area", "flow_diam", "end_depth"]) as cursor:
    # with alive_bar(len(df.data.Nodes), force_tty=True) as bar:
    for query_node in df.data.Nodes:
        muid = query_node.ID
        if muid not in nodes:
            nodes[muid] = Node(muid)
        node = nodes[muid]
        try:
            if not node.ground_level:
                node.ground_level = query_node.CriticalLevel if hasattr(query_node, 'CriticalLevel') and query_node.CriticalLevel else query_node.GroundLevel
            if not node.invert_level:
                query_node.BottomLevel
        except Exception as e:
            if muid == "504120R":
                print("Break")
            print(e)
        # try:
            # node.ground_level = query_node.CriticalLevel if hasattr(query_node, 'CriticalLevel') and query_node.CriticalLevel else query_node.GroundLevel
            # node.invert_level = query_node.BottomLevel
        # except Exception as e:
        #     print(e)

        queries = [QueryDataNode("WaterLevel", muid)]
        query_result = res1d.read(queries)
        node.max_level = np.max(query_result.iloc[:,0])
        node.end_depth = query_result.iloc[-1, 0] - node.invert_level
        if "WaterVolumeAboveGround" in res1d_quantities:
            query = QueryDataNode("WaterVolumeAboveGround", muid)
            try:
                query_result = res1d.read(query)
                mike_flood_volume = np.max(np.max(query_result.iloc[:, 0]))
            except Exception as e:
                mike_flood_volume = None
        else:
            mike_flood_volume = None

        if muid in [reach.tonode for reach in reaches.values()] and muid in [reach.fromnode for reach in reaches.values()]:
            try:
                water_levels = [reach.max_end_water_level for reach in reaches.values() if reach.tonode == muid and reach.type == "Link"]
                node.inlet_waterlevel = np.max(water_levels) if water_levels else 0
                water_levels = [reach.max_start_water_level for reach in reaches.values() if reach.fromnode == muid and reach.type == "Link"]
                node.outlet_waterlevel = np.max(water_levels) if water_levels else 0
                node.max_headloss = node.inlet_waterlevel - node.outlet_waterlevel
                inlet_velocities = [reach.max_flow_velocity for reach in reaches.values() if reach.tonode == muid and reach.type == "Link"]
                node.max_inlet_velocity = np.max(inlet_velocities) if inlet_velocities else 0

            except Exception as e:
                print(muid)
                # if node.id == "D08089XR":
                #     print([np.max(df.get_reach_end_values(reach.muid, "WaterLevel")) for reach in reaches.values() if reach.tonode == muid and reach.type == "Link" and hasattr(reach, "muid")])
                #     print(muid, node.max_headloss, node.outlet_waterlevel, node.inlet_waterlevel)
                print(traceback.format_exc())
                print(e)
        cursor.insertRow([arcpy.Point(query_node.XCoordinate, query_node.YCoordinate), muid, node.diameter if node.diameter else 0, node.invert_level, node.max_level, node.flood_depth, node.flood_volume if not mike_flood_volume else mike_flood_volume, node.net_type_no if node.net_type_no is not None else 0, node.max_headloss if node.max_headloss else 0, node.max_inlet_velocity if node.max_inlet_velocity else 0, node.flow_area, node.flow_area_diameter, node.end_depth if node.end_depth else 0])
            # bar()
# cProfile.run("main()")