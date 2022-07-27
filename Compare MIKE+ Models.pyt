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
        self.label = "Compare MIKE+ Models"
        self.alias = "Compare MIKE+ Models"
        self.canRunInBackground = True
        # List of tool classes associated with this toolbox
        self.tools = [CompareMikePlusModels]


class CompareMikePlusModels(object):
    def __init__(self):
        self.label = "Compare MIKE+ Models"
        self.description = "Compare MIKE+ Models"
        self.canRunInBackground = False

    def getParameterInfo(self):
        # Define parameter definitions

        database1 = arcpy.Parameter(
            displayName="Reference MIKE+ Model",
            name="database1",
            datatype="DEWorkspace",
            parameterType="Required",
            direction="Input")
        database1.filter.list = ["sqlite"]

        database2 = arcpy.Parameter(
            displayName="MIKE+ Model to compare to reference model",
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
        check_features.filter.type = "ValueList"
        check_features.filter.list = ["msm_Catchment", "msm_Node", "msm_Link", "msm_Weir", "msm_Orifice"]
        check_features.value = ["msm_Catchment", "msm_Node", "msm_Link", "msm_Weir", "msm_Orifice"]

        parameters = [database1, database2, check_features]
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
                      if field.name not in ["N/A"]]
            if "SHAPE@" not in fields:
                fields.append("SHAPE@")

            with arcpy.da.SearchCursor(feature_path_1, fields) as cursor:
                for row in cursor:
                    features_1[row[0]] = row

            with arcpy.da.SearchCursor(feature_path_2, fields) as cursor:
                for row in cursor:
                    features_2[row[0]] = row

            # Check MUIDs
            MUIDs = [features_1.keys() + features_2.keys()][0]

            missing_MUIDs = [MUID for MUID in MUIDs if MUIDs.count(MUID) == 1]
            MUIDs_to_check = [MUID for MUID in MUIDs if MUID not in missing_MUIDs]
            features_changed = {}

            def compare_rows(row1, row2):
                fields_diff = []
                for field_i in range(len(row1)):
                    if row1[field_i] != row2[field_i]:
                        fields_diff.append(field_i)
                return fields_diff

            MUIDs_field_changed = {}
            for MUID in MUIDs_to_check:
                idx = compare_rows(features_1[MUID], features_2[MUID])
                if idx:
                    MUIDs_field_changed[MUID] = [fields[i] for i in idx]

            with arcpy.da.InsertCursor(result_layer, fields) as cursor:
                for missing_MUID in missing_MUIDs:
                    if missing_MUID in features_1.keys():
                        cursor.insertRow(features_1[missing_MUID])
                    else:
                        cursor.insertRow(features_2[missing_MUID])
            
            arcpy.AddMessage(fields)
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
