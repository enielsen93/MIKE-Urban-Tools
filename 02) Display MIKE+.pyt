# -*- coding: utf-8 -*-
# Created by Emil Nielsen
# Contact: 
# E-mail: enielsen93@hotmail.com

import arcpy
if "mapping" in dir(arcpy):
    arcgis_pro = False
    import arcpy.mapping as arcpymapping
    from arcpy.mapping import MapDocument as arcpyMapDocument
else:
    arcgis_pro = True
    import arcpy.mp as arcpymapping
    from arcpy.mp import ArcGISProject as arcpyMapDocument
import numpy as np
import csv
import os
import traceback
import re
import scipy.integrate
from collections import namedtuple
import warnings
import shutil

# Cumtrapz changed name in scipy, so this handles this
try:
    # Try the old name first (for SciPy <1.14)
    from scipy.integrate import cumtrapz
except ImportError:
    # For SciPy >=1.14, use the new name
    from scipy.integrate import cumulative_trapezoid as cumtrapz


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

def addLayer(layer_source, source, group=None, workspace_type="ACCESS_WORKSPACE", new_name=None,
             definition_query=None):
    # updated 2025-06-18
    if arcgis_pro:
        mxd = arcpy.mp.ArcGISProject("CURRENT")
        df = mxd.listMaps()[0]
    else:
        mxd = arcpy.mapping.MapDocument("CURRENT")
        df = arcpy.mapping.ListDataFrames(mxd)[0]

    if arcgis_pro and not ".lyrx" in layer_source and os.path.exists(layer_source.replace(".lyr", ".lyrx")):
        layer_source = layer_source.replace(".lyr", ".lyrx")

    if source and ".sqlite" in source:
        source_layer = arcpymapping.LayerFile(layer_source) if arcgis_pro else arcpy.mapping.Layer(source)
        if group:
            if arcgis_pro:
                update_layer = df.addLayerToGroup(group, source_layer, "BOTTOM")
            else:
                arcpymapping.AddLayerToGroup(df, group, source_layer, "BOTTOM")
        else:
            if arcgis_pro:
                update_layer = df.addLayer(source_layer, "TOP")
            else:
                arcpymapping.AddLayer(df, source_layer, "TOP")

        if not arcgis_pro: update_layer = df.listLayers(mxd, source_layer.name, df)[0] if arcgis_pro else \
            arcpy.mapping.ListLayers(mxd, source_layer.name, df)[0]

        if arcgis_pro:
            new_connection_properties = update_layer.connectionProperties
            new_connection_properties["workspace_factory"] = 'Sql'
            new_connection_properties["connection_info"]["database"] = os.path.dirname(source)
            update_layer.updateConnectionProperties()
        else:
            if ".sqlite" in source:
                layer = arcpymapping.Layer(layer_source)
                update_layer.visible = layer.visible
                update_layer.labelClasses = layer.labelClasses
                update_layer.showLabels = layer.showLabels
                update_layer.name = layer.name
                update_layer.definitionQuery = definition_query

                try:
                    arcpymapping.UpdateLayer(df, update_layer, layer, symbology_only=True)
                except Exception as e:
                    arcpy.AddWarning(source)
                    pass
            else:
                update_layer.replaceDataSource(unicode(os.path.dirname(source.replace(r"\mu_Geometry", ""))),
                                               workspace_type, os.path.basename(source))

        try:
            arcpymapping.UpdateLayer(df, update_layer, layer, symbology_only=True)
        except Exception as e:
            arcpy.AddWarning(source)
            pass
    else:
        layer = arcpymapping.LayerFile(layer_source) if arcgis_pro else arcpymapping.Layer(layer_source)
        if group:
            if arcgis_pro:
                df.addLayerToGroup(group, layer, "BOTTOM")
            else:
                arcpymapping.AddLayerToGroup(df, group, layer, "BOTTOM")
        else:
            if arcgis_pro:
                df.addLayer(layer, "TOP")
            else:
                arcpymapping.AddLayer(df, layer, "TOP")
        update_layer = df.listLayers(layer.listLayers()[0].name)[0] if arcgis_pro else \
            arcpymapping.ListLayers(mxd, layer.name, df)[0]
        if definition_query:
            update_layer.definitionQuery = definition_query
        if new_name:
            update_layer.name = new_name

        if source:
            if arcgis_pro:
                # CONFIRMED WORKING FOR SHAPEFILE -> FILEGDB
                import copy
                cp = copy.deepcopy(update_layer.connectionProperties)
                if workspace_type == "FILEGDB_WORKSPACE":
                    workspace_type = "File Geodatabase"
                cp["connection_info"]['database'] = os.path.dirname(
                    source.replace(r"\mu_Geometry", ""))  # output db path+name
                cp['dataset'] = os.path.basename(source)
                cp['workspace_factory'] = workspace_type
                update_layer.updateConnectionProperties(update_layer.connectionProperties, cp)
            else:
                update_layer.replaceDataSource(unicode(os.path.dirname(source.replace(r"\mu_Geometry", ""))),
                                               workspace_type, os.path.basename(source))
    return update_layer

from arcpy import env

class Toolbox(object):
    def __init__(self):
        self.label =  "Display MIKE+"
        self.alias  = "Display MIKE+"

        # List of tool classes associated with this toolbox
        if arcgis_pro:
            self.tools = [CopyMuppTemplate, DisplaySqlitePro]
        else:
            self.tools = [DisplaySqliteStep1, DisplaySqliteStep2, CopyMuppTemplate]

class DisplaySqliteStep1(object):
    def __init__(self):
        self.label = "1) Display MIKE+ - Step 1"
        self.description = ("1) Display MIKE+ - Step 1")
        self.canRunInBackground = False

    def getParameterInfo(self):
        # Define parameter definitions

        # Input Features parameter
        sqlite_database = arcpy.Parameter(
            displayName="Sqlite database",
            name="database",
            datatype="DEFile",
            parameterType="Required",
            direction="Input")
        sqlite_database.filter.list = ["sqlite"]

        join_catchments = arcpy.Parameter(
            displayName="Join catchments with imperviousness from msm_HModA table",
            name="join_catchments",
            datatype="Boolean",
            parameterType="optional",
            direction="Output")
        join_catchments.value = False

        features_to_display = arcpy.Parameter(
            displayName="Display the following features:",
            name="features_to_display",
            datatype="GPString",
            parameterType="Optional",
            multiValue=True,
            category="Additional Settings",
            direction="Input")
        features_to_display.filter.type = "ValueList"
        features_to_display.filter.list = ["Manholes", "Pipes", "Basins", "Weirs", "Orifices", "Pumps", "Network Loads",
                                           "Boundary Water Levels", "Catchment Connections", "Catchments", "Control Actions",
                                           "Annotations"]
        features_to_display.value = ["Manholes", "Pipes", "Weirs", "Orifices", "Pumps", "Network Loads",
                                     "Boundary Water Levels", "Catchment Connections", "Catchments"]

        sql_query = arcpy.Parameter(
            displayName="Set as Definition Query for layers",
            name="sql_query",
            datatype="GPString",
            category="Additional Settings",
            parameterType="optional",
            direction="Output")

        copy_and_show_delete = arcpy.Parameter(
            displayName="Duplicate .sqlite and show duplicate (!delete!)",
            name="copy_and_show_delete",
            datatype="Boolean",
            category="Additional Settings",
            parameterType="optional",
            direction="Output")
        copy_and_show_delete.value = False

        parameters = [sqlite_database, join_catchments, features_to_display, sql_query, copy_and_show_delete]

        return parameters

    def isLicensed(self):  # optional
        return True

    def updateParameters(self, parameters):  # optional
        # MU_database = parameters[0].ValueAsText
        if parameters[0].ValueAsText and '"' in parameters[0].ValueAsText:
            parameters[0].Value = parameters[0].ValueAsText.replace('"','')
        return

    def updateMessages(self, parameters):  # optional

        return

    def execute(self, parameters, messages):
        MU_database = parameters[0].ValueAsText
        join_catchments = parameters[1].Value
        features_to_display = [feature_name.replace("'", "").replace('"', '') for feature_name in
                               parameters[2].ValueAsText.split(";")]
        sql_query = parameters[3].Value
        copy_and_show_delete = parameters[4].Value

        if copy_and_show_delete:
            new_file_path = os.path.join(*os.path.split(MU_database)[:-1] + (
            os.path.splitext(os.path.basename(MU_database))[0] + "!delete!" + os.path.splitext(MU_database)[1],))

            if os.path.exists(new_file_path):
                try:
                    os.remove(new_file_path)  # Attempt to delete the existing file
                except Exception as e:
                    raise IOError("The file '{}' is locked and cannot be deleted: {}".format(new_file_path, str(e)))

            try:
                shutil.copy2(MU_database, new_file_path)  # Duplicate the file
                print("File duplicated successfully: {}".format(new_file_path))
            except Exception as e:
                raise IOError("Failed to duplicate the file: {}".format(str(e)))
            MU_database = new_file_path

        msm_Node = MU_database + "\main.msm_Node"
        msm_Link = MU_database + "\main.msm_Link"
        # arcpy.AddMessage(MU_database)
        ms_Catchment = MU_database + "\ms_Catchment" if not ".sqlite" in MU_database else MU_database + "\main.msm_Catchment"
        msm_CatchCon = MU_database + "\msm_CatchConLink" if not ".sqlite" in MU_database else MU_database + "\main.msm_CatchCon"
        msm_Weir = MU_database + "\msm_Weir" if not ".sqlite" in MU_database else MU_database + "\main.msm_Weir"
        msm_Orifice = MU_database + "\main.msm_Orifice"
        msm_BBoundary = MU_database + "\main.msm_BBoundary"
        msm_Pump = MU_database + "\main.msm_Pump"
        msm_BItem = MU_database + "\main.msm_BItem"
        msm_PasReg = MU_database + "\main.msm_PasReg"
        ms_TabD = MU_database + "\main.ms_TabD"
        msm_RTC = MU_database + "\msm_RTC"
        mxd = arcpyMapDocument("CURRENT")
        df = mxd.listMaps()[0] if arcgis_pro else arcpymapping.ListDataFrames(mxd)[0]

        is_sqlite_database = True if ".sqlite" in MU_database else False

        import time
        start_time = time.time()

        def printStepAndTime(txt):
            arcpy.AddMessage("%s - %d" % (txt, time.time() - start_time))

        import subprocess

        def copy2clip(txt):
            cmd = 'echo ' + txt.strip() + '|clip'
            return subprocess.check_call(cmd, shell=True)
        clipboard_txt = []

        if "Manholes" in features_to_display:
            clipboard_txt.append(msm_Node)

        if "Pipes" in features_to_display:
            clipboard_txt.append(msm_Link)

        if "Weirs" in features_to_display:
            # arcpy.AddMessage(weirs)
            # if len([row[0] for row in arcpy.da.SearchCursor(weirs,["MUID"])])>0:
            clipboard_txt.append(msm_Weir)

        if "Orifices" in features_to_display:
            # arcpy.AddMessage(weirs)
            # if len([row[0] for row in arcpy.da.SearchCursor(weirs,["MUID"])])>0:
            clipboard_txt.append(msm_Orifice)

        if "Pumps" in features_to_display:
            clipboard_txt.append(msm_Pump)

        printStepAndTime("Adding Empty Group")
        empty_group_mapped = arcpymapping.LayerFile(os.path.dirname(
            os.path.realpath(__file__)) + r"\Data\EmptyGroup.lyr") if arcgis_pro else arcpy.mapping.Layer(
            os.path.dirname(os.path.realpath(__file__)) + r"\Data\EmptyGroup.lyr")
        empty_group = df.addLayer(empty_group_mapped) if arcgis_pro else arcpymapping.AddLayer(df, empty_group_mapped,
                                                                                               "TOP")
        empty_group_layer = df.listLayers('Empty Group')[0] if arcgis_pro else \
        arcpymapping.ListLayers(mxd, "Empty Group", df)[0]
        empty_group_layer.name = os.path.splitext(os.path.basename(MU_database))[0]

        MIKE_folder = os.path.join(os.path.dirname(arcpy.env.scratchGDB), "MIKE URBAN")
        if not os.path.exists(MIKE_folder):
            os.mkdir(MIKE_folder)
        MIKE_gdb = os.path.join(MIKE_folder, empty_group_layer.name)
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
                MIKE_gdb = os.path.join(MIKE_folder, "%s_%d" % (empty_group_layer.name, dir_ext))
        arcpy.env.scratchWorkspace = MIKE_gdb

        arcpy.env.addOutputsToMap = False
        # addLayer = arcpymapping.Layer(os.path.dirname(os.path.realpath(__file__)) + ("\Data\MOUSE Manholes with LossPar.lyr" if show_loss_par else "\Data\MOUSE Manholes.lyr"))

        templates_folder = os.path.dirname(os.path.realpath(
            __file__)) + "\Data\Templates\MIKE Plus" if arcgis_pro and is_sqlite_database else os.path.dirname(
            os.path.realpath(__file__)) + "\Data"
        templates_extension = ".lyrx" if arcgis_pro and is_sqlite_database else ".lyr"

        def addLayer(layer_source, source, group=None, workspace_type="ACCESS_WORKSPACE", new_name=None,
                     definition_query=None):
            if ".sqlite" in source:
                source_layer = arcpymapping.LayerFile(layer_source) if arcgis_pro else arcpy.mapping.Layer(source)
                # if not "objectid" in [field.name.lower() for field in arcpy.ListFields(source)]:
                #     import sqlite3
                #     with sqlite3.connect(MU_database) as connection:
                #         update_cursor = connection.cursor()
                #         sql_expression = """
                #         PRAGMA foreign_keys=off;
                #         BEGIN TRANSACTION;
                #
                #         ALTER TABLE %s RENAME TO delete_table;
                #
                #         CREATE TABLE %s
                #         (
                #           column1 datatype [ NULL | NOT NULL ],
                #           column2 datatype [ NULL | NOT NULL ],
                #           ...
                #           CONSTRAINT constraint_name UNIQUE (uc_col1, uc_col2, ... uc_col_n)
                #         );
                #
                #         INSERT INTO table_name SELECT * FROM old_table;
                #
                #         COMMIT;
                #
                #         PRAGMA foreign_keys=on;
                #         """
                #         try:
                #             update_cursor.execute("ALTER TABLE %s ADD COLUMN OBJECTID INTEGER" % os.path.basename(source))
                #             sql_expression = "CREATE INDEX OBJECTID ON %s(OBJECTID)" % os.path.basename(source)
                #             update_cursor.execute(sql_expression)
                #         except Exception as e:
                #             arcpy.AddMessage(source)
                #             raise(e)

                if group:
                    if arcgis_pro:
                        update_layer = df.addLayerToGroup(group, source_layer, "BOTTOM")
                    else:
                        arcpymapping.AddLayerToGroup(df, group, source_layer, "BOTTOM")
                else:
                    if arcgis_pro:
                        update_layer = df.addLayer(source_layer, "BOTTOM")
                    else:
                        arcpymapping.AddLayer(df, source_layer, "BOTTOM")

                if not arcgis_pro: update_layer = df.listLayers(mxd, source_layer.name, df)[0] if arcgis_pro else \
                arcpy.mapping.ListLayers(mxd, source_layer.name, df)[0]

                if arcgis_pro:
                    new_connection_properties = update_layer.connectionProperties
                    new_connection_properties["workspace_factory"] = 'Sql'
                    new_connection_properties["connection_info"]["database"] = os.path.dirname(source)
                    update_layer.updateConnectionProperties()
                else:
                    if ".sqlite" in source:
                        layer = arcpymapping.Layer(layer_source)
                        update_layer.visible = layer.visible
                        update_layer.labelClasses = layer.labelClasses
                        update_layer.showLabels = layer.showLabels
                        update_layer.name = layer.name
                        update_layer.definitionQuery = definition_query

                        try:
                            arcpymapping.UpdateLayer(df, update_layer, layer, symbology_only=True)
                        except Exception as e:
                            arcpy.AddWarning(source)
                            pass
                    else:
                        update_layer.replaceDataSource(unicode(os.path.dirname(source.replace(r"\mu_Geometry", ""))),
                                                       workspace_type, os.path.basename(source))

                # layer_source_mike_plus = layer_source.replace("MOUSE", "MIKE+") if "MOUSE" in layer_source and os.path.exists(layer_source.replace("MOUSE", "MIKE+")) else None
                # layer_source = layer_source_mike_plus if layer_source_mike_plus else layer_source
                # layer = arcpymapping.Layer(layer_source)
                # update_layer.visible = layer.visible
                # update_layer.labelClasses = layer.labelClasses
                # update_layer.showLabels = layer.showLabels
                # update_layer.name = layer.name
                # update_layer.definitionQuery = definition_query

                try:
                    arcpymapping.UpdateLayer(df, update_layer, layer, symbology_only=True)
                except Exception as e:
                    arcpy.AddWarning(source)
                    pass
            else:
                # arcpy.AddMessage(layer_source)
                layer = arcpymapping.LayerFile(layer_source) if arcgis_pro else arcpymapping.Layer(layer_source)
                if group:
                    if arcgis_pro:
                        df.addLayerToGroup(group, layer, "BOTTOM")
                    else:
                        arcpymapping.AddLayerToGroup(df, group, layer, "BOTTOM")
                else:
                    if arcgis_pro:
                        df.addLayer(layer, "BOTTOM")
                    else:
                        arcpymapping.AddLayer(df, layer, "BOTTOM")
                update_layer = df.listLayers(layer.listLayers()[0].name)[0] if arcgis_pro else \
                arcpymapping.ListLayers(mxd, layer.name, df)[0]
                if definition_query:
                    update_layer.definitionQuery = definition_query
                if new_name:
                    update_layer.name = new_name

                if arcgis_pro:
                    df.updateConnectionProperties(update_layer.connectionProperties['connection_info']['database'],
                                                  os.path.dirname(source.replace(r"\mu_Geometry", "")))
                else:
                    update_layer.replaceDataSource(unicode(os.path.dirname(source.replace(r"\mu_Geometry", ""))),
                                                   workspace_type, os.path.basename(source))

            # arcpy.AddMessage("Bob")
            if "msm_Node" in source:
                # arcpy.AddMessage("Bob")
                for label_class in (update_layer.listLabelClasses() if arcgis_pro else update_layer.labelClasses):
                    if not show_depth:
                        import re
                        arcpy.AddMessage(r'if \[GroundLevel\] and \[InvertLevel\]:.+\n')
                        label_class.expression = re.sub(r'if \[GroundLevel\] and \[InvertLevel\]:.+\n', "", label_class.expression)
