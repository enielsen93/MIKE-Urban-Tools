"""
Created on Mon Jul 30 11:21:31 2018

@author: eni
"""
import os
import arcpy
import numpy as np
import re
import hashlib
import math
import os
import sys
import networkx as nx
import ColebrookWhite
import networker
import pandas as pd
import traceback
import datetime
import pythonaddins
import mikegraph
import sqlite3
import timearea
from copy import deepcopy

if "mapping" in dir(arcpy):
    import arcpy.mapping as apmapping
    from arcpy.mapping import MapDocument as MapDocument
    from arcpy.mapping import MapDocument as MapDocument
else:
    import arcpy.mp as apmapping
    from arcpy.mp import ArcGISProject as MapDocument
    from arcpy.mapping import MapDocument as MapDocument

diameters_plastic = [188, 235, 297, 377, 493, 588, 781, 985, 1185, 1385, 1485, 1585, 2000, 2200, 2400, 2600, 2800, 3000]
diameters_concrete = [200, 300, 400, 500, 600, 700, 800, 900, 1000, 1200, 1400, 1600, 1800, 2000, 2250, 2500, 3000, 3500]

def getAvailableFilename(filepath, parent = None):
    parent = "F%s" % (parent) if parent and parent[0].isdigit() else None
    parent = os.path.basename(re.sub(r"\.[^\.\\]+$","", parent)).replace(".","_").replace("-","_").replace(" ","_").replace(",","_") if parent else None
    filepath = "%s\%s_%s" % (os.path.dirname(filepath), parent, os.path.basename(filepath)) if parent else filepath
    if arcpy.Exists(filepath):
        i = 1
        while arcpy.Exists(filepath + "%d" % i):
            i += 1
        return filepath + "%d" % i
        # try:
            # arcpy.Delete_management(filepath)
            # return filepath
        # except:
            # i = 1
            # while arcpy.Exists(filepath + "%d" % i):
                # try:
                    # arcpy.Delete_management(filepath + "%d" % i)
                    # return filepath + "%d" % i
                # except:
                    # i += 1
            # return filepath + "%d" % i
    else:
        return filepath

class Toolbox(object):
    def __init__(self):
        self.label =  "Pipe Dimension Tool"
        self.alias  = "Pipe Dimension Tool"
        self.canRunInBackground = True
        # List of tool classes associated with this toolbox
        self.tools = [PipeDimensionToolTAPro, upgradeDimensions, downgradeDimensions, setOutletLoss, reverseChange, InterpolateInvertLevels, GetMinimumSlope, CopyDiameter, CalculateSlopeOfPipe, ResetUpLevelDwlevel]

