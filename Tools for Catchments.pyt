# Created by Emil Nielsen
# Contact: 
# E-mail: enielsen93@hotmail.com
import os
import arcpy
import numpy as np
import re
import pythonaddins
import hashlib
import xlwt
import csv

def getAvailableFilename(filepath):
    if arcpy.Exists(filepath):
        i = 1
        while arcpy.Exists(filepath + "%d" % i):
            i += 1
        return filepath + "%d" % i
    else:
        return filepath

from arcpy import env
class Toolbox(object):
    def __init__(self):
        self.label =  "Catchments"
        self.alias  = "Catchments"

        # List of tool classes associated with this toolbox
        self.tools = [CatchmentProcessing, CatchmentProcessingAlt, AlteredCatchments, CheckCatchments, FAS2Deloplande, TransferCatchments, GetImperviousness, GetImperviousnessFlora, DuplicateCatchments, GenerateCatchmentConnections, SetImperviousness]

class CatchmentProcessing(object):
    def __init__(self):
        self.label       = "Calculate imperviousness"
        self.description = "Calculate imperviousness of catchments from shapefiles delineating impervious areas"
        self.canRunInBackground = False

    def getParameterInfo(self):
        #Define parameter definitions

        # Input Features parameter
        imp_layer1 = arcpy.Parameter(
            displayName="Shapefile no. 1 delineating impervious areas",
            name="imp_layer1",
            datatype="GPFeatureLayer",
            parameterType="Required",
            direction="Input")
        imp_layer1.filter.list = ["Polygon"]
        
        imp_layer2 = arcpy.Parameter(
            displayName="Shapefile no. 2 delineating impervious areas",
            name="imp_layer2",
            datatype="GPFeatureLayer",
            parameterType="Optional",
            direction="Input")
        imp_layer2.filter.list = ["Polygon"]

        imp_layer3 = arcpy.Parameter(
            displayName="Shapefile no. 3 delineating impervious areas",
            name="imp_layer3",
            datatype="GPFeatureLayer",
            parameterType="Optional",
            direction="Input")
        imp_layer3.filter.list = ["Polygon"]

        catchments = arcpy.Parameter(
            displayName="Catchment layer",
            name="catchments",
            datatype="GPFeatureLayer",
            parameterType="Required",
            direction="Input")
        catchments.filter.list = ["Polygon"]

        parameters = [imp_layer1, imp_layer2, imp_layer3, catchments]
        return parameters

    def isLicensed(self):
        return True

    def updateParameters(self, parameters): #optional
        return

    def updateMessages(self, parameters): #optional
        return

    def execute(self, parameters, messages):
        # imparea = os.path.join(arcpy.env.scratchGDB,"ImpArea")
        #catchintsec = os.path.join(arcpy.env.scratchGDB,"catchintsec")
        #catchspatialjoin = os.path.join(arcpy.env.scratchGDB,"CatchSpatialJoin")
        #ms_catchments = os.path.join(arcpy.env.scratchGDB, "ms_catchments")
        imparea = os.path.join("in_memory","ImpArea")
        catchintsec = os.path.join("in_memory","catchintsec")
        catchspatialjoin = os.path.join("in_memory","CatchSpatialJoin")
        ms_catchments = os.path.join("in_memory", "ms_catchments")
        catchments = parameters[3].ValueAsText
        arcpy.SetProgressor ("default", "Preparing catchments")
        arcpy.CopyFeatures_management(catchments,ms_catchments)
        
        arcpy.SetProgressor ("default", "Answer user promt (may be behind window)")
        userquery = pythonaddins.MessageBox("Calculate and assign imperviousness to %s catchments?" % (arcpy.GetCount_management(ms_catchments)[0]), "Confirm Assignment", 4)
        if userquery == "Yes":
            arcpy.AddMessage ("Repairing catchments layer")
            arcpy.RepairGeometry_management(ms_catchments)
            arcpy.DefineProjection_management(in_dataset=ms_catchments, coor_system="PROJCS['ETRS_1989_UTM_Zone_32N',GEOGCS['GCS_ETRS_1989',DATUM['D_ETRS_1989',SPHEROID['GRS_1980',6378137.0,298.257222101]],PRIMEM['Greenwich',0.0],UNIT['Degree',0.0174532925199433]],PROJECTION['Transverse_Mercator'],PARAMETER['false_easting',500000.0],PARAMETER['false_northing',0.0],PARAMETER['central_meridian',9.0],PARAMETER['scale_factor',0.9996],PARAMETER['latitude_of_origin',0.0],UNIT['Meter',1.0]]")

            arcpy.AddMessage ("Preparing and combining shapefiles delineating impervious areas")
            #arcpy.SetProgressor ("default", "Clipping shapefiles delineating impervious areas to speed up geoprocessing calculation")
            extentPolygon = arcpy.CreateFeatureclass_management("in_memory", "extentPolygon", geometry_type = "POLYGON")
            extentCoordinates = arcpy.Describe(ms_catchments).extent
            array = arcpy.Array([arcpy.Point(extentCoordinates.XMin, extentCoordinates.YMin),
                         arcpy.Point(extentCoordinates.XMax, extentCoordinates.YMin),
                         arcpy.Point(extentCoordinates.XMax, extentCoordinates.YMax),
                         arcpy.Point(extentCoordinates.XMin, extentCoordinates.YMax),])
            polygon = arcpy.Polygon(array)
            with arcpy.da.InsertCursor(extentPolygon, ['SHAPE@']) as cursor:
                cursor.insertRow([polygon])
            
            layersBasename = []
            layers = []
            for i in range(2):
                if parameters[i].value:
                    layersBasename.append(arcpy.Describe(parameters[i].value).baseName)
                    if arcpy.Describe(parameters[i].value).dataElementType == "DEShapeFile":
                        layers.append(arcpy.MakeFeatureLayer_management(parameters[i].value,"in_memory\layer%d.lyr" % i))
                    else:
                        layers.append(parameters[i].value)

            layersClipped = []
            for i,layer in enumerate(layers):
                try:
                    # layersClipped.append(os.path.join("in_memory","layersClipped%d" % i))
                    arcpy.AddMessage ("Clipping layer %s" % layersBasename[i])
                    layersClipped.append(arcpy.SelectLayerByLocation_management(in_layer=layer, overlap_type="INTERSECT", select_features=extentPolygon, search_distance="", selection_type="NEW_SELECTION", invert_spatial_relationship="NOT_INVERT"))
                    # arcpy.Clip_analysis(layer, extentPolygon, os.path.join("in_memory","layersClipped%d" % i))
                except Exception as e:
                    arcpy.AddWarning("Could not clip layer %s to extent of catchment shapefile" % layersBasename[i])
                    raise(e)
                try:
                    arcpy.AddMessage ("Repairing layer %s" % layersBasename[i])
                    arcpy.RepairGeometry_management(layersClipped[-1])
                except Exception as e:
                    arcpy.AddWarning("Could not repair layer %s" % layersBasename[i])
            if len(layersClipped)>1:
                arcpy.AddMessage ("Processing union between %s and %s" % (layersBasename[0],layersBasename[1]))
                arcpy.Union_analysis (layersClipped[0:2], imparea, join_attributes="ALL", cluster_tolerance="", gaps="GAPS")
                for i in range(len(layersClipped)-2):
                    arcpy.SetProgressor ("default", "Processing union for %s" % (layersBasename[i+2]))
                    arcpy.Union_analysis([imparea, layersClipped[i+2]], imparea + str(i), join_attributes="ALL", cluster_tolerance="", gaps="GAPS")
                    imparea = imparea + str(i)
            else:
                arcpy.SetProgressor ("default", "Processing union for %s" % (layersBasename[0]))
                arcpy.Union_analysis(layersClipped[0], imparea, join_attributes="ALL", cluster_tolerance="", gaps="GAPS")

            arcpy.SetProgressor ("default", "Processing intersect analysis")
            arcpy.Intersect_analysis ([[imparea,2],[ms_catchments,1]], catchintsec)
            
            arcpy.CopyFeatures_management(catchintsec, "C:\Papirkurv\CatchIntSec.shp")
            
            hashes = []
            try:
                with arcpy.da.SearchCursor(catchintsec, ['SHAPE@WKT']) as catchmentcursor:
                    for row in catchmentcursor:
                        hashes.append(hash(row[0]))
            except RuntimeError as e:
                arcpy.AddError(imparea)
                arcpy.AddError(arcpy.Exists(imparea))
                arcpy.AddError(ms_catchments)
                arcpy.AddError(arcpy.Exists(ms_catchments))
                arcpy.AddError(arcpy.Exists(catchintsec))
                raise(e)
            duplicates = set([x for x in hashes if hashes.count(x) > 1])

            duplicatesDict = {}
            for dup in duplicates:
                duplicatesDict[dup] = 0

            with arcpy.da.UpdateCursor(catchintsec, ['SHAPE@WKT']) as catchmentcursor:
                for row in catchmentcursor:
                    if hash(row[0]) in duplicatesDict.keys():
                        if duplicatesDict[hash(row[0])] > 0:
                            catchmentcursor.deleteRow()
                        duplicatesDict[hash(row[0])] = duplicatesDict[hash(row[0])] + 1


            arcpy.AddField_management(in_table=catchintsec, field_name="shapearea", field_type="FLOAT", field_precision="20", field_scale="10", field_length="", field_alias="", field_is_nullable="NULLABLE", field_is_required="NON_REQUIRED", field_domain="")
            arcpy.DefineProjection_management(in_dataset=catchintsec, coor_system="PROJCS['ETRS_1989_UTM_Zone_32N',GEOGCS['GCS_ETRS_1989',DATUM['D_ETRS_1989',SPHEROID['GRS_1980',6378137.0,298.257222101]],PRIMEM['Greenwich',0.0],UNIT['Degree',0.0174532925199433]],PROJECTION['Transverse_Mercator'],PARAMETER['false_easting',500000.0],PARAMETER['false_northing',0.0],PARAMETER['central_meridian',9.0],PARAMETER['scale_factor',0.9996],PARAMETER['latitude_of_origin',0.0],UNIT['Meter',1.0]]")
            arcpy.CalculateField_management(catchintsec, "shapearea", "!SHAPE.AREA@SQUAREMETERS!", "PYTHON_9.3")
            arcpy.SpatialJoin_analysis(target_features=ms_catchments, join_features=catchintsec, out_feature_class=catchspatialjoin, join_operation="JOIN_ONE_TO_ONE", join_type="KEEP_ALL", field_mapping="""MUID "MUID" true true false 40 Text 0 0 ,First,#,%s,MUID,-1,-1;shapearea "shapearea" true true false 4 Float 0 0 ,Sum,#,%s,shapearea,-1,-1""" % (ms_catchments,catchintsec), match_option="CONTAINS", search_radius="", distance_field_name="")
            arcpy.AddField_management(in_table=catchspatialjoin, field_name="ImpArea", field_type="FLOAT", field_precision="20", field_scale="10", field_length="", field_alias="", field_is_nullable="NULLABLE", field_is_required="NON_REQUIRED", field_domain="")
            arcpy.CalculateField_management(catchspatialjoin, "ImpArea", "!shapearea!/!SHAPE.AREA@SQUAREMETERS!*100", "PYTHON_9.3")

            MUIDs = []
            ImpAreas = []
            with arcpy.da.SearchCursor(catchspatialjoin, ['MUID','ImpArea']) as catchmentcursor:
                for row in catchmentcursor:
                    MUIDs.append(row[0])
                    ImpAreas.append(row[1])
                    if False and type(row[1])==float:
                        arcpy.AddMessage("%s: %f" %(row[0],row[1]))
            catchmentsWithoutModelParameters = np.ones(len(MUIDs),dtype=bool)

            if "OplandData_GDB" in arcpy.Describe(catchments).file:
                catchmentcursor = arcpy.da.UpdateCursor(catchments, ["MUID","BEF_GRAD"])
            else:
                catchmentcursor = arcpy.da.UpdateCursor(os.path.join(os.path.dirname(arcpy.Describe(catchments).path),"msm_HModA"), ["CatchID","ImpArea"])
            for row in catchmentcursor:
                j = [k for k,a in enumerate(MUIDs) if a==row[0]]
                if len(j)==1:
                    oldValue = row[1]
                    catchmentsWithoutModelParameters[j] = False
                    if type(ImpAreas[j[0]])==float:
                        row[1] = ImpAreas[j[0]]
                    else:
                        row[1] = 0
                    if abs(oldValue-row[1])>1:
                        arcpy.AddMessage("Changed catchment %s from %1.0f to %1.0f" % (row[0],oldValue,row[1]))
                        try:
                            catchmentcursor.updateRow(row)
                        except Exception as e:
                            arcpy.AddError("Can't change %s from %d to %d" % (row[0],oldValue,row[1]))
                            raise(e)

            del catchmentcursor
            if True in catchmentsWithoutModelParameters:
                arcpy.AddWarning("Catchments without Model Records [msm_HModA] (imperviousness not set): '" + "', '".join(np.array(MUIDs)[np.where(catchmentsWithoutModelParameters)]) + "'")
            #arcpy.CopyFeatures_management(catchspatialjoin,r"C:/Dokumenter/catchspatialjoin")
        return

