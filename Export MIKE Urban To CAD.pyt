# Created by Emil Nielsen
# Contact: 
# E-mail: enielsen93@hotmail.com

import arcpy
import os
import traceback


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
        self.label =  "Export to CAD"
        self.alias  = "Export to CAD"

        # List of tool classes associated with this toolbox
        self.tools = [DisplayMikeUrbanAsCAD, ExportToCAD]

class DisplayMikeUrbanAsCAD(object):
    def __init__(self):
        self.label = "Display Model as CAD"
        self.description = "Display Model as CAD"
        self.canRunInBackground = False

    def getParameterInfo(self):
        # Define parameter definitions

        # Input Features parameter
        MU_database = arcpy.Parameter(
            displayName="Mike Urban database",
            name="database",
            datatype="DEWorkspace",
            parameterType="Required",
            direction="Input")

        parameters = [MU_database]

        return parameters

    def isLicensed(self):  # optional
        return True

    def updateParameters(self, parameters):  # optional
        return

    def updateMessages(self, parameters):  # optional

        return

    def execute(self, parameters, messages):
        MU_database = parameters[0].ValueAsText

        mxd = arcpy.mapping.MapDocument("CURRENT")
        df = arcpy.mapping.ListDataFrames(mxd)[0]
        df.scale = 500

        empty_group_mapped = arcpy.mapping.Layer(os.path.dirname(os.path.realpath(__file__)) + r"\Data\EmptyGroup.lyr")
        empty_group = arcpy.mapping.AddLayer(df, empty_group_mapped, "TOP")
        empty_group_layer = arcpy.mapping.ListLayers(mxd, "Empty Group", df)[0]
        empty_group_layer.name = os.path.splitext(os.path.basename(MU_database))[0]

        show_depth = True

        def addLayer(layer_source, source, group=None, workspace_type="ACCESS_WORKSPACE", new_name=None):
            if ".sqlite" in source:
                source_layer = arcpy.mapping.Layer(source)

                if group:
                    arcpy.mapping.AddLayerToGroup(df, group, source_layer, "BOTTOM")
                else:
                    arcpy.mapping.AddLayer(df, source_layer, "BOTTOM")
                update_layer = arcpy.mapping.ListLayers(mxd, source_layer.name, df)[0]

                layer_source_mike_plus = layer_source.replace("MOUSE",
                                                              "MIKE+") if "MOUSE" in layer_source and os.path.exists(
                    layer_source.replace("MOUSE", "MIKE+")) else None
                layer_source = layer_source_mike_plus if layer_source_mike_plus else layer_source
                layer = arcpy.mapping.Layer(layer_source)
                update_layer.visible = layer.visible
                update_layer.labelClasses = layer.labelClasses
                update_layer.showLabels = layer.showLabels
                update_layer.name = layer.name

                try:
                    arcpy.mapping.UpdateLayer(df, update_layer, layer, symbology_only=True)
                except Exception as e:
                    arcpy.AddWarning(source)
                    pass
            else:
                layer = arcpy.mapping.Layer(layer_source)
                if group:
                    arcpy.mapping.AddLayerToGroup(df, group, layer, "BOTTOM")
                else:
                    arcpy.mapping.AddLayer(df, layer, "BOTTOM")
                update_layer = arcpy.mapping.ListLayers(mxd, layer.name, df)[0]
                if new_name:
                    update_layer.name = new_name
                update_layer.replaceDataSource(unicode(os.path.dirname(source.replace(r"\mu_Geometry", ""))),
                                               workspace_type, unicode(os.path.basename(source)))

            if "msm_Node" in source:
                for label_class in update_layer.labelClasses:
                    if show_depth:
                        label_class.expression = label_class.expression.replace("return labelstr",
                                                                                'if [GroundLevel] and [InvertLevel]: labelstr += "\\nD:%1.2f" % ( convertToFloat([GroundLevel]) - convertToFloat([InvertLevel]) )\r\n  return labelstr')

        msm_Node = os.path.join(MU_database, "msm_Node")
        msm_Link = os.path.join(MU_database, "msm_Link")
        for manhole_layer in [u"Wastewater Manhole.lyr", u"Rainwater Manhole.lyr", u"Combined Manhole.lyr"]:
            addLayer(os.path.dirname(os.path.realpath(__file__)) + ur"\Data\ExportToCAD\%s" % manhole_layer,
                     msm_Node, group=empty_group_layer)

        for pipe_layer in [u"Wastewater Pipe.lyr", "Rainwater Pipe.lyr", "Combined Pipe.lyr"]:
            addLayer(os.path.dirname(os.path.realpath(__file__)) + r"\Data\ExportToCAD\%s" % pipe_layer,
                     msm_Link, group=empty_group_layer)


