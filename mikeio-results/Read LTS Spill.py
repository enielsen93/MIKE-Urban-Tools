from mikeio1d.res1d import Res1D, QueryDataNode, QueryDataReach
import arcpy
import os
import numpy as np
import traceback
import cProfile
from alive_progress import alive_bar
import math

extension = "_1D_spill"

MU_model = None
MU_model = r"C:\Users\ELNN\OneDrive - Ramboll\Documents\Aarhus Vand\Vesterbro Torv\MIKE_URBAN\VBT_STATUS_005\VBT_STATUS_005.sqlite"
# res1d_file = r"C:\Users\ELNN\OneDrive - Ramboll\Documents\Aarhus Vand\Kongelund og Marselistunnel\MIKE\KOM_Plan_027\KOM_CDS_5_sc3Base.res1d"
res1d_file = r"C:\Users\ELNN\OneDrive - Ramboll\Documents\Aarhus Vand\Vesterbro Torv\MIKE_URBAN\05_RESULTS\01_NETWORK\2023-11-01\VBT_STATUS_005_CDS_20_138_spillBaseDefault_LTS_extreme_statistics.res1d"
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

# class Reach:
#     def __init__(self, muid):
#         self.muid = muid
#         self.net_type_no = 0
#         self.diameter = 0
#         # self.start_coordinate = None
#         # self.end_coordinate = None
#         self.shape = None
#         self.length = None
#         self.uplevel = None
#         self.dwlevel = None
#         self.max_discharge = None
#         self.sum_discharge = None
#         self.end_discharge = None
#         self.min_discharge = None
#         self.fromnode = None
#         self.tonode = None
#         self.type = "Link"
#         self.max_flow_velocity = None
#         self.min_start_water_level = None
#         self.min_end_water_level = None
#         self.max_start_water_level = None
#         self.max_end_water_level = None
#
#     @property
#     def energy_line_gradient(self):
#         return ((self.max_start_water_level - self.max_end_water_level) - (self.min_start_water_level-self.min_end_water_level)) / self.shape.length
#
#     @property
#     def friction_loss(self):
#         return (self.max_start_water_level - self.max_end_water_level) - (self.min_start_water_level-self.min_end_water_level)
#
#     @property
#     def fill_degree(self):
#         if all((self.max_start_water_level, self.uplevel, self.diameter)):
#             return (self.max_start_water_level-self.uplevel)/self.diameter*1e2
#     # @property
#     # def shape(self):
#     #     return arcpy.Polyline(arcpy.Array([arcpy.Point(*self.start_coordinate), arcpy.Point(*self.end_coordinate)]))


print("Reading MIKE Database")
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

    # cursor.execute('select MUID, NetTypeNo from msm_Weir')
    # rows = cursor.fetchall()
    # for row in rows:
    #     reaches[row[0]] = Reach(row[0])
    #     reaches[row[0]].net_type_no = row[1]
    #     reaches[row[0]].type = "Weir"
    #
    # cursor.execute('select MUID, NetTypeNo, Diameter, uplevel, uplevel_c, dwlevel, dwlevel_c from msm_Link')
    # rows = cursor.fetchall()
    # for row in rows:
    #     reaches[row[0]] = Reach(row[0])
    #     reaches[row[0]].net_type_no = row[1]
    #     reaches[row[0]].diameter = row[2]
    #     reaches[row[0]].uplevel = row[3] if row[3] else row[4]
    #     reaches[row[0]].dwlevel = row[5] if row[5] else row[6]

elif MU_model and ".sqlite" in MU_model:
    with arcpy.da.SearchCursor(os.path.join(MU_model, "msm_Node"), ["MUID", "Diameter", "NetTypeNo", "GroundLevel", "CriticalLevel", "InvertLevel"]) as cursor:
        for row in cursor:
            nodes[row[0]] = Node(row[0])
            nodes[row[0]].diameter = row[1]
            nodes[row[0]].net_type_no = row[2]
            nodes[row[0]].ground_level = row[3]
            nodes[row[0]].critical_level = row[4]
            nodes[row[0]].invert_level = row[5]

    # with arcpy.da.SearchCursor(os.path.join(MU_model, "msm_Weir"), ["MUID", "NetTypeNo"]) as cursor:
    #     for row in cursor:
    #         reaches[row[0]] = Reach(row[0])
    #         reaches[row[0]].net_type_no = row[1]
    #         reaches[row[0]].type = "Weir"
    #
    # with arcpy.da.SearchCursor(os.path.join(MU_model, "msm_Link"), ["MUID", "NetTypeNo", "Diameter", "uplevel", "uplevel_c", "dwlevel", "dwlevel_c"]) as cursor:
    #     for row in cursor:
    #         reaches[row[0]] = Reach(row[0])
    #         reaches[row[0]].net_type_no = row[1]
    #         reaches[row[0]].diameter = row[2]
    #         reaches[row[0]].uplevel = row[3] if row[3] else row[4]
    #         reaches[row[0]].dwlevel = row[5] if row[5] else row[6]