#                         label_class.expression = label_class.expression.replace("return labelstr",
#                                                                                 'if [GroundLevel] and [InvertLevel]: labelstr += "\\nD:%1.2f" % ( convertToFloat([GroundLevel]) - convertToFloat([InvertLevel]) )\r\n  return labelstr')

        class Basin:
            def __init__(self, geometry_id):
                self.geometry_id = geometry_id or ""
                self.invert_level = None
                self.permanent_level = None

                self.value1 = []
                self.value3 = []

                # None means "derive critical level from geometry".
                self._critical_level = None

            @property
            def elevations(self):
                """Return basin elevations adjusted to the invert level."""
                if not self.value1:
                    return np.array([], dtype=float)

                elevations = np.asarray(self.value1, dtype=float)

                if self.invert_level is not None:
                    minimum = np.min(elevations)

                    if minimum < self.invert_level:
                        elevations = elevations + (
                                self.invert_level - minimum
                        )

                return elevations

            @property
            def critical_level(self):
                """
                Return the critical level.

                If a CriticalLevel was supplied from msm_Node, use that.
                Otherwise use the highest geometry elevation.
                """
                if self._critical_level is not None:
                    return self._critical_level

                if len(self.elevations) == 0:
                    return None

                return float(np.max(self.elevations))

            @critical_level.setter
            def critical_level(self, value):
                self._critical_level = value

            @property
            def max_area(self):
                """Return the maximum surface area of the basin."""
                if not self.value3:
                    return 0.0

                return float(np.max(self.value3))

            def _volume_curve(self):
                """
                Build the elevation-volume relationship.

                Returns
                -------
                elevations : numpy.ndarray
                    Elevation values.
                volumes : numpy.ndarray
                    Cumulative volume at each elevation.
                """
                elevations = self.elevations

                if len(elevations) == 0:
                    return np.array([], dtype=float), np.array([], dtype=float)

                areas = np.asarray(self.value3, dtype=float)

                if len(elevations) != len(areas):
                    raise ValueError(
                        "Number of elevations does not match number of surface areas."
                    )

                # Sort elevation/area pairs together.
                sort_index = np.argsort(elevations)
                sorted_elevations = elevations[sort_index]
                sorted_areas = areas[sort_index]

                critical_level = self.critical_level

                if critical_level is not None:
                    # Only include geometry below the critical level and then
                    # explicitly add the critical level itself.
                    mask = sorted_elevations < critical_level

                    curve_elevations = np.append(
                        sorted_elevations[mask],
                        critical_level
                    )

                    curve_areas = np.interp(
                        curve_elevations,
                        sorted_elevations,
                        sorted_areas
                    )
                else:
                    curve_elevations = sorted_elevations
                    curve_areas = sorted_areas

                if len(curve_elevations) == 1:
                    volumes = np.array([0.0])

                else:
                    # Cumulative trapezoidal integration.
                    #
                    # This avoids scipy.integrate.cumtrapz, which is deprecated.
                    volumes = np.concatenate((
                        [0.0],
                        np.cumsum(
                            (
                                    curve_areas[:-1] + curve_areas[1:]
                            ) / 2.0
                            * np.diff(curve_elevations)
                        )
                    ))

                return curve_elevations, volumes

            @property
            def max_volume(self):
                """Return the total volume up to the critical level."""
                elevations, volumes = self._volume_curve()

                if len(elevations) == 0:
                    return 0.0

                return float(volumes[-1])

            def get_volume(self, level):
                """Return basin volume at the specified water level."""
                elevations, volumes = self._volume_curve()

                if len(elevations) == 0:
                    return 0.0

                volume = float(np.interp(level, elevations, volumes))

                if self.permanent_level is not None:
                    permanent_volume = float(
                        np.interp(
                            self.permanent_level,
                            elevations,
                            volumes
                        )
                    )

                    volume -= permanent_volume

                return max(0.0, volume)

        if "Basins" in features_to_display:
            arcpy.SetProgressor(
                "default",
                "Calculating volume of basins"
            )
            printStepAndTime("Calculating volume of basins")

            # ------------------------------------------------------------------
            # Import basins
            # ------------------------------------------------------------------

            basins = {}

            with arcpy.da.SearchCursor(
                    msm_Node,
                    ["MUID", "GeometryID"],
                    where_clause="TypeNo = 2"
            ) as cursor:

                for muid, geometry_id in cursor:
                    basins[muid] = Basin(geometry_id)

            if basins:

                # Create a direct GeometryID -> Basin lookup.
                #
                # The old code searched through every basin for every ms_TabD
                # row, which was unnecessarily O(n²).
                basins_by_geometry = {
                    basin.geometry_id: basin
                    for basin in basins.values()
                }

                # ------------------------------------------------------------------
                # Import basin geometry
                # ------------------------------------------------------------------

                geometry_ids = list(basins_by_geometry)

                if geometry_ids:

                    # Build the SQL using ArcPy's field delimiter/SQL helper
                    # rather than manually constructing "IN ('...', '...')".
                    tab_id_field = arcpy.AddFieldDelimiters(
                        os.path.join(MU_database, "ms_TabD"),
                        "TabID"
                    )

                    geometry_id_sql = ",".join(
                        "'{}'".format(str(geometry_id).replace("'", "''"))
                        for geometry_id in geometry_ids
                    )

                    where_clause = "{} IN ({})".format(
                        tab_id_field,
                        geometry_id_sql
                    )

                    with arcpy.da.SearchCursor(
                            os.path.join(MU_database, "ms_TabD"),
                            ["TabID", "Value1", "Value3"],
                            where_clause=where_clause
                    ) as cursor:

                        for tab_id, elevation, surface_area in cursor:

                            basin = basins_by_geometry.get(tab_id)

                            if basin is None:
                                continue

                            if elevation is not None and surface_area is not None:
                                basin.value1.append(elevation)
                                basin.value3.append(surface_area)

                # ------------------------------------------------------------------
                # Create basin output
                # ------------------------------------------------------------------

                export_basins = getAvailableFilename(
                    arcpy.env.scratchGDB + r"\basins",
                    parent=MU_database
                )

                arcpy.Select_analysis(
                    msm_Node,
                    export_basins,
                    where_clause="TypeNo = 2"
                )

                arcpy.management.AlterField(
                    export_basins,
                    "Description",
                    field_length=500
                )

                arcpy.management.AddField(
                    export_basins,
                    "Volume",
                    "FLOAT"
                )

                arcpy.management.AddField(
                    export_basins,
                    "MaxArea",
                    "FLOAT"
                )

                # ------------------------------------------------------------------
                # Calculate basin volumes
                # ------------------------------------------------------------------

                cursor_fields = [
                    "MUID",
                    "Volume",
                    "CriticalLevel",
                    "GeometryID",
                    "Description",
                    "GroundLevel",
                    "InvertLevel",
                    "MaxArea",
                ]

                with arcpy.da.UpdateCursor(
                        export_basins,
                        cursor_fields
                ) as cursor:

                    for row in cursor:

                        muid = row[0]
                        basin = basins.get(muid)

                        if basin is None:
                            continue

                        try:
                            basin.invert_level = row[6]

                            # CriticalLevel from msm_Node overrides the
                            # geometry-derived critical level.
                            if row[2] is not None:
                                basin.critical_level = row[2]

                            if not basin.value1:
                                raise ValueError(
                                    "No geometry elevations found."
                                )

                            if not basin.value3:
                                raise ValueError(
                                    "No surface areas found."
                                )

                            # ------------------------------------------------------
                            # Calculate volume and maximum area
                            # ------------------------------------------------------

                            row[1] = basin.max_volume
                            row[7] = basin.max_area

                            # ------------------------------------------------------
                            # Build description
                            # ------------------------------------------------------

                            description_lines = []

                            # The old code used value1[0] here.
                            #
                            # Database row order is not guaranteed, so using the
                            # minimum elevation is both safer and what the
                            # calculation logically requires.
                            elevation_discrepancy = (
                                    basin.invert_level - min(basin.value1)
                            )

                            # Add volumes at the geometry elevations.
                            geometry_elevations = sorted(
                                elevation
                                for elevation in basin.value1
                                if elevation < basin.critical_level
                            )
                            for elevation in geometry_elevations:
                                adjusted_elevation = (
                                        elevation + elevation_discrepancy
                                )

                                volume = basin.get_volume(
                                    adjusted_elevation
                                )

                                description_lines.append(
                                    "%1.2f: %d m3"
                                    % (
                                        adjusted_elevation,
                                        volume
                                    )
                                )

                            # ------------------------------------------------------
                            # Add maximum volume
                            # ------------------------------------------------------

                            critical_level = basin.critical_level

                            if (
                                    critical_level is not None
                                    and critical_level < row[5]
                            ):
                                maximum_level = critical_level
                                maximum_volume = basin.get_volume(
                                    critical_level
                                )

                            else:
                                maximum_level = row[5]
                                maximum_volume = min(
                                    basin.max_volume,
                                    basin.get_volume(row[5])
                                )

                            description_lines.append(
                                "Maks. (%1.2f): %d m3"
                                % (
                                    maximum_level,
                                    maximum_volume
                                )
                            )

                            description = "\n".join(description_lines)

                            # ArcGIS text field is limited here in practice,
                            # so preserve the original 220-character behaviour.
                            row[4] = description[:220]

                            arcpy.AddMessage(description)

                        except Exception:
                            arcpy.AddWarning(
                                "Error: Could not calculate volume of basin %s"
                                % muid
                            )

                            arcpy.AddWarning(
                                "Elevations: %s" % basin.value1
                            )

                            arcpy.AddWarning(
                                "Surface areas: %s" % basin.value3
                            )

                            arcpy.AddWarning(
                                traceback.format_exc()
                            )

                        cursor.updateRow(row)

                # ------------------------------------------------------------------
                # Add basins to map
                # ------------------------------------------------------------------

                printStepAndTime("Adding basins to map")

                arcpy.SetProgressor(
                    "default",
                    "Adding basins to map"
                )

                addLayer(
                    os.path.join(
                        os.path.dirname(os.path.realpath(__file__)),
                        "Data",
                        "MOUSE Basins.lyr"
                    ),
                    export_basins,
                    group=empty_group_layer,
                    workspace_type="FILEGDB_WORKSPACE",
                    definition_query=sql_query
                )

        arcpy.SetProgressor("default", "Adding links, weirs and pumps to map")

        if is_sqlite_database:
            links_sql_query = sql_query + " AND Enabled = True" if sql_query else "Enabled = True"
        else:
            links_sql_query = sql_query

        if "Network Loads" in features_to_display:
            printStepAndTime("Adding network loads to map")
            # Create Network Load
            arcpy.SetProgressor("default", "Adding network loads to map")
            networkShape = getAvailableFilename(arcpy.env.scratchGDB + r"\NetworkLoads", parent=MU_database)

            class NetworkLoad():
                Geometry = None
                net_type_no = None

                @property
                def title(self):
                    t = os.path.basename(self.TSConnection) + " " + self.TimeseriesName if self.TSConnection else None
                    return t

            network_loads = []
            networkLoadInProject = False
            fields = ["MUID", "ApplyBoundaryNo", "ConnectionTypeNo", "CatchLoadNo",
                      "IndividualConnectionNo" if not is_sqlite_database else "TypeNo", "NodeID", "LinkID", "CatchID"]
            with arcpy.da.SearchCursor(msm_BBoundary, fields,
                                       where_clause="ApplyBoundaryNo = 1 AND GroupNo = 2 AND TypeNo IN (9,10)" if is_sqlite_database else "ApplyBoundaryNo = 1 AND GroupNo = 2 AND IndividualConnectionNo = 1") as cursor:
                for row in cursor:
                    networkLoadInProject = True
                    network_load = NetworkLoad()

                    for i, val in enumerate(row):
                        setattr(network_load, fields[i], val)
                    network_loads.append(network_load)

            if True:
                # arcpy.AddMessage("MUID IN ('%s')" % "', '".join([network_load.MUID for network_load in network_loads]) if is_sqlite_database else "BoundaryID IN ('%s')" % "', '".join([network_load.MUID for network_load in network_loads]))
                fields = ["MUID" if is_sqlite_database else "BoundaryID", "VariationNo", "ConstantValue",
                          "TSConnection", "TimeseriesName"]
                with arcpy.da.SearchCursor(msm_BBoundary if is_sqlite_database else msm_BItem, fields,
                                           where_clause="MUID IN ('%s')" % "', '".join(
                                               [network_load.MUID for network_load in
                                                network_loads]) if is_sqlite_database else "BoundaryID IN ('%s')" % "', '".join(
                                               [network_load.MUID for network_load in network_loads])) as cursor:
                    for row in cursor:
                        network_load = network_loads[
                            [i for i, network_load in enumerate(network_loads) if network_load.MUID == row[0]][0]]
                        for i, val in enumerate(row):
                            setattr(network_load, fields[i], val)

                        if network_load.VariationNo != 1:
                            network_load.ConstantValue = None
                        elif network_load.VariationNo != 3:
                            network_load.TSConnection = None
                            network_load.TimeseriesName = None

                        if network_load.CatchLoadNo:
                            with arcpy.da.SearchCursor(ms_Catchment, ["MUID", "SHAPE@XY"],
                                                       where_clause="MUID = '%s'" % (network_load.CatchID)) as xycursor:
                                for xyrow in xycursor:
                                    network_load.Geometry = xyrow[1]
                        elif (is_sqlite_database and network_load.TypeNo == 9) or (
                                not is_sqlite_database and network_load.IndividualConnectionNo == 1):
                            with arcpy.da.SearchCursor(msm_Node, ["MUID", "SHAPE@XY", "NetTypeNo"],
                                                       where_clause="MUID = '%s'" % (network_load.NodeID)) as xycursor:
                                for xyrow in xycursor:
                                    network_load.Geometry = xyrow[1]
                                    network_load.net_type_no = xyrow[2]
                        elif (is_sqlite_database and network_load.TypeNo == 10) or (
                                not is_sqlite_database and network_load.IndividualConnectionNo == 2):
                            with arcpy.da.SearchCursor(msm_Link, ["MUID", "SHAPE@XY", "NetTypeNo"],
                                                       where_clause="MUID = '%s'" % (network_load.LinkID)) as xycursor:
                                for xyrow in xycursor:
                                    network_load.Geometry = xyrow[1]
                                    network_load.net_type_no = xyrow[2]
                        else:
                            arcpy.AddError("Unknown error")

            if networkLoadInProject:
                arcpy.CreateFeatureclass_management(os.path.dirname(networkShape), os.path.basename(networkShape),
                                                    "POINT", spatial_reference = msm_Node)
                arcpy.AddField_management(networkShape, "MUID", "TEXT")
                arcpy.AddField_management(networkShape, "NetTypeNo", "SHORT")
                arcpy.AddField_management(networkShape, "Discharge", "DOUBLE")
                arcpy.AddField_management(networkShape, "Title", "STRING")
                arcpy.AddField_management(networkShape, "NodeID", "STRING")
                with arcpy.da.InsertCursor(networkShape,
                                           ["MUID", "SHAPE@XY", "Discharge", "Title", "NodeID", "NetTypeNo"]) as cursor:
                    for network_load in network_loads:
                        if network_load.Geometry:
                            cursor.insertRow([network_load.MUID, network_load.Geometry, network_load.ConstantValue,
                                              network_load.title, network_load.NodeID, network_load.net_type_no])

                addLayer(os.path.dirname(os.path.realpath(__file__)) + "\Data\MOUSE Network Load.lyr",
                         networkShape, group=empty_group_layer, workspace_type="FILEGDB_WORKSPACE",
                         definition_query=sql_query)

            # if not is_sqlite_database:
            printStepAndTime("Adding passive regulations to map")
            # Adding passive regulations to project
            arcpy.SetProgressor("default", "Adding passive regulations to map")

            class Regulation:
                q_max = 0
                linkID = None
                tabID = None
                net_type_no = None
                shape = None

            passive_regulations = {}
            if is_sqlite_database:
                with arcpy.da.SearchCursor(msm_Link, ["MUID", "FunctionID"], where_clause="FLowRegNo = 1") as cursor:
                    for row in cursor:
                        passive_regulations[row[0]] = Regulation()
                        passive_regulations[row[0]].tabID = row[1]
                        passive_regulations[row[0]].linkID = row[0]
            else:
                with arcpy.da.SearchCursor(msm_PasReg, ["LinkID", "FunctionID"], where_clause="TypeNo = 1") as cursor:
                    for row in cursor:
                        passive_regulations[row[0]] = Regulation()
                        passive_regulations[row[0]].tabID = row[1]
                        passive_regulations[row[0]].linkID = row[0]

            regulationsShape = getAvailableFilename(arcpy.env.scratchGDB + r"\passive_regulations",
                                                    parent=MU_database)
            if len(passive_regulations) > 0:
                with arcpy.da.SearchCursor(ms_TabD, ["TabID", "Sqn", "Value2"], where_clause="TabID IN ('%s')" % (
                "', '".join([regulation.tabID for regulation in passive_regulations.values()]))) as cursor:
                    for row in cursor:
                        linkIDs = [regulation.linkID for regulation in passive_regulations.values() if
                                   regulation.tabID == row[0]]
                        for linkID in linkIDs:
                            passive_regulations[linkID].q_max = row[2] if passive_regulations[linkID].q_max < row[
                                2] else passive_regulations[linkID].q_max

            printStepAndTime("Adding pump regulations to map")
            # Adding passive regulations to project
            arcpy.SetProgressor("default", "Adding pump regulations to map")

            pumps = {}
            with arcpy.da.SearchCursor(msm_Pump, ["MUID", "QMaxSetID", "NetTypeNo", "SHAPE@"],
                                       where_clause="CapTypeNo = 1") as cursor:
                for row in cursor:
                    pumps[row[0]] = Regulation()
                    pumps[row[0]].linkID = row[0]
                    pumps[row[0]].tabID = row[1]
                    pumps[row[0]].shape = row[3]
                    pumps[row[0]].net_type_no = row[2]

            with arcpy.da.SearchCursor(ms_TabD, ["TabID", "Sqn", "Value2"], where_clause="TabID IN ('%s')" % (
                    "', '".join([regulation.tabID for regulation in pumps.values()]))) as cursor:
                for row in cursor:
                    regulations = [regulation for regulation in pumps.values() if regulation.tabID == row[0]]
                    for regulation in regulations:
                        regulation.q_max = row[2] if regulation.q_max < row[2] else regulation.q_max

            arcpy.CreateFeatureclass_management(os.path.dirname(regulationsShape), os.path.basename(regulationsShape),
                                                "POLYLINE", spatial_reference = msm_Node)
            arcpy.AddField_management(regulationsShape, "LinkID", "TEXT")
            arcpy.AddField_management(regulationsShape, "NetTypeNo", "SHORT")
            arcpy.AddField_management(regulationsShape, "FunctionID", "TEXT")
            arcpy.AddField_management(regulationsShape, "QMax", "FLOAT")
            with arcpy.da.InsertCursor(regulationsShape,
                                       ["SHAPE@", "LinkID", "FunctionID", "QMax", "NetTypeNo"]) as regulation_cursor:
                with arcpy.da.SearchCursor(msm_Link, ["SHAPE@", "MUID", "NetTypeNo"], where_clause="MUID IN ('%s')" % (
                        "', '".join(passive_regulations.keys()))) as link_cursor:
                    for row in link_cursor:
                        passive_regulations[row[1]].net_type_no = row[2]
                        regulation_cursor.insertRow(
                            [row[0], row[1], passive_regulations[row[1]].tabID, passive_regulations[row[1]].q_max,
                             passive_regulations[row[1]].net_type_no])

                for regulation in pumps.values():
                    row = [regulation.shape, regulation.linkID, regulation.tabID, regulation.q_max,
                           regulation.net_type_no]
                    regulation_cursor.insertRow(row)

            addLayer(os.path.dirname(os.path.realpath(__file__)) + "\Data\Passive Regulations.lyr",
                     regulationsShape, group=empty_group_layer, workspace_type="FILEGDB_WORKSPACE",
                     definition_query=sql_query)

        if "Boundary Water Levels" in features_to_display:
            printStepAndTime("Adding outlets to map")

            # Adding outlets to project
            class Outlet:
                boundary_MUID = None
                boundary_item_MUID = None
                boundary_water_level = None
                geometry = None
                TSConnection = None
                TimeseriesName = None
                net_type_no = None

                def __init__(self, nodeID):
                    self.nodeID = nodeID

                @property
                def title(self):
                    t = os.path.basename(self.TSConnection) + " " + self.TimeseriesName if self.TSConnection else None
                    return t

            outlets = {}
            with arcpy.da.SearchCursor(msm_BBoundary, ["MUID", "NodeID"],
                                       where_clause="ApplyBoundaryNo = 1 AND TypeNo = 12") as cursor:
                for row in cursor:
                    outlets[row[1]] = Outlet(row[1])
                    outlets[row[1]].boundary_MUID = row[0]

            if not is_sqlite_database:
                with arcpy.da.SearchCursor(msm_BItem,
                                           ["MUID", "BoundaryID", "ConstantValue", "VariationNo", "TSConnection",
                                            "TimeseriesName"],
                                           where_clause="BoundaryType = 12 AND TypeNo = 1") as cursor:
                    for row in cursor:
                        nodeIDs = [outlet.nodeID for outlet in outlets.values() if outlet.boundary_MUID == row[1]]
                        if nodeIDs:
                            outlets[nodeIDs[0]].boundary_item_MUID = row[0]
                            if row[3] == 1:
                                outlets[nodeIDs[0]].boundary_water_level = row[2]
                            elif row[3] == 3:
                                outlets[nodeIDs[0]].TSConnection = row[4]
                                outlets[nodeIDs[0]].TimeseriesName = row[5]
            else:
                with arcpy.da.SearchCursor(msm_BBoundary, ["NodeID", "ConstantValue"],
                                           where_clause="ApplyBoundaryNo = 1 AND TypeNo = 12 AND ConnectionTypeNo = 3") as cursor:
                    for row in cursor:
                        outlets[row[0]].boundary_water_level = row[1]

            with arcpy.da.SearchCursor(msm_Node, ["SHAPE@", "MUID", "NetTypeNo"],
                                       where_clause="TypeNo = 3 AND MUID IN ('%s')" % (
                                       "', '".join(outlets.keys()))) as cursor:
                for row in cursor:
                    outlets[row[1]].geometry = row[0]
                    outlets[row[1]].net_type_no = row[2]

            if len([outlet for outlet in outlets.values()]) > 0:  # if any outlets with water level exist
                boundariesShape = getAvailableFilename(arcpy.env.scratchGDB + r"\BoundaryWaterLevel",
                                                       parent=MU_database)
                try:
                    arcpy.CreateFeatureclass_management(os.path.dirname(boundariesShape),
                                                        os.path.basename(boundariesShape), "POINT", spatial_reference = msm_Node)
                    arcpy.AddField_management(boundariesShape, "NodeID", "TEXT")
                    arcpy.AddField_management(boundariesShape, "NetTypeNo", "SHORT")
                    arcpy.AddField_management(boundariesShape, "B_MUID", "TEXT")
                    arcpy.AddField_management(boundariesShape, "BI_MUID", "TEXT")
                    arcpy.AddField_management(boundariesShape, "Wat_Lev", "FLOAT")
                    arcpy.AddField_management(boundariesShape, "Title", "TEXT")

                    with arcpy.da.InsertCursor(boundariesShape,
                                               ["SHAPE@", "NodeID", "B_MUID", "BI_MUID", "Wat_Lev", "Title",
                                                "NetTypeNo"]) as cursor:
                        for outlet in outlets.values():
                            cursor.insertRow(
                                [outlet.geometry, outlet.nodeID, outlet.boundary_MUID, outlet.boundary_item_MUID,
                                 outlet.boundary_water_level, outlet.title, outlet.net_type_no])
                    addLayer(os.path.dirname(os.path.realpath(__file__)) + "\Data\Boundary Water Level.lyr",
                             boundariesShape, group=empty_group_layer, workspace_type="FILEGDB_WORKSPACE",
                             definition_query=sql_query)
                except Exception as e:
                    arcpy.AddError(traceback.format_exc())

        if "Catchment Connections" in features_to_display:
            printStepAndTime("Adding catchment connections to map")
            arcpy.SetProgressor("default", "Adding catchment connections to map")
            addLayer(os.path.dirname(os.path.realpath(__file__)) + "\Data\Catchment Connections.lyr",
                     msm_CatchCon, group=empty_group_layer)

        if "Catchments" in features_to_display:
            printStepAndTime("Adding catchments to map")
            if join_catchments:
                arcpy.SetProgressor("default", "Joining ms_Catchment and msm_HModA and adding catchments to map")
                ms_Catchment = arcpy.CopyFeatures_management(ms_Catchment, getAvailableFilename(
                    arcpy.env.scratchGDB + "\ms_CatchmentImp", parent=MU_database)).getOutput(0)
                arcpy.management.RepairGeometry(ms_Catchment, delete_null = "DELETE_NULL")

                                                # arcpy.JoinField_management(in_data=ms_Catchment, in_field="MUID", join_table=MU_database + r"\msm_HModA", join_field="CatchID", fields="ImpArea")

                arcpy.management.AddField(ms_Catchment, "ImpArea", "FLOAT")
                arcpy.management.AddField(ms_Catchment, "ParAID", "TEXT")
                arcpy.management.AddField(ms_Catchment, "RedFactor", "FLOAT")
                arcpy.management.AddField(ms_Catchment, "ConcTime", "FLOAT")
                arcpy.management.AddField(ms_Catchment, "InitLoss", "FLOAT")
                arcpy.management.AddField(ms_Catchment, "NodeID", "TEXT")
                arcpy.management.AddField(ms_Catchment, "NodeNT", "SHORT")

                class HParA:
                    reduction_factor = None
                    concentration_time = None
                    initial_loss = None

                hParA_dict = {}
                with arcpy.da.SearchCursor(MU_database + r"\msm_HParA",
                                           ["MUID", "RedFactor", "ConcTime", "InitLoss"]) as cursor:
                    for row in cursor:
                        hParA_dict[row[0]] = HParA()
                        hParA_dict[row[0]].reduction_factor = row[1]
                        hParA_dict[row[0]].concentration_time = row[2]
                        hParA_dict[row[0]].initial_loss = row[3]

                catchments_dict = {}

                class Catchment:
                    imperviousness = None
                    local_parameters = None
                    ParAID = None
                    reduction_factor = None
                    concentration_time = None
                    initial_loss = None
                    node_ID = None
                    node_id_net_type_no = None

                if "mdb" in MU_database:
                    cursor = arcpy.da.SearchCursor(MU_database + r"\msm_HModA",
                                                   ["CatchID", "ImpArea", "ParAID", "LocalNo", "RFactor", "ConcTime",
                                                    "ILoss"])
                else:
                    cursor = arcpy.da.SearchCursor(ms_Catchment,
                                                   ["muid", "modelaimparea", "modelaparaid", "modelalocalno",
                                                    "modelarfactor", "modelaconctime",
                                                    "modelailoss"])

                for row in cursor:
                    # try:
                    catchments_dict[row[0]] = Catchment()
                    catchments_dict[row[0]].local_parameters = row[3] if "mdb" in MU_database else 1 - row[3]
                    catchments_dict[row[0]].imperviousness = row[1]
                    catchments_dict[row[0]].ParAID = row[2] if not catchments_dict[row[0]].local_parameters else ""
                    if catchments_dict[row[0]].local_parameters or row[2] in hParA_dict:
                        catchments_dict[row[0]].reduction_factor = (hParA_dict[row[2]].reduction_factor
                                                                    if not catchments_dict[row[0]].local_parameters else
                                                                    row[4])
                        catchments_dict[row[0]].concentration_time = (hParA_dict[row[2]].concentration_time
                                                                      if not catchments_dict[
                            row[0]].local_parameters else row[5])
                        catchments_dict[row[0]].initial_loss = (hParA_dict[row[2]].initial_loss
                                                                if not catchments_dict[row[0]].local_parameters else
                                                                row[6])
                    else:
                        arcpy.AddWarning("%s not in msm_HParA" % row[2])
                    # arcpy.AddMessage((catchments_dict[row[0]].ParAID, catchments_dict[row[0]], catchments_dict[row[0]].local_parameters))
                # except Exception as e:
                #     catchments_dict[row[0]].concentration_time = 7
                #     catchments_dict[row[0]].reduction_factor = 0
                #     arcpy.AddWarning("%s not found in msm_HParA" % (row[2]))
                #     arcpy.AddWarning(e)

                del cursor

                nodes_net_type_no = {row[0]: row[1] for row in arcpy.da.SearchCursor(msm_Node, ["MUID", "NetTypeNo"])}

                with arcpy.da.SearchCursor(os.path.join(MU_database, "msm_CatchCon"), ["CatchID", "NodeID"]) as cursor:
                    for row in cursor:
                        if row[0] in catchments_dict:
                            catchments_dict[row[0]].node_ID = row[1]

                            if row[1] in nodes_net_type_no:
                                catchments_dict[row[0]].node_id_net_type_no = nodes_net_type_no[row[1]]
                        else:
                            arcpy.AddWarning(
                                "Catchment connection registers connection to nonexisting catchment %s" % row[0])

                with arcpy.da.UpdateCursor(ms_Catchment,
                                           ["MUID", "ImpArea", "ParAID", "RedFactor", "ConcTime", "InitLoss", "NodeID",
                                            "NodeNT"]) as cursor:
                    for row in cursor:
                        try:
                            catchment = catchments_dict[row[0]]
                        except Exception as e:
                            arcpy.AddWarning("Could not find catchment %s in msm_HModA" % (row[0]))
                        else:
                            row[1] = catchment.imperviousness*1e2
                            row[2] = catchment.ParAID
                            row[3] = catchment.reduction_factor
                            row[4] = catchment.concentration_time
                            row[5] = catchment.initial_loss
                            row[6] = catchment.node_ID
                            row[7] = catchment.node_id_net_type_no
                            cursor.updateRow(row)

                # arcpy.JoinField_management(in_data=ms_Catchment, in_field="MUID", join_table=MU_database + r"\msm_CatchCon", join_field="CatchID", fields="NodeID")
                # arcpy.management.AddField(ms_Catchment, "RedFactor", field_type = "FLOAT")

                addLayer(os.path.dirname(os.path.realpath(__file__)) + "\Data\Catchments W Imp Area.lyr",
                         ms_Catchment, group=empty_group_layer, workspace_type="FILEGDB_WORKSPACE")

            else:
                # arcpy.AddMessage((os.path.dirname(os.path.realpath(__file__)) + "\Data\Catchments WO Imp Area.lyr",
                # catchments, empty_group_layer))
                clipboard_txt.append(ms_Catchment)

        if "Control Actions" in features_to_display:
            control_actions = {}
            class ControlAction:
                def __init__(self, applyno, structuretypeno, structure_id):
                    self.applyno = applyno
                    self.structuretypeno = structuretypeno
                    self.structure_id = structure_id
                    self.shape = None

            with arcpy.da.SearchCursor(msm_RTC, ["muid", "applyno", "structuretypeno", "pumpid", "weirid", "valveid", "orifricegateid", "orificeweirid"], where_clause = "active == 1") as cursor:
                for row in cursor:
                    if row[2] == 1: # Pump
                        control_actions[row[0]] = ControlAction(row[1], row[2], row[3])
                    elif row[2] == 3: # orifice
                        control_actions[row[0]] = ControlAction(row[1], row[2], row[6])
                    elif any(row[4:]):
                        for i, value in enumerate(row[4:]):
                            control_actions[row[0]] = ControlAction(row[1], row[2], row[i])

            pumps = [control_action.structure_id for control_action in control_actions.values() if control_action.structuretypeno == 1]
            with arcpy.da.SearchCursor(msm_Pump, ["MUID", "SHAPE@"], where_clause = "MUID IN ('%s')" % "', '".join(pumps)) as cursor:
                for row in cursor:
                    for control_action in [control_action for control_action in control_actions.values() if control_action.structure_id == row[0] and control_action.structuretypeno == 1]:
                        control_action.shape = row[1]

            orifices = [control_action.structure_id for control_action in control_actions.values() if control_action.structuretypeno == 3]


            with arcpy.da.SearchCursor(msm_Orifice, ["MUID", "SHAPE@"],
                                       where_clause="MUID IN ('%s')" % "', '".join(orifices)) as cursor:
                for row in cursor:
                    for control_action in [control_action for control_action in control_actions.values() if
                                           control_action.structure_id == row[
                                               0] and control_action.structuretypeno == 3]:
                        control_action.shape = row[1]

                        # arcpy.AddMessage(control_action.shape.firstPoint.X)

            control_actions_fc = getAvailableFilename(arcpy.env.scratchGDB + r"\RTC",
                                                   parent=MU_database)
            arcpy.CreateFeatureclass_management(os.path.dirname(control_actions_fc),
                                                os.path.basename(control_actions_fc), "POLYLINE", spatial_reference = msm_Node)

            arcpy.AddField_management(control_actions_fc, "muid", "TEXT")
            arcpy.AddField_management(control_actions_fc, "rtc_muid", "TEXT")
            arcpy.AddField_management(control_actions_fc, "struct_type_no", "SHORT")
            # arcpy.AddField_management(control_actions_fc, "muid", "TEXT")

            with arcpy.da.InsertCursor(control_actions_fc, ["SHAPE@", "muid", "rtc_muid", "struct_type_no"]) as cursor:
                for muid in control_actions:
                    # arcpy.AddMessage(dir(control_actions[muid].shape))
                    # arcpy.AddMessage([control_actions[muid].shape, control_actions[muid].structure_id, muid, control_actions[muid].structuretypeno])
                    cursor.insertRow([control_actions[muid].shape, control_actions[muid].structure_id, muid, control_actions[muid].structuretypeno])
                    arcpy.AddMessage(control_actions[muid].shape.length)

            # arcpy.AddMessage((os.path.dirname(os.path.realpath(__file__)) + "\Data\RTC.lyr", control_actions_fc))
            addLayer(os.path.dirname(os.path.realpath(__file__)) + "\Data\RTC.lyr",
                     control_actions_fc, group=empty_group_layer, workspace_type="FILEGDB_WORKSPACE", new_name="RTC")

            # arcpy.AddMessage(control_actions_fc)

        old_workspace = arcpy.env.workspace
        if "Annotations" in features_to_display and not is_sqlite_database:
            arcpy.env.workspace = os.path.join(MU_database, "mu_Geometry")
            annotation_classes = [os.path.join(MU_database, fc) for fc in
                                  arcpy.ListFeatureClasses(feature_type="Annotation")]
            for annotation_class in annotation_classes:
                try:
                    # arcpymapping.AddLayerToGroup(df, empty_group_layer, arcpymapping.Layer(annotation_class), "BOTTOM")
                    addLayer(os.path.dirname(os.path.realpath(__file__)) + "\Data\Annotation.lyr",
                             annotation_class, group=empty_group_layer,
                             new_name=empty_group_layer.name + " " + os.path.basename(annotation_class))
                except Exception as e:
                    arcpy.AddWarning(e)
            arcpy.env.workspace = old_workspace

        # printStepAndTime("Refreshing Map")
        # arcpy.SetProgressor("default","Refreshing map")
        # arcpy.RefreshTOC()
        # arcpy.RefreshActiveView()
        copy2clip("; ".join(clipboard_txt))

        arcpy.AddMessage("Feature paths copied to Clipboard. Open <Add Data> and paste from Clipboard then click <Add>. For all subsequent dialog boxes tick muid and click OK. Then Drag & Drop Layers into Group %s." % empty_group_layer.name)
        # arcpy.RefreshTOC()
        return