class CatchmentProcessingAlt(object):
    def __init__(self):
        self.label       = "Calculate imperviousness (set to field of shapefile)"
        self.description = "Calculate imperviousness of catchments from shapefiles delineating impervious areas"
        self.canRunInBackground = False

    def getParameterInfo(self):
        #Define parameter definitions

        # Input Features parameter
        # Input Features parameter
        imp_layer1 = arcpy.Parameter(
            displayName="Shapefile no. 1 delineating impervious areas",
            name="imp_layer1",
            datatype="GPFeatureLayer",
            parameterType="Required",
            direction="Input")
        imp_layer1.filter.list = ["Polygon"]
        
        imp_layer2 = arcpy.Parameter(
            displayName="Shapefile no. 2 delineating impervious areas",
            name="imp_layer2",
            datatype="GPFeatureLayer",
            parameterType="Optional",
            direction="Input")
        imp_layer2.filter.list = ["Polygon"]

        imp_layer3 = arcpy.Parameter(
            displayName="Shapefile no. 3 delineating impervious areas",
            name="imp_layer3",
            datatype="GPFeatureLayer",
            parameterType="Optional",
            direction="Input")
        imp_layer3.filter.list = ["Polygon"]

        catchments = arcpy.Parameter(
            displayName="Catchment layer",
            name="catchments",
            datatype="GPFeatureLayer",
            parameterType="Required",
            direction="Input")
        catchments.filter.list = ["Polygon"]

        field = arcpy.Parameter(
            displayName= "Field to assign imperviousness to",
            name="Field",
            datatype="GPString",
            parameterType="Required",
            direction="Input")

        parameters = [imp_layer1, imp_layer2, imp_layer3, catchments, field]
        return parameters

    def isLicensed(self):
        return True

    def updateParameters(self, parameters): #optional
        if parameters[3].altered:
            parameters[4].filter.list = [f.name for f in arcpy.Describe(parameters[3].value).fields]
        return

    def updateMessages(self, parameters): #optional
        return

    def execute(self, parameters, messages):
        # imparea = os.path.join(arcpy.env.scratchGDB,"ImpArea")
        #catchintsec = os.path.join(arcpy.env.scratchGDB,"catchintsec")
        #catchspatialjoin = os.path.join(arcpy.env.scratchGDB,"CatchSpatialJoin")
        #ms_catchments = os.path.join(arcpy.env.scratchGDB, "ms_catchments")
        imparea = os.path.join("in_memory","ImpArea")
        catchintsec = os.path.join("in_memory","catchintsec")
        catchspatialjoin = os.path.join("in_memory","CatchSpatialJoin")
        ms_catchments = os.path.join("in_memory", "ms_catchments")
        field = parameters[4].ValueAsText
        arcpy.SetProgressor ("default", "Preparing catchments")
        tempField = "temp"
        arcpy.AddField_management(parameters[3].ValueAsText, "temp","SHORT")
        with arcpy.da.UpdateCursor(parameters[3].ValueAsText,"temp") as cursor:
            for i,row in enumerate(cursor):
                row[0] = int(i)
                cursor.updateRow(row)
        arcpy.CopyFeatures_management(parameters[3].ValueAsText,ms_catchments)

        arcpy.SetProgressor ("default", "Answer user promt (may be behind window)")
        userquery = pythonaddins.MessageBox("Calculate and assign imperviousness to %s catchments?" % (arcpy.GetCount_management(ms_catchments)[0]), "Confirm Assignment", 4)
        if userquery == "Yes":
            arcpy.AddMessage ("Repairing catchments layer")
            arcpy.RepairGeometry_management(ms_catchments)
            arcpy.DefineProjection_management(in_dataset=ms_catchments, coor_system="PROJCS['ETRS_1989_UTM_Zone_32N',GEOGCS['GCS_ETRS_1989',DATUM['D_ETRS_1989',SPHEROID['GRS_1980',6378137.0,298.257222101]],PRIMEM['Greenwich',0.0],UNIT['Degree',0.0174532925199433]],PROJECTION['Transverse_Mercator'],PARAMETER['false_easting',500000.0],PARAMETER['false_northing',0.0],PARAMETER['central_meridian',9.0],PARAMETER['scale_factor',0.9996],PARAMETER['latitude_of_origin',0.0],UNIT['Meter',1.0]]")

            arcpy.AddMessage ("Preparing and combining shapefiles delineating impervious areas")
            #arcpy.SetProgressor ("default", "Clipping shapefiles delineating impervious areas to speed up geoprocessing calculation")
            extentPolygon = arcpy.CreateFeatureclass_management("in_memory", "extentPolygon", geometry_type = "POLYGON")
            extentCoordinates = arcpy.Describe(ms_catchments).extent
            array = arcpy.Array([arcpy.Point(extentCoordinates.XMin, extentCoordinates.YMin),
                         arcpy.Point(extentCoordinates.XMax, extentCoordinates.YMin),
                         arcpy.Point(extentCoordinates.XMax, extentCoordinates.YMax),
                         arcpy.Point(extentCoordinates.XMin, extentCoordinates.YMax),])
            polygon = arcpy.Polygon(array)
            with arcpy.da.InsertCursor(extentPolygon, ['SHAPE@']) as cursor:
                cursor.insertRow([polygon])

            layersBasename = []
            layers = []
            for i in range(2):
                if parameters[i].value:
                    layersBasename.append(arcpy.Describe(parameters[i].value).baseName)
                    if arcpy.Describe(parameters[i].value).dataElementType == "DEShapeFile":
                        layers.append(arcpy.MakeFeatureLayer_management(parameters[i].value,"in_memory\layer%d.lyr" % i))
                    else:
                        layers.append(parameters[i].value)

            layersClipped = []
            for i,layer in enumerate(layers):
                try:
                    # layersClipped.append(os.path.join("in_memory","layersClipped%d" % i))
                    arcpy.AddMessage ("Clipping layer %s" % layersBasename[i])
                    layersClipped.append(arcpy.SelectLayerByLocation_management(in_layer=layer, overlap_type="INTERSECT", select_features=extentPolygon, search_distance="", selection_type="NEW_SELECTION", invert_spatial_relationship="NOT_INVERT"))
                    # arcpy.Clip_analysis(layer, extentPolygon, os.path.join("in_memory","layersClipped%d" % i))
                except Exception as e:
                    arcpy.AddWarning("Could not clip layer %s to extent of catchment shapefile" % layersBasename[i])
                    raise(e)
                try:
                    arcpy.AddMessage ("Repairing layer %s" % layersBasename[i])
                    arcpy.RepairGeometry_management(layersClipped[-1])
                except Exception as e:
                    arcpy.AddWarning("Could not repair layer %s" % layersBasename[i])
            if len(layersClipped)>1:
                arcpy.AddMessage ("Processing union between %s and %s" % (layersBasename[0],layersBasename[1]))
                arcpy.Union_analysis (layersClipped[0:2], imparea, join_attributes="ALL", cluster_tolerance="", gaps="GAPS")
                for i in range(len(layersClipped)-2):
                    arcpy.SetProgressor ("default", "Processing union for %s" % (layersBasename[i+2]))
                    arcpy.Union_analysis([imparea, layersClipped[i+2]], imparea + str(i), join_attributes="ALL", cluster_tolerance="", gaps="GAPS")
                    imparea = imparea + str(i)
            else:
                arcpy.SetProgressor ("default", "Processing union for %s" % (layersBasename[0]))
                arcpy.Union_analysis(layersClipped[0], imparea, join_attributes="ALL", cluster_tolerance="", gaps="GAPS")
            
            arcpy.SetProgressor ("default", "Processing intersect analysis")
            arcpy.Intersect_analysis ([[imparea,2],[ms_catchments,1]], catchintsec)

            hashes = []
            try:
                with arcpy.da.SearchCursor(catchintsec, ['SHAPE@WKT']) as catchmentcursor:
                    for row in catchmentcursor:
                        hashes.append(hash(row[0]))
            except RuntimeError as e:
                arcpy.AddError(imparea)
                arcpy.AddError(arcpy.Exists(imparea))
                arcpy.AddError(ms_catchments)
                arcpy.AddError(arcpy.Exists(ms_catchments))
                arcpy.AddError(arcpy.Exists(catchintsec))
                raise(e)
            duplicates = set([x for x in hashes if hashes.count(x) > 1])

            duplicatesDict = {}
            for dup in duplicates:
                duplicatesDict[dup] = 0

            with arcpy.da.UpdateCursor(catchintsec, ['SHAPE@WKT']) as catchmentcursor:
                for row in catchmentcursor:
                    if hash(row[0]) in duplicatesDict.keys():
                        if duplicatesDict[hash(row[0])] > 0:
                            catchmentcursor.deleteRow()
                        duplicatesDict[hash(row[0])] = duplicatesDict[hash(row[0])] + 1


            arcpy.AddField_management(in_table=catchintsec, field_name="shapearea", field_type="FLOAT", field_precision="20", field_scale="10", field_length="", field_alias="", field_is_nullable="NULLABLE", field_is_required="NON_REQUIRED", field_domain="")
            arcpy.DefineProjection_management(in_dataset=catchintsec, coor_system="PROJCS['ETRS_1989_UTM_Zone_32N',GEOGCS['GCS_ETRS_1989',DATUM['D_ETRS_1989',SPHEROID['GRS_1980',6378137.0,298.257222101]],PRIMEM['Greenwich',0.0],UNIT['Degree',0.0174532925199433]],PROJECTION['Transverse_Mercator'],PARAMETER['false_easting',500000.0],PARAMETER['false_northing',0.0],PARAMETER['central_meridian',9.0],PARAMETER['scale_factor',0.9996],PARAMETER['latitude_of_origin',0.0],UNIT['Meter',1.0]]")
            arcpy.CalculateField_management(catchintsec, "shapearea", "!SHAPE.AREA@SQUAREMETERS!", "PYTHON_9.3")
            # arcpy.CopyFeatures_management(catchintsec,"P:\Temp\catchintsec.shp")
            # arcpy.CopyFeatures_management(ms_catchments,"P:\Temp\ms_catchments.shp")
            # arcpy.CopyFeatures_management(ms_catchments,"P:\Temp\ms_catchments2.shp")
            arcpy.SpatialJoin_analysis(target_features=ms_catchments, join_features=catchintsec, out_feature_class=catchspatialjoin, join_operation="JOIN_ONE_TO_ONE", join_type="KEEP_ALL", field_mapping="""temp "temp" true true false 40 Text 0 0 ,First,#,%s,temp,-1,-1;shapearea "shapearea" true true false 4 Float 0 0 ,Sum,#,%s,shapearea,-1,-1""" % (ms_catchments,catchintsec), match_option="CONTAINS", search_radius="", distance_field_name="")
            arcpy.AddField_management(in_table=catchspatialjoin, field_name="ImpArea", field_type="FLOAT", field_precision="20", field_scale="10", field_length="", field_alias="", field_is_nullable="NULLABLE", field_is_required="NON_REQUIRED", field_domain="")
            arcpy.CalculateField_management(catchspatialjoin, "ImpArea", "!shapearea!/!SHAPE.AREA@SQUAREMETERS!*100", "PYTHON_9.3")
            # arcpy.CopyFeatures_management(catchspatialjoin,"P:\Temp\ms_catchments.shp")
            
            IDColumn = "temp"
            if IDColumn not in [f.name for f in arcpy.ListFields(parameters[3].ValueAsText)]:
                arcpy.AddError("No index column named %s found on shapefile" % (IDColumn))
            OBJECTID = []
            ImpAreas = []
            with arcpy.da.SearchCursor(catchspatialjoin, [IDColumn,'ImpArea']) as catchmentcursor:
                for row in catchmentcursor:
                    OBJECTID.append(row[0])
                    ImpAreas.append(row[1])
                    if False and type(row[1])==float:
                        arcpy.AddMessage("%s: %f" %(row[0],row[1]))
            arcpy.AddMessage(OBJECTID)
            catchmentsWithoutModelParameters = np.ones(len(OBJECTID),dtype=bool)
            arcpy.AddMessage(ImpAreas)
            catchmentcursor = arcpy.da.UpdateCursor(parameters[3].ValueAsText, [IDColumn, field])
            for row in catchmentcursor:
                j = [k for k,a in enumerate(OBJECTID) if int(a)==row[0]]
                if len(j)==1:
                    oldValue = row[1]
                    catchmentsWithoutModelParameters[j] = False
                    if type(ImpAreas[j[0]])==float:
                        row[1] = ImpAreas[j[0]]
                    else:
                        row[1] = 0
                    if oldValue and abs(oldValue-row[1])>1:
                        arcpy.AddMessage("Changed catchment %s from %1.0f to %1.0f" % (row[0],oldValue,row[1]))
                    try:
                        catchmentcursor.updateRow(row)
                    except Exception as e:
                        arcpy.AddError("Can't change %s from %d to %d" % (row[0],oldValue,row[1]))
                        raise(e)
            arcpy.DeleteField_management(parameters[3].ValueAsText,"temp")
            del catchmentcursor

            #arcpy.CopyFeatures_management(catchspatialjoin,r"C:/Dokumenter/catchspatialjoin")
        return

