# Created by Emil Nielsen
# Contact: 
# E-mail: enielsen93@hotmail.com

import arcpy
if "mapping" in dir(arcpy):
    import arcpy.mapping as apmapping
    from arcpy.mapping  import MapDocument as MapDocument
    from arcpy.mapping  import MapDocument as MapDocument
else: 
    import arcpy.mp as apmapping
    from arcpy.mp import ArcGISProject as MapDocument
    from arcpy.mapping  import MapDocument as MapDocument
import numpy as np
import csv
import os
import traceback
import re

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

from arcpy import env
class Toolbox(object):
    def __init__(self):
        self.label =  "Display Mike Urban Model"
        self.alias  = "Display Mike Urban Model"

        # List of tool classes associated with this toolbox
        self.tools = [DisplayMikeUrban, DimensionAnalysis, DisplayPipeElevation, GenerateCatchmentConnections] 

class DisplayMikeUrban(object):
    def __init__(self):
        self.label       = "Display Mike Urban Model"
        self.description = "Display Mike Urban Model"
        self.canRunInBackground = False

    def getParameterInfo(self):
        #Define parameter definitions

        # Input Features parameter
        MU_database = arcpy.Parameter(
            displayName="Mike Urban database",
            name="database",
            datatype="DEFile",
            parameterType="Required",
            direction="Input")
        MU_database.filter.list = ["mdb", "sqlite"]
        
        join_catchments = arcpy.Parameter(
            displayName="Join catchments with imperviousness from msm_HModA table",
            name="join_catchments",
            datatype="Boolean",
            parameterType="optional",
            direction="Output")
        join_catchments.value = False
        
        show_loss_par = arcpy.Parameter(
            displayName="Show Loss Parameters on Manhole Text",
            name="show_loss_par",
            datatype="Boolean",
            category="Additional Settings",
            parameterType="optional",
            direction="Output")
        show_loss_par.value = False
        
        show_outlet_boundary_conditions = arcpy.Parameter(
            displayName="Show Outlet Boundary Conditions",
            name="show_outlet_boundary_conditions",
            datatype="Boolean",
            category="Additional Settings",
            parameterType="optional",
            direction="Output")
        show_outlet_boundary_conditions.value = True
                
        parameters = [MU_database, join_catchments, show_loss_par, show_outlet_boundary_conditions]
        
        return parameters

    def isLicensed(self): #optional
        return True

    def updateParameters(self, parameters): #optional
        return

    def updateMessages(self, parameters): #optional
       
        return

    def execute(self, parameters, messages):        
        MU_database = parameters[0].ValueAsText
        join_catchments = parameters[1].Value
        show_loss_par = parameters[2].Value
        show_outlet_boundary_conditions = parameters[3].Value
        manholes = MU_database + "\mu_Geometry\msm_Node"
        links = MU_database + "\mu_Geometry\msm_Link"
        catchments = MU_database + "\mu_Geometry\ms_Catchment" if not ".sqlite" in MU_database else MU_database + "\msm_Catchment"
        catchcons = MU_database + "\mu_Geometry\msm_CatchConLink" if not ".sqlite" in MU_database else MU_database + "\msm_CatchCon"
        weirs = MU_database + "\mu_Geometry\msm_Weir"
        networkLoad = MU_database + "\msm_BBoundary"
        msm_Pump = MU_database + "\msm_Pump"
        boundaryItem = MU_database + "\msm_BItem"
        msm_PasReg = MU_database + "\msm_PasReg"
        ms_TabD = MU_database + "\ms_TabD"
        mxd = MapDocument("CURRENT")
        df = apmapping.ListDataFrames(mxd)[0]

        is_sqlite_database = True if ".sqlite" in MU_database else False
        
        import time
        start_time = time.time()
        def printStepAndTime(txt):
            arcpy.AddMessage("%s - %d" % (txt, time.time() - start_time))
        
        printStepAndTime("Adding Empty Group")
        empty_group_mapped = apmapping.Layer(os.path.dirname(os.path.realpath(__file__)) + r"\Data\EmptyGroup.lyr")
        empty_group = apmapping.AddLayer(df, empty_group_mapped, "TOP")
        empty_group_layer = apmapping.ListLayers(mxd, "Empty Group", df)[0]
        empty_group_layer.name = os.path.splitext(os.path.basename(MU_database))[0]
        
        printStepAndTime("Adding nodes to map")
        arcpy.SetProgressor("default","Adding nodes to map")
        arcpy.env.addOutputsToMap = False
        # addLayer = apmapping.Layer(os.path.dirname(os.path.realpath(__file__)) + ("\Data\MOUSE Manholes with LossPar.lyr" if show_loss_par else "\Data\MOUSE Manholes.lyr"))        
        
        def addLayer(layer_source, source, group = None, workspace_type = "ACCESS_WORKSPACE"):
            if ".sqlite" in source:
                source_layer = apmapping.Layer(source)
                
                if group:
                    apmapping.AddLayerToGroup(df, group, source_layer, "BOTTOM")
                else:
                    apmapping.AddLayer(df, source_layer, "BOTTOM")
                update_layer = apmapping.ListLayers(mxd, source_layer.name, df)[0]
                
                layer_source_mike_plus = layer_source.replace("MOUSE", "MIKE+") if "MOUSE" in layer_source and os.path.exists(layer_source.replace("MOUSE", "MIKE+")) else None
                layer_source = layer_source_mike_plus if layer_source_mike_plus else layer_source
                layer = apmapping.Layer(layer_source)
                
                update_layer.visible = layer.visible
                update_layer.labelClasses = layer.labelClasses
                update_layer.showLabels = layer.showLabels
                update_layer.name = layer.name
                
                try:
                    arcpy.mapping.UpdateLayer(df, update_layer, layer, symbology_only = True)
                except Exception as e:
                    arcpy.AddWarning(source)
                    pass
            else:
                layer = apmapping.Layer(layer_source)
                if group:
                    apmapping.AddLayerToGroup(df, group, layer, "BOTTOM")
                else:
                    apmapping.AddLayer(df, layer, "BOTTOM")
                updatelayer = apmapping.ListLayers(mxd, layer.name, df)[0]
                updatelayer.replaceDataSource(unicode(os.path.dirname(source.replace(r"\mu_Geometry",""))), workspace_type, unicode(os.path.basename(source)))
        
        addLayer(os.path.dirname(os.path.realpath(__file__)) + ("\Data\MOUSE Manholes with LossPar.lyr" if show_loss_par else "\Data\MOUSE Manholes.lyr"        ),
                manholes, group = empty_group_layer)
        
        if not is_sqlite_database:
            printStepAndTime("Getting volume of basins")
            # Import basins
            if len([row[0] for row in arcpy.da.SearchCursor(manholes, ["MUID"], where_clause = "TypeNo = 2")])>0:
                arcpy.SetProgressor("default","Getting volume of basins")
                exportBasins = getAvailableFilename(arcpy.env.scratchGDB + r"\basins", parent = MU_database)
                arcpy.Select_analysis(manholes, exportBasins, where_clause = "TypeNo = 2")
                with arcpy.da.UpdateCursor(exportBasins, ["MUID","Freeboard_2D", "CriticalLevel","GeometryID"]) as cursor:
                    for row in cursor:
                        try:
                            with arcpy.da.SearchCursor(MU_database + r"\ms_TabD", ["Value1","Value3"], where_clause = "TabID = '%s'" % (row[3])) as msTabCursor:
                                basinH = []
                                basinA = []
                                for msTabRow in msTabCursor:
                                    basinH.append(msTabRow[0])
                                    basinA.append(msTabRow[1])
                                    
                            idxSort = np.argsort(basinH)
                            basinH = np.array(basinH)
                            basinA = np.array(basinA)
                            basinH = basinH[idxSort]
                            basinA = basinA[idxSort]
                            if not row[2]:
                                row[2] = np.max(basinH)
                            basinHCrit = [a for a in basinH if a<row[2]] + [row[2]]
                            basinACrit = np.interp([a for a in basinH if a<row[2]] + [row[2]],basinH,basinA)
                            row[1] = np.trapz(basinACrit,basinHCrit)
                            if row[0] == "Bassin_B021_Ny":
                                arcpy.AddMessage(basinACrit)
                                arcpy.AddMessage(basinHCrit)
                            cursor.updateRow(row)
                        except Exception as e:
                            arcpy.AddWarning("Error: Could not calculate volume of basin %s" % (row[0]))
                            arcpy.AddWarning(traceback.format_exc())
                
                printStepAndTime("Adding basins to map")
                arcpy.SetProgressor("default","Adding basins to map")
                addLayer(os.path.dirname(os.path.realpath(__file__)) + "\Data\MOUSE Basins.lyr",
                    exportBasins, group = empty_group_layer, workspace_type = "FILEGDB_WORKSPACE")
        
        printStepAndTime("Adding links, weirs and pumps to map")
        arcpy.SetProgressor("default","Adding links, weirs and pumps to map")
        
        addLayer(os.path.dirname(os.path.realpath(__file__)) + "\Data\MOUSE Links.lyr",
                links, group = empty_group_layer)
        
        if len([row[0] for row in arcpy.da.SearchCursor(weirs,["MUID"])])>0:
            addLayer(os.path.dirname(os.path.realpath(__file__)) + "\Data\MOUSE Weir.lyr",
                    weirs, group = empty_group_layer)
        
        if len([row[0] for row in arcpy.da.SearchCursor(msm_Pump,["MUID"])])>0:
            addLayer(os.path.dirname(os.path.realpath(__file__)) + "\Data\MOUSE Pumps.lyr",
                    msm_Pump, group = empty_group_layer)
        

        printStepAndTime("Adding network loads to map")
        # Create Network Load
        arcpy.SetProgressor("default","Adding network loads to map")
        networkShape = getAvailableFilename(arcpy.env.scratchGDB + r"\NetworkLoads", parent = MU_database)

        class NetworkLoad():
            Geometry = None
            @property
            def title(self):
                t = os.path.basename(self.TSConnection) + " " + self.TimeseriesName if self.TSConnection else None
                return t

        network_loads = []
        networkLoadInProject = False
        fields = ["MUID","ApplyBoundaryNo","ConnectionTypeNo","CatchLoadNo","IndividualConnectionNo" if not is_sqlite_database else "ConnectionTypeNo","NodeID","LinkID","CatchID"]
        with arcpy.da.SearchCursor(networkLoad, fields, where_clause = "ApplyBoundaryNo = 1 AND GroupNo = 2 AND ConnectionTypeNo = 3") as cursor:
            for row in cursor:
                networkLoadInProject = True
                network_load = NetworkLoad()

                for i,val in enumerate(row):
                    setattr(network_load, fields[i], val)
                network_loads.append(network_load)

        if not is_sqlite_database:
            fields = ["BoundaryID","VariationNo","ConstantValue", "TSConnection", "TimeseriesName"]
            with arcpy.da.SearchCursor(boundaryItem, fields,
                                        where_clause = "BoundaryID IN ('%s')" % "', '".join([network_load.MUID for network_load in network_loads])) as cursor:
                for row in cursor:
                    network_load = network_loads[[i for i,network_load in enumerate(network_loads) if network_load.MUID == row[0]][0]]
                    for i,val in enumerate(row):
                        setattr(network_load, fields[i], val)

                    if network_load.VariationNo != 1:
                        network_load.ConstantValue = None
                    elif network_load.VariationNo != 3:
                        network_load.TSConnection = None
                        network_load.TimeseriesName = None

                    if network_load.CatchLoadNo:
                        with arcpy.da.SearchCursor(catchments, ["MUID","SHAPE@XY"], where_clause = "MUID = '%s'" % (network_load.CatchID)) as xycursor:
                            for xyrow in xycursor:
                                network_load.Geometry = xyrow[1]
                    elif network_load.IndividualConnectionNo == 1:
                        with arcpy.da.SearchCursor(manholes, ["MUID","SHAPE@XY"], where_clause = "MUID = '%s'" % (network_load.NodeID)) as xycursor:
                            for xyrow in xycursor:
                                network_load.Geometry = xyrow[1]
                    elif network_load.IndividualConnectionNo == 2:
                        with arcpy.da.SearchCursor(links, ["MUID","SHAPE@XY"], where_clause = "MUID = '%s'" % (network_load.LinkID)) as xycursor:
                            for xyrow in xycursor:
                                network_load.Geometry = xyrow[1]
                    else:
                        arcpy.AddError("Unknown error")

        if networkLoadInProject:
            arcpy.CreateFeatureclass_management(os.path.dirname(networkShape), os.path.basename(networkShape), "POINT")
            arcpy.AddField_management(networkShape, "MUID", "TEXT")
            arcpy.AddField_management(networkShape, "Discharge", "DOUBLE")
            arcpy.AddField_management(networkShape, "Title", "STRING")
            with arcpy.da.InsertCursor(networkShape, ["MUID", "SHAPE@XY","Discharge", "Title"]) as cursor:
                for network_load in network_loads:
                    if network_load.Geometry:
                        cursor.insertRow([network_load.MUID, network_load.Geometry, network_load.ConstantValue, network_load.title])

            addLayer(os.path.dirname(os.path.realpath(__file__)) + "\Data\MOUSE Network Load.lyr",
                    networkShape, group = empty_group_layer, workspace_type = "FILEGDB_WORKSPACE")

        if not is_sqlite_database:
            printStepAndTime("Adding passive regulations to map")
            # Adding passive regulations to project
            arcpy.SetProgressor("default","Adding passive regulations to map")
            class Regulation:
                q_max = 0
                linkID = None
                tabID = None

            regulations = {}
            with arcpy.da.SearchCursor(msm_PasReg, ["LinkID", "FunctionID"], where_clause = "TypeNo = 1") as cursor:
                for row in cursor:
                    regulations[row[0]] = Regulation()
                    regulations[row[0]].tabID = row[1]
                    regulations[row[0]].linkID = row[0]

            if len(regulations)>0:
                regulationsShape = getAvailableFilename(arcpy.env.scratchGDB + r"\Regulations", parent = MU_database)

                with arcpy.da.SearchCursor(ms_TabD, ["TabID", "Sqn", "Value2"], where_clause = "TabID IN ('%s')" % ("', '".join([regulation.tabID for regulation in regulations.values()]))) as cursor:
                    for row in cursor:
                        linkIDs = [regulation.linkID for regulation in regulations.values() if regulation.tabID == row[0]]
                        for linkID in linkIDs:
                            regulations[linkID].q_max = row[2] if regulations[linkID].q_max < row[2] else regulations[linkID].q_max

                arcpy.CreateFeatureclass_management(os.path.dirname(regulationsShape), os.path.basename(regulationsShape), "POLYLINE")
                arcpy.AddField_management(regulationsShape, "LinkID", "TEXT")
                arcpy.AddField_management(regulationsShape, "FunctionID", "TEXT")
                arcpy.AddField_management(regulationsShape, "QMax", "FLOAT")
                with arcpy.da.InsertCursor(regulationsShape, ["SHAPE@", "LinkID", "FunctionID", "QMax"]) as regulation_cursor:
                    with arcpy.da.SearchCursor(links, ["SHAPE@", "MUID"], where_clause = "MUID IN ('%s')" % ("', '".join(regulations.keys()))) as link_cursor:
                        for row in link_cursor:
                            regulation_cursor.insertRow([row[0], row[1], regulations[row[1]].tabID, regulations[row[1]].q_max])

                addLayer(os.path.dirname(os.path.realpath(__file__)) + "\Data\Passive Regulations.lyr",
                        regulationsShape, group = empty_group_layer, workspace_type = "FILEGDB_WORKSPACE")

        printStepAndTime("Adding outlets to map")
        # Adding outlets to project
        if show_outlet_boundary_conditions:
            class Outlet:
                boundary_MUID = None
                boundary_item_MUID = None
                boundary_water_level = None
                geometry = None

                def __init__(self, nodeID):
                    self.nodeID = nodeID

            outlets = {}
            with arcpy.da.SearchCursor(networkLoad, ["MUID", "NodeID"], where_clause = "ApplyBoundaryNo = 1 AND TypeNo = 12") as cursor:
                for row in cursor:
                    outlets[row[1]] = Outlet(row[1])
                    outlets[row[1]].boundary_MUID = row[0]

            if not is_sqlite_database:
                with arcpy.da.SearchCursor(boundaryItem, ["MUID", "BoundaryID", "ConstantValue"],
                                            where_clause = "BoundaryType = 12 AND TypeNo = 1 AND VariationNo = 1 AND ConstantValue IS NOT NULL") as cursor:
                    for row in cursor:
                        nodeIDs = [outlet.nodeID for outlet in outlets.values() if outlet.boundary_MUID == row[1]]
                        if nodeIDs:
                            outlets[nodeIDs[0]].boundary_item_MUID = row[0]
                            outlets[nodeIDs[0]].boundary_water_level = row[2]
            else:
                with arcpy.da.SearchCursor(networkLoad, ["NodeID", "ConstantValue"],
                                           where_clause="ApplyBoundaryNo = 1 AND TypeNo = 12 AND ConnectionTypeNo = 3") as cursor:
                    for row in cursor:
                        outlets[row[0]].boundary_water_level = row[1]


            with arcpy.da.SearchCursor(manholes, ["SHAPE@", "MUID"], where_clause = "TypeNo = 3 AND MUID IN ('%s')" % ("', '".join(outlets.keys()))) as cursor:
                for row in cursor:
                    outlets[row[1]].geometry = row[0]


            if len([outlet for outlet in outlets.values() if outlet.boundary_water_level is not None])>0: # if any outlets with water level exist
                boundariesShape = getAvailableFilename(arcpy.env.scratchGDB + r"\BoundaryWaterLevel", parent = MU_database)
                try:
                    arcpy.CreateFeatureclass_management(os.path.dirname(boundariesShape), os.path.basename(boundariesShape), "POINT")
                    arcpy.AddField_management(boundariesShape, "NodeID", "TEXT")
                    arcpy.AddField_management(boundariesShape, "B_MUID", "TEXT")
                    arcpy.AddField_management(boundariesShape, "BI_MUID", "TEXT")
                    arcpy.AddField_management(boundariesShape, "Wat_Lev", "FLOAT")

                    with arcpy.da.InsertCursor(boundariesShape, ["SHAPE@", "NodeID", "B_MUID", "BI_MUID", "Wat_Lev"]) as cursor:
                        for outlet in outlets.values():
                            if outlet.boundary_water_level is not None:
                                cursor.insertRow([outlet.geometry, outlet.nodeID, outlet.boundary_MUID, outlet.boundary_item_MUID, outlet.boundary_water_level])
                    addLayer(os.path.dirname(os.path.realpath(__file__)) + "\Data\Boundary Water Level.lyr",
                        boundariesShape, group = empty_group_layer, workspace_type = "FILEGDB_WORKSPACE")
                except Exception as e:
                    arcpy.AddError(traceback.format_exc())
                
        printStepAndTime("Adding catchment connections to map")
        arcpy.SetProgressor("default","Adding catchment connections to map")
        addLayer(os.path.dirname(os.path.realpath(__file__)) + "\Data\Catchment Connections.lyr",
                    catchcons, group = empty_group_layer)
        
        printStepAndTime("Adding catchments to map")
        if join_catchments and not ".sqlite" in MU_database:
            arcpy.SetProgressor("default","Joining ms_Catchment and msm_HModA and adding catchments to map")
            ms_Catchment = arcpy.CopyFeatures_management(MU_database + r"\mu_Geometry\ms_Catchment", getAvailableFilename(arcpy.env.scratchGDB + "\ms_CatchmentImp", parent = MU_database)).getOutput(0)
            ms_CatchmentImpLayer = arcpy.MakeFeatureLayer_management(ms_Catchment, getAvailableFilename(arcpy.env.scratchGDB + "\ms_CatchmentImpLayer", parent = MU_database)).getOutput(0).name
            arcpy.JoinField_management(in_data=ms_CatchmentImpLayer, in_field="MUID", join_table=parameters[0].ValueAsText + r"\msm_HModA", join_field="CatchID", fields="ImpArea")
            arcpy.JoinField_management(in_data=ms_CatchmentImpLayer, in_field="MUID", join_table=parameters[0].ValueAsText + r"\msm_CatchCon", join_field="CatchID", fields="NodeID")
            arcpy.AddMessage(ms_CatchmentImpLayer)
            addLayer(os.path.dirname(os.path.realpath(__file__)) + "\Data\Catchments W Imp Area.lyr",
                    ms_CatchmentImpLayer, group = empty_group_layer, workspace_type = "FILEGDB_WORKSPACE")
            
        else:
            addLayer(os.path.dirname(os.path.realpath(__file__)) + "\Data\Catchments WO Imp Area.lyr",
                    catchments, group = empty_group_layer)
        
        printStepAndTime("Refreshing Map")
        arcpy.SetProgressor("default","Refreshing map")
        arcpy.RefreshTOC()
        arcpy.RefreshActiveView()
        return
        