class PipeDimensionToolTAPro(object):
    def __init__(self):
        self.label       = "Calculate minimum required pipe diameter through Time Area Method"
        self.description = "Calculate minimum required pipe diameter through Time Area Method"
        self.canRunInBackground = False

    def getParameterInfo(self):
        #Define parameter definitions

        pipe_layer = arcpy.Parameter(
            displayName="Pipe feature layer",
            name="pipe_layer",
            datatype="GPFeatureLayer",
            parameterType="Required",
            direction="Input")

        # flags = arcpy.Parameter(
            # displayName="Layer to trace upstream network and analyze catchment for",
            # name="flags",
            # datatype="GPFeatureLayer",
            # parameterType="Required",
            # direction="Input")
        # flags.filter.list = ["Simple Junction"]

        reaches = arcpy.Parameter(
            displayName="Trace network through:",
            name="reaches",
            datatype="GPString",
            parameterType="Optional",
            multiValue=True,
            direction="Input")
        reaches.filter.type = "ValueList"
        reaches.filter.list = ["Orifice","Weir","Pump", "Basin"]
        
        result_field = arcpy.Parameter(
			displayName= "Field to assign diameter to",
			name="result_field",
			datatype="GPString",
			parameterType="Optional",
			direction="Input")

        breakChainOnNodes = arcpy.Parameter(
            displayName="End each trace at following node MUIDs (each node should by delimited by a comma: node1, node2)",
            name="breakChainOnNodes",
            datatype="GPString",
            parameterType="optional",
            direction="Input")
        breakChainOnNodes.category = "Additional settings"

        runoff_file = arcpy.Parameter(
            displayName="Runoff rain event in ASCII Format",
            name="runoff",
            datatype="file",
            parameterType="Required",
            direction="Input")
        runoff_file.filter.list = ["txt","km2","kmd","csv"]

        scaling_factor = arcpy.Parameter(
			displayName= "Scaling Factor for runoff rain event",
			name="scaling_factor",
			datatype="GPString",
			parameterType="Required",
			direction="Input")
        scaling_factor.value = "1"

        useMaxInflow = arcpy.Parameter(
            displayName="Use Max. Inflow field as additional discharge to system (checkbox on msm_Node must be left unticked) - unit m3/s",
            name="useMaxInflow",
            datatype="Boolean",
            parameterType="optional",
            direction="Input")
        useMaxInflow.category = "Additional settings"
        useMaxInflow.value = True

        slopeOverwrite = arcpy.Parameter(
            displayName="Overwrite slope of pipes to:",
            name="slopeOverwrite",
            datatype="double",
            parameterType="optional",
            direction="Input")
        slopeOverwrite.category = "Additional settings"

        writeDFS0 = arcpy.Parameter(
            displayName="Write csv file of runoff for every selected pipe to txt file:",
            name="writeDFS0",
            datatype="file",
            parameterType="optional",
            direction="Output")
        writeDFS0.category = "Additional settings"

        runoff_file = arcpy.Parameter(
            displayName="Runoff rain event in ASCII Format",
            name="runoff",
            datatype="file",
            parameterType="Required",
            direction="Input")
        runoff_file.filter.list = ["txt","km2","kmd","csv"]

        keep_largest_diameter = arcpy.Parameter(
            displayName="Only change diameter if it's greater than existing",
            name="keep_largest_diameter",
            datatype="Boolean",
            parameterType="optional",
            direction="Input")
        keep_largest_diameter.category = "Additional settings"
        keep_largest_diameter.value = True
        
        change_material = arcpy.Parameter(
            displayName="Change material (Plastic if less than 500 mm, concrete if greater than or equal to 500 mm",
            name="change_material",
            datatype="Boolean",
            parameterType="optional",
            direction="Input")
        change_material.category = "Additional settings"
        change_material.value = True

        debug_output = arcpy.Parameter(
            displayName="Export Layer with attributes instead",
            name="debug_output",
            datatype="Boolean",
            parameterType="optional",
            direction="Input")
        # get_start_time = arcpy.Parameter(
            # displayName="Copy start time from dfs0 file:",
            # name="get_start_time",
            # datatype="file",
            # parameterType="optional",
            # direction="Input")
        # get_start_time.filter.list = ["dfs0"]
        # get_start_time.category = "Additional settings"
        # get_start_time.enabled = False

        parameters = [pipe_layer, reaches, result_field, runoff_file, scaling_factor, breakChainOnNodes, useMaxInflow, slopeOverwrite, writeDFS0, keep_largest_diameter, change_material, debug_output]
        return parameters

    def isLicensed(self):
        return True

    def updateParameters(self, parameters): #optional
        #pipe_layer = parameters[0].ValueAsText
        #MU_database = os.path.dirname(arcpy.Describe(pipe_layer).catalogPath)
        
        #if ".sqlite" in MU_database:
        #    parameters[2].Enabled = False
        #else:
        #    parameters[2].Enabled = True
        # mxd = arcpy.mapping.MapDocument("CURRENT")  
        # df = arcpy.mapping.ListDataFrames(mxd)[0]  
        # workspaces = set()
        # for lyr in arcpy.mapping.ListLayers(mxd, df):
            # if lyr.supports("workspacepath"):
                # workspaces.add(lyr.workspacePath)


        # if parameters[0].altered:
            # pipe_layer = parameters[0].ValueAsText
            # MU_database = os.path.dirname(arcpy.Describe(pipe_layer).catalogPath)
            # parameters[2].filter.list = [f.name for f in arcpy.Describe(MU_database + "\msm_Link").fields]

        # if parameters[9].ValueAsText:
            # parameters[10].enabled = True
        # else:
            # parameters[10].enabled = False
        return

    def updateMessages(self, parameters): #optional
        return

    def execute(self, parameters, messages):
        pipe_layer = parameters[0].ValueAsText
        MU_database = os.path.dirname(arcpy.Describe(pipe_layer).catalogPath).replace("\mu_Geometry", "")
        reaches = parameters[1].ValueAsText
        reaches = reaches + ";Link" if reaches else "Link"
        result_field = parameters[2].ValueAsText
        runoff_file = parameters[3].ValueAsText
        scaling_factor = float(parameters[4].Value)
        breakChainOnNodes = parameters[5].ValueAsText
        useMaxInflow = parameters[6].Value
        slopeOverwrite = parameters[7].Value
        writeDFS0 = parameters[8].ValueAsText
        keep_largest_diameter = parameters[9].Value
        change_material = parameters[10].Value
        debug_output = parameters[11].Value

        MIKE_folder = os.path.join(os.path.dirname(arcpy.env.scratchGDB), "MIKE URBAN")
        if not os.path.exists(MIKE_folder):
            os.mkdir(MIKE_folder)
        MIKE_gdb = os.path.join(MIKE_folder, os.path.splitext(os.path.basename(MU_database))[0])
        no_dir = True
        dir_ext = 0
        while no_dir:
            try:
                if arcpy.Exists(MIKE_gdb):
                    os.rmdir(MIKE_gdb)
                os.mkdir(MIKE_gdb)
                no_dir = False
            except Exception as e:
                dir_ext += 1
                MIKE_gdb = os.path.join(MIKE_folder,
                                        "%s_%d" % (os.path.splitext(os.path.basename(MU_database))[0], dir_ext))
        arcpy.env.scratchWorkspace = MIKE_gdb

        arcpy.SetProgressorLabel("Preparing")
        selected_pipes = [row[0] for row in arcpy.da.SearchCursor(pipe_layer, ["muid"])]

        mxd = arcpy.mapping.MapDocument("CURRENT")
        df = arcpy.mapping.ListDataFrames(mxd)[0]

        def addLayer(layer_source, source, group=None, workspace_type="ACCESS_WORKSPACE"):
            layer = apmapping.Layer(layer_source)
            if group:
                apmapping.AddLayerToGroup(df, group, layer, "BOTTOM")
            else:
                apmapping.AddLayer(df, layer, "TOP")
            updatelayer = apmapping.ListLayers(mxd, layer.name, df)[0]
            updatelayer.replaceDataSource(unicode(os.path.dirname(source.replace(r"\mu_Geometry", ""))), workspace_type,
                                          unicode(os.path.basename(source)))

        is_sqlite = True if ".sqlite" in MU_database else False

        msm_Link = os.path.join(MU_database, "msm_Link")
        msm_Node = os.path.join(MU_database, "msm_Node")
        msm_Orifice = os.path.join(MU_database, "msm_Orifice")
        msm_Weir = os.path.join(MU_database, "msm_Weir")
        msm_Pump = os.path.join(MU_database, "msm_Pump")
        msm_CatchCon = os.path.join(MU_database, "msm_CatchCon")
        ms_Catchment = os.path.join(MU_database, "msm_Catchment") if is_sqlite else os.path.join(MU_database,
                                                                                                 "ms_Catchment")
        msm_HParA = os.path.join(MU_database, "msm_HParA")
        ms_TabD = os.path.join(MU_database, "ms_TabD")

        arcpy.SetProgressorLabel("Mapping Network")
        graph = mikegraph.Graph(MU_database)
        graph.map_network()

        if breakChainOnNodes:
            breakEdges = [edge for edge in graph.graph.edges if
                          edge[0] in re.findall("([^'^(),; \n]+)", breakChainOnNodes)]
            graph.graph.network.remove_edges_from(breakEdges)
            for edge in breakEdges:
                arcpy.AddMessage(
                    "Removed edge %s-%s because %s is included in list of nodes to end trace at" % (edge[0], edge[1]))

        arcpy.SetProgressorLabel("Reading Rain Series")
        rainseries = timearea.TimeArea(runoff_file)

        target_manholes = [graph.network.links[link].fromnode for link in selected_pipes]
        connected_sources = []
        arcpy.SetProgressor("step", "Tracing to every pipe selected", 0, len(target_manholes), 1)

        # critical_node = {'MUID': None, 'Slope': None, 'Elevation Difference': None, 'Distance': None}

        timearea_curves = {}
        peak_discharge = {}
        peak_discharge_time = {}
        total_catchments = []
        for target_i, target_manhole in enumerate(target_manholes):
            arcpy.SetProgressorPosition(target_i)
            timearea_curves[target_manhole] = rainseries.timeareaCurve(target_manhole, graph)


            if debug_output:
                old_setting = arcpy.env.addOutputsToMap
                arcpy.env.addOutputsToMap = False
                table = arcpy.management.CreateTable(r"in_memory", target_manhole, os.path.dirname(
                    os.path.realpath(__file__)) + "\Data\PipeDimensionTool\Template.dbf")[0]

                with arcpy.da.InsertCursor(table, ["Discharge"]) as cursor:
                    for discharge in timearea_curves[target_manhole]:
                        cursor.insertRow([discharge])

                table_view = arcpy.MakeTableView_management(table, r"%s_tv" % os.path.basename(table))

                arcpy.env.addOutputsToMap = True
                gr = arcpy.Graph()

                gr.addSeriesAreaVertical(table_view, 'Discharge', "OID")
                gr.graphPropsGeneral.title = target_manhole

                graph_template = os.path.dirname(
                    os.path.realpath(__file__)) + "\Data\PipeDimensionTool\graph_template.grf"
                arcpy.MakeGraph_management(graph_template, gr, target_manhole)
                arcpy.env.addOutputsToMap = old_setting

            peak_discharge[target_manhole] = np.max(timearea_curves[target_manhole])
            peak_discharge_time[target_manhole] = np.argmax(timearea_curves[target_manhole])

        return
        # arcpy.AddMessage(("total catchments", total_catchments))
        # arcpy.AddMessage(("total_red_opl", total_red_opl))

        if writeDFS0:
            dfs0_text = np.empty((2 + len(timearea_curves[timearea_curves.keys()[0]])), dtype=object)
            dfs0_text[0] = "\t".join(["Discharge[meter^3/sec]:Instantaneous"] * len(timearea_curves.keys()))
            dfs0_text[1] = "Time"
            for i in range(len(dfs0_text) - 2):
                dfs0_text[i + 2] = str(series.index[0] + datetime.timedelta(minutes=i))

            for target_manhole in sorted(timearea_curves.keys()):
                dfs0_text[1] += "\t" + target_manhole
                for discharge_i, discharge in enumerate(timearea_curves[target_manhole] / 1e3):
                    dfs0_text[discharge_i + 2] += "\t%1.6f" % (discharge)
            filepath = writeDFS0
            with open(filepath, 'w') as f:
                for i in range(len(dfs0_text)):
                    f.write(dfs0_text[i] + "\n")
            # import mikeio
            # dfs0_template = mikeio.dfs.Dfs0(get_start_time)
            # for target_manhole in hydrographs.keys():
            # filepath = os.path.join(writeDFS0, target_manhole + ".txt")
            # with open(filepath,'w') as f:
            # f.write("Discharge[meter^3/sec]:Instantaneous\n")
            # f.write("Time\t%s\n" % target_manhole)
            # for discharge_i, discharge in enumerate((hydrographs[target_manhole])):
            # f.write("%s\t%1.6f\n" % (series.index[0] + datetime.timedelta(minutes=discharge_i), discharge))
            # dfs0 = mikeio.dfs0.Dfs0()
            # dfs0.write(filepath, data = [np.concatenate((hydrograph_summed,np.zeros((60))))], start_time = dfs0_template.start_time,
            # items = [mikeio.eum.ItemInfo("Discharge", mikeio.eum.EUMType.Discharge, unit = mikeio.eum.EUMUnit.meter_pow_3_per_sec)],
            # title=target_manhole, dt = 60)

        arcpy.SetProgressorLabel("Calculating Pipe Dimensions")
        arcpy.AddMessage(peak_discharge)
        arcpy.AddMessage(peak_discharge_time)

        def addField(shapefile, field_name, datatype):
            i = 1
            while field_name in [f.name for f in arcpy.Describe(shapefile).fields]:
                field_name = "%s_%d" % (field_name, i)
            arcpy.AddField_management(shapefile, field_name, datatype)
            return field_name

        # arcpy.SetProgressorLabel("Creating debug output")
        # debug_output = True
        # if debug_output:
        # if len(target_manholes)==1:
        # with open(r"C:\Papirkurv\Hydrograph.csv", 'w') as f:
        # for discharge in runoffs:
        # f.write("%s\n" % ("\t".join([str(d) for d in discharge])))
        # debug_output_fc = str(arcpy.CopyFeatures_management(pipe_layer, getAvailableFilename(arcpy.env.scratchGDB + "\debug_output")))
        # RedOpl_field = addField(debug_output_fc, "RedOpl", "FLOAT")
        # QMax_field = addField(debug_output_fc, "QMax", "FLOAT")
        # QMaxT_field = addField(debug_output_fc, "QMaxT", "FLOAT")
        # with arcpy.da.UpdateCursor(debug_output_fc, ["MUID", RedOpl_field, QMax_field, QMaxT_field], where_clause = "MUID IN ('%s')" % ("','".join(selected_pipes))) as cursor:
        # for row in cursor:
        # row[1] = total_red_opl[msm_Link_Network.links[row[0]].fromnode]
        # row[2] = peak_discharge[msm_Link_Network.links[row[0]].fromnode]
        # row[3] = peak_discharge_time[msm_Link_Network.links[row[0]].fromnode]
        # cursor.updateRow(row)
        arcpy.AddMessage(debug_output)
        if debug_output:
            try:
                result_layer = getAvailableFilename(arcpy.env.scratchGDB + "\Pipe_Dimensions", parent=MU_database)
                arcpy.CreateFeatureclass_management(arcpy.env.scratchGDB, os.path.basename(result_layer), "POLYLINE")
                fields = ["muid", "diameter", "materialid", "slope", "nettypeno", "enabled", "ImpArea", "RedArea",
                          "MaxFlow", "CritTime"]

                addField(result_layer, "muid", "TEXT")
                addField(result_layer, "diameter", "FLOAT")
                addField(result_layer, "materialid", "TEXT")
                addField(result_layer, "slope", "FLOAT")
                addField(result_layer, "nettypeno", "SHORT")
                addField(result_layer, "enabled", "SHORT")
                addField(result_layer, "ImpArea", "FLOAT")
                addField(result_layer, "RedArea", "FLOAT")
                addField(result_layer, "MaxFlow", "FLOAT")
                addField(result_layer, "CritTime", "SHORT")
                with arcpy.da.InsertCursor(result_layer, ["SHAPE@"] + fields) as ins_cursor:
                    with arcpy.da.SearchCursor(msm_Link,
                                               ["Slope" if is_sqlite else "Slope_C", "Diameter", "MaterialID", "MUID",
                                                "SHAPE@", "NetTypeNo",
                                                "enabled"],
                                               where_clause="MUID IN ('%s')" % ("','".join(selected_pipes))) as cursor:
                        for row_i, row in enumerate(cursor):
                            # diameter_old = row[4]
                            arcpy.SetProgressorPosition(row_i)
                            if change_material:
                                D = [diameter for diameter in diameters_plastic if diameter < 450] + [
                                    diameter for diameter in diameters_concrete if diameter > 450]
                            else:
                                D = diameters_plastic if not "concrete" in row[1].lower() and not "beton" in row[
                                    1].lower() else diameters_concrete
                            slope = slopeOverwrite if slopeOverwrite else row[0] * 1e-2
                            # if writeDischargeInstead:
                            #     diameter = # ins_row = (row[4], row[3], peak_discharge[msm_Link_Network.links[row[3]].fromnode], row[2], row[0], row[5], row[6])
                            #     ins_cursor.insertRow(ins_row)
                            QFull = 0
                            Di = -1

                            if peak_discharge[graph.network.links[row[3]].fromnode] == 0:
                                Di = 0
                            else:
                                while QFull is not None and QFull * 1e3 < peak_discharge[
                                    graph.network.links[row[3]].fromnode] and Di + 1 < len(D):
                                    Di += 1
                                    QFull = ColebrookWhite.QFull(D[Di] / 1e3, slope, row[2])
                                    arcpy.AddMessage(QFull)
                            diameter = D[Di] / 1.0e3

                            material = row[2]
                            if keep_largest_diameter and diameter < row[1]:
                                diameter = row[1]
                            else:
                                if change_material:
                                    material = "Concrete (Normal)" if diameter > 0.45 else "Plastic"
                                arcpy.AddMessage("Changed %s from %d to %d" % (row[3], row[1] * 1e3, D[Di]))

                            upstream_nodes = graph.find_upstream_nodes(graph.network.links[row[3]].fromnode)
                            catchments = [graph.find_connected_catchments(node) for node in upstream_nodes][0]

                            ins_row = (row[4], row[3], diameter, material, row[0], row[5], row[6],
                                       np.sum([catchment.impervious_area for catchment in catchments]),
                                       np.sum([catchment.reduced_area for catchment in catchments]),
                                       peak_discharge[graph.network.links[row[3]].fromnode],
                                       peak_discharge_time[graph.network.links[row[3]].fromnode])
                            ins_cursor.insertRow(ins_row)
                            # if diameter_old != row[1]:
                            # arcpy.AddMessage("Changed diameter from %1.2f to %1.2f for pipe %s" % (diameter_old, row[1], row[3]))
            except Exception as e:
                if row[0] not in peak_discharge:
                    arcpy.AddError(traceback.format_exc())
                    arcpy.AddError("Failed to analyze catchments connected to node %s on pipe %s" % (
                    graph.network.links[row[3]].fromnode, graph.network.links[row[3]].MUID))
                    raise (e)
                arcpy.AddError(row)
                arcpy.AddError(traceback.format_exc())
                raise (e)
            addLayer(os.path.dirname(os.path.realpath(__file__)) + "\Data\MOUSE Links Dimensioned.lyr", result_layer,
                     workspace_type="FILEGDB_WORKSPACE")
        elif is_sqlite:
            with sqlite3.connect(
                    MU_database) as connection:
                update_cursor = connection.cursor()
                with arcpy.da.SearchCursor(msm_Link,
                                           ["Slope" if is_sqlite else "Slope_C", "Diameter", "MaterialID", "MUID",
                                            "SHAPE@",
                                            "NetTypeNo",
                                            "enabled"],
                                           where_clause="MUID IN ('%s')" % ("','".join(selected_pipes))) as cursor:
                    for row_i, row in enumerate(cursor):
                        arcpy.SetProgressorPosition(row_i)
                        if change_material:
                            D = [diameter for diameter in diameters_plastic if diameter < 450] + [
                                diameter for diameter in diameters_concrete if diameter > 450]
                        else:
                            D = diameters_plastic if not "concrete" in row[1].lower() and not "beton" in row[
                                1].lower() else diameters_concrete
                        slope = slopeOverwrite if slopeOverwrite else row[0] * 1e-2
                        # if writeDischargeInstead:
                        #     diameter = # ins_row = (row[4], row[3], peak_discharge[msm_Link_Network.links[row[3]].fromnode], row[2], row[0], row[5], row[6])
                        #     ins_cursor.insertRow(ins_row)
                        QFull = 0
                        Di = -1

                        if peak_discharge[graph.network.links[row[3]].fromnode] == 0:
                            Di = 0
                        else:
                            while QFull is not None and QFull * 1e3 < peak_discharge[
                                graph.network.links[row[3]].fromnode] and Di + 1 < len(D):
                                Di += 1
                                QFull = ColebrookWhite.QFull(D[Di] / 1e3, slope, row[2])
                        diameter = D[Di] / 1.0e3

                        material = row[2]
                        if keep_largest_diameter and diameter <= row[1]:
                            diameter = row[1]
                        else:
                            if change_material:
                                material = "Concrete (Normal)" if diameter > 0.45 else "Plastic"
                            arcpy.AddMessage("Changed %s from %d to %d" % (row[3], row[1] * 1e3, D[Di]))
                            # arcpy.AddMessage("UPDATE msm_Link SET Diameter = %1.3f, SET MaterialID = %s WHERE MUID = %s" % (diameter, material, row[3]))
                            update_cursor.execute(
                                "UPDATE msm_Link SET Diameter = %1.3f, MaterialID = '%s' WHERE MUID = '%s'" % (
                                diameter, material, row[3]))

        else:
            try:
                edit = arcpy.da.Editor(MU_database)
                edit.startEditing(False, True)
                edit.startOperation()

                fields = ["Slope_C", "MaterialID", "MUID", "Diameter"]
                if result_field and result_field not in fields:
                    result_field_index = len(fields) - 1
                    fields.append(result_field)

                arcpy.AddMessage(fields)
                with arcpy.da.UpdateCursor(msm_Link, fields,
                                           where_clause="MUID IN ('%s')" % ("','".join(selected_pipes))) as cursor:
                    for row_i, row in enumerate(cursor):
                        # diameter_old = row[4]
                        arcpy.SetProgressorPosition(row_i)
                        if change_material:
                            D = [diameter for diameter in diameters_plastic if diameter < 450] + [
                                diameter for diameter in diameters_concrete if diameter > 450]
                        else:
                            D = diameters_plastic if not "concrete" in row[1].lower() and not "beton" in row[
                                1].lower() else diameters_concrete
                        slope = slopeOverwrite if slopeOverwrite else row[0] * 1e-2
                        QFull = 0
                        Di = -1

                        if peak_discharge[graph.network.links[row[2]].fromnode] == 0:
                            Di = 0
                        else:
                            while QFull is not None and QFull * 1e3 < peak_discharge[
                                graph.network.links[row[2]].fromnode] and Di + 1 < len(D):
                                Di += 1
                                QFull = ColebrookWhite.QFull(D[Di] / 1e3, slope, row[1])

                        diameter = D[Di]
                        if keep_largest_diameter and diameter / 1.0e3 <= row[3]:
                            diameter = row[3]
                        else:
                            arcpy.AddMessage(
                                "Changed %s from %d to %d" % (row[2], row[3] * 1e3 if row[3] else 0, D[Di]))
                            row[-1] = D[Di] / 1.0e3
                            if change_material:
                                row[1] = "Concrete (Normal)" if row[-1] > 0.45 else "Plastic"
                            # if diameter_old != row[1]:
                            # arcpy.AddMessage("Changed diameter from %1.2f to %1.2f for pipe %s" % (diameter_old, row[1], row[3]))
                        try:
                            cursor.updateRow(row)
                        except Exception as e:
                            arcpy.AddWarning("Could not update row:")
                            arcpy.AddWarning(row)
                edit.stopOperation()
                edit.stopEditing(True)
            except Exception as e:
                arcpy.AddError(row)
                arcpy.AddError(traceback.format_exc())
                raise (e)
        # edit.stopOperation()
        # edit.stopEditing(True)
        return