class ExportToCAD(object):
    def __init__(self):
        self.label = "Export Model to CAD"
        self.description = "Export Model to CAD"
        self.canRunInBackground = False

    def getParameterInfo(self):
        # Define parameter definitions

        # Input Features parameter
        MU_database = arcpy.Parameter(
            displayName="Mike Urban database",
            name="database",
            datatype="DEWorkspace",
            parameterType="Required",
            direction="Input")

        dgn_file = arcpy.Parameter(
            displayName="Output DGN file",
            name="dgn_file",
            datatype="File",
            parameterType="Required",
            direction="Output")
        dgn_file.filter.list = ["dwg", "dgn"]

        parameters = [MU_database, dgn_file]

        return parameters

    def isLicensed(self):  # optional
        return True

    def updateParameters(self, parameters):  # optional
        return

    def updateMessages(self, parameters):  # optional

        return

    def execute(self, parameters, messages):
        MU_database = parameters[0].ValueAsText
        dgn_file = parameters[1].ValueAsText

        msm_Node = os.path.join(MU_database, "msm_Node")

        arcpy.env.overwriteOutput = True

        mxd = arcpy.mapping.MapDocument("CURRENT")
        df = arcpy.mapping.ListDataFrames(mxd)[0]
        df.scale = 500

        MIKE_folder = os.path.join(os.path.dirname(arcpy.env.scratchGDB), "MIKE URBAN")
        if not os.path.exists(MIKE_folder):
            os.mkdir(MIKE_folder)
        MIKE_gdb = os.path.join(MIKE_folder, os.path.splitext(os.path.basename(MU_database))[0])
        arcpy.AddMessage(MIKE_gdb)
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
                MIKE_gdb = os.path.join(MIKE_folder, "%s_%d" % (os.path.splitext(os.path.basename(MU_database))[0], dir_ext))
        mxd.saveACopy(os.path.join(MIKE_gdb, "CAD.mxd"))
        arcpy.CreateFileGDB_management(MIKE_gdb, "scratch.gdb")
        arcpy.AddMessage(MIKE_gdb)
        arcpy.env.scratchWorkspace = os.path.join(MIKE_gdb, "scratch.gdb")

        arcpy.CreateFeatureclass_management(arcpy.env.scratchWorkspace, "Extent", geometry_type="Polygon")
        extent = arcpy.Describe(msm_Node).extent
        with arcpy.da.InsertCursor(os.path.join(arcpy.env.scratchWorkspace, "Extent"), ["SHAPE@"]) as cursor:
            row = [arcpy.Polygon(arcpy.Array([arcpy.Point(extent.XMin, extent.YMin),
                                              arcpy.Point(extent.XMax, extent.YMin),
                                              arcpy.Point(extent.XMax, extent.YMax),
                                              arcpy.Point(extent.XMin, extent.YMax)]))]
            cursor.insertRow(row)

        inPolygonIndexLayer = os.path.join(arcpy.env.scratchWorkspace, "Extent")

        arcpy.TiledLabelsToAnnotation_cartography(
            os.path.join(MIKE_gdb, "CAD.mxd"), "Layers", inPolygonIndexLayer, arcpy.env.scratchWorkspace,
            "anno", "_", 500, generate_unplaced_annotation="NOT_GENERATE_UNPLACED_ANNOTATION")

        arcpy.env.workspace = arcpy.env.scratchWorkspace
        anno_classes = [os.path.join(arcpy.env.scratchWorkspace, fc) for fc in arcpy.ListFeatureClasses(feature_type = "Annotation")]
        feature_layers = [layer.longName for layer in arcpy.mapping.ListLayers(mxd, "", df) if not layer.isGroupLayer and layer.isFeatureLayer and layer.visible]
        layers = anno_classes + feature_layers
        arcpy.ExportCAD_conversion(anno_classes + feature_layers, Output_Type = "DWG_R2010", Output_File = dgn_file,
                                    Seed_File = os.path.dirname(os.path.realpath(__file__)) + r"\Data\ExportToCAD\Seedfile.dwg")
        return