class DimensionAnalysis(object):
    def __init__(self):
        self.label       = "Display Mike Urban Model with Q Full"
        self.description = "Display Mike Urban Model with Q Full"
        self.canRunInBackground = False

    def getParameterInfo(self):
        #Define parameter definitions

        # Input Features parameter
        MU_database = arcpy.Parameter(
            displayName="Mike Urban database",
            name="database",
            datatype="DEWorkspace",
            parameterType="Required",
            direction="Input")
        
        parameters = [MU_database]
        
        return parameters

    def isLicensed(self): #optional
        return True

    def updateParameters(self, parameters): #optional
        return

    def updateMessages(self, parameters): #optional
       
        return

    def execute(self, parameters, messages):        
        MU_database = parameters[0].ValueAsText
        manholes = MU_database + "\mu_Geometry\msm_Node"
        links = MU_database + "\mu_Geometry\msm_Link"
        catchcons = MU_database + "\mu_Geometry\msm_CatchConLink"
        mxd = MapDocument("CURRENT")
        df = apmapping.ListDataFrames(mxd)[0]
        arcpy.env.addOutputsToMap = False
        addLayer = apmapping.Layer(manholes)
        apmapping.AddLayer(df, addLayer)
        updatelayer = apmapping.ListLayers(mxd, "msm_Node", df)[0]
        sourcelayer = apmapping.Layer(os.path.dirname(os.path.realpath(__file__)) + "\Data\MOUSE Manholes.lyr")
        apmapping.UpdateLayer(df,updatelayer,sourcelayer,False)
        updatelayer.replaceDataSource(unicode(addLayer.workspacePath), 'ACCESS_WORKSPACE', unicode(addLayer.datasetName))
        
        addLayer = apmapping.Layer(links)   
        apmapping.AddLayer(df, addLayer)
        updatelayer = apmapping.ListLayers(mxd, "msm_Link", df)[0]
        sourcelayer = apmapping.Layer(os.path.dirname(os.path.realpath(__file__)) + "\Data\MOUSE Links W QFull.lyr")
        apmapping.UpdateLayer(df,updatelayer,sourcelayer,False)
        updatelayer.replaceDataSource(unicode(addLayer.workspacePath), 'ACCESS_WORKSPACE', unicode(addLayer.datasetName))
        #arcpy.ApplySymbologyFromLayer_management (addLayer, "Template.lyr")
        
      
        ms_CatchmentImp = arcpy.CopyFeatures_management (MU_database + r"\mu_Geometry\ms_Catchment", getAvailableFilename(arcpy.env.scratchGDB + "\ms_CatchmentImp")).getOutput(0)
        ms_CatchmentImpLayer = arcpy.MakeFeatureLayer_management(ms_CatchmentImp, getAvailableFilename(arcpy.env.scratchGDB + "\ms_CatchmentImpLayer")).getOutput(0).name
        arcpy.JoinField_management(in_data=ms_CatchmentImpLayer, in_field="MUID", join_table=parameters[0].ValueAsText + r"\msm_HModA", join_field="CatchID", fields="ImpArea")
        arcpy.JoinField_management(in_data=ms_CatchmentImpLayer, in_field="MUID", join_table=parameters[0].ValueAsText + r"\msm_CatchCon", join_field="CatchID", fields="NodeID")
        addLayer = apmapping.Layer(ms_CatchmentImpLayer)
        apmapping.AddLayer(df, addLayer)
        updatelayer = apmapping.ListLayers(mxd, ms_CatchmentImpLayer, df)[0]
        sourcelayer = apmapping.Layer(os.path.dirname(os.path.realpath(__file__)) + "\Data\Catchments W Imp Area.lyr")
        apmapping.UpdateLayer(df,updatelayer,sourcelayer,False)
        updatelayer.replaceDataSource(unicode(addLayer.workspacePath), 'FILEGDB_WORKSPACE', unicode(addLayer.datasetName))
        
        # addLayer = apmapping.Layer(MU_database + r"\mu_Geometry\ms_Catchment")   
        # apmapping.AddLayer(df, addLayer)
        # updatelayer = apmapping.ListLayers(mxd, "ms_Catchment", df)[0]
        # sourcelayer = apmapping.Layer(os.path.dirname(os.path.realpath(__file__)) + "\Data\Catchments W Imp Area.lyr")
        # apmapping.UpdateLayer(df,updatelayer,sourcelayer,False)
        # arcpy.AddJoin_management(apmapping.ListLayers(mxd, "Delopland", df)[0], "MUID", MU_database + r"\msm_HModA", "CatchID")
        # updatelayer.replaceDataSource(unicode(addLayer.workspacePath), 'ACCESS_WORKSPACE', unicode(addLayer.datasetName))
        # for lblClass in apmapping.ListLayers(mxd, "Delopland", df)[0].labelClasses:
            # lblClass.expression = '"%1.2f bef. ha (%1.0f%s)" % (float( [ms_Catchment.SHAPE_Area])/1e4*float([msm_HModA.ImpArea])/1e2,round(float([msm_HModA.ImpArea])/5,0)*5,"%")'

        
        addLayer = apmapping.Layer(catchcons)
        apmapping.AddLayer(df, addLayer)
        updatelayer = apmapping.ListLayers(mxd, "msm_CatchConLink", df)[0]
        sourcelayer = apmapping.Layer(os.path.dirname(os.path.realpath(__file__)) + "\Data\Catchment Connections.lyr")
        apmapping.UpdateLayer(df,updatelayer,sourcelayer,False)
        updatelayer.replaceDataSource(unicode(addLayer.workspacePath), 'ACCESS_WORKSPACE', unicode(addLayer.datasetName))
        
        arcpy.RefreshTOC()
        arcpy.RefreshActiveView()
        return
        