class upgradeDimensions(object):
    def __init__(self):
        self.label       = "Upgrade dimensions"
        self.description = "Upgrade dimensions"
        self.canRunInBackground = False

    def getParameterInfo(self):
        #Define parameter definitions

        pipe_layer = arcpy.Parameter(
            displayName="Pipe feature layer",
            name="pipe_layer",
            datatype="GPFeatureLayer",
            parameterType="Required",
            direction="Input")
            
        change_material = arcpy.Parameter(
            displayName="Change material (Plastic if less than 500 mm, concrete if greater than or equal to 500 mm",
            name="change_material",
            datatype="Boolean",
            parameterType="optional",
            direction="Input")
        change_material.value = "true"
        
        parameters = [pipe_layer, change_material]
        return parameters

    def isLicensed(self):
        return True

    def updateParameters(self, parameters):


        return

    def updateMessages(self, parameters): #optional
        return

    def execute(self, parameters, messages):
        pipe_layer = parameters[0].Value
        change_material = parameters[1].Value
        MU_database = os.path.dirname(arcpy.Describe(pipe_layer).catalogPath).replace("\mu_Geometry", "")
        is_sqlite = True if ".sqlite" in MU_database else False

        MUIDs = [row[0] for row in arcpy.da.SearchCursor(pipe_layer,["MUID"])]
        if len(MUIDs) == len([row[0] for row in arcpy.da.SearchCursor(arcpy.Describe(pipe_layer).CatalogPath,["MUID"])]):
            userquery = pythonaddins.MessageBox("Change dimension of %d pipes?" % (len(MUIDs)), "Confirm Assignment", 4)
            if not userquery == "Yes":
                return

        if is_sqlite:
            with sqlite3.connect(
                    MU_database) as connection:
                update_cursor = connection.cursor()
                D_plastic = np.array(diameters_plastic)
                D_concrete = np.array(diameters_concrete)
                with arcpy.da.SearchCursor(arcpy.Describe(pipe_layer).catalogPath, ["MUID", "Diameter", "MaterialID"],
                                           where_clause="MUID IN ('%s')" % ("', '".join(MUIDs))) as cursor:
                    for row in cursor:
                        if change_material:
                            D = [diameter for diameter in diameters_plastic if diameter < 450] + [
                                diameter for diameter in diameters_concrete if diameter > 450]
                        else:
                            D = diameters_plastic if not "concrete" in row[2].lower() and not "beton" in row[
                                2].lower() else diameters_concrete
                        D = np.array(D)
                        oldDiameter = row[1] * 1e3
                        diameter = D[np.where(row[1] * 1e3 < D)[0][0]] / 1e3
                        material = row[2]
                        if change_material:
                            material = "Concrete (Normal)" if row[1] > 0.45 else "Plastic"
                        update_cursor.execute("UPDATE msm_Link SET Diameter = %1.3f, MaterialID = '%s' WHERE MUID = '%s'" % (diameter, material, row[0]))
                        arcpy.AddMessage("Upgraded pipe %s from %d to %d" % (row[0], oldDiameter, diameter*1e3))
        else:
            edit = arcpy.da.Editor(os.path.dirname(os.path.dirname(arcpy.Describe(pipe_layer).catalogPath)))
            edit.startEditing(False, True)
            edit.startOperation()



            D_plastic = np.array(diameters_plastic)
            D_concrete = np.array(diameters_concrete)
            with arcpy.da.UpdateCursor(arcpy.Describe(pipe_layer).catalogPath,["MUID", "Diameter", "MaterialID"], where_clause = "MUID IN ('%s')" % ("', '".join(MUIDs))) as cursor:
                for row in cursor:
                    if change_material:
                        D = [diameter for diameter in diameters_plastic if diameter < 450] + [
                            diameter for diameter in diameters_concrete if diameter > 450]
                    else:
                        D = diameters_plastic if not "concrete" in row[2].lower() and not "beton" in row[
                            2].lower() else diameters_concrete
                    D = np.array(D)
                    oldDiameter = row[1]*1e3
                    row[1] = D[np.where(row[1]*1e3<D)[0][0]]/1e3
                    if change_material:
                        row[2] = "Concrete (Normal)" if row[1]>0.45 else "Plastic"
                    cursor.updateRow(row)
                    arcpy.AddMessage("Upgraded pipe %s from %d to %d" % (row[0],oldDiameter,row[1]*1e3))

            edit.stopOperation()
            edit.stopEditing(True)
        return