class DisplaySqliteStep2(object):
    def __init__(self):
        self.label = "2) Display MIKE+ - Step 2"
        self.description = "2) Display MIKE+ - Step 2"
        self.canRunInBackground = False

    def getParameterInfo(self):
        # Define parameter definitions

        # Input Features parameter
        group_layer = arcpy.Parameter(
            displayName="Group Layer",
            name="group_layer",
            datatype="GPGroupLayer",
            parameterType="Required",
            direction="Input")

        show_loss_par = arcpy.Parameter(
            displayName="Show Loss Parameters on Manhole Text",
            name="show_loss_par",
            datatype="Boolean",
            category="Additional Settings",
            parameterType="optional",
            direction="Output")
        show_loss_par.value = False

        show_depth = arcpy.Parameter(
            displayName="Show Depth",
            name="show_depth",
            datatype="Boolean",
            category="Additional Settings",
            parameterType="optional",
            direction="Output")
        show_depth.value = True

        save_layer = arcpy.Parameter(
            displayName="Save it to layer",
            name="save_layer",
            datatype="Boolean",
            category="Additional Settings",
            parameterType="optional",
            direction="Output")

        parameters = [group_layer, show_loss_par, show_depth, save_layer]

        return parameters

    def isLicensed(self):  # optional
        return True

    def updateParameters(self, parameters):  # optional
        if not parameters[0].Value:
            mxd = arcpyMapDocument("CURRENT")
            df = mxd.listMaps()[0] if arcgis_pro else arcpymapping.ListDataFrames(mxd)[0]
            layers = df.listLayers('*') if arcgis_pro else arcpymapping.ListLayers(mxd, '*', df)
            print(layers)
            # try:
            parameters[0].Value = [layer for layer in layers if layer.isGroupLayer][0].name
            # except Exception as e:
            #     pass

        return

    def updateMessages(self, parameters):  # optional

        return

    def execute(self, parameters, messages):
        group_layer = parameters[0].ValueAsText
        show_loss_par = parameters[1].Value
        show_depth = parameters[2].Value
        save_layer = parameters[3].Value

        mxd = arcpyMapDocument("CURRENT")
        df = mxd.listMaps()[0] if arcgis_pro else arcpymapping.ListDataFrames(mxd)[0]

        # layers = df.listLayers(group_layer)[0] if arcgis_pro else arcpymapping.ListLayers(mxd, group_layer, df)[0]
        layers = df.listLayers("")[0] if arcgis_pro else arcpymapping.ListLayers(mxd, "", df)

        templates_folder = os.path.dirname(os.path.realpath(
            __file__)) + "\Data\Templates\MIKE Plus"

        def apply_layer_settings(layer, layer_template):
            arcpy.management.ApplySymbologyFromLayer(layer, layer_template)

            layer_template_lyr = arcpy.mapping.Layer(layer_template)
            layer.labelClasses = layer_template_lyr.labelClasses

            layer.name = layer_template_lyr.name
            layer.showLabels = True

        layout_layer_path = None
        for layer in layers:
            # arcpy.AddMessage(((group_layer + r"\\.", layer.name)))
            if re.match(group_layer + r"\\.", layer.longName):
                if "msm_Node" in layer.dataSource:
                    if show_loss_par:
                        layer_template = os.path.join(templates_folder, "msm_Node_with_loss_par.lyr")
                        apply_layer_settings(layer, layer_template)
                    else:
                        layer_template = os.path.join(templates_folder, "msm_Node.lyr")
                        apply_layer_settings(layer, layer_template)
                    if not show_depth:
                        arcpy.AddMessage(r'if \[GroundLevel\] and \[InvertLevel\]:.+\n')
                        for label_class in layer.labelClasses:
                            label_class.expression = re.sub(r'if \[GroundLevel\] and \[InvertLevel\]:.+\n', "", label_class.expression)

                if "msm_Link" in layer.dataSource:
                    layer_template = os.path.join(templates_folder, "msm_Link.lyr")
                    apply_layer_settings(layer, layer_template)

                if "msm_Weir" in layer.dataSource:
                    layer_template = os.path.join(templates_folder, "msm_Weir.lyr")
                    apply_layer_settings(layer, layer_template)

                if "msm_Orifice" in layer.dataSource:
                    layer_template = os.path.join(templates_folder, "msm_Orifice.lyr")
                    apply_layer_settings(layer, layer_template)

                if "msm_Pump" in layer.dataSource:
                    layer_template = os.path.join(templates_folder, "msm_Pump.lyr")
                    apply_layer_settings(layer, layer_template)

                if "msm_Catchment" in layer.dataSource:
                    layer_template = os.path.join(templates_folder, "msm_Catchment.lyr")
                    apply_layer_settings(layer, layer_template)

                if not layout_layer_path and "sqlite" in layer.dataSource:
                    layout_layer_path = os.path.dirname(layer.dataSource.replace(".sqlite", ".lyr"))

            # arcpy.RefreshTOC()
        # for layer in layers:
        #     arcpy.AddMessage(dir(layer))
        #     try:
                # if "sqlite" in layer.dataSource:
                    # layout_layer_path = layer.dataSource.replace(".sqlite", ".lyr")
        if save_layer:
            arcpy.management.SaveToLayerFile(group_layer, layout_layer_path)
            # except Exception as e:
            #     arcpy.AddWarning(e)