class DisplayPipeElevation(object):

    def __init__(self):
        self.label       = "Show Pipes with Erronous Elevation"
        self.description = "Show Pipes with Erronous Elevation"
        self.canRunInBackground = False

    def getParameterInfo(self):
        #Define parameter definitions

        # Input Features parameter
        MU_database = arcpy.Parameter(
            displayName="Mike Urban database",
            name="database",
            datatype="DEWorkspace",
            parameterType="Required",
            direction="Input")
        
        parameters = [MU_database]
        
        return parameters

    def isLicensed(self): #optional
        return True

    def updateParameters(self, parameters): #optional
        return

    def updateMessages(self, parameters): #optional
       
        return

    def execute(self, parameters, messages):        
        MU_database = parameters[0].ValueAsText
        links = MU_database + "\mu_Geometry\msm_Link"
        mxd = MapDocument("CURRENT")
        df = apmapping.ListDataFrames(mxd)[0]
        arcpy.env.addOutputsToMap = False
        groupLayer = apmapping.Layer(os.path.dirname(os.path.realpath(__file__)) + "\Data\MOUSE Links Elevation Error.lyr")
        groupLayer = apmapping.AddLayer(df, groupLayer)
        groupLayer = apmapping.ListLayers(mxd, groupLayer, df)[0]
        #arcpy.AddMessage(groupLayer)
        for layer in groupLayer:
            arcpy.AddMessage(layer.datasetName)
            layer.replaceDataSource(unicode(MU_database), 'ACCESS_WORKSPACE', unicode(layer.datasetName))     
        
        arcpy.RefreshTOC()
        arcpy.RefreshActiveView()
        return
        