class downgradeDimensions(object):
    def __init__(self):
        self.label       = "Downgrade dimensions"
        self.description = "Downgrade dimensions"
        self.canRunInBackground = False

    def getParameterInfo(self):
        #Define parameter definitions

        pipe_layer = arcpy.Parameter(
            displayName="Pipe feature layer",
            name="pipe_layer",
            datatype="GPFeatureLayer",
            parameterType="Required",
            direction="Input")
            
        change_material = arcpy.Parameter(
            displayName="Change material (Plastic if less than 500 mm, concrete if greater than or equal to 500 mm",
            name="change_material",
            datatype="Boolean",
            parameterType="optional",
            direction="Input")
        change_material.value = "true"
        # pipe_layer.filter.list = ["Polyline"] # does not work for some reason

        parameters = [pipe_layer, change_material]
        return parameters

    def isLicensed(self):
        return True

    def updateParameters(self, parameters): #optional
        # mxd = arcpy.mapping.MapDocument("CURRENT")  
        # df = arcpy.mapping.ListDataFrames(mxd)[0]  
        # workspaces = set()
        # for lyr in arcpy.mapping.ListLayers(mxd, df):
            # if lyr.supports("workspacepath"):
                # workspaces.add(lyr.workspacePath)

        return

    def updateMessages(self, parameters): #optional
        return

    def execute(self, parameters, messages):
        pipe_layer = parameters[0].Value
        change_material = parameters[1].Value
        MU_database = os.path.dirname(arcpy.Describe(pipe_layer).catalogPath).replace("\mu_Geometry", "")
        is_sqlite = True if ".sqlite" in MU_database else False

        MUIDs = [row[0] for row in arcpy.da.SearchCursor(pipe_layer,["MUID"])]
        if len(MUIDs) == len([row[0] for row in arcpy.da.SearchCursor(arcpy.Describe(pipe_layer).CatalogPath,["MUID"])]):
            userquery = pythonaddins.MessageBox("Change dimension of %d pipes?" % (len(MUIDs)), "Confirm Assignment", 4)
            if not userquery == "Yes":
                return

        if is_sqlite:
            with sqlite3.connect(
                    MU_database) as connection:
                update_cursor = connection.cursor()
                D_plastic = np.array(diameters_plastic)
                D_concrete = np.array(diameters_concrete)
                with arcpy.da.SearchCursor(arcpy.Describe(pipe_layer).catalogPath, ["MUID", "Diameter", "MaterialID"],
                                           where_clause="MUID IN ('%s')" % ("', '".join(MUIDs))) as cursor:
                    for row in cursor:
                        if change_material:
                            D = [diameter for diameter in diameters_plastic if diameter < 450] + [
                                diameter for diameter in diameters_concrete if diameter > 450]
                        else:
                            D = diameters_plastic if not "concrete" in row[2].lower() and not "beton" in row[
                                2].lower() else diameters_concrete
                        D = np.array(D)
                        oldDiameter = row[1] * 1e3
                        diameter = D[np.where(row[1]*1e3>D)[0][-1]]/1e3
                        material = row[2]
                        if change_material:
                            material = "Concrete (Normal)" if row[1] > 0.45 else "Plastic"
                        update_cursor.execute("UPDATE msm_Link SET Diameter = %1.3f, MaterialID = '%s' WHERE MUID = '%s'" % (diameter, material, row[0]))
                        arcpy.AddMessage("Upgraded pipe %s from %d to %d" % (row[0], oldDiameter, diameter*1e3))
        else:
            edit = arcpy.da.Editor(os.path.dirname(os.path.dirname(arcpy.Describe(pipe_layer).catalogPath)))
            edit.startEditing(False, True)
            edit.startOperation()
            D_plastic = np.array(diameters_plastic)
            D_concrete = np.array(diameters_concrete)
            with arcpy.da.UpdateCursor(arcpy.Describe(pipe_layer).catalogPath,["MUID", "Diameter", "MaterialID"], where_clause = "MUID IN ('%s')" % ("', '".join(MUIDs))) as cursor:
                for row in cursor:
                    if change_material:
                        D = [diameter for diameter in diameters_plastic if diameter < 450] + [
                            diameter for diameter in diameters_concrete if diameter > 450]
                    else:
                        D = diameters_plastic if not "concrete" in row[2].lower() and not "beton" in row[
                            2].lower() else diameters_concrete
                    D = np.array(D)
                    oldDiameter = row[1]*1e3
                    row[1] = D[np.where(row[1]*1e3>D)[0][-1]]/1e3
                    if change_material:
                        row[2] = "Concrete (Normal)" if row[1]>0.45 else "Plastic"
                    cursor.updateRow(row)
                    arcpy.AddMessage("Downgraded pipe %s from %d to %d" % (row[0],oldDiameter,row[1]*1e3))

            edit.stopOperation()
            edit.stopEditing(True)
        return