class AlteredCatchments(object):
    def __init__(self):
        self.label       = "Find altered catchments"
        self.description = "Compare two catchment databases and select the catchments in the first database that differ from the second"
        self.canRunInBackground = False

    def getParameterInfo(self):
        #Define parameter definitions

        # Input Features parameter
        newcatchments = arcpy.Parameter(
            displayName="New catchments",
            name="newcatchments",
            datatype="GPFeatureLayer",
            parameterType="Required",
            direction="Input")
        newcatchments.filter.list = ["Polygon"]

        oldcatchments = arcpy.Parameter(
            displayName="Old catchments",
            name="oldcatchments",
            datatype="GPFeatureLayer",
            parameterType="Required",
            direction="Input")
        oldcatchments.filter.list = ["Polygon"]

        selectiontypeparameter = arcpy.Parameter(
           displayName = "Selection type",
           name = "selection_type",
           datatype = "GPString",
           parameterType = "Required",
           direction = "Input")
        selectiontypeparameter.value = "NEW_SELECTION"
        selectiontypeparameter.filter.list = ["NEW_SELECTION", "ADD_TO_SELECTION", "REMOVE_FROM_SELECTION", "SUBSET_SELECTION"]


        parameters = [newcatchments, oldcatchments, selectiontypeparameter]
        return parameters

    def isLicensed(self):
        return True

    def updateParameters(self, parameters): #optional
        return

    def updateMessages(self, parameters): #optional
        return

    def execute(self, parameters, messages):
        oldCatchmentsFile = parameters[1].ValueAsText
        newCatchmentsFile = parameters[0].ValueAsText
        selectiontype = parameters[2].ValueAsText

        oldCatchments = {}
        with arcpy.da.SearchCursor(oldCatchmentsFile, ['MUID','SHAPE@AREA']) as catchmentcursor:
            for row in catchmentcursor:
                oldCatchments[row[0]] = row[1]
        arcpy.AddMessage(oldCatchments)
        changedCatchments = []
        with arcpy.da.SearchCursor(newCatchmentsFile, ['MUID','SHAPE@AREA']) as catchmentcursor:
            for row in catchmentcursor:
                matchMUID = [row[0] for a in oldCatchments.keys() if row[0]==a]
                if not matchMUID:
                    changedCatchments.append(row[0])
                elif oldCatchments[matchMUID[0]] != row[1]:
                    changedCatchments.append(row[0])
        where_clause=r"""MUID IN (%s)""" % ("'" + "', '".join(changedCatchments) + "'")

        arcpy.AddMessage(where_clause)
        arcpy.AddMessage("%1.0f catchments changed (%1.1f%s)" % (len(changedCatchments),float(len(changedCatchments))/len(oldCatchments)*100,"%"))

        arcpy.SelectLayerByAttribute_management(in_layer_or_view="ms_Catchment", selection_type="NEW_SELECTION", where_clause = where_clause   )
        # arcpy.SelectLayerByAttribute_management(in_layer_or_view="ReduktionKnude", selection_type="NEW_SELECTION", where_clause = "NodeID IN ('000846R','000866R')")
        return