class CopyMuppTemplate(object):
    def __init__(self):
        self.label = "a) Copy mupp Template"
        self.description = ("a) Copy mupp Template")
        self.canRunInBackground = True

    def getParameterInfo(self):
        # Define parameter definitions

        # Input Features parameter
        sqlite_database = arcpy.Parameter(
            displayName="Sqlite database",
            name="database",
            datatype="DEFile",
            parameterType="Required",
            multiValue=True,
            direction="Input")
        sqlite_database.filter.list = ["sqlite"]

        create_custom_labels = arcpy.Parameter(
            displayName="Create Custom Labels",
            name="create_custom_labels",
            datatype="Boolean",
            parameterType="Optional",
            direction="Input")

        parameters = [sqlite_database, create_custom_labels]

        return parameters

    def isLicensed(self):  # optional
        return True

    def updateParameters(self, parameters):  # optional
        # MU_database = parameters[0].ValueAsText
        return

    def updateMessages(self, parameters):  # optional
        if parameters[0].ValueAsText and '"' in parameters[0].ValueAsText:
            parameters[0].Value = parameters[0].ValueAsText.replace('"','')
        return

    def execute(self, parameters, messages):
        MU_databases = parameters[0].ValueAsText.split(';') if parameters[0].valueAsText else []
        MU_databases = [MU_database.replace("'","") for MU_database in MU_databases]
        create_custom_labels = parameters[1].Value

        for MU_database in MU_databases:
            mupp_template_filepath = os.path.dirname(os.path.realpath(__file__)) + r"\Data\Templates\MIKE Plus\Template.mupp"

            if ".sqlite" in MU_database:
                shutil.copy(mupp_template_filepath, MU_database.replace(".sqlite",".mupp"))
            else:
                raise Exception("Could not find .sqlite in MU_database")

            with open(MU_database.replace(".sqlite",".mupp"),'r') as f:
                txt_lines = f.readlines()

            for lineno in range(len(txt_lines[:30])):
            # Replace DBName and DBFilePath
                txt_lines[lineno] = re.sub(r"DBName\s*=\s*'.*?'", r"DBName = '%s'" % (os.path.basename(MU_database)), txt_lines[lineno])
                txt_lines[lineno] = re.sub(r"DBFilePath\s*=\s*\|.*?\|", r"DBFilePath = |%s|" % (os.path.basename(MU_database)), txt_lines[lineno])

            with open(MU_database.replace(".sqlite", ".mupp"), 'w') as f:
                f.writelines(txt_lines)

            if create_custom_labels:
                import sqlite3

                # Path to your SQLite database
                db_path = MU_database

                # Connect to the database
                conn = sqlite3.connect(db_path)
                conn.text_factory = str  # 💥 Forces all TEXT to be Unicode
                cursor = conn.cursor()


                cursor.execute("PRAGMA table_info(m_UserDefinedColumn)")
                columns = [row[1] for row in cursor.fetchall()]  # row[1] is column name
                has_typeno = 'typeno' in columns

                # Define rows
                rows = [
                    (
                        u"udf_1", 0, 1, u"msm_Node", u"label", u"label", 16,
                        u'[MUID] + "\\n" + If(ToString([Diameter]) != "", "ø" + ToString([Diameter]*1e3), "") + "\\n" + '
                        u'If(ToString([GroundLevel]) != "", "TK: " + ToString(Round([GroundLevel], 2)), "") + "\\n" + '
                        u'If(ToString([InvertLevel]) != "", "BK: " + ToString(Round([InvertLevel], 2)), "") + "\\n" + '
                        u'If(ToString([GroundLevel]) != "" && ToString([InvertLevel]) != "", "D: " + '
                        u'ToString(Round([GroundLevel] - [InvertLevel], 2)), "")'
                    ),
                    (
                        u"udf_2", 0, 1, u"msm_Link", u"label", u"label", 16,
                        u'"ø" + ToString([Diameter]*1e3) + Ifs(StartsWith(\'Plastic\',[MaterialID]), "pl","") + '
                        u'Ifs(StartsWith(\'Concrete\',[MaterialID]), "bt","") + "-" + '
                        u'ToString(Round([Slope]*10, 1)) + " o/oo"'
                    )
                ]

                rows = [r[:7] + (r[7],) for r in rows]

                # First delete any existing rows with same tablename and fieldname
                for row in rows:
                    cursor.execute(
                        "DELETE FROM m_UserDefinedColumn WHERE tablename = ? AND fieldname = ?",
                        (row[3], row[4])
                    )

                if has_typeno:
                    # Add typeno = 1 as 8th field in each tuple
                    rows = [r[:7] + (1,) + r[7:] for r in
                            rows]  # Insert 1 before expression (which is currently last)

                    # Adjust insert SQL for typeno column
                    insert_sql = u"""
                        INSERT INTO m_UserDefinedColumn (
                            muid, altid, active, tablename, fieldname, headertext, datatype, typeno, expression
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """
                else:
                    rows = rows
                    insert_sql = u"""
                        INSERT INTO m_UserDefinedColumn (
                            muid, altid, active, tablename, fieldname, headertext, datatype, expression
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """


                # Insert the new rows
                cursor.executemany(insert_sql, rows)

                # Commit and close
                conn.commit()
                conn.close()
                arcpy.AddMessage("Succesfull for db %s" % db_path)