# res1d_file = r"C:\Users\ELNN\OneDrive - Ramboll\Documents\Aarhus Vand\Kongelund og Marselistunnel\MIKE\KOM_Plan_017_sc2\KOM_Plan_017_sc2_CDS_5Base.res1d"
print(res1d_file)
# queries = []
res1d = Res1D(res1d_file)

# for reach in [r for r in res1d.data.Reaches if r.Name.replace("Weir:","") in reaches]:
#     muid = reach.Name.replace("Weir:","")
#     reach.type = "Weir"
#     res1d_nodes = [node for node in res1d.data.Nodes]
#     reaches[muid].shape = arcpy.Polyline(arcpy.Array([arcpy.Point(coordinate.X, coordinate.Y) for coordinate in reach.DigiPoints]))
#     reaches[muid].fromnode = res1d_nodes[reach.StartNodeIndex].ID
#     reaches[muid].tonode = res1d_nodes[reach.EndNodeIndex].ID
#     reaches[muid].length = reach.Length

print("Reading res1D_file")
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

print("Creating Feature Class")
nodes_output_filepath = arcpy.CreateFeatureclass_management(output_folder, os.path.basename(nodes_new_filename), "POINT")[0]
arcpy.management.AddField(nodes_output_filepath, "MUID", "TEXT")
arcpy.management.AddField(nodes_output_filepath, "NetTypeNo", "SHORT")
for field in ["Diameter", "Invert_lev", "Max_elev", "Flood_dep", "Flood_vol", "max_hl", "max_I_V", "flow_area", "flow_diam", "end_depth"]:
    arcpy.management.AddField(nodes_output_filepath, field, "FLOAT", 8, 2)

# timeseries = [time.timestamp() for time in df.time_index]
res1d_quantities = res1d.quantities

Vesterbro_Torv_nodes = ['P62020K', 'P62010Z', 'P62010X', 'P62010R', 'P62010K', 'P50900K', 'P50120K', 'P50110Z', 'P50110X', 'P50110K', 'P62011Z', 'P50900Z', 'P50150R', 'P50141R', 'P50140NR', 'P50130Z', 'P50080Z', 'O31C_1', 'P62023Z', 'P62021K', 'P50914K', 'P50913K', 'P50912W', 'P50901Z', 'P50211K', 'P50170K', 'P50160K', 'P50121Z', 'P50100R', 'P50090R', 'P50083K', 'P50082K', 'P50081K', 'P50080K', 'P50070W', 'P50061K', 'P50060K', 'P49110K', 'O031C', 'F901', 'F31A_1', 'F031A']
Vesterbro_Torv_flood_vol = {}

print("Reading and writing results")
with arcpy.da.InsertCursor(nodes_output_filepath, ["SHAPE@", "MUID", "Diameter", "Invert_lev", "Flood_vol"]) as cursor:
    with alive_bar(len(list(df.data.Nodes)), force_tty=True) as bar:
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
                print(e)
            # try:
                # node.ground_level = query_node.CriticalLevel if hasattr(query_node, 'CriticalLevel') and query_node.CriticalLevel else query_node.GroundLevel
                # node.invert_level = query_node.BottomLevel
            # except Exception as e:
            #     print(e)

            # query_result = res1d.read(queries)

            print(muid)
            print(muid in Vesterbro_Torv_nodes)
            # if "SurchargeIntegrated" in res1d_quantities:
            mike_flood_volume = None
            try:
                query = [QueryDataNode("WaterSpillDischargeIntegratedTime", muid), QueryDataNode("WaterSpillDischargeIntegrated", muid)]
                # try:
                surcharge_int_time, surcharge_int = res1d.read(query).values[0]
                surcharge_int_date = surcharge_int_time.date()
                mike_flood_volume = surcharge_int
                # print(muid)
                # if muid in Vesterbro_Torv_nodes:
                if surcharge_int_date in Vesterbro_Torv_flood_vol:
                    Vesterbro_Torv_flood_vol[surcharge_int_date] += surcharge_int
                else:
                    Vesterbro_Torv_flood_vol[surcharge_int_date] = surcharge_int
            except Exception as e:
                print(e)
            # except Exception as e:
            #     mike_flood_volume = None
            # else:
            #     mike_flood_volume = None

            # if muid in [reach.tonode for reach in reaches.values()] and muid in [reach.fromnode for reach in reaches.values()]:
            #     try:
            #
            #     except Exception as e:
            #         print(muid)
            #         # if node.id == "D08089XR":
            #         #     print([np.max(df.get_reach_end_values(reach.muid, "WaterLevel")) for reach in reaches.values() if reach.tonode == muid and reach.type == "Link" and hasattr(reach, "muid")])
            #         #     print(muid, node.max_headloss, node.outlet_waterlevel, node.inlet_waterlevel)
            #         print(traceback.format_exc())
            #         print(e)
            cursor.insertRow([arcpy.Point(query_node.XCoordinate, query_node.YCoordinate), muid, node.diameter if node.diameter else 0, node.invert_level, mike_flood_volume if mike_flood_volume else 0])
            bar()
# cProfile.run("main()")