class CheckCatchments(object):
    def __init__(self):
        self.label       = "Check catchments"
        self.description = "Check catchments"

    def getParameterInfo(self):
        #Define parameter definitions

        MU_database = arcpy.Parameter(
            displayName="Mike Urban database",
            name="database",
            datatype="DEWorkspace",
            parameterType="Required",
            direction="Input")
             # try:
        # MU_database.filter.list = ["hey"] 
        # mxd = arcpy.mapping.MapDocument("CURRENT")
        # df = arcpy.mapping.ListDataFrames(mxd)[0]
        # databases = set()
        # for layer in arcpy.mapping.ListLayers(df):
            # desc = arcpy.Describe(layer)
            # if ".mdb" in desc.catalogPath:
                # databases.add(desc.catalogPath.split(".mdb")[0] + ".mdb") 
        # MU_database.filter.list = list(databases)
        # except:
            # pass

        parameters = [MU_database]
        return parameters

    def isLicensed(self):
        return True

    def updateParameters(self, parameters): #optional
        return

    def updateMessages(self, parameters): #optional
        return

    def execute(self, parameters, messages):
        MU_database = parameters[0].ValueAsText
        catchments = MU_database + "\mu_Geometry\ms_Catchment"
        catchCon = MU_database + "\msm_CatchCon"
        hModA = MU_database + "\msm_HModA"
        nodesShape = MU_database + "\msm_Node"

        MUIDs = []
        MUIDsBadName = []
        badNameRegex = re.compile("^Catchment")
        with arcpy.da.SearchCursor(catchments,["MUID"]) as cursor:
            for row in cursor:
                MUIDs.append(row[0])
                if badNameRegex.findall(row[0]):
                    MUIDsBadName.append(row[0])

        duplicates = set([x for x in MUIDs if MUIDs.count(x) > 1])

        if len(duplicates)>0:
            arcpy.AddError("Critical error: Duplicate catchments in table ms_Catchment found: '" + "', '".join(duplicates) + "'")

        if len(MUIDsBadName)>0:
            arcpy.AddWarning("Warning: Catchments with unoriginal names found (not suitable for FLORA): '" + "', '".join(MUIDsBadName) + "'")

        catchmentsSinglePart = arcpy.MultipartToSinglepart_management(catchments,
                                               r"in_memory\singlepartCatchments")

        MUIDsSinglePart = []
        with arcpy.da.SearchCursor(catchmentsSinglePart,["MUID"]) as cursor:
            for row in cursor:
                MUIDsSinglePart.append(row[0])

        singlePartDuplicates = set([x for x in MUIDsSinglePart if MUIDsSinglePart.count(x) > 1])
        multiPartFeatures = [a for a in singlePartDuplicates if not a in duplicates]

        if len(multiPartFeatures)>0:
            arcpy.AddWarning("Warning: Multipart catchments in table ms_Catchment found (unable to import catchments into Dandas): '" + "', '".join(multiPartFeatures) + "'")

        MUIDsWithoutModelRecords = set(MUIDs)
        catchIDs = []
        with arcpy.da.SearchCursor(hModA,["CatchID"]) as cursor:
            for row in cursor:
                catchIDs.append(row[0])
                if row[0] in MUIDsWithoutModelRecords:
                    MUIDsWithoutModelRecords.remove(row[0])

        if len(MUIDsWithoutModelRecords)>0:
            arcpy.AddError("Critical error: Catchments without model records found: '" + "', '".join(MUIDsWithoutModelRecords) + "'")

        catchIDsWithoutCatchments = []
        for catchID in set(catchIDs):
            if not catchID in MUIDs:
                catchIDsWithoutCatchments.append(catchID)

        if len(catchIDsWithoutCatchments):
            arcpy.AddWarning("Warning: Model records without catchments found: '" + "', '".join(catchIDsWithoutCatchments) + "'")
        catchIDsDuplicates = set([x for x in catchIDs if catchIDs.count(x) > 1])
        if len(catchIDsDuplicates)>0:
            arcpy.AddError("Critical error: Duplicate entries in table msm_HModA found: '" + "', '".join(catchIDsDuplicates) + "'")

        nodes = [row[0] for row in arcpy.da.SearchCursor(nodesShape,"MUID")]

        catchConIDs = []
        MUIDsWithoutConnection = set(MUIDs)
        MUIDsWithConnectionToDeletedNode = set(MUIDs)
        with arcpy.da.SearchCursor(catchCon,["CatchID","NodeID"]) as cursor:
            for row in cursor:
                catchConIDs.append(row[0])
                if row[0] in MUIDsWithoutConnection:
                    MUIDsWithoutConnection.remove(row[0])
                if row[1] in nodes:
                    try:
                        MUIDsWithConnectionToDeletedNode.remove(row[0])
                    except Exception as e:
                        pass

        if len(MUIDsWithoutConnection)>0:
            arcpy.AddError("Critical error: Catchments without connection to node found: '" + "', '".join(MUIDsWithoutConnection) + "'")

        if len(MUIDsWithConnectionToDeletedNode)>0:
            arcpy.AddError("Critical error: Catchments connected to non-existant node found: '" + "', '".join(MUIDsWithConnectionToDeletedNode) + "'")

        catchConIDsDuplicates = set([x for x in catchConIDs if catchConIDs.count(x) > 1])
        if len(catchConIDsDuplicates)>0:
            arcpy.AddError("Critical error: Duplicate entries in table msm_CatchCon found: '" + "', '".join(catchConIDsDuplicates) + "'")

        catchConsWithoutCatchments = []
        for catchConID in set(catchConIDs):
            if not catchConID in MUIDs:
                catchConsWithoutCatchments.append(catchConID)
        if len(catchConsWithoutCatchments)>0:
            arcpy.AddWarning("Warning: Connections in msm_CatchCon without catchments found: '" + "', '".join(catchConsWithoutCatchments) + "'")


        arcpy.AddMessage("Catchment check done.")

        return

