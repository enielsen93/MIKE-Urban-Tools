import arcpy
import os
import re
import numpy as np
from arcpy._mapping import Layer


def getAvailableFilename(filepath, parent=None):
    parent = "F%s" % (parent) if parent and parent[0].isdigit() else None
    parent = os.path.basename(re.sub(r"\.[^\.\\]+$", "", parent)).replace(".", "_").replace("-", "_").replace(" ",
                                                                                                              "_").replace(
        ",", "_") if parent else None
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
        self.label = "Compare MIKE Models"
        self.alias = "Compare MIKE Models"
        self.canRunInBackground = True
        # List of tool classes associated with this toolbox
        self.tools = [CompareMikeModels]


class CompareMikeModels(object):
    def __init__(self):
        self.label = "Compare MIKE Models"
        self.description = "Compare MIKE Models"
        self.canRunInBackground = False

    def getParameterInfo(self):
        # Define parameter definitions

        database1 = arcpy.Parameter(
            displayName="Reference MIKE Model",
            name="database1",
            datatype="DEWorkspace",
            parameterType="Required",
            direction="Input")
        database1.filter.list = ["sqlite"]

        database2 = arcpy.Parameter(
            displayName="MIKE Model to compare to reference model",
            name="database2",
            datatype="DEWorkspace",
            parameterType="Required",
            direction="Input")
        database2.filter.list = ["sqlite"]

        check_features = arcpy.Parameter(
            displayName="Check these features:",
            name="check_features",
            datatype="GPString",
            parameterType="Required",
            multiValue=True,
            direction="Input")
        check_features.filter.list = ["msm_Catchment", "msm_Node", "msm_Link", "msm_Weir", "msm_Orifice"]
        check_features.value = ["msm_Catchment", "msm_Node", "msm_Link", "msm_Weir", "msm_Orifice"]

        ignore_fields = arcpy.Parameter(
            displayName="Ignore following common fields:",
            name="ignore_fields",
            datatype="GPString",
            parameterType="Optional",
            multiValue=True,
            direction="Input")
        ignore_fields.filter.list = ["OBJECTID", "SHAPE", "Slope", "UpLevel_C", "DwLevel_C", "Length_C", "UpLevel", "DwLevel", "Diameter", "NetTypeNo", "GroundLevel", "CriticalLevel", "Area"]
        ignore_fields.value = ["OBJECTID", "Slope", "UpLevel_C", "DwLevel_C", "Length_C", "CriticalLevel", "Area"]
        #ignore_fields.value = ["msm_Catchment", "msm_Node", "msm_Link", "msm_Weir", "msm_Orifice"]

        parameters = [database1, database2, check_features, ignore_fields]
        return parameters

    def isLicensed(self):
        return True

    def updateParameters(self, parameters):
        return

    def updateMessages(self, parameters):  # optional
        return

    def execute(self, parameters, messages):
        database1 = parameters[0].ValueAsText
        database2 = parameters[1].ValueAsText
        check_features = parameters[2].ValueAsText.split(";")
        ignore_fields = [field.lower() for field in parameters[3].ValueAsText.split(";")]

        if "slope" in ignore_fields:
            ignore_fields.append("slope_c")
        if "shape" in ignore_fields:
            ignore_fields.append("shape@")

        #arcpy.AddMessage(ignore_fields)

        def ignore_field(fieldname):
            if fieldname.lower() in ignore_fields:
                return True
            else:
                return False

        mxd = arcpy.mapping.MapDocument("CURRENT")
        df = arcpy.mapping.ListDataFrames(mxd)[0]

        def addLayer(layer_source, source, group=None, workspace_type="ACCESS_WORKSPACE"):
            layer = arcpy.mapping.Layer(layer_source)
            if group:
                arcpy.mapping.AddLayerToGroup(df, group, layer, "BOTTOM")
            else:
                arcpy.mapping.AddLayer(df, layer, "BOTTOM")
            updatelayer = arcpy.mapping.ListLayers(mxd, layer.name, df)[0]
            updatelayer.replaceDataSource(unicode(os.path.dirname(source.replace(r"\mu_Geometry", ""))), workspace_type,
                                          unicode(os.path.basename(source)))

        empty_group_mapped = arcpy.mapping.Layer(os.path.dirname(os.path.realpath(__file__)) + r"\Data\EmptyGroup.lyr")
        empty_group = arcpy.mapping.AddLayer(df, empty_group_mapped, "TOP")
        empty_group_layer = arcpy.mapping.ListLayers(mxd, "Empty Group", df)[0]
        empty_group_layer.name = "%s vs. %s" % (os.path.basename(database1), os.path.basename(database2))

        for feature in check_features:
            arcpy.AddMessage("Checking feature %s" % (feature))
            feature_path_1 = os.path.join(database1, feature)
            if ".mdb" in feature_path_1 and "Catchment" in feature_path_1:
                feature_path_1 = feature_path_1.replace("msm_Catchment", "ms_Catchment")
            feature_path_2 = os.path.join(database2, feature)
            if ".mdb" in feature_path_2 and "Catchment" in feature_path_2:
                feature_path_2 = feature_path_2.replace("msm_Catchment", "ms_Catchment")

            result_layer = getAvailableFilename(os.path.join(arcpy.env.scratchGDB, feature))
            arcpy.CreateFeatureclass_management(arcpy.env.scratchGDB, os.path.basename(result_layer),
                                                template=feature_path_1)

            arcpy.AddField_management(result_layer, "fields", "TEXT", field_is_nullable="NULLABLE")

            features_1 = {}
            features_2 = {}
            fields = [field.name if field.name != "geometry" else "SHAPE@" for field in arcpy.ListFields(feature_path_1)
                      if not ignore_field(field.name)]
            arcpy.AddMessage(fields)

            MUID_field_i = [i for i, field in enumerate(fields) if field.lower() == "muid"][0]

            if "SHAPE@" not in fields:
                fields.append("SHAPE@")

            arcpy.SetProgressor("step","Checking feature %s" % (feature_path_1), 0, len([1 for row in arcpy.da.SearchCursor(feature_path_1, "OID@")]), 1)
            with arcpy.da.SearchCursor(feature_path_1, fields) as cursor:
                step = 0
                for row in cursor:
                    arcpy.SetProgressorPosition(step)
                    step += 1
                    features_1[row[MUID_field_i]] = row

            arcpy.SetProgressor("step","Checking feature %s" % (feature_path_2), 0, len([1 for row in arcpy.da.SearchCursor(feature_path_2, "OID@")]), 1)
            with arcpy.da.SearchCursor(feature_path_2, fields) as cursor:
                step = 0
                for row in cursor:
                    arcpy.SetProgressorPosition(step)
                    step += 1
                    features_2[row[MUID_field_i]] = row
            
            arcpy.SetProgressor("default", "Getting MUIDs")
            # Check MUIDs
            MUIDs = set([features_1.keys() + features_2.keys()][0])

            missing_MUIDs = set(np.concatenate((np.setdiff1d(features_1.keys(), features_2.keys(), assume_unique = False), np.setdiff1d(features_2.keys(), features_1.keys(), assume_unique = False))))
            MUIDs_to_check = [MUID for MUID in MUIDs if MUID not in missing_MUIDs]
            features_changed = {}

            def compare_rows(row1, row2):
                fields_diff = []
                for field_i in range(len(row1)):
                    if row1[field_i] != row2[field_i]:
                        fields_diff.append(field_i)
                return fields_diff

            arcpy.SetProgressor("step","Comparing rows for feature %s" % (feature), 0, len(MUIDs_to_check), 1)
            MUIDs_field_changed = {}
            for step, MUID in enumerate(MUIDs_to_check):
                arcpy.SetProgressorPosition(step)
                idx = compare_rows(features_1[MUID], features_2[MUID])
                if idx:
                    MUIDs_field_changed[MUID] = [fields[i] for i in idx]


            if feature == "msm_Catchment" and ".mdb" in feature_path_1:
                msm_HModA_1 = {}
                msm_HModA_fields = [field.name for field in arcpy.ListFields(os.path.join(database1, "msm_HModA")) if not ignore_field(field.name)]
                catchID_field_i = [i for i, field in enumerate(msm_HModA_fields) if field.lower() == "catchid"][0]

                with arcpy.da.SearchCursor(os.path.join(database1, "msm_HModA"), msm_HModA_fields) as cursor:
                    for row in cursor:
                        msm_HModA_1[row[catchID_field_i]] = row

                msm_CatchCon_1 = {}
                msm_CatchCon_fields = [field.name for field in arcpy.ListFields(os.path.join(database1, "msm_CatchCon")) if not ignore_field(field.name)]
                catchID_field_i = [i for i, field in enumerate(msm_CatchCon_fields) if field.lower() == "catchid"][0]
                with arcpy.da.SearchCursor(os.path.join(database1, "msm_CatchCon"), msm_CatchCon_fields) as cursor:
                    for row in cursor:
                        msm_CatchCon_1[row[catchID_field_i]] = row

                msm_HModA_2 = {}
                msm_HModA_fields = [field.name for field in arcpy.ListFields(os.path.join(database2, "msm_HModA")) if not ignore_field(field.name)]
                catchID_field_i = [i for i, field in enumerate(msm_HModA_fields) if field.lower() == "catchid"][0]

                with arcpy.da.SearchCursor(os.path.join(database2, "msm_HModA"), msm_HModA_fields) as cursor:
                    for row in cursor:
                        msm_HModA_2[row[catchID_field_i]] = row

                msm_CatchCon_2 = {}
                msm_CatchCon_fields = [field.name for field in arcpy.ListFields(os.path.join(database1, "msm_CatchCon")) if not ignore_field(field.name)]
                catchID_field_i = [i for i, field in enumerate(msm_CatchCon_fields) if field.lower() == "catchid"][0]
                with arcpy.da.SearchCursor(os.path.join(database2, "msm_CatchCon"), msm_CatchCon_fields) as cursor:
                    for row in cursor:
                        msm_CatchCon_2[row[catchID_field_i]] = row


                for MUID in MUIDs_to_check:
                    if MUID in msm_HModA_1 and MUID in msm_HModA_2:
                        idx = compare_rows(msm_HModA_1[MUID], msm_HModA_2[MUID])
                        if idx:
                            MUIDs_field_changed[MUID] = [msm_HModA_fields[i] for i in idx]

                    if MUID in msm_CatchCon_1 and MUID in msm_CatchCon_2:
                        idx = compare_rows(msm_CatchCon_1[MUID], msm_CatchCon_2[MUID])
                        if idx:
                            MUIDs_field_changed[MUID] = [msm_CatchCon_fields[i] for i in idx]

            with arcpy.da.InsertCursor(result_layer, fields) as cursor:
                for missing_MUID in missing_MUIDs:
                    if missing_MUID in features_1.keys():
                        cursor.insertRow(features_1[missing_MUID])
                    else:
                        cursor.insertRow(features_2[missing_MUID])

            #arcpy.AddMessage(fields)
            geometry_field_i = [field_i for field_i, field in enumerate(fields) if field.lower() == "shape@"][0]
            MUID_field_i = [field_i for field_i, field in enumerate(fields) if field.lower() == "muid"][0]
            with arcpy.da.InsertCursor(result_layer, ["MUID", "SHAPE@", "fields"]) as cursor:
                for MUID in MUIDs_field_changed.keys():
                    row = (features_1[MUID][MUID_field_i], features_1[MUID][geometry_field_i],
                           ", ".join(MUIDs_field_changed[MUID]))
                    cursor.insertRow(row)

            newlayer = arcpy.mapping.Layer(result_layer)
            arcpy.mapping.AddLayerToGroup(df, empty_group_layer, newlayer, "TOP")

        return