class CopyDiameter(object):
    def __init__(self):
        self.label       = "Copy field value from layer to layer"
        self.description = "Copy field value from layer to layer"
        self.canRunInBackground = False

    def getParameterInfo(self):
        #Define parameter definitions

        reference_feature_layer = arcpy.Parameter(
            displayName="Reference feature layer",
            name="reference_feature_layer",
            datatype="GPFeatureLayer",
            parameterType="Required",
            direction="Input")

        target_feature_layer = arcpy.Parameter(
            displayName="Target feature layer",
            name="target_feature_layer",
            datatype="GPFeatureLayer",
            parameterType="Required",
            direction="Input")

        copy_field = arcpy.Parameter(
            displayName="Field to copy",
            name="result_field",
            datatype="GPString",
            parameterType="Required",
            multiValue=True,
            direction="Input")
        copy_field.filter.type = "ValueList"

        match_by = arcpy.Parameter(
            displayName="Match Feature Classes by",
            name="match_by",
            datatype="GPString",
            parameterType="Required",
            multiValue=True,
            direction="Input")
        match_by.filter.type = "ValueList"
        match_by.filter.list = ["SHAPE@", "OBJECTID", "MUID"]
        match_by.value = "SHAPE@"

        parameters = [reference_feature_layer, target_feature_layer, copy_field, match_by]
        return parameters

    def isLicensed(self):
        return True

    def updateParameters(self, parameters): #optional
        reference_feature_layer = parameters[0].Value
        target_feature_layer = parameters[1].Value
        copy_field = parameters[2].ValueAsText
        match_by = parameters[3].ValueAsText
    
        def changeShapeFieldname(fields):
                for i in range(len(fields)):
                    if fields[i] == "SHAPE":
                        fields[i] = "SHAPE@"
                return fields
        if parameters[0].altered:
            reference_feature_layer = parameters[0].ValueAsText

            parameters[2].filter.list = changeShapeFieldname([f.name for f in arcpy.Describe(reference_feature_layer).fields])

        if "Diameter" in parameters[2].filter.list and not parameters[2].value:
            parameters[2].value = "Diameter"
            if "MaterialID" in parameters[2].filter.list:
                parameters[2].value = ["Diameter", "MaterialID"]
        
        if parameters[1].ValueAsText:
            MU_database = os.path.dirname(os.path.dirname(arcpy.Describe(target_feature_layer).catalogPath))
            
            is_sqlite = True if ".sqlite" in MU_database else False
            if is_sqlite:
                parameters[3].value = "MUID"

        return

    def updateMessages(self, parameters): #optional
        return

    def execute(self, parameters, messages):
        reference_feature_layer = parameters[0].Value
        target_feature_layer = parameters[1].Value
        copy_field = parameters[2].ValueAsText
        match_by = parameters[3].ValueAsText
        MU_database = os.path.dirname(arcpy.Describe(target_feature_layer).catalogPath).replace("mu_Geometry","")
        reference_MU_database = os.path.dirname(arcpy.Describe(target_feature_layer).catalogPath).replace("mu_Geometry","")
        
        # arcpy.AddMessage(MU_database)
        
        is_sqlite = True if ".sqlite" in MU_database else False
        if is_sqlite:
            if "shape" in copy_field.lower():
                arcpy.AddError("Copy field %s is not supported for sqlite" % (copy_field))
            if "shape" in match_by.lower():
                arcpy.AddError("Match field %s is not supported for sqlite" % (match_by))
        
        field_for_where_clause = "OBJECTID" if not is_sqlite else "MUID"
        check_other_layer = True
        try:
            if arcpy.Describe(reference_feature_layer).fidSet:
                count = int(arcpy.GetCount_management(reference_feature_layer).getOutput(0))
                userquery = pythonaddins.MessageBox("Change for %d features (selected in reference layer)?" % (count), "Confirm Assignment", 4)
                if not userquery == "Yes":
                    pass
                else:
                    if field_for_where_clause == "MUID":
                        reference_where_clause = "%s IN ('%s')" % (field_for_where_clause, "', '".join([str(row[0]) for row in arcpy.da.SearchCursor(reference_feature_layer, [field_for_where_clause])])) 
                    else:
                        reference_where_clause = "%s IN (%s)" % (field_for_where_clause, ", ".join([str(row[0]) for row in arcpy.da.SearchCursor(reference_feature_layer, [field_for_where_clause])])) 
                    target_where_clause = ""
                    check_other_layer = False
        except Exception as e:
            arcpy.AddError(e)
            pass
       
        # arcpy.AddMessage((check_other_layer and arcpy.Describe(target_feature_layer).fidSet))
        try:
            if check_other_layer and arcpy.Describe(target_feature_layer).fidSet:
                count = int(arcpy.GetCount_management(target_feature_layer).getOutput(0))
                userquery = pythonaddins.MessageBox("Change for %d features (selected in target layer)?" % (count), "Confirm Assignment", 4)
                if not userquery == "Yes": 
                    arcpy.AddMessage("Cancelled both user queries")
                    return
                else:
                    if field_for_where_clause == "MUID":
                        target_where_clause = "%s IN ('%s')" % (field_for_where_clause, "', '".join([str(row[0]) for row in arcpy.da.SearchCursor(target_feature_layer, [field_for_where_clause])]))
                    else:
                        target_where_clause = "%s IN (%s)" % (field_for_where_clause, ", ".join([str(row[0]) for row in arcpy.da.SearchCursor(target_feature_layer, [field_for_where_clause])])) 
                    reference_where_clause = ""
            else:
                if check_other_layer:
                    arcpy.AddMessage("Nothing selected")
                    return
        except Exception as e:
            arcpy.AddError(e)
            return  
            
        # arcpy.AddMessage(target_where_clause)
        # arcpy.AddMessage(reference_where_clause)
                
        class Reference():
            pass
            
        def changeShapeFieldname(fields):
            for i in range(len(fields)):
                if fields[i] == "SHAPE":
                    fields[i] = "SHAPE@"
            return fields

        references = []
        fields = changeShapeFieldname([field.name for field in arcpy.ListFields(reference_feature_layer)])
        if "ESRI_OID" in fields:
            fields.remove("ESRI_OID")
        # arcpy.AddMessage(fields)
        
        with arcpy.da.SearchCursor(arcpy.Describe(reference_feature_layer).catalogPath, fields, where_clause = reference_where_clause) as cursor:
            for row in cursor:
                reference = Reference()
                for field_i, field in enumerate(fields):
                    setattr(reference, field.lower(), row[field_i])
                
                references.append(reference)
        # arcpy.AddMessage([reference.muid for reference in references])
        # arcpy.AddMessage([reference.diameter for reference in references])
        
        fields = changeShapeFieldname([field.name for field in arcpy.ListFields(target_feature_layer)])
        if "ESRI_OID" in fields:
            fields.remove("ESRI_OID")
        
        match_by_field_i = [field_i for field_i, field in enumerate(fields) if field.lower() == match_by.lower()][0]
        # arcpy.AddMessage(fields)
        # arcpy.AddMessage(match_by_field_i)
        
        # target_where_clause = target_where_clause if target_where_clause else reference_where_clause
        arcpy.AddMessage(target_where_clause)
        
        if is_sqlite:
            with sqlite3.connect(
                        MU_database) as connection:
                update_cursor = connection.cursor()
                layer_name = os.path.basename(arcpy.Describe("target").catalogPath).replace("main.","")
                copy_field = copy_field if type(copy_field) is str else copy_field.split(";")
                # arcpy.AddMessage(copy_field)
                # arcpy.AddMessage(target_where_clause)
                # arcpy.AddMessage([row[0] for row in arcpy.da.SearchCursor(target_feature_layer, ["MUID"], target_where_clause)])
                
                for MUID in [row[0] for row in arcpy.da.SearchCursor(target_feature_layer, ["MUID"], target_where_clause)]:
                    match = [reference for reference in references if getattr(reference, "muid") == MUID][0]
                    for field in copy_field:
                        field_value = getattr(match, field.lower())
                        # arcpy.AddMessage(type(field_value) is str or type(field_value) is unicode)
                        
                        old_field_value = update_cursor.execute("SELECT %s FROM %s WHERE MUID = '%s'" % (field, layer_name, MUID)).fetchone()[0]
                        sql_expression = "UPDATE %s SET %s = %s WHERE MUID = '%s'" % (layer_name, field,
                                            "'%s'" % (field_value) if type(field_value) is str or type(field_value) is unicode else "%s" % (field_value),
                                            MUID)
                        # arcpy.AddMessage(sql_expression)
                        arcpy.AddMessage(
                                    "Changed %s field %s from %s to %s" % (MUID, field, old_field_value, field_value))
                        update_cursor.execute(sql_expression)
        else:
            edit = arcpy.da.Editor(MU_database)
            edit.startEditing(False, True)
            edit.startOperation()
            with arcpy.da.UpdateCursor(arcpy.Describe(target_feature_layer).catalogPath, fields, where_clause = target_where_clause) as cursor:
                for row in cursor:
                    
                    match = [reference for reference in references if getattr(reference, match_by.lower()) == row[match_by_field_i]]
                    arcpy.AddMessage(match)
                    arcpy.AddMessage(row[match_by_field_i])
                    
                    if match:
                        reference = match[0]
                        for field_i, field in enumerate(fields):
                            if field in copy_field:
                                arcpy.AddMessage(
                                    "Changed %s field %s from %s to %s" % (row[match_by_field_i], field, row[field_i], getattr(reference, field.lower())))
                                row[field_i] = getattr(reference, field.lower())
                            elif field == "SHAPE":
                                shape = deepcopy(row[field_i])
                                row[field_i] = shape
                        
                        cursor.updateRow(row)


            edit.stopOperation()
            edit.stopEditing(True)
        return