class FAS2Deloplande(object):
    def __init__(self):
        self.label       = "Assign FAS Data to Catchments"
        self.description = "Assign FAS Data to Catchments"
        self.canRunInBackground = False

    def getParameterInfo(self):
        #Define parameter definitions

        # Input Features parameter
        fas_features = arcpy.Parameter(
            displayName="FAS shape file",
            name="fas_features",
            datatype="GPFeatureLayer",
            parameterType="Required",
            direction="Input")

        fas_features.filter.list = ["Point"]

        catchment_features = arcpy.Parameter(
            displayName="Catchment shape file",
            name="catchment_features",
            datatype="GPFeatureLayer",
            parameterType="Required",
            direction="Input")

        catchment_features.filter.list = ["Polygon"]

        fields = arcpy.Parameter(
            displayName= "Field to assign FAS data to",
            name="Fields",
            datatype="GPString",
            parameterType="Required",
            direction="Input")

        matchtype = arcpy.Parameter(
            displayName= "Only match if FAS address is inside catchment",
            name="matchtype",
            datatype="GPBoolean",
            parameterType="Required",
            direction="Input")
        matchtype.value = "false"

        taksttype = arcpy.Parameter(
            displayName= "Include the following taksttyper:",
            name="taksttype",
            datatype="GPString",
            multiValue="true",
            parameterType="Required",
            direction="Input")

        searchDistance = arcpy.Parameter(
            displayName= "Search distance for matching FAS-point to catchment:",
            name="searchDistance",
            datatype="GPDouble",
            parameterType="Optional",
            direction="Input")
        searchDistance.value = 100.0

        taksttype.filter.list = [u'1/2 vandafledning - samletanke', u'Anden form for nedsivning', u'Biologisk', u'Biologisk rensning', u'Godkendt', u'Godkendt nedsivning', u'Off. kloak', u'Off. kloak - erhverv', u'Pumpestation- el ref.', u'Samletank', u'Samletank bidrag, Kjellerup', u'Samletank toilet', u'Samletank uden m\xe5ler', u'Samletank, m. m\xe5ler', u'Statsafg. 50% Aqua', u'Statsafgift nit.biologisk', u'Statsafgift spildevand', u'Statsafgift spildevand biologisk fa', u'Trappemodel', u'Trappemodel - samlet over 500 m\xb3', u'Trappemodel %', u'Trappemodel >20.000', u'Trappemodel over 20.000 m\xb3', u'Trappemodel over 20.000 m\xb3 - Fast enhed', u'Trappemodel over 500 m\xb3', u'Trappemodel uden rabat', u'Vandafl.', u'vandafl. bl. bolig & erhverv', u'vandafl. bl. bolig og erhverv', u'Vandafl.bidrag', u'Vandafledning']
        taksttype.value = [u'Off. kloak', u'Off. kloak - erhverv', u'Pumpestation- el ref.', u'Trappemodel', u'Trappemodel - samlet over 500 m\xb3', u'Trappemodel %', u'Trappemodel >20.000', u'Trappemodel over 20.000 m\xb3', u'Trappemodel over 20.000 m\xb3 - Fast enhed', u'Trappemodel over 500 m\xb3', u'Trappemodel uden rabat', u'Vandafl.', u'vandafl. bl. bolig & erhverv', u'vandafl. bl. bolig og erhverv', u'Vandafl.bidrag', u'Vandafledning', u'Vandafledning']
        parameters = [fas_features, catchment_features, fields, matchtype, taksttype, searchDistance]

        return parameters

    def isLicensed(self): #optional
        return True

    def updateParameters(self, parameters): #optional
        if parameters[1].altered:
            parameters[2].filter.list = [f.name for f in arcpy.Describe(parameters[1].value).fields]
        return

    def updateMessages(self, parameters): #optional
        return

    def execute(self, parameters, messages):
        searchDistance = parameters[5].ValueAsText
        FASFile = parameters[0].ValueAsText
        arcpy.env.workspace = "in_memory/FASJoin"
        OIDs = []
        with arcpy.da.SearchCursor(FASFile,"FID") as fascursor:
            for row in fascursor:
                OIDs.append("%d" % row[0])

        arcpy.CopyFeatures_management (arcpy.Describe(parameters[1].ValueAsText).catalogPath, "catchmentFile")
        arcpy.DefineProjection_management("catchmentFile",arcpy.Describe(parameters[0].ValueAsText).spatialReference)

        catchments = 0
        with arcpy.da.SearchCursor("catchmentFile", ['SHAPE@']) as catchmentcursor:
            for row in catchmentcursor:
                catchments = catchments+1
        catchmentForbrug = np.zeros((catchments),dtype=np.float)
        arcpy.SetProgressor("step","Calculating FAS per catchment", 0, int(arcpy.GetCount_management(FASFile)[0]), 1)
        selectedFAS = 0
        nodesOutsideSearchDistance = []
        nodesOutsideSearchDistanceValue = []

        with arcpy.da.SearchCursor(FASFile, ['SHAPE@',"Forbrug", "taksttype","FID"]) as fascursor:
            for i, fasrow in enumerate(fascursor):
                arcpy.SetProgressorPosition(i)
                if fasrow[2] in parameters[4].ValueAsText:
                    geometry = fascursor[0]
                    selectedFAS = selectedFAS +1
                    dist = []
                    with arcpy.da.SearchCursor("catchmentFile", ['SHAPE@']) as catchmentcursor:
                        for row in catchmentcursor:
                            newgeometry = catchmentcursor[0]
                            dist.append(geometry.distanceTo(newgeometry))
                            if dist[-1] == 0:
                                break
                    idx = np.argmin(dist)
                    if parameters[3].ValueAsText == "false" or dist[idx]==0:
                        catchmentForbrug[idx] = catchmentForbrug[idx] + fasrow[1]
                        if searchDistance and float(searchDistance)<np.min(dist):
                            nodesOutsideSearchDistance.append("%d" % fasrow[3])
                            nodesOutsideSearchDistanceValue.append(np.min(dist))

        idxSort = np.flipud(np.argsort(nodesOutsideSearchDistanceValue))
        if len(nodesOutsideSearchDistance)>0:
            nodesOutsideSearchDistanceValue = np.array(nodesOutsideSearchDistanceValue)
            nodesOutsideSearchDistance = np.array(nodesOutsideSearchDistance)
            messageStr = "Do you want to assign FAS to catchments from these nodes:\n([OBJECTID]: distance to nearest catchment)\n"
            for nodei in idxSort:
                messageStr += "%s: %dm\n" % (nodesOutsideSearchDistance[nodei], nodesOutsideSearchDistanceValue[nodei])
            arcpy.SetProgressor ("default", "Confirm assignment")
            arcpy.SelectLayerByAttribute_management(in_layer_or_view=FASFile, selection_type="NEW_SELECTION", where_clause = "FID IN (" + ",".join(nodesOutsideSearchDistance) + ")")
            userquery = pythonaddins.MessageBox(messageStr, "Confirm Assignment", 3)

            if userquery == "Yes":
                arcpy.SetProgressor("step","Assigning FAS to catchments", 0, catchments, 1)
                with arcpy.da.UpdateCursor(parameters[1].ValueAsText, [parameters[2].ValueAsText]) as catchmentcursor:
                    for i,row in enumerate(catchmentcursor):
                        arcpy.SetProgressorPosition(i)
                        if catchmentForbrug[i] <> 0:
                            row[0] = catchmentForbrug[i]
                            catchmentcursor.updateRow(row)

            elif userquery == "No":
                for OID in nodesOutsideSearchDistance:
                    OIDs.remove(OID)
                catchmentForbrug = np.zeros((catchments),dtype=np.float)
                arcpy.SelectLayerByAttribute_management(in_layer_or_view=FASFile, selection_type="NEW_SELECTION", where_clause = "FID IN (" + ",".join(OIDs) + ")"  )
                with arcpy.da.SearchCursor(FASFile, ['SHAPE@',"Forbrug", "taksttype","FID"]) as fascursor:
                    for i, fasrow in enumerate(fascursor):
                        arcpy.SetProgressorPosition(i)
                        if fasrow[2] in parameters[4].ValueAsText:
                            geometry = fascursor[0]
                            dist = []
                            with arcpy.da.SearchCursor("catchmentFile", ['SHAPE@']) as catchmentcursor:
                                for row in catchmentcursor:
                                    newgeometry = catchmentcursor[0]
                                    dist.append(geometry.distanceTo(newgeometry))
                            idx = np.argmin(dist)
                            if parameters[3].ValueAsText == "false" or dist[idx]==0:
                                if searchDistance and float(searchDistance)>np.min(dist):
                                    catchmentForbrug[idx] = catchmentForbrug[idx] + fasrow[1]
                arcpy.SetProgressor("step","Assigning FAS to catchments", 0, catchments, 1)
                with arcpy.da.UpdateCursor(parameters[1].ValueAsText, [parameters[2].ValueAsText]) as catchmentcursor:
                    for i,row in enumerate(catchmentcursor):
                        arcpy.SetProgressorPosition(i)
                        if catchmentForbrug[i] <> 0:
                            row[0] = catchmentForbrug[i]
                            catchmentcursor.updateRow(row)
            else:
                arcpy.AddMessage("Cancelled FAS assignment")
        else:
            arcpy.SetProgressor("step","Assigning FAS to catchments", 0, catchments, 1)
            with arcpy.da.UpdateCursor(parameters[1].ValueAsText, [parameters[2].ValueAsText]) as catchmentcursor:
                for i,row in enumerate(catchmentcursor):
                    arcpy.SetProgressorPosition(i)
                    if catchmentForbrug[i] <> 0:
                        row[0] = catchmentForbrug[i]
                        catchmentcursor.updateRow(row)
        return

