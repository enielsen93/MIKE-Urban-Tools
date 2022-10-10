# Created by Emil Nielsen
# Contact: 
# E-mail: enielsen93@hotmail.com

import arcpy
import os
import traceback
import networker


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
            
        label_scale = arcpy.Parameter(
            displayName="Label Scale",
            name="label_scale",
            datatype="GPLong",
            parameterType="Required",
            direction="Output")
        label_scale.value = 500

        parameters = [MU_database, label_scale]

        return parameters

    def isLicensed(self):  # optional
        return True

    def updateParameters(self, parameters):  # optional
        return

    def updateMessages(self, parameters):  # optional

        return

    def execute(self, parameters, messages):
        MU_database = parameters[0].ValueAsText
        label_scale = parameters[0].Value

        mxd = arcpy.mapping.MapDocument("CURRENT")
        df = arcpy.mapping.ListDataFrames(mxd)[0]
        df.label_scale = label_scale

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

        arcpy.SetProgressorLabel("Creating Workspace")
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
                MIKE_gdb = os.path.join(MIKE_folder,
                                        "%s_%d" % (os.path.splitext(os.path.basename(MU_database))[0], dir_ext))

        arcpy.CreateFileGDB_management(MIKE_gdb, "scratch.gdb")
        arcpy.AddMessage(MIKE_gdb)
        arcpy.env.scratchWorkspace = os.path.join(MIKE_gdb, "scratch.gdb")

        msm_Node = os.path.join(MU_database, "msm_Node")
        msm_Link = os.path.join(MU_database, "msm_Link")
        msm_Weir = MU_database + "\mu_Geometry\msm_Weir"
        msm_Pump = MU_database + "\msm_Pump"
        # net_types = {"Regnvand":2, "Spildvand":1, u"Fællesvand":3}
        
        # for net_type in net_types.keys():
            # addLayer(os.path.dirname(os.path.realpath(__file__)) + ur"\Data\ExportToCAD\",
                     # msm_Node, group=empty_group_layer)
        arcpy.SetProgressorLabel("Copying msm_Node")
        msm_Node_z = arcpy.CreateFeatureclass_management(arcpy.env.scratchWorkspace,
                                                         os.path.basename(arcpy.Describe(msm_Node).catalogPath),
                                                         "POINT", template=msm_Node, has_z="ENABLED")[0]

        arcpy.management.Append(msm_Node, msm_Node_z)

        arcpy.SetProgressor("step", "Setting Z Coordinate of msm_Node", 0, int(arcpy.GetCount_management(msm_Node).getOutput(0)), 1)
        with arcpy.da.UpdateCursor(msm_Node_z, ["SHAPE@Z", "InvertLevel"],
                                   where_clause="InvertLevel IS NOT NULL") as cursor:
            for row_i, row in enumerate(cursor):
                arcpy.SetProgressorPosition(row_i)
                row[0] = row[1]
                cursor.updateRow(row)

        arcpy.SetProgressorLabel("Copying msm_Link")
        msm_Link_z = arcpy.CreateFeatureclass_management(arcpy.env.scratchWorkspace,
                                                         os.path.basename(arcpy.Describe(msm_Link).catalogPath),
                                                         "POLYLINE", template=msm_Link, has_z="ENABLED")[0]

        arcpy.management.Append(msm_Link, msm_Link_z)

        arcpy.SetProgressorLabel("Reading Invert Levels")
        nodes_invert_level = {row[0]: row[1] for row in arcpy.da.SearchCursor(msm_Node, ["MUID", "InvertLevel"])}

        arcpy.SetProgressorLabel("Networking MIKE Urban Database")
        network = networker.NetworkLinks(MU_database)

        arcpy.SetProgressor("step", "Setting Z Coordinate of msm_Link", 0, int(arcpy.GetCount_management(msm_Link).getOutput(0)), 1)
        with arcpy.da.UpdateCursor(msm_Link_z, ["SHAPE@", "MUID", "UpLevel", "DwLevel", "length"]) as cursor:
            for row_i, row in enumerate(cursor):
                try:
                    arcpy.SetProgressorPosition(row_i)
                    uplevel = nodes_invert_level[network.links[row[1]].fromnode] if not row[2] else row[2]
                    dwlevel = nodes_invert_level[network.links[row[1]].tonode] if not row[3] else row[3]
                    length = network.links[row[1]].length
                    slope = (uplevel - dwlevel) / length

                    linelist = []
                    for part in row[0]:
                        parts = []
                        for part_i, point in enumerate(part):
                            if part_i == 0:
                                z = uplevel
                            elif part_i == len(part):
                                z = dwlevel
                            else:
                                total_distance = 0
                                point_geometries = [arcpy.PointGeometry(p) for p in part]
                                for i in range(1, part_i + 1):
                                    total_distance += point_geometries[i - 1].distanceTo(point_geometries[i])
                                z = uplevel - total_distance * slope

                            parts.append(arcpy.Point(point.X, point.Y, z))
                        linelist.append(parts)

                    row[0] = arcpy.Polyline(arcpy.Array(linelist), arcpy.Describe(msm_Link_z).spatialReference, True)
                except Exception as e:
                    arcpy.AddError(traceback.format_exc())
                    arcpy.AddError(row)
                    raise(e)

        arcpy.SetProgressorLabel("Adding Layers")
        for manhole_layer in [u"Wastewater Manhole.lyr", u"Rainwater Manhole.lyr", u"Combined Manhole.lyr"]:
            addLayer(os.path.dirname(os.path.realpath(__file__)) + ur"\Data\ExportToCAD\%s" % manhole_layer,
                     msm_Node_z, group=empty_group_layer, workspace_type = "FILEGDB_WORKSPACE")

        for pipe_layer in [u"Wastewater Pipe.lyr", "Rainwater Pipe.lyr", "Combined Pipe.lyr"]:
            addLayer(os.path.dirname(os.path.realpath(__file__)) + r"\Data\ExportToCAD\%s" % pipe_layer,
                     msm_Link_z, group=empty_group_layer, workspace_type = "FILEGDB_WORKSPACE")

        # for pipe_layer in [u"Wastewater Pipe.lyr", "Rainwater Pipe.lyr", "Combined Pipe.lyr"]:
        #     addLayer(os.path.dirname(os.path.realpath(__file__)) + r"\Data\ExportToCAD\%s" % pipe_layer,
        #              msm_Link, group=empty_group_layer)

        addLayer(os.path.dirname(os.path.realpath(__file__)) + r"\Data\ExportToCAD\Pump.lyr",
                 msm_Pump, group=empty_group_layer)
        addLayer(os.path.dirname(os.path.realpath(__file__)) + r"\Data\ExportToCAD\CSO.lyr",
                 msm_Weir, group=empty_group_layer)

        # for link in arcpy.da.SearchCursor(msm_Link, ["MUID", "UpLevel", "DwLevel", "SHAPE@"], where_clause = "UpLevel IS NOT NULL OR DwLevel IS NOT NULL"):
        #     for row in cursor:
        #         if row[1] is not None:


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
            displayName="Output dwg file",
            name="dgn_file",
            datatype="File",
            parameterType="Required",
            direction="Output")
        dgn_file.filter.list = ["dwg"]
        
        label_scale = arcpy.Parameter(
            displayName="Label Scale",
            name="label_scale",
            datatype="GPLong",
            parameterType="Required",
            direction="Output")
        label_scale.value = 500
        
        

        parameters = [MU_database, dgn_file, label_scale]

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
        label_scale = parameters[2].Value

        msm_Node = os.path.join(MU_database, "msm_Node")

        arcpy.env.overwriteOutput = True

        mxd = arcpy.mapping.MapDocument("CURRENT")
        df = arcpy.mapping.ListDataFrames(mxd)[0]
        df.scale = label_scale

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
            "anno", "_", label_scale, generate_unplaced_annotation="NOT_GENERATE_UNPLACED_ANNOTATION")

        arcpy.env.workspace = arcpy.env.scratchWorkspace
        anno_classes = [os.path.join(arcpy.env.scratchWorkspace, fc) for fc in arcpy.ListFeatureClasses(feature_type = "Annotation")]
        feature_layers = [layer.longName for layer in arcpy.mapping.ListLayers(mxd, "", df) if not layer.isGroupLayer and layer.isFeatureLayer and layer.visible]
        layers = anno_classes + feature_layers
        arcpy.ExportCAD_conversion(anno_classes + feature_layers, Output_Type = "DWG_R2010", Output_File = dgn_file,
                                    Seed_File = os.path.dirname(os.path.realpath(__file__)) + r"\Data\ExportToCAD\Seedfile.dwg")
        return