class InterpolateInvertLevels(object):
    def __init__(self):
        self.label       = "Interpolate Invert Levels"
        self.description = "Interpolate Invert Levels"
        self.canRunInBackground = False

    def getParameterInfo(self):
        #Define parameter definitions

        pipe_layer = arcpy.Parameter(
            displayName="Pipe feature layer",
            name="pipe_layer",
            datatype="GPFeatureLayer",
            parameterType="Required",
            direction="Input")
            
        usePipeElevations = arcpy.Parameter(
            displayName="Include UpLevel and DwLevel",
            name="usePipeElevations",
            datatype="Boolean",
            parameterType="optional",
            direction="Input")
            
        fixed_slope = arcpy.Parameter(
            displayName="Use Fixed Slope instead of Interpolation:",
            name="fixed_slope",
            datatype="double",
            parameterType="optional",
            direction="Input")
        fixed_slope.category = "Use Fixed Slope"
        
        use_slope_from_upstream = arcpy.Parameter(
            displayName="Use Upstream Node as Fix Point for setting Fixed Slope",
            name="use_slope_from_upstream",
            datatype="Boolean",
            parameterType="optional",
            direction="Input")
        use_slope_from_upstream.enabled = False
        use_slope_from_upstream.category = "Use Fixed Slope"
        use_slope_from_upstream.value = True
            
        use_slope_from_downstream = arcpy.Parameter(
            displayName="Use Downstream Node as Fix Point for setting Fixed Slope",
            name="use_slope_from_downstream",
            datatype="Boolean",
            parameterType="optional",
            direction="Input")
        use_slope_from_downstream.enabled = False
        use_slope_from_downstream.category = "Use Fixed Slope"

        parameters = [pipe_layer, usePipeElevations, fixed_slope, use_slope_from_upstream, use_slope_from_downstream]
        return parameters

    def isLicensed(self):
        return True

    def updateParameters(self, parameters):
        if parameters[2].value is not None:
            parameters[3].enabled = True
            parameters[4].enabled = True
        else:
            parameters[3].enabled = False
            parameters[4].enabled = False
        
        if not parameters[0].value:
            mxd = arcpy.mapping.MapDocument("CURRENT")
            links = [lyr.longName for lyr in arcpy.mapping.ListLayers(mxd) if lyr.getSelectionSet() and arcpy.Describe(lyr).shapeType == 'Polyline'
                    and "muid" in [field.name.lower() for field in arcpy.ListFields(lyr)]][0]
            if links:
                parameters[0].value = links
        return

    def updateMessages(self, parameters): #optional
        return

    def execute(self, parameters, messages):
        pipe_layer = parameters[0].Value
        usePipeElevations = parameters[1].Value
        fixed_slope = parameters[2].Value
        use_slope_from_upstream = parameters[3].Value
        use_slope_from_downstream = parameters[4].Value
        
        MU_database = (os.path.dirname(os.path.dirname(arcpy.Describe(pipe_layer).catalogPath)) if ".mdb" in arcpy.Describe(pipe_layer).catalogPath else
                        os.path.dirname(arcpy.Describe(pipe_layer).catalogPath))
        is_sqlite = True if ".sqlite" in MU_database else False        
        
        links_MUIDs = [row[0] for row in arcpy.da.SearchCursor(pipe_layer,["MUID"])]
        msm_Node = os.path.join(MU_database, "msm_Node")
        msm_Link = os.path.join(MU_database, "msm_Link")
        end_node_critical = None

        if len(links_MUIDs) == len(
                [row[0] for row in arcpy.da.SearchCursor(arcpy.Describe(pipe_layer).CatalogPath, ["MUID"])]):
            userquery = pythonaddins.MessageBox("Interpolate invert slope for %d pipes?" % (len(links_MUIDs)), "Confirm Assignment", 4)
            if not userquery == "Yes":
                return
        
        if not len(links_MUIDs) == len(set(links_MUIDs)):
            arcpy.AddError("Error: There's two or more pipes with identical names.")
            duplicates = []
            for MUID in links_MUIDs:
                if links_MUIDs.count(MUID)>1 and MUID not in duplicates:
                    arcpy.AddError("Pipe %s" % (MUID))
                    duplicates.append(MUID)
            raise(Exception("Cancelling toolbox"))
        
        msm_Link_Network = networker.NetworkLinks(MU_database, map_only="link")
        
        tonodes = [msm_Link_Network.links[MUID].tonode for MUID in links_MUIDs]
        fromnodes = [msm_Link_Network.links[MUID].fromnode for MUID in links_MUIDs]
        try:
            start_node = [fromnode for fromnode in fromnodes if fromnode not in tonodes][0]
            end_node = [tonode for tonode in tonodes if tonode not in fromnodes][0]
        except Exception as e:
            for MUID in links_MUIDs:
                arcpy.AddMessage("%s: %s-%s" % (MUID, msm_Link_Network.links[MUID].fromnode, msm_Link_Network.links[MUID].tonode))
            arcpy.AddWarning(("fromnodes:", fromnodes))
            arcpy.AddWarning(("tonodes:", tonodes))
            raise(e)

        invert_levels = {row[0]: row[1] for row in
                         arcpy.da.SearchCursor(msm_Node,
                                               ["MUID", "InvertLevel"],
                                               where_clause="MUID IN ('%s', '%s')" % (start_node, end_node))}
        
        if usePipeElevations:
            last_link = [MUID for MUID in links_MUIDs if msm_Link_Network.links[MUID].tonode == end_node][0]
            dwlevel = [row[0] for row in arcpy.da.SearchCursor(pipe_layer, ["dwlevel"], where_clause = "MUID = '%s'" % (last_link))][0]
            
            first_link = [MUID for MUID in links_MUIDs if msm_Link_Network.links[MUID].fromnode == start_node][0]
            uplevel = [row[0] for row in arcpy.da.SearchCursor(pipe_layer, ["dwlevel"], where_clause = "MUID = '%s'" % (first_link))][0]
            if uplevel:
                invert_levels[start_node] = uplevel
            if dwlevel:
                invert_levels[end_node] = dwlevel

        network = nx.DiGraph()
        for link in msm_Link_Network.links.values():
            network.add_edge(link.fromnode, link.tonode,
                             weight=link.length)

        path_nodes = nx.bellman_ford_path(network, start_node, end_node, weight="weight")
        lengths = np.zeros(len(path_nodes) - 1, dtype=np.float)
        for i in range(1, len(path_nodes)):
            lengths[i - 1] = network.edges[path_nodes[i - 1], path_nodes[i]]["weight"]

        try:
            if fixed_slope is not None:
                slope = fixed_slope
                invert_levels[end_node] = invert_levels[start_node] - fixed_slope * np.sum(lengths) if use_slope_from_upstream else invert_levels[end_node]
            else:
                slope = (invert_levels[start_node] - invert_levels[end_node]) / np.sum(lengths)
        except Exception as e:
            arcpy.AddError(("start_node", start_node))
            arcpy.AddError(("end_node", end_node))
            arcpy.AddError(("tonodes", tonodes))
            arcpy.AddError(("fromnodes", fromnodes))
            arcpy.AddError(("invert_levels[start_node]", invert_levels[start_node]))
            arcpy.AddError(("invert_levels[end_node]", invert_levels[end_node]))
            arcpy.AddError(("np.sum(lengths)", np.sum(lengths)))
            raise(e)
        arcpy.AddMessage("Assuming slope %d o/oo" % (slope*1e3))

        if is_sqlite:
            with sqlite3.connect(
                    MU_database) as connection:
                update_cursor = connection.cursor()
                
                with arcpy.da.SearchCursor(msm_Node, ["MUID", "InvertLevel", "GroundLevel"],
                                           where_clause="MUID IN ('%s')" % ("', '".join(path_nodes))) as cursor:
                    for row in cursor:
                        if (row[0] != end_node 
                            or (fixed_slope is not None and use_slope_from_downstream and row[0] != end_node)
                            or (fixed_slope is not None and use_slope_from_upstream and row[0] != start_node)):
                            total_length = nx.bellman_ford_path_length(network, row[0], end_node, weight="weight")
                            
                            new_invert_level = round(invert_levels[end_node] + total_length * slope,2)
                            if new_invert_level != row[1]:
                                update_cursor.execute("UPDATE msm_Node SET InvertLevel = %1.2f WHERE MUID = '%s'" % (new_invert_level, row[0]))
                                arcpy.AddMessage(
                                    "Changed invert level of %s from %1.2f to %1.2f" % (row[0], row[1] if row[1] else 0, new_invert_level))
        else:
            edit = arcpy.da.Editor(MU_database)
            edit.startEditing(False, True)
            edit.startOperation()

            with arcpy.da.UpdateCursor(msm_Node, ["MUID", "InvertLevel", "GroundLevel"],
                                       where_clause="MUID IN ('%s')" % ("', '".join(path_nodes))) as cursor:
                for row in cursor:
                    if row[0] != end_node or (fixed_slope is not None and use_slope_from_downstream and row[0] != end_node) or (fixed_slope is not None and use_slope_from_upstream and row[0] != start_node):
                        total_length = nx.bellman_ford_path_length(network, row[0], end_node, weight="weight")

                        new_invert_level = round(invert_levels[end_node] + total_length * slope,2)
                        if new_invert_level != row[1]:
                            arcpy.AddMessage(
                                "Changed invert level of %s from %1.2f to %1.2f" % (row[0], row[1] if row[1] else 0, new_invert_level))
                            row[1] = new_invert_level
                            cursor.updateRow(row)

            edit.stopOperation()
            edit.stopEditing(True)
        return