class TransferCatchments(object):
    def __init__(self):
        self.label       = "Transfer Catchments from shapefile to Mike Urban Model"
        self.description = "Transfer Catchments from shapefile to Mike Urban Model"
        self.canRunInBackground = False

    def getParameterInfo(self):
        #Define parameter definitions

        # Input Features parameter
        ms_Catchment = arcpy.Parameter(
            displayName="Catchments Layer",
            name="ms_Catchment",
            datatype="GPFeatureLayer",
            parameterType="Required",
            direction="Input")
        ms_Catchment.filter.list = ["Polygon"]
        
        muidField = arcpy.Parameter(
            displayName="MUID field",
            name="muidField",
            datatype="String",
            parameterType="Optional",
            direction="Input")
        
        impField = arcpy.Parameter(
            displayName="Imperviousness field",
            name="impField",
            datatype="String",
            parameterType="Optional",
            direction="Input")

        nodeID = arcpy.Parameter(
            displayName="Field indicating connection to node",
            name="nodeID",
            datatype="String",
            parameterType="Optional",
            direction="Input")

        MU_database = arcpy.Parameter(
            displayName="Mike Urban Model",
            name="mikeUrbanModel",
            datatype="DEWorkspace",
            parameterType="Required",
            direction="Input")

        parameters = [ms_Catchment, muidField, impField, nodeID, MU_database]
        return parameters

    def isLicensed(self):
        return True

    def updateParameters(self, parameters): #optional
        # if parameters[0].altered:
            # parameters[1].filter.list = [f.name for f in arcpy.Describe(parameters[0].value).fields]
            # muidi = [i for i,a in enumerate(parameters[1].filter.list) if "muid" in a.lower()]
            # parameters[1].value = parameters[1].filter.list[muidi[0]] if muidi else ""
            
            # parameters[2].filter.list = [f.name for f in arcpy.Describe(parameters[0].value).fields]
            # impi = [i for i,a in enumerate(parameters[2].filter.list) if "imp" in a.lower()]
            # parameters[2].value = parameters[2].filter.list[impi[0]] if impi else ""
            
            # parameters[3].filter.list = [f.name for f in arcpy.Describe(parameters[0].value).fields]
            # nodei = [i for i,a in enumerate(parameters[3].filter.list) if "node" in a.lower()]
            # parameters[3].value = parameters[3].filter.list[nodei[0]] if nodei else ""
            
        if not parameters[4].valueAsText:
            mxd = arcpy.mapping.MapDocument("CURRENT")
            database = [lyr.dataSource for lyr in arcpy.mapping.ListLayers(mxd) if not lyr.getSelectionSet() and lyr.isFeatureLayer and ".mdb" in lyr.dataSource]
            if database:
                database = re.findall(r"(.+)(?=\.mdb)", database[0])[0] + ".mdb"
                parameters[4].value = database
        return

    def updateMessages(self, parameters): #optional
        return

    def execute(self, parameters, messages):
        ms_Catchment = parameters[0].ValueAsText
        muidField = parameters[1].ValueAsText
        impField = parameters[2].ValueAsText
        nodeID = parameters[3].ValueAsText
        MU_database = parameters[4].ValueAsText
        
        # ms_CatchmentCopy = os.path.join("P:\Temp", "ms_catchments56435")
        ms_CatchmentCopy = getAvailableFilename(os.path.join(arcpy.env.scratchGDB, "ms_catchments"))
        arcpy.CopyFeatures_management(ms_Catchment,ms_CatchmentCopy)
        arcpy.AddMessage(ms_CatchmentCopy)
        if not muidField == "MUID" and "MUID" in [f.name for f in arcpy.ListFields(ms_CatchmentCopy)]:
            arcpy.DeleteField_management(ms_CatchmentCopy, "MUID")
            arcpy.AlterField_management(ms_CatchmentCopy, muidField, "MUID")
        
        errorMessage = ""
        if not ".sqlite" in MU_database:
            edit = arcpy.da.Editor(MU_database)
            edit.startEditing(True,False)
            edit.startOperation()
            ms_CatchmentMUIDs = [row[0] for row in arcpy.da.SearchCursor(ms_CatchmentCopy,"MUID")]
            duplicateMUIDs = [row[0] for row in arcpy.da.SearchCursor(os.path.join(MU_database,"ms_Catchment"),"MUID",where_clause = "MUID IN ('%s')" % ("', '".join(ms_CatchmentMUIDs)))]
            duplicateHModA = [row[0] for row in arcpy.da.SearchCursor(os.path.join(MU_database,"msm_HModA"),"CatchID",where_clause = "CatchID IN ('%s')" % ("', '".join(ms_CatchmentMUIDs)))]
            duplicateCatchCon = [row[0] for row in arcpy.da.SearchCursor(os.path.join(MU_database,"msm_CatchCon"),"CatchID",where_clause = "CatchID IN ('%s')" % ("', '".join(ms_CatchmentMUIDs)))]
            if duplicateMUIDs:
                errorMessage += "Catchments with MUID ('%s') already exist in Catchment Layer in Mike Urban Database" % ("(', '".join(duplicateMUIDs))
            if duplicateHModA:
                errorMessage = errorMessage + "\n" if errorMessage else ""
                errorMessage += "Catchments with MUID ('%s') already exist in Model Records (msm_HModA) in Mike Urban Database" % ("(', '".join(duplicateHModA))
            if duplicateCatchCon:
                errorMessage = errorMessage + "\n" if errorMessage else ""
                errorMessage += "Catchments with MUID ('%s') already exist in Catchment Connections (msm_CatchCon) in Mike Urban Database" % ("(', '".join(duplicateCatchCon))
            # pythonaddins.MessageBox("prutskid", "Confirm Assignment", 4)
            if errorMessage:
                arcpy.AddWarning(errorMessage)
            if not errorMessage or pythonaddins.MessageBox("%s\nTransfer catchments anyway?" % (errorMessage), "Confirm Transfer", 1) == "OK":
                arcpy.Append_management(ms_CatchmentCopy, os.path.join(MU_database,"ms_Catchment"),"NO_TEST")
                
                with arcpy.da.SearchCursor(ms_CatchmentCopy,["MUID",impField,nodeID]) as catchmentCursor:
                    with arcpy.da.InsertCursor(os.path.join(MU_database,"msm_CatchCon"),["CatchID","NodeID","TypeNo"]) as cursor:
                        for row in catchmentCursor:
                            nID = 0 if not row[2] else row[2]
                            cursor.insertRow((row[0],nID,1))
                    catchmentCursor.reset()
                    del cursor
                    with arcpy.da.InsertCursor(os.path.join(MU_database,"msm_HModA"),["CatchID","ImpArea","ParAID","LocalNo","ConcTime","RFactor","ILoss","CoeffNo","TACoeff", "TACurveID"]) as cursor:
                        for row in catchmentCursor:
                            iArea = 0.0 if not row[1] else row[1]
                            cursor.insertRow((row[0], iArea,"-DEFAULT-",0,7,0.9,0.0006,0,0.33, "TACurve1"))
        else:
            ms_CatchmentMUIDs = [row[0] for row in arcpy.da.SearchCursor(ms_CatchmentCopy,"MUID")]
            duplicateMUIDs = [row[0] for row in arcpy.da.SearchCursor(os.path.join(MU_database,"msm_Catchment"),"muid",where_clause = "muid IN ('%s')" % ("', '".join(ms_CatchmentMUIDs)))]
            duplicateCatchCon = [row[0] for row in arcpy.da.SearchCursor(os.path.join(MU_database,"msm_CatchCon"),"catchid",where_clause = "catchid IN ('%s')" % ("', '".join(ms_CatchmentMUIDs)))]
            if duplicateMUIDs:
                errorMessage += "Catchments with MUID ('%s') already exist in Catchment Layer in Mike Urban Database" % ("(', '".join(duplicateMUIDs))
            if duplicateCatchCon:
                errorMessage = errorMessage + "\n" if errorMessage else ""
                errorMessage += "Catchments with MUID ('%s') already exist in Catchment Connections (msm_CatchCon) in Mike Urban Database" % ("(', '".join(duplicateCatchCon))
            # pythonaddins.MessageBox("prutskid", "Confirm Assignment", 4)
            if errorMessage:
                arcpy.AddWarning(errorMessage)
            if not errorMessage or pythonaddins.MessageBox("%s\nTransfer catchments anyway?" % (errorMessage), "Confirm Transfer", 1) == "OK":
                with arcpy.da.SearchCursor(ms_CatchmentCopy, field_names = ["SHAPE@", "MUID",impField,nodeID]) as catchmentCursor:
                    with arcpy.da.InsertCursor(os.path.join(MU_database,"msm_Catchment"), field_names = ["SHAPE@", "muid", "hydrologicalmodelno", "modelaimparea", "modelaparaid"]) as cursor:
                        for row in catchmentCursor:
                            cursor.insertRow((row[0], row[1], 1, row[2], "-DEFAULT-", ))
                    catchmentCursor.reset()
                    with arcpy.da.InsertCursor(os.path.join(MU_database,"msm_CatchCon"),["catchid","nodeid","typeno"]) as cursor:
                        for row in catchmentCursor:
                            nID = 0 if not row[2] else row[2]
                            cursor.insertRow((row[0],nID,1))
                    catchmentCursor.reset()
                    # with arcpy.da.InsertCursor(os.path.join(MU_database,"msm_HModA"),["CatchID","ImpArea","ParAID","LocalNo","ConcTime","RFactor","ILoss","CoeffNo","TACoeff"]) as cursor:
                        # for row in catchmentCursor:
                            # iArea = 0 if not row[1] else row[1]
                            # cursor.insertRow((row[0],iArea,"-DEFAULT-",0,7,0.9,0.0006,0,0.33))
        edit.stopOperation()
        edit.stopEditing(True)
        return
        
class GetImperviousness(object):
    def __init__(self):
        self.label       = "Display imperviousness from Mike Urban database"
        self.description = "Display imperviousness from Mike Urban database"
        self.canRunInBackground = False

    def getParameterInfo(self):
        #Define parameter definitions

        # Input Features parameter
        MU_database = arcpy.Parameter(
            displayName="Mike Urban database",
            name="database",
            datatype="File",
            parameterType="Required",
            direction="Input")
        MU_database.filter.list = ["mdb","sqlite"]
        
        includeWasteWater = arcpy.Parameter(
            displayName="Include wastewater?",
            name="includeWasteWater",
            datatype="Boolean",
            parameterType="Optional",
            direction="Input")
        
        parameters = [MU_database, includeWasteWater]
        
        return parameters

    def isLicensed(self): #optional
        return True

    def updateParameters(self, parameters): #optional
        return

    def updateMessages(self, parameters): #optional
       
        return

    def execute(self, parameters, messages):        
        includeWasteWater = parameters[1].ValueAsText
        mxd = arcpy.mapping.MapDocument("CURRENT")
        df = arcpy.mapping.ListDataFrames(mxd)[0]
        arcpy.env.addOutputsToMap = False
        ms_CatchmentImp = arcpy.CopyFeatures_management (parameters[0].ValueAsText + r"\mu_Geometry\ms_Catchment", getAvailableFilename(arcpy.env.scratchGDB + "\ms_CatchmentImp")).getOutput(0)
        ms_CatchmentImpLayer = arcpy.MakeFeatureLayer_management(ms_CatchmentImp, arcpy.env.scratchGDB + "\ms_CatchmentImpLayer").getOutput(0).name
        arcpy.JoinField_management(in_data=ms_CatchmentImpLayer, in_field="MUID", join_table=parameters[0].ValueAsText + r"\msm_HModA", join_field="CatchID", fields="ImpArea")
        arcpy.JoinField_management(in_data=ms_CatchmentImpLayer, in_field="MUID", join_table=parameters[0].ValueAsText + r"\msm_CatchCon", join_field="CatchID", fields="NodeID")
        addLayer = arcpy.mapping.Layer(ms_CatchmentImpLayer)
        arcpy.mapping.AddLayer(df, addLayer)
        updatelayer = arcpy.mapping.ListLayers(mxd, ms_CatchmentImpLayer, df)[0]
        sourcelayer = arcpy.mapping.Layer(os.path.dirname(os.path.realpath(__file__)) + "\Data\Catchments W Imp Area.lyr")
        arcpy.mapping.UpdateLayer(df,updatelayer,sourcelayer,False)
        updatelayer.replaceDataSource(str(addLayer.workspacePath), 'FILEGDB_WORKSPACE', str(addLayer.datasetName))
        if not includeWasteWater:
            updatelayer.definitionQuery = 'NetTypeNo IS NULL OR NetTypeNo IN (2,3)'
        else: 
            updatelayer.definitionQuery = ''
        #arcpy.ApplySymbologyFromLayer_management (addLayer, "Template.lyr")
        arcpy.RefreshTOC()
        arcpy.RefreshActiveView()
      
        
        return
                