class DisplaySqlitePro(object):
    def __init__(self):
        self.label = "3) Display MIKE+"
        self.description = ("3) Display MIKE+")
        self.canRunInBackground = False

    def getParameterInfo(self):
        # Define parameter definitions

        # Input Features parameter
        sqlite_database = arcpy.Parameter(
            displayName="MIKE+ Database (.sqlite)",
            name="database",
            datatype="DEFile",
            parameterType="Required",
            multiValue="True",
            direction="Input")
        sqlite_database.filter.list = ["sqlite"]

        join_catchments = arcpy.Parameter(
            displayName="Join catchments with imperviousness from msm_HModA table",
            name="join_catchments",
            datatype="Boolean",
            parameterType="optional",
            direction="Output")
        join_catchments.value = False

        features_to_display = arcpy.Parameter(
            displayName="Display the following features:",
            name="features_to_display",
            datatype="GPString",
            parameterType="Optional",
            multiValue=True,
            category="Additional Settings",
            direction="Input")
        features_to_display.filter.type = "ValueList"
        features_to_display.filter.list = ["Basins", "Manhole Head Loss", "Network Loads",
                                           "Boundary Water Levels", "Control Actions",
                                           "Annotations"]
        features_to_display.value = []

        sql_query = arcpy.Parameter(
            displayName="Set as Definition Query for layers",
            name="sql_query",
            datatype="GPString",
            category="Additional Settings",
            parameterType="optional",
            direction="Output")

        copy_and_show_delete = arcpy.Parameter(
            displayName="Duplicate .sqlite and show duplicate (!delete!)",
            name="copy_and_show_delete",
            datatype="Boolean",
            category="Additional Settings",
            parameterType="optional",
            direction="Output")
        copy_and_show_delete.value = False

        parameters = [sqlite_database, join_catchments, features_to_display, sql_query, copy_and_show_delete]

        return parameters

    def isLicensed(self):  # optional
        return True

    def updateParameters(self, parameters):  # optional
        if parameters[0].ValueAsText and '"' in parameters[0].ValueAsText:
            parameters[0].Value = parameters[0].ValueAsText.replace('"','')
        return

    def updateMessages(self, parameters):  # optional

        return

    def execute(self, parameters, messages):
        databases = [database.replace("'", "").replace('"', '') for database in parameters[0].ValueAsText.split(";")]
        join_catchments = parameters[1].Value
        features_to_display = [feature_name.replace("'", "").replace('"', '') for feature_name in
                               parameters[2].ValueAsText.split(";")] if parameters[2].ValueAsText else []
        sql_query = parameters[3].Value
        copy_and_show_delete = parameters[4].Value

        for MU_database in databases:

            if copy_and_show_delete:
                new_file_path = os.path.join(*os.path.split(MU_database)[:-1] + (
                    os.path.splitext(os.path.basename(MU_database))[0] + "!delete!" + os.path.splitext(MU_database)[1],))

                if os.path.exists(new_file_path):
                    try:
                        os.remove(new_file_path)  # Attempt to delete the existing file
                    except Exception as e:
                        raise IOError("The file '{}' is locked and cannot be deleted: {}".format(new_file_path, str(e)))

                try:
                    shutil.copy2(MU_database, new_file_path)  # Duplicate the file
                    print("File duplicated successfully: {}".format(new_file_path))
                except Exception as e:
                    raise IOError("Failed to duplicate the file: {}".format(str(e)))
                MU_database = new_file_path

            mxd = arcpy.mp.ArcGISProject("CURRENT")
            df = mxd.listMaps()[0]

            import tempfile

            mike_project_layer = os.path.join(os.path.dirname(os.path.realpath(__file__)), r"Data\Templates\MIKE Plus\MIKE+ Project.lyrx")

            desc = arcpy.Describe(os.path.join(MU_database, "msm_Node"))
            extent = desc.extent  # extent object with xmin, ymin, xmax, ymax

            xmin = extent.XMin
            ymin = extent.YMin
            xmax = extent.XMax
            ymax = extent.YMax

            # Read original content
            with open(mike_project_layer, 'r', encoding='utf-8') as f:
                content = f.read()

            # Replace DATABASE=... inside "workspaceConnectionString"
            pattern = r'("workspaceConnectionString"\s*:\s*".*?DATABASE=)(.*?)(?=(;|"))'
            replacement = r'\1!replace!'
            # arcpy.AddMessage(replacement)
            new_content = re.sub(pattern, replacement, content)
            new_content = new_content.replace("!replace!", MU_database.replace("\\", "\\\\"))

            if "manhole head loss" in [feature.lower() for feature in features_to_display]:
                new_content = new_content.replace("display_headloss = False","display_headloss = True")

            #Replace Extent

            def replace_extent(text, xmin, ymin, xmax, ymax):
                # This pattern matches the whole extent block, capturing its content inside braces
                pattern = r'("extent"\s*:\s*\{\s*[^}]*\})'

                def replacer(match):
                    block = match.group(1)

                    # Replace only inside this block
                    block = re.sub(r'"xmin"\s*:\s*[-+]?\d*\.?\d+', '"xmin" : {}'.format(xmin), block)
                    block = re.sub(r'"ymin"\s*:\s*[-+]?\d*\.?\d+', '"ymin" : {}'.format(ymin), block)
                    block = re.sub(r'"xmax"\s*:\s*[-+]?\d*\.?\d+', '"xmax" : {}'.format(xmax), block)
                    block = re.sub(r'"ymax"\s*:\s*[-+]?\d*\.?\d+', '"ymax" : {}'.format(ymax), block)

                    return block

                # Substitute only extent blocks with replaced values
                new_text = re.sub(pattern, replacer, text, flags=re.MULTILINE)
                return new_text

            # SETTING THE SQL QUERY TO THE FIELDS FOUND IN THE DATABASE - THEY VARY A LOT BETWEEN MIKE+ VERSIONS
            pattern = r'select\s+(.+?)\s+from\s+([\w.]+)'
            matches = re.finditer(pattern, new_content, re.IGNORECASE)

            for match in matches:
                full_match = match.group(0)
                field_str = match.group(1)
                table_name = match.group(2)

                try:
                    table_path = os.path.join(MU_database, table_name)
                    fields = [f.name for f in arcpy.ListFields(table_path)]
                    new_field_str = ", ".join(fields)

                    # Replace only this specific SELECT clause
                    new_select_clause = "select {} from {}".format(new_field_str, table_name)
                    new_content = new_content.replace(full_match, new_select_clause)

                except Exception as e:
                    print(u"\u26A0 Skipping table '{}': {}".format(table_name, e))  # \u26A0 = ⚠

            new_content = replace_extent(new_content, xmin, ymin, xmax, ymax)
            new_content = re.sub(r'\s*"queryFields"\s*:\s*\[[^\]]*\],?', '', new_content, flags=re.DOTALL)

            # for field in ["label", "enabled", "speclocalwaveno", "waveapproximationtypeno", "useroutingno", "routingtypeno", "routingdelay", "routingshape"/]:
            #     new_content = new_content.replace(", %s" % field, "")
            #     pattern = r""",?\s*\{\s*"name"\s*:\s*"%s"\s*,.*?\}""" % field
            #     new_content = re.sub(pattern, "", new_content, flags=re.DOTALL)

            temp_dir = tempfile.gettempdir()

            output_path = os.path.join(temp_dir, 'mike_project_layer_modified.lyrx')
            arcpy.AddMessage(output_path)
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(new_content)

            arcpy.AddMessage(output_path)
            empty_group_layer = df.addDataFromPath(output_path)

            msm_Node = MU_database + "\main.msm_Node"
            msm_Link = MU_database + "\main.msm_Link"
            # arcpy.AddMessage(MU_database)
            ms_Catchment = MU_database + "\ms_Catchment" if not ".sqlite" in MU_database else MU_database + "\main.msm_Catchment"
            msm_CatchCon = MU_database + "\msm_CatchConLink" if not ".sqlite" in MU_database else MU_database + "\main.msm_CatchCon"
            msm_Weir = MU_database + "\msm_Weir" if not ".sqlite" in MU_database else MU_database + "\main.msm_Weir"
            msm_Orifice = MU_database + "\main.msm_Orifice"
            msm_BBoundary = MU_database + "\main.msm_BBoundary"
            msm_Pump = MU_database + "\main.msm_Pump"
            msm_BItem = MU_database + "\main.msm_BItem"
            msm_PasReg = MU_database + "\main.msm_PasReg"
            ms_TabD = MU_database + "\main.ms_TabD"
            msm_RTC = MU_database + "\msm_RTC"
            mxd = arcpyMapDocument("CURRENT")
            df = mxd.listMaps()[0] if arcgis_pro else arcpymapping.ListDataFrames(mxd)[0]

            is_sqlite_database = True if ".sqlite" in MU_database else False

            import time
            start_time = time.time()

            def printStepAndTime(txt):
                arcpy.AddMessage("%s - %d" % (txt, time.time() - start_time))

            # empty_group_layer = [lyr for lyr in df.listLayers() if lyr.isGroupLayer][0]

            empty_group_layer.name = os.path.splitext(os.path.basename(MU_database))[0]

            MIKE_folder = os.path.join(os.path.dirname(arcpy.env.scratchGDB), "MIKE URBAN")
            if not os.path.exists(MIKE_folder):
                os.mkdir(MIKE_folder)
            MIKE_gdb = os.path.join(MIKE_folder, empty_group_layer.name)
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
                    MIKE_gdb = os.path.join(MIKE_folder, "%s_%d" % (empty_group_layer.name, dir_ext))
            arcpy.env.scratchWorkspace = MIKE_gdb

            arcpy.env.addOutputsToMap = False
            # addLayer = arcpymapping.Layer(os.path.dirname(os.path.realpath(__file__)) + ("\Data\MOUSE Manholes with LossPar.lyr" if show_loss_par else "\Data\MOUSE Manholes.lyr"))

            templates_folder = os.path.dirname(os.path.realpath(
                __file__)) + "\Data\Templates\MIKE Plus" if arcgis_pro and is_sqlite_database else os.path.dirname(
                os.path.realpath(__file__)) + "\Data"
            templates_extension = ".lyrx" if arcgis_pro and is_sqlite_database else ".lyr"

            class Basin:
                def __init__(self, geometry_id):
                    self.geometryID = geometry_id or ""
                    self.value1 = []
                    self.value3 = []
                    self.permanent_level = None
                    self._critical_level = None

                @property
                def critical_level(self):
                    """Return the defined critical level or the maximum basin elevation."""
                    if self._critical_level is not None:
                        return self._critical_level

                    return np.max(self.elevations)

                @property
                def elevations(self):
                    """Return basin elevations adjusted to the invert level."""
                    min_elevation = np.min(self.value1)

                    if min_elevation != self.invert_level:
                        return self.value1 + (self.invert_level - min_elevation)

                @property
                def terrain_elevation(self):
                    return [
                        elevation
                        for elevation in self.elevations
                        if elevation < self.critical_level
                    ] + [self.critical_level]

                @property
                def max_volume(self):
                    elevations = np.sort(self.elevations)
                    surface_areas = np.array(self.value3)[np.argsort(self.elevations)]

                    elevations = [
                                     elevation
                                     for elevation in elevations
                                     if elevation < self.critical_level
                                 ] + [self.critical_level]

                    surface_areas = np.interp(
                        elevations,
                        np.sort(self.elevations),
                        surface_areas
                    )

                    return np.trapz(surface_areas, elevations)

                @property
                def max_area(self):
                    return np.max(self.value3)

                def get_volume(self, level):
                    elevations = np.sort(self.elevations)
                    surface_areas = np.array(self.value3)[np.argsort(self.elevations)]

                    elevations = [
                                     elevation
                                     for elevation in elevations
                                     if elevation < self.critical_level
                                 ] + [self.critical_level]

                    surface_areas = np.interp(
                        elevations,
                        np.sort(self.elevations),
                        surface_areas
                    )

                    cumulative_volume = [0] + list(
                        cumtrapz(surface_areas, elevations)
                    )

                    volume = np.interp(
                        level,
                        elevations,
                        cumulative_volume
                    )

                    if self.permanent_level:
                        volume -= np.interp(
                            self.permanent_level,
                            elevations,
                            cumulative_volume
                        )

                    return volume

            if "Basins" in features_to_display:
                arcpy.SetProgressor("default", "Calculating volume of basins")
                printStepAndTime("Calculating volume of basins")

                basins = {}

                # Import basins
                with arcpy.da.SearchCursor(
                        msm_Node,
                        ["MUID", "GeometryID"],
                        where_clause="TypeNo = 2"
                ) as cursor:
                    for muid, geometry_id in cursor:
                        basins[muid] = Basin(geometry_id)

                if basins:
                    # Import basin geometry data
                    geometry_ids = "', '".join(
                        basin.geometryID for basin in basins.values()
                    )

                    with arcpy.da.SearchCursor(
                            os.path.join(MU_database, "ms_TabD"),
                            ["TabID", "Value1", "Value3"],
                            where_clause="TabID IN ('%s')" % geometry_ids
                    ) as cursor:
                        basins_by_geometry_id = {
                            basin.geometryID: basin
                            for basin in basins.values()
                        }

                        for tab_id, value1, value3 in cursor:
                            basin = basins_by_geometry_id.get(tab_id)

                            if basin is not None:
                                basin.value1.append(value1)
                                basin.value3.append(value3)

                    export_basins = getAvailableFilename(
                        arcpy.env.scratchGDB + r"\basins",
                        parent=MU_database
                    )

                    arcpy.Select_analysis(
                        msm_Node,
                        export_basins,
                        where_clause="TypeNo = 2"
                    )

                    arcpy.management.AddField(
                        export_basins,
                        "Volume",
                        "FLOAT"
                    )
                    arcpy.management.AddField(
                        export_basins,
                        "MaxArea",
                        "FLOAT"
                    )

                    with arcpy.da.UpdateCursor(
                            export_basins,
                            [
                                "MUID",
                                "Volume",
                                "CriticalLevel",
                                "GeometryID",
                                "Description",
                                "GroundLevel",
                                "InvertLevel",
                                "MaxArea"
                            ]
                    ) as cursor:
                        for row in cursor:
                            basin = basins.get(row[0])

                            if basin is None:
                                continue

                            basin.invert_level = row[6]

                            try:
                                row[1] = basin.max_volume
                                row[7] = basin.max_area

                                elevation_discrepancy = (
                                        basin.invert_level - np.min(basin.value1)
                                )

                                description = ""

                                for index in np.argsort(basin.value1):
                                    elevation = basin.value1[index]
                                    surface_area = basin.value3[index]
                                    adjusted_elevation = (
                                            elevation + elevation_discrepancy
                                    )

                                    description += (
                                            "%6.2f m\u00A0\u00A0%8d m²\u00A0\u00A0%8d m³\r\n"
                                            % (
                                                adjusted_elevation,
                                                surface_area,
                                                basin.get_volume(adjusted_elevation)
                                            )
                                    )
                                    # arcpy.AddMessage((row[0], adjusted_elevation, elevation, surface_area))
                                # if row[0].lower() == "kaxbas1":
                                #     return

                                row[4] = description[:220]

                            except Exception:
                                arcpy.AddWarning(
                                    "Could not calculate volume of basin %s"
                                    % row[0]
                                )
                                arcpy.AddWarning(
                                    "Value1: %s" % basin.value1
                                )
                                arcpy.AddWarning(
                                    "Value3: %s" % basin.value3
                                )
                                arcpy.AddWarning(
                                    traceback.format_exc()
                                )

                            cursor.updateRow(row)

                    printStepAndTime("Adding basins to map")
                    arcpy.SetProgressor("default", "Adding basins to map")

                    addLayer(
                        os.path.join(
                            os.path.dirname(os.path.realpath(__file__)),
                            "Data",
                            "MOUSE Basins.lyr"
                        ),
                        export_basins,
                        group=empty_group_layer,
                        workspace_type="FILEGDB_WORKSPACE",
                        definition_query=sql_query
                    )

            # return
            arcpy.SetProgressor("default", "Adding links, weirs and pumps to map")

            if is_sqlite_database:
                links_sql_query = sql_query + " AND Enabled = True" if sql_query else "Enabled = True"
            else:
                links_sql_query = sql_query

            if "Network Loads" in features_to_display:
                printStepAndTime("Adding network loads to map")
                # Create Network Load
                arcpy.SetProgressor("default", "Adding network loads to map")
                networkShape = getAvailableFilename(arcpy.env.scratchGDB + r"\NetworkLoads", parent=MU_database)

                class NetworkLoad():
                    Geometry = None
                    net_type_no = None

                    @property
                    def title(self):
                        t = os.path.basename(self.TSConnection) + " " + self.TimeseriesName if self.TSConnection else None
                        return t

                network_loads = []
                networkLoadInProject = False
                fields = ["MUID", "ApplyBoundaryNo", "ConnectionTypeNo", "CatchLoadNo",
                          "IndividualConnectionNo" if not is_sqlite_database else "TypeNo", "NodeID", "LinkID", "CatchID"]
                with arcpy.da.SearchCursor(msm_BBoundary, fields,
                                           where_clause="ApplyBoundaryNo = 1 AND GroupNo = 2 AND TypeNo IN (9,10)" if is_sqlite_database else "ApplyBoundaryNo = 1 AND GroupNo = 2 AND IndividualConnectionNo = 1") as cursor:
                    for row in cursor:
                        networkLoadInProject = True
                        network_load = NetworkLoad()

                        for i, val in enumerate(row):
                            setattr(network_load, fields[i], val)
                        network_loads.append(network_load)

                if True:
                    # arcpy.AddMessage("MUID IN ('%s')" % "', '".join([network_load.MUID for network_load in network_loads]) if is_sqlite_database else "BoundaryID IN ('%s')" % "', '".join([network_load.MUID for network_load in network_loads]))
                    fields = ["MUID" if is_sqlite_database else "BoundaryID", "VariationNo", "ConstantValue",
                              "TSConnection", "TimeseriesName"]
                    with arcpy.da.SearchCursor(msm_BBoundary if is_sqlite_database else msm_BItem, fields,
                                               where_clause="MUID IN ('%s')" % "', '".join(
                                                   [network_load.MUID for network_load in
                                                    network_loads]) if is_sqlite_database else "BoundaryID IN ('%s')" % "', '".join(
                                                   [network_load.MUID for network_load in network_loads])) as cursor:
                        for row in cursor:
                            network_load = network_loads[
                                [i for i, network_load in enumerate(network_loads) if network_load.MUID == row[0]][0]]
                            for i, val in enumerate(row):
                                setattr(network_load, fields[i], val)

                            if network_load.VariationNo != 1:
                                network_load.ConstantValue = None
                            elif network_load.VariationNo != 3:
                                network_load.TSConnection = None
                                network_load.TimeseriesName = None

                            if network_load.CatchLoadNo:
                                with arcpy.da.SearchCursor(ms_Catchment, ["MUID", "SHAPE@XY"],
                                                           where_clause="MUID = '%s'" % (network_load.CatchID)) as xycursor:
                                    for xyrow in xycursor:
                                        network_load.Geometry = xyrow[1]
                            elif (is_sqlite_database and network_load.TypeNo == 9) or (
                                    not is_sqlite_database and network_load.IndividualConnectionNo == 1):
                                with arcpy.da.SearchCursor(msm_Node, ["MUID", "SHAPE@XY", "NetTypeNo"],
                                                           where_clause="MUID = '%s'" % (network_load.NodeID)) as xycursor:
                                    for xyrow in xycursor:
                                        network_load.Geometry = xyrow[1]
                                        network_load.net_type_no = xyrow[2]
                            elif (is_sqlite_database and network_load.TypeNo == 10) or (
                                    not is_sqlite_database and network_load.IndividualConnectionNo == 2):
                                with arcpy.da.SearchCursor(msm_Link, ["MUID", "SHAPE@XY", "NetTypeNo"],
                                                           where_clause="MUID = '%s'" % (network_load.LinkID)) as xycursor:
                                    for xyrow in xycursor:
                                        network_load.Geometry = xyrow[1]
                                        network_load.net_type_no = xyrow[2]
                            else:
                                arcpy.AddError("Unknown error")

                if networkLoadInProject:
                    arcpy.CreateFeatureclass_management(os.path.dirname(networkShape), os.path.basename(networkShape),
                                                        "POINT", spatial_reference=msm_Node)
                    arcpy.AddField_management(networkShape, "MUID", "TEXT")
                    arcpy.AddField_management(networkShape, "NetTypeNo", "SHORT")
                    arcpy.AddField_management(networkShape, "Discharge", "DOUBLE")
                    arcpy.AddField_management(networkShape, "Title", "STRING")
                    arcpy.AddField_management(networkShape, "NodeID", "STRING")
                    with arcpy.da.InsertCursor(networkShape,
                                               ["MUID", "SHAPE@XY", "Discharge", "Title", "NodeID", "NetTypeNo"]) as cursor:
                        for network_load in network_loads:
                            if network_load.Geometry:
                                cursor.insertRow([network_load.MUID, network_load.Geometry, network_load.ConstantValue,
                                                  network_load.title, network_load.NodeID, network_load.net_type_no])

                    addLayer(os.path.dirname(os.path.realpath(__file__)) + "\Data\MOUSE Network Load.lyr",
                             networkShape, group=empty_group_layer, workspace_type="FILEGDB_WORKSPACE",
                             definition_query=sql_query)

                # if not is_sqlite_database:
                printStepAndTime("Adding passive regulations to map")
                # Adding passive regulations to project
                arcpy.SetProgressor("default", "Adding passive regulations to map")

                class Regulation:
                    q_max = 0
                    linkID = None
                    tabID = None
                    net_type_no = None
                    shape = None

                passive_regulations = {}
                if is_sqlite_database:
                    with arcpy.da.SearchCursor(msm_Link, ["MUID", "FunctionID"], where_clause="FLowRegNo = 1") as cursor:
                        for row in cursor:
                            passive_regulations[row[0]] = Regulation()
                            passive_regulations[row[0]].tabID = row[1]
                            passive_regulations[row[0]].linkID = row[0]
                else:
                    with arcpy.da.SearchCursor(msm_PasReg, ["LinkID", "FunctionID"], where_clause="TypeNo = 1") as cursor:
                        for row in cursor:
                            passive_regulations[row[0]] = Regulation()
                            passive_regulations[row[0]].tabID = row[1]
                            passive_regulations[row[0]].linkID = row[0]

                regulationsShape = getAvailableFilename(arcpy.env.scratchGDB + r"\passive_regulations",
                                                        parent=MU_database)
                if len(passive_regulations) > 0:
                    with arcpy.da.SearchCursor(ms_TabD, ["TabID", "Sqn", "Value2"], where_clause="TabID IN ('%s')" % (
                            "', '".join([regulation.tabID for regulation in passive_regulations.values()]))) as cursor:
                        for row in cursor:
                            linkIDs = [regulation.linkID for regulation in passive_regulations.values() if
                                       regulation.tabID == row[0]]
                            for linkID in linkIDs:
                                passive_regulations[linkID].q_max = row[2] if passive_regulations[linkID].q_max < row[
                                    2] else passive_regulations[linkID].q_max

                printStepAndTime("Adding pump regulations to map")
                # Adding passive regulations to project
                arcpy.SetProgressor("default", "Adding pump regulations to map")

                pumps = {}
                with arcpy.da.SearchCursor(msm_Pump, ["MUID", "QMaxSetID", "NetTypeNo", "SHAPE@"],
                                           where_clause="CapTypeNo = 1") as cursor:
                    for row in cursor:
                        pumps[row[0]] = Regulation()
                        pumps[row[0]].linkID = row[0]
                        pumps[row[0]].tabID = row[1]
                        pumps[row[0]].shape = row[3]
                        pumps[row[0]].net_type_no = row[2]

                with arcpy.da.SearchCursor(ms_TabD, ["TabID", "Sqn", "Value2"], where_clause="TabID IN ('%s')" % (
                        "', '".join([regulation.tabID for regulation in pumps.values()]))) as cursor:
                    for row in cursor:
                        regulations = [regulation for regulation in pumps.values() if regulation.tabID == row[0]]
                        for regulation in regulations:
                            regulation.q_max = row[2] if regulation.q_max < row[2] else regulation.q_max

                arcpy.CreateFeatureclass_management(os.path.dirname(regulationsShape), os.path.basename(regulationsShape),
                                                    "POLYLINE", spatial_reference=msm_Node)
                arcpy.AddField_management(regulationsShape, "LinkID", "TEXT")
                arcpy.AddField_management(regulationsShape, "NetTypeNo", "SHORT")
                arcpy.AddField_management(regulationsShape, "FunctionID", "TEXT")
                arcpy.AddField_management(regulationsShape, "QMax", "FLOAT")
                with arcpy.da.InsertCursor(regulationsShape,
                                           ["SHAPE@", "LinkID", "FunctionID", "QMax", "NetTypeNo"]) as regulation_cursor:
                    with arcpy.da.SearchCursor(msm_Link, ["SHAPE@", "MUID", "NetTypeNo"], where_clause="MUID IN ('%s')" % (
                            "', '".join(passive_regulations.keys()))) as link_cursor:
                        for row in link_cursor:
                            passive_regulations[row[1]].net_type_no = row[2]
                            regulation_cursor.insertRow(
                                [row[0], row[1], passive_regulations[row[1]].tabID, passive_regulations[row[1]].q_max,
                                 passive_regulations[row[1]].net_type_no])

                    for regulation in pumps.values():
                        row = [regulation.shape, regulation.linkID, regulation.tabID, regulation.q_max,
                               regulation.net_type_no]
                        regulation_cursor.insertRow(row)

                addLayer(os.path.dirname(os.path.realpath(__file__)) + "\Data\Passive Regulations.lyr",
                         regulationsShape, group=empty_group_layer, workspace_type="FILEGDB_WORKSPACE",
                         definition_query=sql_query)

            if "Boundary Water Levels" in features_to_display:
                printStepAndTime("Adding outlets to map")

                # Adding outlets to project
                class Outlet:
                    boundary_MUID = None
                    boundary_item_MUID = None
                    boundary_water_level = None
                    geometry = None
                    TSConnection = None
                    TimeseriesName = None
                    net_type_no = None

                    def __init__(self, nodeID):
                        self.nodeID = nodeID

                    @property
                    def title(self):
                        t = os.path.basename(self.TSConnection) + " " + self.TimeseriesName if self.TSConnection else None
                        return t

                outlets = {}
                with arcpy.da.SearchCursor(msm_BBoundary, ["MUID", "NodeID"],
                                           where_clause="ApplyBoundaryNo = 1 AND TypeNo = 12") as cursor:
                    for row in cursor:
                        if row[1]:
                            outlets[row[1]] = Outlet(row[1])
                            outlets[row[1]].boundary_MUID = row[0]

                if not is_sqlite_database:
                    with arcpy.da.SearchCursor(msm_BItem,
                                               ["MUID", "BoundaryID", "ConstantValue", "VariationNo", "TSConnection",
                                                "TimeseriesName"],
                                               where_clause="BoundaryType = 12 AND TypeNo = 1") as cursor:
                        for row in cursor:
                            nodeIDs = [outlet.nodeID for outlet in outlets.values() if outlet.boundary_MUID == row[1]]
                            if nodeIDs:
                                arcpy.AddMessage(NodeIDs)
                                outlets[nodeIDs[0]].boundary_item_MUID = row[0]
                                if row[3] == 1:
                                    outlets[nodeIDs[0]].boundary_water_level = row[2]
                                elif row[3] == 3:
                                    outlets[nodeIDs[0]].TSConnection = row[4]
                                    outlets[nodeIDs[0]].TimeseriesName = row[5]
                else:
                    with arcpy.da.SearchCursor(msm_BBoundary, ["NodeID", "ConstantValue"],
                                               where_clause="ApplyBoundaryNo = 1 AND TypeNo = 12 AND ConnectionTypeNo = 3") as cursor:
                        for row in cursor:
                            if row[0]:
                                outlets[row[0]].boundary_water_level = row[1]
                with arcpy.da.SearchCursor(msm_Node, ["SHAPE@", "MUID", "NetTypeNo"],
                                           where_clause="TypeNo = 3 AND MUID IN ('%s')" % (
                                                   "', '".join(outlets.keys()))) as cursor:
                    for row in cursor:
                        outlets[row[1]].geometry = row[0]
                        outlets[row[1]].net_type_no = row[2]

                if len([outlet for outlet in outlets.values()]) > 0:  # if any outlets with water level exist
                    boundariesShape = getAvailableFilename(arcpy.env.scratchGDB + r"\BoundaryWaterLevel",
                                                           parent=MU_database)
                    try:
                        arcpy.CreateFeatureclass_management(os.path.dirname(boundariesShape),
                                                            os.path.basename(boundariesShape), "POINT",
                                                            spatial_reference=msm_Node)
                        arcpy.AddField_management(boundariesShape, "NodeID", "TEXT")
                        arcpy.AddField_management(boundariesShape, "NetTypeNo", "SHORT")
                        arcpy.AddField_management(boundariesShape, "B_MUID", "TEXT")
                        arcpy.AddField_management(boundariesShape, "BI_MUID", "TEXT")
                        arcpy.AddField_management(boundariesShape, "Wat_Lev", "FLOAT")
                        arcpy.AddField_management(boundariesShape, "Title", "TEXT")

                        with arcpy.da.InsertCursor(boundariesShape,
                                                   ["SHAPE@", "NodeID", "B_MUID", "BI_MUID", "Wat_Lev", "Title",
                                                    "NetTypeNo"]) as cursor:
                            for outlet in outlets.values():
                                cursor.insertRow(
                                    [outlet.geometry, outlet.nodeID, outlet.boundary_MUID, outlet.boundary_item_MUID,
                                     outlet.boundary_water_level, outlet.title, outlet.net_type_no])
                        addLayer(os.path.dirname(os.path.realpath(__file__)) + "\Data\Boundary Water Level.lyr",
                                 boundariesShape, group=empty_group_layer, workspace_type="FILEGDB_WORKSPACE",
                                 definition_query=sql_query)
                    except Exception as e:
                        arcpy.AddError(traceback.format_exc())

            if "Catchment Connections" in features_to_display:
                printStepAndTime("Adding catchment connections to map")
                arcpy.SetProgressor("default", "Adding catchment connections to map")
                addLayer(os.path.dirname(os.path.realpath(__file__)) + "\Data\Catchment Connections.lyr",
                         msm_CatchCon, group=empty_group_layer)

            printStepAndTime("Adding catchments to map")
            if join_catchments:
                arcpy.AddMessage("BRO")
                arcpy.SetProgressor("default", "Joining ms_Catchment and msm_HModA and adding catchments to map")
                ms_Catchment = arcpy.CopyFeatures_management(ms_Catchment, getAvailableFilename(
                    arcpy.env.scratchGDB + "\ms_CatchmentImp", parent=MU_database)).getOutput(0)
                arcpy.management.RepairGeometry(ms_Catchment, delete_null="DELETE_NULL")

                # arcpy.JoinField_management(in_data=ms_Catchment, in_field="MUID", join_table=MU_database + r"\msm_HModA", join_field="CatchID", fields="ImpArea")

                arcpy.management.AddField(ms_Catchment, "ImpArea", "FLOAT")
                arcpy.management.AddField(ms_Catchment, "ParAID", "TEXT")
                arcpy.management.AddField(ms_Catchment, "RedFactor", "FLOAT")
                arcpy.management.AddField(ms_Catchment, "ConcTime", "FLOAT")
                arcpy.management.AddField(ms_Catchment, "InitLoss", "FLOAT")
                arcpy.management.AddField(ms_Catchment, "NodeID", "TEXT")
                arcpy.management.AddField(ms_Catchment, "NodeNT", "SHORT")

                class HParA:
                    reduction_factor = None
                    concentration_time = None
                    initial_loss = None

                hParA_dict = {}
                with arcpy.da.SearchCursor(MU_database + r"\msm_HParA",
                                           ["MUID", "RedFactor", "ConcTime", "InitLoss"]) as cursor:
                    for row in cursor:
                        hParA_dict[row[0]] = HParA()
                        hParA_dict[row[0]].reduction_factor = row[1]
                        hParA_dict[row[0]].concentration_time = row[2]
                        hParA_dict[row[0]].initial_loss = row[3]

                catchments_dict = {}

                class Catchment:
                    imperviousness = None
                    local_parameters = None
                    ParAID = None
                    reduction_factor = None
                    concentration_time = None
                    initial_loss = None
                    node_ID = None
                    node_id_net_type_no = None

                if "mdb" in MU_database:
                    cursor = arcpy.da.SearchCursor(MU_database + r"\msm_HModA",
                                                   ["CatchID", "ImpArea", "ParAID", "LocalNo", "RFactor", "ConcTime",
                                                    "ILoss"])
                else:
                    cursor = arcpy.da.SearchCursor(ms_Catchment,
                                                   ["muid", "modelaimparea", "modelaparaid", "modelalocalno",
                                                    "modelarfactor", "modelaconctime",
                                                    "modelailoss"])

                for row in cursor:
                    # try:
                    catchments_dict[row[0]] = Catchment()
                    catchments_dict[row[0]].local_parameters = row[3] if "mdb" in MU_database else 1 - row[3]
                    catchments_dict[row[0]].imperviousness = row[1]
                    catchments_dict[row[0]].ParAID = row[2] if not catchments_dict[row[0]].local_parameters else ""
                    if catchments_dict[row[0]].local_parameters or row[2] in hParA_dict:
                        catchments_dict[row[0]].reduction_factor = (hParA_dict[row[2]].reduction_factor
                                                                    if not catchments_dict[row[0]].local_parameters else
                                                                    row[4])
                        catchments_dict[row[0]].concentration_time = (hParA_dict[row[2]].concentration_time
                                                                      if not catchments_dict[
                            row[0]].local_parameters else row[5])
                        catchments_dict[row[0]].initial_loss = (hParA_dict[row[2]].initial_loss
                                                                if not catchments_dict[row[0]].local_parameters else
                                                                row[6])
                    else:
                        arcpy.AddWarning("%s not in msm_HParA" % row[2])
                    # arcpy.AddMessage((catchments_dict[row[0]].ParAID, catchments_dict[row[0]], catchments_dict[row[0]].local_parameters))
                # except Exception as e:
                #     catchments_dict[row[0]].concentration_time = 7
                #     catchments_dict[row[0]].reduction_factor = 0
                #     arcpy.AddWarning("%s not found in msm_HParA" % (row[2]))
                #     arcpy.AddWarning(e)

                del cursor

                nodes_net_type_no = {row[0]: row[1] for row in arcpy.da.SearchCursor(msm_Node, ["MUID", "NetTypeNo"])}

                with arcpy.da.SearchCursor(os.path.join(MU_database, "msm_CatchCon"), ["CatchID", "NodeID"]) as cursor:
                    for row in cursor:
                        if row[0] in catchments_dict:
                            catchments_dict[row[0]].node_ID = row[1]

                            if row[1] in nodes_net_type_no:
                                catchments_dict[row[0]].node_id_net_type_no = nodes_net_type_no[row[1]]
                        else:
                            arcpy.AddWarning(
                                "Catchment connection registers connection to nonexisting catchment %s" % row[0])

                with arcpy.da.UpdateCursor(ms_Catchment,
                                           ["MUID", "ImpArea", "ParAID", "RedFactor", "ConcTime", "InitLoss", "NodeID",
                                            "NodeNT"]) as cursor:
                    for row in cursor:
                        try:
                            catchment = catchments_dict[row[0]]
                        except Exception as e:
                            arcpy.AddWarning("Could not find catchment %s in msm_HModA" % (row[0]))
                        else:
                            row[1] = catchment.imperviousness * 1e2
                            row[2] = catchment.ParAID
                            row[3] = catchment.reduction_factor
                            row[4] = catchment.concentration_time
                            row[5] = catchment.initial_loss
                            row[6] = catchment.node_ID
                            row[7] = catchment.node_id_net_type_no
                            cursor.updateRow(row)

                # arcpy.JoinField_management(in_data=ms_Catchment, in_field="MUID", join_table=MU_database + r"\msm_CatchCon", join_field="CatchID", fields="NodeID")
                # arcpy.management.AddField(ms_Catchment, "RedFactor", field_type = "FLOAT")

                update_layer = addLayer(os.path.dirname(os.path.realpath(__file__)) + "\Data\Catchments W Imp Area.lyr",
                         ms_Catchment, group=empty_group_layer, workspace_type="FILEGDB_WORKSPACE")



            if "Control Actions" in features_to_display:
                control_actions = {}

                class ControlAction:
                    def __init__(self, applyno, structuretypeno, structure_id):
                        self.applyno = applyno
                        self.structuretypeno = structuretypeno
                        self.structure_id = structure_id
                        self.shape = None

                with arcpy.da.SearchCursor(msm_RTC, ["muid", "applyno", "structuretypeno", "pumpid", "weirid", "valveid",
                                                     "orifricegateid", "orificeweirid"],
                                           where_clause="active == 1") as cursor:
                    for row in cursor:
                        if row[2] == 1:  # Pump
                            control_actions[row[0]] = ControlAction(row[1], row[2], row[3])
                        elif row[2] == 3:  # orifice
                            control_actions[row[0]] = ControlAction(row[1], row[2], row[6])
                        elif any(row[4:]):
                            for i, value in enumerate(row[4:]):
                                control_actions[row[0]] = ControlAction(row[1], row[2], row[i])

                pumps = [control_action.structure_id for control_action in control_actions.values() if
                         control_action.structuretypeno == 1]
                with arcpy.da.SearchCursor(msm_Pump, ["MUID", "SHAPE@"],
                                           where_clause="MUID IN ('%s')" % "', '".join(pumps)) as cursor:
                    for row in cursor:
                        for control_action in [control_action for control_action in control_actions.values() if
                                               control_action.structure_id == row[
                                                   0] and control_action.structuretypeno == 1]:
                            control_action.shape = row[1]

                orifices = [control_action.structure_id for control_action in control_actions.values() if
                            control_action.structuretypeno == 3]

                with arcpy.da.SearchCursor(msm_Orifice, ["MUID", "SHAPE@"],
                                           where_clause="MUID IN ('%s')" % "', '".join(orifices)) as cursor:
                    for row in cursor:
                        for control_action in [control_action for control_action in control_actions.values() if
                                               control_action.structure_id == row[
                                                   0] and control_action.structuretypeno == 3]:
                            control_action.shape = row[1]

                            # arcpy.AddMessage(control_action.shape.firstPoint.X)

                control_actions_fc = getAvailableFilename(arcpy.env.scratchGDB + r"\RTC",
                                                          parent=MU_database)
                arcpy.CreateFeatureclass_management(os.path.dirname(control_actions_fc),
                                                    os.path.basename(control_actions_fc), "POLYLINE",
                                                    spatial_reference=msm_Node)

                arcpy.AddField_management(control_actions_fc, "muid", "TEXT")
                arcpy.AddField_management(control_actions_fc, "rtc_muid", "TEXT")
                arcpy.AddField_management(control_actions_fc, "struct_type_no", "SHORT")
                # arcpy.AddField_management(control_actions_fc, "muid", "TEXT")

                with arcpy.da.InsertCursor(control_actions_fc, ["SHAPE@", "muid", "rtc_muid", "struct_type_no"]) as cursor:
                    for muid in control_actions:
                        # arcpy.AddMessage(dir(control_actions[muid].shape))
                        # arcpy.AddMessage([control_actions[muid].shape, control_actions[muid].structure_id, muid, control_actions[muid].structuretypeno])
                        cursor.insertRow([control_actions[muid].shape, control_actions[muid].structure_id, muid,
                                          control_actions[muid].structuretypeno])
                        arcpy.AddMessage(control_actions[muid].shape.length)

                # arcpy.AddMessage((os.path.dirname(os.path.realpath(__file__)) + "\Data\RTC.lyr", control_actions_fc))
                addLayer(os.path.dirname(os.path.realpath(__file__)) + "\Data\RTC.lyr",
                         control_actions_fc, group=empty_group_layer, workspace_type="FILEGDB_WORKSPACE", new_name="RTC")

                # arcpy.AddMessage(control_actions_fc)

            old_workspace = arcpy.env.workspace
            if "Annotations" in features_to_display and not is_sqlite_database:
                arcpy.env.workspace = os.path.join(MU_database, "mu_Geometry")
                annotation_classes = [os.path.join(MU_database, fc) for fc in
                                      arcpy.ListFeatureClasses(feature_type="Annotation")]
                for annotation_class in annotation_classes:
                    try:
                        # arcpymapping.AddLayerToGroup(df, empty_group_layer, arcpymapping.Layer(annotation_class), "BOTTOM")
                        addLayer(os.path.dirname(os.path.realpath(__file__)) + "\Data\Annotation.lyr",
                                 annotation_class, group=empty_group_layer,
                                 new_name=empty_group_layer.name + " " + os.path.basename(annotation_class))
                    except Exception as e:
                        arcpy.AddWarning(e)
                arcpy.env.workspace = old_workspace