class GetMinimumSlope(object):
    def __init__(self):
        self.label = "Calculate Minimum Slope of Energy Gradient"
        self.description = "Calculate Minimum Slope of Energy Gradient"
        self.canRunInBackground = False

    def getParameterInfo(self):
        # Define parameter definitions

        pipe_layer = arcpy.Parameter(
            displayName="Pipe feature layer",
            name="pipe_layer",
            datatype="GPFeatureLayer",
            parameterType="Required",
            direction="Input")

        end_node_critical = arcpy.Parameter(
            displayName="Critical Level at End Node",
            name="end_node_critical",
            datatype="double",
            parameterType="Optional",
            direction="Input")

        parameters = [pipe_layer, end_node_critical]
        return parameters

    def isLicensed(self):
        return True

    def updateParameters(self, parameters):
        if not parameters[0].value:
            mxd = arcpy.mapping.MapDocument("CURRENT")
            links = [lyr.longName for lyr in arcpy.mapping.ListLayers(mxd) if lyr.getSelectionSet() and arcpy.Describe(lyr).shapeType == 'Polyline'
                    and "muid" in [field.name.lower() for field in arcpy.ListFields(lyr)]][0]
            if links:
                parameters[0].value = links
        return

    def updateMessages(self, parameters):  # optional
        return

    def execute(self, parameters, messages):
        pipe_layer = parameters[0].Value
        end_node_critical = parameters[1].Value
        MU_database = (os.path.dirname(os.path.dirname(arcpy.Describe(pipe_layer).catalogPath)) if ".mdb" in arcpy.Describe(pipe_layer).catalogPath else
                        os.path.dirname(arcpy.Describe(pipe_layer).catalogPath))
        msm_Node = os.path.join(MU_database, "msm_Node")
        msm_Link = os.path.join(MU_database, "msm_Link")

        mxd = arcpy.mapping.MapDocument("CURRENT")
        df = arcpy.mapping.ListDataFrames(mxd)[0]
        
        def addLayer(layer_source, source, group = None, workspace_type = "ACCESS_WORKSPACE"):
            layer = apmapping.Layer(layer_source)
            if group:
                apmapping.AddLayerToGroup(df, group, layer, "BOTTOM")
            else:
                apmapping.AddLayer(df, layer, "TOP")
            updatelayer = apmapping.ListLayers(mxd, layer.name, df)[0]
            updatelayer.replaceDataSource(unicode(os.path.dirname(source.replace(r"\mu_Geometry",""))), workspace_type, unicode(os.path.basename(source)))

        msm_Link_Network = networker.NetworkLinks(MU_database, map_only="link")

        links_MUIDs = [row[0] for row in arcpy.da.SearchCursor(pipe_layer,["MUID"])]
        tonodes = [msm_Link_Network.links[MUID].tonode for MUID in links_MUIDs]
        fromnodes = [msm_Link_Network.links[MUID].fromnode for MUID in links_MUIDs]
        start_nodes = [fromnode for fromnode in fromnodes if fromnode not in tonodes]
        end_node = [tonode for tonode in tonodes if tonode not in fromnodes][0]

        levels = {row[0]: [row[1], row[2]] for row in
                  arcpy.da.SearchCursor(msm_Node,
                                        ["MUID", "InvertLevel", "GroundLevel"],
                                        where_clause="MUID IN ('%s')" % ("', '".join(set(fromnodes + tonodes))))}

        with arcpy.da.SearchCursor(msm_Link, ["MUID", "Diameter"]) as cursor:
            for row in cursor:
                msm_Link_Network.links[row[0]].diameter = row[1]

        # end_node_critical = (end_node_critical if
        #                      end_node_critical else levels[end_node])

        network = nx.DiGraph()
        for link in msm_Link_Network.links.values():
            network.add_edge(link.fromnode, link.tonode,
                             weight=link.length)

        critical_energy_gradient = {}
        for start_node in start_nodes:
            path_nodes = nx.bellman_ford_path(network, start_node, end_node, weight="weight")

            minimum_ground_slope = {}
            last_critical_energy_gradient = None
            debug = []
            for fromnode_i, fromnode in enumerate(path_nodes[:-1]):
                total_gradient = ((levels[fromnode][1] -
                                   (end_node_critical if end_node_critical else levels[end_node][0] +
                                                                                [link.diameter for link in
                                                                                 msm_Link_Network.links.values() if
                                                                                 link.tonode == end_node and
                                                                                 link.fromnode in path_nodes][0])) /
                                  nx.bellman_ford_path_length(network, fromnode, end_node, weight="weight"))

                for tonode in path_nodes[fromnode_i + 1:]:
                    gradient = ((levels[fromnode][1] - levels[tonode][0] -
                                 [link.diameter for link in msm_Link_Network.links.values() if link.tonode == tonode and
                                  link.fromnode in path_nodes][0]) /
                                nx.bellman_ford_path_length(network, fromnode, tonode, weight="weight"))

                    gradient = gradient if gradient < total_gradient else total_gradient
                    gradient = gradient if not last_critical_energy_gradient or gradient < last_critical_energy_gradient else last_critical_energy_gradient
                    critical_energy_gradient[
                        fromnode] = gradient if not fromnode in critical_energy_gradient or gradient < \
                                                critical_energy_gradient[fromnode] else critical_energy_gradient[
                        fromnode]
                last_critical_energy_gradient = critical_energy_gradient[fromnode]
        
        if ".sqlite" in MU_database:
            msm_Link_result = getAvailableFilename(arcpy.env.scratchGDB + "\msm_Link")
            arcpy.Select_analysis(msm_Link, msm_Link_result, where_clause="MUID IN ('%s')" % ("', '".join(links_MUIDs)))
        else:
            msm_Link_result = msm_Link
            edit = arcpy.da.Editor(MU_database)
            edit.startEditing(False, True)
            edit.startOperation()
        with arcpy.da.UpdateCursor(msm_Link_result, ["MUID", "Slope_C" if not ".sqlite" in MU_database else "Slope"],
                                   where_clause="MUID IN ('%s')" % ("', '".join(links_MUIDs))) as cursor:
            for row in cursor:
                fromnode = msm_Link_Network.links[row[0]].fromnode
                if fromnode in critical_energy_gradient:
                    row[1] = critical_energy_gradient[fromnode] * 1e2
                    cursor.updateRow(row)
                else:
                    arcpy.AddWarning("%s not in critical_energy_gradient" % (fromnode))
        
        if ".sqlite" in MU_database:
            addLayer(os.path.dirname(os.path.realpath(__file__)) + "\Data\MOUSE Links Dimensioned.lyr", msm_Link_result, workspace_type = "FILEGDB_WORKSPACE")
        else:
            edit.stopOperation()
            edit.stopEditing(True)

        return

class setOutletLoss(object):
    def __init__(self):
        self.label       = "Change outlet loss of nodes"
        self.description = "Change outlet loss of nodes"
        self.canRunInBackground = True

    def getParameterInfo(self):
        #Define parameter definitions

        MU_database = arcpy.Parameter(
            displayName="Mike Urban database",
            name="database",
            datatype="DEWorkspace",
            parameterType="Required",
            direction="Input")


        parameters = [MU_database]
        return parameters

    def isLicensed(self):
        return True

    def updateParameters(self, parameters): #optional
        # mxd = arcpy.mapping.MapDocument("CURRENT")  
        # df = arcpy.mapping.ListDataFrames(mxd)[0]  
        # workspaces = set()
        # for lyr in arcpy.mapping.ListLayers(mxd, df):
            # if lyr.supports("workspacepath"):
                # workspaces.add(lyr.workspacePath)

        return

    def updateMessages(self, parameters): #optional
        return

    def execute(self, parameters, messages):

        MU_database = parameters[0].ValueAsText
        msm_Node = os.path.join(MU_database, "msm_Node")
        msm_Link = os.path.join(MU_database, "msm_Link")

        msm_Node_saddle = set()
        try:
            with arcpy.da.SearchCursor(msm_Link, ["FromNode","ToNode","Diameter"]) as cursor:
                for row in cursor:
                    for node in [row[0],row[1]]:
                        if row[2] > 0.950:
                            msm_Node_saddle.add(node)
        except Exception as e:
            arcpy.AddError("Error: Try running Project Check Tool.")
            raise(e)


        edit = arcpy.da.Editor(MU_database)
        edit.startEditing(False, True)
        edit.startOperation()
        with arcpy.da.UpdateCursor(msm_Node, ["MUID", "LossParID"]) as cursor:
            for row in cursor:
                if row[0] in msm_Node_saddle and not row[1] == "No Cross Section Changes":
                    old_loss_par_id = row[1]
                    row[1] = "No Cross Section Changes"
                    cursor.updateRow(row)
                    arcpy.AddMessage("Changed Loss Par ID of node %s from %s to %s because connected pipe has diameter above 1000 mm" % (row[0], old_loss_par_id, row[1]))
                elif row[0] not in msm_Node_saddle and not row[1] == "Weighted Inlet Energy":
                    old_loss_par_id = row[1]
                    row[1] = "Weighted Inlet Energy"
                    cursor.updateRow(row)
                    arcpy.AddMessage("Changed Loss Par ID of node %s from %s to %s" % (row[0], old_loss_par_id, row[1]))

        edit.stopOperation()
        edit.stopEditing(True)
        # MUIDs = [row[0] for row in arcpy.da.SearchCursor(pipe_layer,["MUID"])]

        # edit = arcpy.da.Editor(os.path.dirname(os.path.dirname(arcpy.Describe(pipe_layer).catalogPath)))
        # edit.startEditing(False, True)
        # edit.startOperation()
        # D = np.array([102.4, 149, 188, 235, 278, 396, 470.8, 497, 588, 781, 885, 985, 1085, 1185, 1285, 1385, 1485, 1585, 2000, 2200, 2400, 2600])
        # with arcpy.da.UpdateCursor(arcpy.Describe(pipe_layer).catalogPath,["MUID", "Diameter"], where_clause = "MUID IN ('%s')" % ("', '".join(MUIDs))) as cursor:
            # for row in cursor:
                # oldDiameter = row[1]*1e3
                # row[1] = D[np.where(row[1]*1e3>D)[0][-1]]/1e3
                # cursor.updateRow(row)
                # arcpy.AddMessage("Downgraded pipe %s from %d to %d" % (row[0],oldDiameter,row[1]*1e3))

        # edit.stopOperation()
        # edit.stopEditing(True)
        return

# class internalDimensions(object):
    # def __init__(self):
        # self.label       = "Change diameter to internal dimensions for plastic pipes"
        # self.description = "Change diameter to internal dimensions for plastic pipes"
        # self.canRunInBackground = False

    # def getParameterInfo(self):
        # #Define parameter definitions

        # MU_database = arcpy.Parameter(
            # displayName="Mike Urban database",
            # name="database",
            # datatype="DEWorkspace",
            # parameterType="Required",
            # direction="Input")


        # parameters = [MU_database]
        # return parameters

    # def isLicensed(self):
        # return True

    # def updateParameters(self, parameters): #optional
        # # mxd = arcpy.mapping.MapDocument("CURRENT")
        # # df = arcpy.mapping.ListDataFrames(mxd)[0]
        # # workspaces = set()
        # # for lyr in arcpy.mapping.ListLayers(mxd, df):
            # # if lyr.supports("workspacepath"):
                # # workspaces.add(lyr.workspacePath)

        # return

    # def updateMessages(self, parameters): #optional
        # return

    # def execute(self, parameters, messages):

        # MU_database = parameters[0].ValueAsText
        # msm_Link = os.path.join(MU_database, "msm_Link")

        # externalDiameters = {0.200: 0.180, 0.250: 0.233, 0.300: 0.276, 0.400: 0.392, 0.500: 0.493, 0.600: 0.588, 0.800: 0.781, 1.000: 0.985, 1.100, 1.200, 1.300, 1.400, 1.500, 1.600}
        # [180, 233, 276, 392, 493, 588, 781, 985, 1185, 1285, 1385, 1485, 1585, 2000, 2200, 2400, 2600]

        # with arcpy.da.UpdateCursor(msm_Link,["MUID","Diameter","MaterialID"]), where_clause = "MaterialID = 'Plastic' AND Diameter IN (0.160, 0.200, 0.250, 0.300, 0.400, 0.500, 0.600, 0.800, 0.900, 1.000, 1.100, 1.200, 1.300, 1.400, 1.500, 1.600)") as cursor:
            # for row in cursor:

        # return