class GetImperviousnessFlora(object):
    def __init__(self):
        self.label       = "Display imperviousness from Flora Catchments"
        self.description = "Display imperviousness from Flora Catchments"
        self.canRunInBackground = False

    def getParameterInfo(self):
        #Define parameter definitions

        # Input Features parameter
        FLORA_database = arcpy.Parameter(
            displayName="Mike Urban database",
            name="database",
            datatype="DEWorkspace",
            parameterType="Required",
            direction="Input")
        
        includeWasteWater = arcpy.Parameter(
            displayName="Include wastewater?",
            name="includeWasteWater",
            datatype="Boolean",
            parameterType="Optional",
            direction="Input")
        
        parameters = [FLORA_database, includeWasteWater]
        
        return parameters

    def isLicensed(self): #optional
        return True

    def updateParameters(self, parameters): #optional
        return

    def updateMessages(self, parameters): #optional
       
        return

    def execute(self, parameters, messages):        
        includeWasteWater = parameters[1].ValueAsText
        mxd = arcpy.mapping.MapDocument("CURRENT")
        df = arcpy.mapping.ListDataFrames(mxd)[0]
        arcpy.env.addOutputsToMap = False
        addLayer = arcpy.mapping.Layer(parameters[0].ValueAsText + r"\Oplandsrelaterede_data\OplandData_GDB")
        arcpy.mapping.AddLayer(df, addLayer)
        updatelayer = arcpy.mapping.ListLayers(mxd, "OplandData_GDB", df)[0]
        sourcelayer = arcpy.mapping.Layer(os.path.dirname(os.path.realpath(__file__)) + "\Data\OplandData_GDB_Symbology.lyr")
        arcpy.mapping.UpdateLayer(df,updatelayer,sourcelayer,False)
        arcpy.AddMessage(str(addLayer.workspacePath))
        arcpy.AddMessage(str(addLayer.datasetName))
        updatelayer.replaceDataSource(str(addLayer.workspacePath), 'ACCESS_WORKSPACE', str(addLayer.datasetName))
        if not includeWasteWater:
            updatelayer.definitionQuery = 'NetTypeNo = 3'
        arcpy.RefreshTOC()
        arcpy.RefreshActiveView()
      
        
        return
 
class GetImperviousness(object):
    def __init__(self):
        self.label       = "Display imperviousness from Mike Urban database"
        self.description = "Display imperviousness from Mike Urban database"
        self.canRunInBackground = False

    def getParameterInfo(self):
        #Define parameter definitions

        # Input Features parameter
        MU_database = arcpy.Parameter(
            displayName="Mike Urban database",
            name="database",
            datatype="File",
            parameterType="Required",
            direction="Input")
        MU_database.filter.list = ["mdb","sqlite"]
        
        includeWasteWater = arcpy.Parameter(
            displayName="Include wastewater?",
            name="includeWasteWater",
            datatype="Boolean",
            parameterType="Optional",
            direction="Input")
        
        parameters = [MU_database, includeWasteWater]
        
        return parameters

    def isLicensed(self): #optional
        return True

    def updateParameters(self, parameters): #optional
        return

    def updateMessages(self, parameters): #optional
       
        return

    def execute(self, parameters, messages):        
        includeWasteWater = parameters[1].ValueAsText
        mxd = arcpy.mapping.MapDocument("CURRENT")
        df = arcpy.mapping.ListDataFrames(mxd)[0]
        arcpy.env.addOutputsToMap = False
        ms_CatchmentImp = arcpy.CopyFeatures_management (parameters[0].ValueAsText + r"\mu_Geometry\ms_Catchment", getAvailableFilename(arcpy.env.scratchGDB + "\ms_CatchmentImp")).getOutput(0)
        ms_CatchmentImpLayer = arcpy.MakeFeatureLayer_management(ms_CatchmentImp, arcpy.env.scratchGDB + "\ms_CatchmentImpLayer").getOutput(0).name
        arcpy.JoinField_management(in_data=ms_CatchmentImpLayer, in_field="MUID", join_table=parameters[0].ValueAsText + r"\msm_HModA", join_field="CatchID", fields="ImpArea")
        arcpy.JoinField_management(in_data=ms_CatchmentImpLayer, in_field="MUID", join_table=parameters[0].ValueAsText + r"\msm_CatchCon", join_field="CatchID", fields="NodeID")
        addLayer = arcpy.mapping.Layer(ms_CatchmentImpLayer)
        arcpy.mapping.AddLayer(df, addLayer)
        updatelayer = arcpy.mapping.ListLayers(mxd, ms_CatchmentImpLayer, df)[0]
        sourcelayer = arcpy.mapping.Layer(os.path.dirname(os.path.realpath(__file__)) + "\Data\Catchments W Imp Area.lyr")
        arcpy.mapping.UpdateLayer(df,updatelayer,sourcelayer,False)
        updatelayer.replaceDataSource(str(addLayer.workspacePath), 'FILEGDB_WORKSPACE', str(addLayer.datasetName))
        if not includeWasteWater:
            updatelayer.definitionQuery = 'NetTypeNo IS NULL OR NetTypeNo IN (2,3)'
        else: 
            updatelayer.definitionQuery = ''
        #arcpy.ApplySymbologyFromLayer_management (addLayer, "Template.lyr")
        arcpy.RefreshTOC()
        arcpy.RefreshActiveView()
      
        
        return
                