class GenerateCatchmentConnections(object):
    def __init__(self):
        self.label       = "Generate Catchment Connections"
        self.description = "Generate Catchment Connections"
        self.canRunInBackground = False

    def getParameterInfo(self):
        #Define parameter definitions

        catchment_layer = arcpy.Parameter(
            displayName="Catchment feature layer",
            name="pipe_layer",
            datatype="GPFeatureLayer",
            parameterType="Required",
            direction="Input")

        delete_old_connections = arcpy.Parameter(
            displayName="Delete All Old Catchment Connections",
            name="delete_old_connections",
            datatype="Boolean",
            parameterType="optional",
            direction="Output")
        delete_old_connections.value = True

        parameters = [catchment_layer, delete_old_connections]
        return parameters

    def isLicensed(self):
        return True

    def updateParameters(self, parameters):


        return

    def updateMessages(self, parameters): #optional
        return

    def execute(self, parameters, messages):
        catchment_layer = parameters[0].Value
        delete_old_connections = parameters[0].ValueAsText
        mu_database = os.path.dirname(os.path.dirname(arcpy.Describe(catchment_layer).catalogPath))
        
        MUIDs = [row[0] for row in arcpy.da.SearchCursor(catchment_layer,["MUID"])]
        arcpy.AddMessage("%d selected catchments" % (len(MUIDs)))
        
        msm_Node = os.path.join(mu_database, "msm_Node")
        ms_Catchment = os.path.join(mu_database, "ms_Catchment")
        msm_CatchCon = os.path.join(mu_database, "msm_CatchCon")
        msm_CatchConLink = os.path.join(mu_database, "msm_CatchConLink")

        where_clause = "MUID IN ('%s')" % "', '".join(MUIDs)
        if len(where_clause) > 2900:
            where_clause = ""
            arcpy.AddMessage("Query exceeds 2900 chars")
        
        catchments_coordinates = {row[0]:row[1] for row in arcpy.da.SearchCursor(ms_Catchment, ["MUID", "SHAPE@XY"], 
                                    where_clause = where_clause)}

        links = {row[0]:[row[1], row[2]] for row in arcpy.da.SearchCursor(msm_CatchCon, ["MUID", "CatchID", "NodeID"], 
                                    where_clause = where_clause.replace("MUID","CatchID")) if row[1] in MUIDs}

        with arcpy.da.UpdateCursor(msm_CatchConLink, ["MUID"], where_clause = "CatchConID IN (%s)" % ", ".join([str(key) for key in links.keys()])
                                                                                if not delete_old_connections else "") as cursor:
            for row in cursor:
                cursor.deleteRow()

        nodes_MUIDs = [node for catchment, node in links.values()]
        
        nodes_coordinates = {row[0]:row[1] for row in arcpy.da.SearchCursor(msm_Node, ["MUID", "SHAPE@XY"], 
                                    where_clause = "MUID IN ('%s')" % "', '".join(nodes_MUIDs) if where_clause else "")}

        arcpy.AddMessage("Generating %d links" % (len(links)))
        arcpy.SetProgressor("step","Generating Catchment Connections", 0, len(links), 1)
        with arcpy.da.InsertCursor(msm_CatchConLink, ["SHAPE@", "MUID", "CatchConID","SHAPE_Length"]) as cursor:
            for link_i, link in enumerate(links.keys()):
                catchment, node = links[link]
                catchment_coordinate = catchments_coordinates[catchment]
                node_coordinate = nodes_coordinates[node]
                shape = arcpy.Polyline(arcpy.Array([arcpy.Point(catchment_coordinate[0], catchment_coordinate[1]),
                                             arcpy.Point(node_coordinate[0], node_coordinate[1])]))
                row = [shape, link_i, link, shape.length]
                cursor.insertRow(row)
                arcpy.SetProgressorPosition(link_i)
                
        return