class reverseChange(object):
    def __init__(self):
        self.label       = "Revert changed dimensions"
        self.description = "Revert changed dimensions"
        self.canRunInBackground = True

    def getParameterInfo(self):
        #Define parameter definitions

        pipe_layer = arcpy.Parameter(
            displayName="Pipe feature layer",
            name="pipe_layer",
            datatype="GPFeatureLayer",
            parameterType="Required",
            direction="Input")

        reverse_text = arcpy.Parameter(
            displayName="Output log of upgrade/downgrade dimensions result",
            name="reverse_text",
            datatype="String",
            parameterType="Required",
            direction="Input")

        parameters = [pipe_layer, reverse_text]
        return parameters

    def isLicensed(self):
        return True

    def updateParameters(self, parameters): #optional
        # mxd = arcpy.mapping.MapDocument("CURRENT")  
        # df = arcpy.mapping.ListDataFrames(mxd)[0]  
        # workspaces = set()
        # for lyr in arcpy.mapping.ListLayers(mxd, df):
            # if lyr.supports("workspacepath"):
                # workspaces.add(lyr.workspacePath)

        return

    def updateMessages(self, parameters): #optional
        return

    def execute(self, parameters, messages):

        pipe_layer = parameters[0].Value
        reverse_text = parameters[1].Value

        find_pipe_dimension = re.compile("pipe ([^ ]+) from ([\d\.]+)")
        results = find_pipe_dimension.findall(reverse_text)

        pipe_dimension_dictionairy = {}
        for result in results:
            pipe_dimension_dictionairy[result[0]] = float(result[1])/1e3


        edit = arcpy.da.Editor(os.path.dirname(os.path.dirname(arcpy.Describe(pipe_layer).catalogPath)))
        edit.startEditing(False, True)
        edit.startOperation()
        with arcpy.da.UpdateCursor(pipe_layer, ["MUID","Diameter"], where_clause = "MUID IN ('%s')" % "', '".join(pipe_dimension_dictionairy.keys())) as cursor:
            for row in cursor:
                arcpy.AddMessage("Changing pipe %s from %d to %d" % (row[1], pipe_dimension_dictionairy[row[0]]))
                row[1] = pipe_dimension_dictionairy[row[0]]
                cursor.updateRow(row)
        edit.stopOperation()
        edit.stopEditing(True)
        return
        

class CalculateSlopeOfPipe(object):
    def __init__(self):
        self.label       = "Calculate Slope of Pipe"
        self.description = "Calculate Slope of Pipe"
        self.canRunInBackground = False

    def getParameterInfo(self):
        #Define parameter definitions

        pipe_layer = arcpy.Parameter(
            displayName="Pipe feature layer",
            name="pipe_layer",
            datatype="GPFeatureLayer",
            parameterType="Required",
            direction="Input")

        parameters = [pipe_layer]
        return parameters

    def isLicensed(self):
        return True

    def updateParameters(self, parameters): #optional
        if not parameters[0].value:
            mxd = arcpy.mapping.MapDocument("CURRENT")
            links = [lyr.longName for lyr in arcpy.mapping.ListLayers(mxd) if lyr.getSelectionSet() and arcpy.Describe(lyr).shapeType == 'Polyline'
                    and "muid" in [field.name.lower() for field in arcpy.ListFields(lyr)]][0]
            if links:
                parameters[0].value = links
        return

    def updateMessages(self, parameters): #optional
        return

    def execute(self, parameters, messages):
        pipe_layer = parameters[0].Value
        
        links_OID = [row[0] for row in arcpy.da.SearchCursor(pipe_layer, ["OID@"])]
        OID_fieldname = arcpy.Describe(pipe_layer).OIDFieldName
        
        MU_database = os.path.dirname(arcpy.Describe(pipe_layer).catalogPath).replace("\mu_Geometry","")
        
        msm_Node = os.path.join(MU_database, "msm_Node")
        
        nodes_invert_level = {row[0]: row[1] for row in arcpy.da.SearchCursor(msm_Node, ["MUID", "InvertLevel"])}
               
        network = networker.NetworkLinks(MU_database, map_only = "link")
        
        edit = arcpy.da.Editor(MU_database)
        edit.startEditing(False, True)
        edit.startOperation()

        arcpy.SetProgressor("step", "Calculating slope of pipes", 0, len(links_OID), 1)
        with arcpy.da.UpdateCursor(arcpy.Describe(pipe_layer).catalogPath, ["MUID", "Slope_C", "UpLevel", "DwLevel"], where_clause = "%s IN (%s)" % (OID_fieldname, ', '.join([str(OID) for OID in links_OID]))) as cursor:
            for row_i, row in enumerate(cursor):
                try:
                    arcpy.SetProgressorPosition(row_i)
                    uplevel = nodes_invert_level[network.links[row[0]].fromnode] if not row[2] else row[2]
                    dwlevel = nodes_invert_level[network.links[row[0]].tonode] if not row[3] else row[3]
                    length = network.links[row[0]].length
                    slope = (uplevel-dwlevel)/length*1e2
                    row[1] = slope
                    #arcpy.AddMessage((uplevel, dwlevel, length, slope))
                    cursor.updateRow(row)
                except Exception as e:
                    arcpy.AddError(traceback.format_exc())
                    arcpy.AddError(row)
        edit.stopOperation()
        edit.stopEditing(True)
        return


class ResetUpLevelDwlevel(object):
    def __init__(self):
        self.label = "Set Uplevel and Dwlevel to NULL if equal to invert level"
        self.description = "Set Uplevel and Dwlevel to NULL if equal to invert level"
        self.canRunInBackground = False

    def getParameterInfo(self):
        # Define parameter definitions

        pipe_layer = arcpy.Parameter(
            displayName="Pipe feature layer",
            name="pipe_layer",
            datatype="GPFeatureLayer",
            parameterType="Required",
            direction="Input")

        parameters = [pipe_layer]
        return parameters

    def isLicensed(self):
        return True

    def updateParameters(self, parameters):  # optional
        if not parameters[0].value:
            mxd = arcpy.mapping.MapDocument("CURRENT")
            links = [lyr.longName for lyr in arcpy.mapping.ListLayers(mxd) if
                     lyr.getSelectionSet() and arcpy.Describe(lyr).shapeType == 'Polyline'
                     and "muid" in [field.name.lower() for field in arcpy.ListFields(lyr)]][0]
            if links:
                parameters[0].value = links
        return

    def updateMessages(self, parameters):  # optional
        return

    def execute(self, parameters, messages):
        pipe_layer = parameters[0].Value

        links_OID = [row[0] for row in arcpy.da.SearchCursor(pipe_layer, ["OID@"])]
        if len(links_OID) == 0:
            links_OID = [row[0] for row in arcpy.da.SearchCursor(arcpy.Describe(pipe_layer).catalogPath, ["OID@"])]
        OID_fieldname = arcpy.Describe(pipe_layer).OIDFieldName

        MU_database = os.path.dirname(arcpy.Describe(pipe_layer).catalogPath).replace("\mu_Geometry", "")

        msm_Node = os.path.join(MU_database, "msm_Node")

        nodes_invert_level = {row[0]: row[1] for row in arcpy.da.SearchCursor(msm_Node, ["MUID", "InvertLevel"])}

        network = networker.NetworkLinks(MU_database, map_only="link")

        edit = arcpy.da.Editor(MU_database)
        edit.startEditing(False, True)
        edit.startOperation()


        where_clause = "%s IN (%s) AND (UpLevel IS NOT NULL OR DwLevel IS NOT NULL)" % (
                                   OID_fieldname, ', '.join([str(OID) for OID in links_OID]))

        links_count = np.sum([1 for row in arcpy.da.SearchCursor(arcpy.Describe(pipe_layer).catalogPath, ["MUID"],
                                                               where_clause = where_clause)])
        arcpy.SetProgressor("step", "Setting UpLevel and DwLevel", 0, links_count, 1)
        with arcpy.da.UpdateCursor(arcpy.Describe(pipe_layer).catalogPath, ["MUID", "UpLevel", "DwLevel"],
                                   where_clause=where_clause) as cursor:
            for row_i, row in enumerate(cursor):
                arcpy.SetProgressorPosition(row_i)
                try:
                    uplevel = row[1]
                    dwlevel = row[2]
                    if row[1] == nodes_invert_level[network.links[row[0]].fromnode]:
                        row[1] = None
                        arcpy.AddMessage("Set UpLevel for %s to Null" % (row[0]))
                    if row[2] == nodes_invert_level[network.links[row[0]].tonode]:
                        row[2] = None
                        arcpy.AddMessage("Set DwLevel for %s to Null" % (row[0]))
                    cursor.updateRow(row)
                except Exception as e:
                    arcpy.AddError(traceback.format_exc())
                    arcpy.AddError(row)
                    raise(e)
        edit.stopOperation()
        edit.stopEditing(True)
        return