class DuplicateCatchments(object):
    def __init__(self):
        self.label       = "Solve Catchments with identical MUIDs"
        self.description = "Solve Catchments with identical MUIDs"
        self.canRunInBackground = False

    def getParameterInfo(self):
        #Define parameter definitions

        # Input Features parameter
        catchments = arcpy.Parameter(
            displayName="Catchment Layer",
            name="catchments",
            datatype="GPFeatureLayer",
            parameterType="Required",
            direction="Input")
        catchments.filter.list = ["Polygon"]

        parameters = [catchments]
        return parameters

    def isLicensed(self): #optional
        return True

    def updateParameters(self, parameters): #optional
        return

    def updateMessages(self, parameters): #optional
       
        return

    def execute(self, parameters, messages):        
        catchments = parameters[0].ValueAsText
        
        MU_database = os.path.dirname(arcpy.Describe(catchments).catalogPath).replace("\mu_Geometry","")
        ms_Catchment = os.path.join(MU_database, "ms_Catchment")
        msm_HModA = os.path.join(MU_database, "msm_HModA")
        msm_CatchCon = os.path.join(MU_database, "msm_CatchCon")
        MUIDs = [row[0] for row in arcpy.da.SearchCursor(catchments, ["MUID"])]

        max_catchcon_MUID = np.max([row[0] for row in arcpy.da.SearchCursor(os.path.join(MU_database, 'ms_Catchment'), ["MUID"])])

        arcpy.SetProgressorLabel("Creating Workspace")
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

        arcpy.CreateFileGDB_management(MIKE_gdb, "scratch.gdb")
        arcpy.AddMessage(MIKE_gdb)
        arcpy.env.scratchWorkspace = os.path.join(MIKE_gdb, "scratch.gdb")

        arcpy.SetProgressorLabel("Creating backup in %s" % (arcpy.env.scratchWorkspace))
        for feature_class in [ms_Catchment, msm_HModA, msm_CatchCon]:
            arcpy.Copy_management(feature_class, os.path.join(arcpy.env.scratchWorkspace, os.path.basename(feature_class)))

        MUIDs_duplicate = set()
        for MUID in MUIDs:
            if MUIDs.count(MUID)>1:
                MUIDs_duplicate.add(MUID)

        MUIDs_reassigned = {MUID:[] for MUID in MUIDs_duplicate}
        MUIDs_used = MUIDs

        for MUID_duplicate in MUIDs_duplicate:
            idx_of_duplicates = [i for i,MUID in enumerate(MUIDs) if MUID == MUID_duplicate][1:]

            for idx in idx_of_duplicates:
                i = 2
                new_MUID = MUID_duplicate + "s%d" % i
                while new_MUID in MUIDs_used:
                    i += 1
                    new_MUID = MUID_duplicate + "s%d" % i

                MUIDs_reassigned[MUID_duplicate].append(new_MUID)
                MUIDs_used.append(new_MUID)

        msm_HModA_table = {}
        with arcpy.da.SearchCursor(msm_HModA, '*' , "CatchID IN ('%s')" % ("', '".join(MUIDs_duplicate))) as cursor:
            for row in cursor:
                msm_HModA_table[row[1]] = row
        arcpy.AddMessage((msm_HModA, "CatchID IN ('%s')" % ("', '".join(MUIDs_duplicate)), msm_HModA_table))

        msm_CatchCon_table = {}
        with arcpy.da.SearchCursor(msm_CatchCon, '*' , "CatchID IN ('%s')" % ("', '".join(MUIDs_duplicate))) as cursor:
            for row in cursor:
                msm_CatchCon_table[row[2]] = row

        MUIDs_reassigned_loop = {MUID:0 for MUID in MUIDs_reassigned.keys()}# dictionairy to check how many times the loop has found this MUID
        with arcpy.da.UpdateCursor(catchments, ['MUID'], "MUID IN ('%s')" % ("', '".join(MUIDs_duplicate))) as cursor:
            for row in cursor:
                MUID = row[0]
                if row[0] in MUIDs_reassigned:
                    if MUIDs_reassigned_loop[row[0]] > 0:
                        arcpy.AddMessage(row)
                        row[0] = MUIDs_reassigned[row[0]][MUIDs_reassigned_loop[row[0]]-1]
                        arcpy.AddMessage(row)
                        cursor.updateRow(row)
                        arcpy.AddMessage(row)
                    MUIDs_reassigned_loop[MUID] += 1

        for MUID in MUIDs_reassigned:
            MUIDs_reassigned[MUID][0] = MUID
        arcpy.AddMessage(msm_HModA_table)
        with arcpy.da.InsertCursor(msm_HModA, '*') as cursor:
            for original_MUID in MUIDs_reassigned.keys():
                for new_MUID in MUIDs_reassigned[original_MUID]:
                    row = list(msm_HModA_table[original_MUID])
                    row[1] = new_MUID
                    arcpy.AddMessage(row)
                    cursor.insertRow(row)

        new_MUID_i = 0
        catch_con_max_MUID = np.max([row[0] for row in arcpy.da.SearchCursor(msm_CatchCon, ["MUID"])])
        with arcpy.da.InsertCursor(msm_CatchCon, '*') as cursor:
            for original_MUID in MUIDs_reassigned.keys():
                for new_MUID in MUIDs_reassigned[original_MUID]:
                    new_MUID_i += 1
                    temp_row = list(msm_CatchCon_table[original_MUID])
                    temp_row[2] = new_MUID
                    arcpy.AddMessage((catch_con_max_MUID, new_MUID_i))
                    temp_row[1] = catch_con_max_MUID + new_MUID_i
                    arcpy.AddMessage(row)
                    row = temp_row
                    cursor.insertRow(row)
      
        
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
        catchment_layer.filter.list = ["Polygon"]

        delete_old_connections = arcpy.Parameter(
            displayName="Delete All Old Catchment Connections",
            name="delete_old_connections",
            datatype="Boolean",
            parameterType="optional",
            direction="Output")
        delete_old_connections.value = True

        catchcon_layer = arcpy.Parameter(
            displayName="Generate catchment connections in this layer (default is msm_CatchConLink)",
            name="catchment_layer",
            datatype="GPFeatureLayer",
            parameterType="optional",
            category="Additional Settings",
            direction="Input")

        parameters = [catchment_layer, delete_old_connections, catchcon_layer]
        return parameters

    def isLicensed(self):
        return True

    def updateParameters(self, parameters):


        return

    def updateMessages(self, parameters): #optional
        return

    def execute(self, parameters, messages):
        catchment_layer = parameters[0].Value
        delete_old_connections = parameters[1].Value
        catchcon_layer = parameters[2].Value
        mu_database = os.path.dirname(os.path.dirname(arcpy.Describe(catchment_layer).catalogPath))
        
        MUIDs = [row[0] for row in arcpy.da.SearchCursor(catchment_layer,["MUID"])]
        arcpy.AddMessage("%d selected catchments" % (len(MUIDs)))
        
        msm_Node = os.path.join(mu_database, "msm_Node")
        ms_Catchment = os.path.join(mu_database, "ms_Catchment")
        msm_CatchCon = os.path.join(mu_database, "msm_CatchCon")
        msm_CatchConLink = os.path.join(mu_database, "msm_CatchConLink") if not catchcon_layer else catchcon_layer

        where_clause = "MUID IN ('%s')" % "', '".join(MUIDs)
        if len(where_clause) > 2900:
            where_clause = ""
            arcpy.AddMessage("Query exceeds 2900 chars")
        
        catchments_coordinates = {row[0]:row[1] for row in arcpy.da.SearchCursor(ms_Catchment, ["MUID", "SHAPE@XY"], 
                                    where_clause = where_clause)}

        links = {row[0]:[row[1], row[2]] for row in arcpy.da.SearchCursor(msm_CatchCon, ["MUID", "CatchID", "NodeID"], 
                                    where_clause = where_clause.replace("MUID","CatchID")) if row[1] in MUIDs}
        # arcpy.AddMessage(where_clause.replace("MUID","CatchID"))
        # arcpy.AddMessage(links)

        if not catchcon_layer:
            with arcpy.da.UpdateCursor(msm_CatchConLink, ["CatchConID"], where_clause = "CatchConID IN (%s)" % ", ".join([str(key) for key in links.keys()])) as cursor:
                for row in cursor:
                    if row[0] in links.keys():
                        # arcpy.AddMessage(row)
                        cursor.deleteRow()

        nodes_MUIDs = [node for catchment, node in links.values()]
        
        nodes_coordinates = {row[0]:row[1] for row in arcpy.da.SearchCursor(msm_Node, ["MUID", "SHAPE@XY"], 
                                    where_clause = "MUID IN ('%s')" % "', '".join(nodes_MUIDs) if where_clause else "")}

        # arcpy.AddMessage("Generating %d links" % (len(links)))
        arcpy.SetProgressor("step","Generating Catchment Connections", 0, len(links), 1)
        fields = ["shape@"]
        for field in ["MUID", "CatchConID","SHAPE_Length", "CatchID"]:
            if field.lower() in [f.name.lower() for f in arcpy.ListFields(msm_CatchConLink)]:
                fields.append(field.lower())
        arcpy.AddMessage(fields)
        with arcpy.da.InsertCursor(msm_CatchConLink, fields) as cursor:
            for link_i, link in enumerate(links.keys()):
                arcpy.AddMessage(links[link])
                catchment, node = links[link]
                catchment_coordinate = catchments_coordinates[catchment]
                if node not in nodes_coordinates:
                    arcpy.AddWarning("Could not find node %s for catchment %s" % (node, catchment)) 
                else:
                    node_coordinate = nodes_coordinates[node] 
                    shape = arcpy.Polyline(arcpy.Array([arcpy.Point(catchment_coordinate[0], catchment_coordinate[1]),
                                                 arcpy.Point(node_coordinate[0], node_coordinate[1])]))
                    # row = [shape, link_i, link, shape.length]
                    row = [None]*len(fields)
                    arcpy.AddMessage([i for i,field in enumerate(fields) if field=="shape@"][0])
                    row[[i for i,field in enumerate(fields) if field=="shape@"][0]] = shape
                    if "muid" in fields:
                        row[[i for i, field in enumerate(fields) if field == "muid"][0]] = link_i
                    if "catchconid" in fields:
                        row[[i for i, field in enumerate(fields) if field == "catchconid"][0]] = link
                    if "shape_length" in fields:
                        row[[i for i, field in enumerate(fields) if field == "shape_length"][0]] = shape.length
                    if "catchid" in fields:
                        row[[i for i, field in enumerate(fields) if field == "catchid"][0]] = catchment
                    cursor.insertRow(row)
                arcpy.SetProgressorPosition(link_i)

                
        return


class SetImperviousness(object):
    def __init__(self):
        self.label = "Set Imperviousness"
        self.description = "Set Imperviousness"
        self.canRunInBackground = False

    def getParameterInfo(self):
        # Define parameter definitions
        catchments = arcpy.Parameter(
            displayName="Catchment layer",
            name="catchments",
            datatype="GPFeatureLayer",
            parameterType="Required",
            direction="Input")
        catchments.filter.list = ["Polygon"]

        imperviousness = arcpy.Parameter(
            displayName="Imperviousness:",
            name="imperviousness",
            datatype="double",
            parameterType="Required",
            direction="Input")

        parameters = [catchments, imperviousness]
        return parameters

    def isLicensed(self):
        return True

    def updateParameters(self, parameters):  # optional
        return

    def updateMessages(self, parameters):  # optional
        return

    def execute(self, parameters, messages):
        # imparea = os.path.join(arcpy.env.scratchGDB,"ImpArea")
        # catchintsec = os.path.join(arcpy.env.scratchGDB,"catchintsec")
        # catchspatialjoin = os.path.join(arcpy.env.scratchGDB,"CatchSpatialJoin")
        # ms_catchments = os.path.join(arcpy.env.scratchGDB, "ms_catchments")
        catchments = parameters[0].ValueAsText
        imperviousness = parameters[1].Value

        MUIDs = [row[0] for row in arcpy.da.SearchCursor(catchments, ["MUID"])]

        userquery = pythonaddins.MessageBox(
            "Assign imperviousness to %s catchments?" % (len(MUIDs)),
            "Confirm Assignment", 4)
        arcpy.AddMessage("MUIDs IN ('%s')" % ("', '".join(MUIDs)))
        if userquery == "Yes":
            if "OplandData_GDB" in arcpy.Describe(catchments).file:
                catchmentcursor = arcpy.da.UpdateCursor(catchments, ["MUID", "BEF_GRAD"], where_clause = "MUIDs IN ('%s')" % ("', '".join(MUIDs)))
            else:
                catchmentcursor = arcpy.da.UpdateCursor(
                    os.path.join(os.path.dirname(arcpy.Describe(catchments).path), "msm_HModA"), ["CatchID", "ImpArea"], where_clause = "CatchID IN ('%s')" % ("', '".join(MUIDs)))
            for row in catchmentcursor:
                oldValue = row[1]
                row[1] = imperviousness
                if abs(oldValue - row[1]) > 1:
                    arcpy.AddMessage("Changed catchment %s from %1.0f to %1.0f" % (row[0], oldValue, row[1]))
                    try:
                        catchmentcursor.updateRow(row)
                    except Exception as e:
                        arcpy.AddError("Can't change %s from %d to %d" % (row[0], oldValue, row[1]))
                        raise (e)

            del catchmentcursor
            # if True in catchmentsWithoutModelParameters:
            #     arcpy.AddWarning(
            #         "Catchments without Model Records [msm_HModA] (imperviousness not set): '" + "', '".join(
            #             np.array(MUIDs)[np.where(catchmentsWithoutModelParameters)]) + "'")
                # arcpy.CopyFeatures_management(catchspatialjoin,r"C:/Dokumenter/catchspatialjoin")
        return