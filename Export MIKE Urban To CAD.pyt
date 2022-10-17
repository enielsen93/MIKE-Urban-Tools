# -*- coding: utf-8 -*-

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
        self.tools = [DisplayMikeUrbanAsCAD, ExportToCAD, ExportToDUModelBuilder]

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

        draw_3d = arcpy.Parameter(
            displayName="Draw in 3D",
            name="draw_3d",
            datatype="Boolean",
            parameterType="Optional",
            direction="Input")
        draw_3d.value = True

        separate_diameter = arcpy.Parameter(
            displayName="Separate pipe dimension and material in CAD Levels",
            name="separate_diameter",
            datatype="Boolean",
            parameterType="Optional",
            direction="Input")
        separate_diameter.value = True

        extent_feature = arcpy.Parameter(
            displayName="Crop data to Polygon",
            name="extent_feature",
            datatype="GPFeatureLayer",
            parameterType="Optional",
            category="Additonal Settings",
            direction="Input")
        extent_feature.filter.list = ["Polygon"]

        parameters = [MU_database, label_scale, draw_3d, separate_diameter, extent_feature]

        return parameters

    def isLicensed(self):  # optional
        return True

    def updateParameters(self, parameters):  # optional
        return

    def updateMessages(self, parameters):  # optional

        return

    def execute(self, parameters, messages):
        MU_database = parameters[0].ValueAsText
        label_scale = parameters[1].Value
        draw_3d = parameters[2].Value
        separate_diameter = parameters[3].Value
        extent_feature = parameters[4].Value

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

        arcpy.CopyFeatures_management(msm_Node, os.path.join(arcpy.env.scratchWorkspace,
                                                                        os.path.basename(
                                                                            arcpy.Describe(msm_Node).catalogPath)))[0]
        msm_Node = os.path.join(arcpy.env.scratchWorkspace, os.path.join(os.path.basename(
                                                                            arcpy.Describe(msm_Node).catalogPath)))
                                                                            
        arcpy.CopyFeatures_management(msm_Link, os.path.join(arcpy.env.scratchWorkspace,
                                                                        os.path.basename(
                                                                            arcpy.Describe(msm_Link).catalogPath)))[0]
        msm_Link = os.path.join(arcpy.env.scratchWorkspace, os.path.join(os.path.basename(
                                                                            arcpy.Describe(msm_Link).catalogPath)))

        if extent_feature:
            arcpy.SetProgressorLabel("Clipping Features")
            extent_shapes = [row[0] for row in arcpy.da.SearchCursor(extent_feature, ["SHAPE@"])]
            with arcpy.da.UpdateCursor(msm_Node, "SHAPE@") as cursor:
                for row in cursor:
                    touches = False
                    for extent_shape in extent_shapes:
                        if row[0].within(extent_shape):
                            touches = True
                    if not touches:
                        cursor.deleteRow()

            with arcpy.da.UpdateCursor(msm_Link, "SHAPE@") as cursor:
                for row in cursor:
                    touches = False
                    for extent_shape in extent_shapes:
                        if row[0].within(extent_shape):
                            touches = True
                    if not touches:
                        cursor.deleteRow()


        if separate_diameter:
            arcpy.SetProgressorLabel("Filtering msm_Node and msm_Link by polygon")
            arcpy.management.AddField(msm_Link, "Layer", "TEXT")

            diameters = {0.1024: 0.11, 0.149: 0.16, 0.188: 0.2, 0.233: 0.25, 0.276: 0.3, 0.392: 0.4, 0.493: 0.5,
                         0.588: 0.6,
                         0.781: 0.8, 0.885: 0.9, 0.985: 1, 1.085: 1.1, 1.185: 1.2, 1.285: 1.3, 1.385: 1.4,
                         1.485: 1.5,
                         1.585: 1.6}
            diameters_by_index = [outer_diameter for outer_diameter in diameters.values()]

            def pipe_layer(diameter, materialid, typeno, width, height):
                label = ""
                diameter = float(diameter) if diameter else 0
                material = materialid.lower() if materialid else ""
                if "concrete" in material or "beton" in material:
                    materialAbb = "bt"
                elif "plast" in material:
                    materialAbb = "pl"
                    if diameter in diameters:
                        diameter = diameters[diameter]
                    else:
                        dist = [abs(inner_diameter - diameter) for inner_diameter in diameters]
                        diameter = diameters_by_index[dist.index(min(dist))]
                else:
                    materialAbb = ""

                if typeno == 'Rectangular' or typeno == '3':
                    label += "%dx%d" % (float(width) * 1e3, float(height) * 1e3)
                elif typeno == 'CRS' or typeno == '2':
                    label += "CRS"
                else:
                    label += "%d" % (diameter * 1000)

                label += materialAbb
                return label

            with arcpy.da.UpdateCursor(msm_Link, ["MUID", "Diameter", "MaterialID", "Layer", "TypeNo", "Width", "Height"]) as cursor:
                for row_i, row in enumerate(cursor):
                    arcpy.SetProgressorPosition(row_i)
                    row[3] = pipe_layer(row[1], row[2], row[4], row[5], row[6])
                    cursor.updateRow(row)

        if draw_3d:
            arcpy.SetProgressorLabel("Copying msm_Node")
            msm_Node_z = arcpy.CreateFeatureclass_management(arcpy.env.scratchWorkspace,
                                                             os.path.basename(arcpy.Describe(msm_Node).catalogPath) + "_z",
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
                                                             os.path.basename(arcpy.Describe(msm_Link).catalogPath) + "_z",
                                                             "POLYLINE", template=msm_Link, has_z="ENABLED")[0]

            arcpy.management.Append(msm_Link, msm_Link_z)

            arcpy.SetProgressorLabel("Reading Invert Levels")
            nodes_invert_level = {row[0]: row[1] for row in arcpy.da.SearchCursor(os.path.join(MU_database, "msm_Node"), ["MUID", "InvertLevel"])}

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
                                elif part_i == len(part)-1:
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
                        cursor.updateRow(row)
                    except Exception as e:
                        arcpy.AddError(traceback.format_exc())
                        arcpy.AddError(row)
                        raise(e)
        else:
            msm_Node_z = msm_Node
            msm_Link_z = msm_Link


        arcpy.SetProgressorLabel("Adding Layers")
        for manhole_layer in [u"Wastewater Manhole.lyr", u"Rainwater Manhole.lyr", u"Combined Manhole.lyr"]:
            addLayer(os.path.dirname(os.path.realpath(__file__)) + r"\Data\ExportToCAD\%s" % manhole_layer,
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
        dgn_file.filter.list = ["dwg", "dgn"]
        
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
        
class ExportToDUModelBuilder(object):
    def __init__(self):
        self.label = "Export MIKE Urban Model to D&U Model Builder"
        self.description = "Export MIKE Urban Model to D&U Model Builder"
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
            
        extent_feature = arcpy.Parameter(
            displayName="Crop data to Polygon",
            name="extent_feature",
            datatype="GPFeatureLayer",
            parameterType="Optional",
            category="Additonal Settings",
            direction="Input")
        extent_feature.filter.list = ["Polygon"]

        parameters = [MU_database, extent_feature]

        return parameters

    def isLicensed(self):  # optional
        return True

    def updateParameters(self, parameters):  # optional
        return

    def updateMessages(self, parameters):  # optional

        return

    def execute(self, parameters, messages):
        MU_database = parameters[0].ValueAsText
        extent_feature = parameters[1].Value

        mxd = arcpy.mapping.MapDocument("CURRENT")
        df = arcpy.mapping.ListDataFrames(mxd)[0]

        empty_group_mapped = arcpy.mapping.Layer(os.path.dirname(os.path.realpath(__file__)) + r"\Data\EmptyGroup.lyr")
        empty_group = arcpy.mapping.AddLayer(df, empty_group_mapped, "TOP")
        empty_group_layer = arcpy.mapping.ListLayers(mxd, "Empty Group", df)[0]
        empty_group_layer.name = os.path.splitext(os.path.basename(MU_database))[0]

        show_depth = True

        def addLayer(layer_source, source, group = None, workspace_type = "ACCESS_WORKSPACE", new_name = None, definition_query = None):
            if ".sqlite" in source:
                source_layer = arcpy.mapping.Layer(source)
                
                if group:
                    arcpy.mapping.AddLayerToGroup(df, group, source_layer, "BOTTOM")
                else:
                    arcpy.mapping.AddLayer(df, source_layer, "BOTTOM")
                update_layer = arcpy.mapping.ListLayers(mxd, source_layer.name, df)[0]
                
                layer_source_mike_plus = layer_source.replace("MOUSE", "MIKE+") if "MOUSE" in layer_source and os.path.exists(layer_source.replace("MOUSE", "MIKE+")) else None
                layer_source = layer_source_mike_plus if layer_source_mike_plus else layer_source
                layer = arcpy.mapping.Layer(layer_source)
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
                layer = arcpy.mapping.Layer(layer_source)
                if group:
                    arcpy.mapping.AddLayerToGroup(df, group, layer, "BOTTOM")
                else:
                    arcpy.mapping.AddLayer(df, layer, "BOTTOM")
                update_layer2 = arcpy.mapping.ListLayers(mxd, layer.name, df)[0]
                if definition_query:
                    update_layer2.definitionQuery = definition_query
                if new_name:
                    update_layer2.name = new_name
                update_layer2.replaceDataSource(unicode(os.path.dirname(source.replace(r"\mu_Geometry",""))), workspace_type, unicode(os.path.basename(source)))
                
            # if "msm_Node" in source:
                # for label_class in update_layer2.labelClasses:
                    # if show_depth:
                        # label_class.expression = label_class.expression.replace("return labelstr", 'if [GroundLevel] and [InvertLevel]: labelstr += "\\nD:%1.2f" % ( convertToFloat([GroundLevel]) - convertToFloat([InvertLevel]) )\r\n  return labelstr')

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
        
        arcpy.CopyFeatures_management(msm_Node, os.path.join(arcpy.env.scratchWorkspace,
                                                                        os.path.basename(
                                                                            arcpy.Describe(msm_Node).catalogPath)))[0]
        msm_Node = os.path.join(arcpy.env.scratchWorkspace, os.path.join(os.path.basename(
                                                                            arcpy.Describe(msm_Node).catalogPath)))
                                                                            
        arcpy.CopyFeatures_management(msm_Link, os.path.join(arcpy.env.scratchWorkspace,
                                                                        os.path.basename(
                                                                            arcpy.Describe(msm_Link).catalogPath)))[0]
        msm_Link = os.path.join(arcpy.env.scratchWorkspace, os.path.join(os.path.basename(
                                                                            arcpy.Describe(msm_Link).catalogPath)))

        if extent_feature:
            arcpy.SetProgressorLabel("Clipping Features")
            extent_shapes = [row[0] for row in arcpy.da.SearchCursor(extent_feature, ["SHAPE@"])]
            with arcpy.da.UpdateCursor(msm_Node, "SHAPE@") as cursor:
                for row in cursor:
                    touches = False
                    for extent_shape in extent_shapes:
                        if row[0].within(extent_shape):
                            touches = True
                    if not touches:
                        cursor.deleteRow()

            with arcpy.da.UpdateCursor(msm_Link, "SHAPE@") as cursor:
                for row in cursor:
                    touches = False
                    for extent_shape in extent_shapes:
                        if row[0].intersect(extent_shape, 2):
                            touches = True
                    if not touches:
                        cursor.deleteRow()
        
        arcpy.management.AddField(msm_Node, "Label", "TEXT")
        arcpy.management.AddField(msm_Node, "X_Coordinate", "TEXT")
        arcpy.management.AddField(msm_Node, "Y_Coordinate", "TEXT")

        draw_3d = True
        if draw_3d:
            arcpy.SetProgressorLabel("Copying msm_Node")
            msm_Node_z = arcpy.CreateFeatureclass_management(arcpy.env.scratchWorkspace,
                                                             os.path.basename(arcpy.Describe(msm_Node).catalogPath) + "_z",
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
                                                             os.path.basename(arcpy.Describe(msm_Link).catalogPath) + "_z",
                                                             "POLYLINE", template=msm_Link, has_z="ENABLED")[0]

            arcpy.management.Append(msm_Link, msm_Link_z)

            arcpy.SetProgressorLabel("Reading Invert Levels")
            nodes_invert_level = {row[0]: row[1] for row in arcpy.da.SearchCursor(os.path.join(MU_database, "msm_Node"), ["MUID", "InvertLevel"])}

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
                                elif part_i == len(part)-1:
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
                        cursor.updateRow(row)
                    except Exception as e:
                        arcpy.AddError(traceback.format_exc())
                        arcpy.AddError(row)
                        raise(e)

            msm_Node = msm_Node_z
            msm_Link = msm_Link_z

        
        with arcpy.da.UpdateCursor(msm_Node, ["Label", "X_Coordinate", "Y_Coordinate", "MUID", "SHAPE@X", "SHAPE@Y"]) as cursor:
            for row in cursor:
                row[0] = row[3]
                row[1] = row[4]
                row[2] = row[5]
                cursor.updateRow(row)
        
        arcpy.management.AddField(msm_Link, "Label", "TEXT")
        arcpy.management.AddField(msm_Link, "Descript", "TEXT")
        arcpy.management.AddField(msm_Link, "Start_Node", "TEXT")
        arcpy.management.AddField(msm_Link, "Stop_Node", "TEXT")
        arcpy.management.AddField(msm_Link, "Invert_Start_m", "TEXT")
        arcpy.management.AddField(msm_Link, "Invert_Stop_m", "TEXT")
        arcpy.management.AddField(msm_Link, "WallThick", "DOUBLE", 8, 4)

        diameters = {0.1024: 0.11, 0.149: 0.16, 0.188: 0.2, 0.233: 0.25, 0.276: 0.3, 0.392: 0.4, 0.493: 0.5,
                     0.588: 0.6,
                     0.781: 0.8, 0.885: 0.9, 0.985: 1, 1.085: 1.1, 1.185: 1.2, 1.285: 1.3, 1.385: 1.4,
                     1.485: 1.5,
                     1.585: 1.6}
        diameters_by_index = [outer_diameter for outer_diameter in diameters.values()]

        def pipe_layer(diameter, materialid, typeno, width, height):
            label = u""
            diameter = float(diameter) if diameter else 0
            material = materialid.lower() if materialid else ""
            if "concrete" in material or "beton" in material:
                materialAbb = "bt"
            elif "plast" in material:
                materialAbb = "pl"
                if diameter in diameters:
                    diameter = diameters[diameter]
                else:
                    dist = [abs(inner_diameter - diameter) for inner_diameter in diameters]
                    diameter = diameters_by_index[dist.index(min(dist))]
            else:
                materialAbb = ""

            if typeno == 'Rectangular' or typeno == '3':
                label += "%dx%d" % (float(width) * 1e3, float(height) * 1e3)
            elif typeno == 'CRS' or typeno == '2':
                label += "CRS"
            else:
                label += "%d" % (diameter * 1000)

            label += materialAbb
            return label

        class Pipe_type:
            def __init__(self, diameter, wallthickness):
                self.diameter = diameter
                self.wallthickness = wallthickness

        pipe_catalogue = {}
        with arcpy.da.SearchCursor(os.path.dirname(os.path.realpath(__file__)) + ur"\Data\ExportToCAD\Pipe Catalogue.dbf", ["Pipe_type", "Diameter", "WallThi"]) as cursor:
            for row in cursor:
                pipe_catalogue[row[0]] = Pipe_type(row[1], row[2])


        with arcpy.da.UpdateCursor(msm_Link, ["MUID", "Diameter", "MaterialID", "Descript", "TypeNo", "Width", "Height", "Label", "WallThick"]) as cursor:
            for row_i, row in enumerate(cursor):
                arcpy.SetProgressorPosition(row_i)
                row[3] = pipe_layer(row[1], row[2], row[4], row[5], row[6])
                row[7] = "l" + row[0]
                if row[3] in pipe_catalogue:
                    row[1] = pipe_catalogue[row[3]].diameter
                    row[8] = pipe_catalogue[row[3]].wallthickness
                else:
                    row[1] = row[1]*1000
                cursor.updateRow(row)

        arcpy.SetProgressorLabel("Reading Invert Levels")
        nodes_invert_level = {row[0]: row[1] for row in arcpy.da.SearchCursor(os.path.join(MU_database, "msm_Node"), ["MUID", "InvertLevel"])}

        arcpy.SetProgressorLabel("Networking MIKE Urban Database")
        network = networker.NetworkLinks(MU_database)

        with arcpy.da.UpdateCursor(msm_Link, ["MUID", "UpLevel", "DwLevel", "length", "Start_Node", "Stop_Node", "Invert_Start_m", "Invert_Stop_m"]) as cursor:
            for row_i, row in enumerate(cursor):
                arcpy.SetProgressorPosition(row_i)
                row[3] = network.links[row[0]].length
                row[4] = network.links[row[0]].fromnode
                row[5] = network.links[row[0]].tonode
                row[6] = nodes_invert_level[network.links[row[0]].fromnode] if not row[1] else row[1]
                row[7] = nodes_invert_level[network.links[row[0]].tonode] if not row[2] else row[2]           
                cursor.updateRow(row)
        
        msm_Node_req_fields = ["Label", "X_Coordinate", "Y_Coordinate", "Diameter", "InvertLevel", "GroundLevel", "NetTypeNo", "Length", "SHAPE", "OBJECTID", "SHAPE_Length"]
        arcpy.DeleteField_management(msm_Node, [field.name for field in arcpy.ListFields(msm_Node) if field.name not in msm_Node_req_fields])
        
        msm_Link_req_fields = ["Label", "Start_Node", "Stop_Node", "Diameter", "Descript", "NetTypeNo", "Invert_Start_m", "Length", "Invert_Stop_m", "WallThick", "SHAPE", "OBJECTID", "SHAPE_Length"]
        arcpy.DeleteField_management(msm_Link, [field.name for field in arcpy.ListFields(msm_Link) if field.name not in msm_Link_req_fields])

        arcpy.SetProgressorLabel("Adding Layers")
        # arcpy.AddMessage(msm_Node)
        # layer = arcpy.mapping.Layer(msm_Node)    
        # arcpy.mapping.AddLayerToGroup(df, empty_group_layer, layer, "BOTTOM")
        # layer = arcpy.mapping.Layer(msm_Link)    
        # arcpy.mapping.AddLayerToGroup(df, empty_group_layer, layer, "BOTTOM")
        for manhole_layer in [u"Wastewater Manhole.lyr", u"Rainwater Manhole.lyr", u"Combined Manhole.lyr"]:
            addLayer(os.path.dirname(os.path.realpath(__file__)) + ur"\Data\ExportToCAD\%s" % manhole_layer,
                     msm_Node, group=empty_group_layer, workspace_type = "FILEGDB_WORKSPACE")

        for pipe_layer in [u"Wastewater Pipe.lyr", "Rainwater Pipe.lyr", "Combined Pipe.lyr"]:
            addLayer(os.path.dirname(os.path.realpath(__file__)) + r"\Data\ExportToCAD\%s" % pipe_layer,
                     msm_Link, group=empty_group_layer, workspace_type = "FILEGDB_WORKSPACE")

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