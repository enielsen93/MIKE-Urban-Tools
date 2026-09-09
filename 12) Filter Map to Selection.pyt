import os
import numpy as np
import re
import arcpy
import tkinter

if "mapping" in dir(arcpy):
    arcgis_pro = False
    import arcpy.mapping as arcpymapping
    from arcpy.mapping import MapDocument as arcpyMapDocument
    from arcpy._mapping import Layer
else:
    arcgis_pro = True
    import arcpy.mp as arcpymapping
    from arcpy.mp import ArcGISProject as arcpyMapDocument

class Toolbox(object):
    def __init__(self):
        self.label = "Set Definition Query to Selection"
        self.alias = "Set Definition Query to Selection"
        self.canRunInBackground = True
        # List of tool classes associated with this toolbox
        self.tools = [SetDefinitionQuery, SummarizeSelection, CopyInExpression]


class SetDefinitionQuery(object):
    def __init__(self):
        self.label = "Set Definition Query to Selection"
        self.description = "Set Definition Query to Selection"
        self.canRunInBackground = False

    def getParameterInfo(self):
        # Define parameter definitions

        layer = arcpy.Parameter(
            displayName="Layer",
            name="layer",
            datatype="GPFeatureLayer",
            parameterType="Required",
            multiValue = True,
            direction="Input")

        append = arcpy.Parameter(
            displayName="Append to existing Definition Query",
            name="append",
            datatype="GPBoolean",
            parameterType="Optional",
            direction="Input")

        remove_selection = arcpy.Parameter(
            displayName="Remove from filter instead",
            name="remove_selection",
            datatype="GPBoolean",
            parameterType="Optional",
            direction="Input")

        specific_definition_query = arcpy.Parameter(
            displayName="Specific Definition Query",
            name="specific_definition_query",
            datatype="GPString",
            parameterType="Optional",
            category="Additional Settings",
            direction="Input")

        apply_to_labels = arcpy.Parameter(
            displayName="Apply to labels instead of definition query",
            name="apply_to_labels",
            datatype="GPBoolean",
            parameterType="Optional",
            category="Additional Settings",
            direction="Input")

        parameters = [layer, append, remove_selection, specific_definition_query, apply_to_labels]
        return parameters

    def isLicensed(self):
        return True

    def updateParameters(self, parameters):
        if not parameters[0].Values:
            if arcgis_pro:
                # Reference the active map in the current project
                aprx = arcpymapping.ArcGISProject("CURRENT")
                map_view = aprx.activeMap

                layers = []
                # List layers with selected features
                for layer in map_view.listLayers():
                    try:
                        if layer.getSelectionSet():
                            layers.append(layer.longName)
                    except:
                        pass
            else:
                mxd = arcpy.mapping.MapDocument("CURRENT")

                layers = [lyr.longName for lyr in arcpy.mapping.ListLayers(mxd) if
                         lyr.getSelectionSet()]
            if layers:
                parameters[0].value = layers


        return

    def updateMessages(self, parameters):  # optional
        return

    def execute(self, parameters, messages):
        layers = parameters[0].Values
        append = parameters[1].Value
        remove_selection = parameters[2].Value
        specific_definition_query = parameters[3].ValueAsText
        apply_to_labels = parameters[4].Value

        def setDefinitionQuery(layer, definition_query):
            if arcgis_pro:
                aprx = arcpy.mp.ArcGISProject("CURRENT")
                m = aprx.activeMap

                layers = m.listLayers()
                layer = [lyr for lyr in layers if lyr.name == layer.name and lyr.dataSource == layer.dataSource][0]

                layer.updateDefinitionQueries([{"name": "Query 1", "sql": definition_query, "isActive": True}])
                aprx.save()
            else:
                layer.definitionQuery = definition_query

        def setLabelQuery(layer, definition_query, append = True):
            if arcgis_pro:
                aprx = arcpy.mp.ArcGISProject("CURRENT")
                m = aprx.activeMap

                layers = m.listLayers()
                layer = [lyr for lyr in layers if lyr.name == layer.name and lyr.dataSource == layer.dataSource][0]

                for lbl_class in layer.listLabelClasses():
                    existing_query = lbl_class.SQLQuery.strip()

                    if existing_query and append:
                        if remove_selection:
                            lbl_class.SQLQuery = "{} AND {}".format(existing_query, definition_query)
                        else:
                            lbl_class.SQLQuery = "{} OR {}".format(existing_query, definition_query)
                    else:
                        lbl_class.SQLQuery = definition_query
                    arcpy.AddMessage(definition_query)

                    lbl_class.showClassLabels = True  # Make sure labeling is enabled
            else:
                raise RuntimeError("This script is currently not supported in ArcMap. Use ArcGIS Pro.")

        if apply_to_labels:
            for layer in layers:
                if specific_definition_query:
                    setLabelQuery(layer, specific_definition_query, append = append)
                else:
                    oid_fieldname = arcpy.Describe(layer).OIDFieldName
                    if "muid" in [field.name.lower() for field in arcpy.ListFields(layer)] and "CatchConLink" not in getattr(layer, "datasetName", ""):
                        new_definition_query = "muid %sIN ('%s')" % ("NOT " if remove_selection else "", "', '".join(
                            [row[0] for row in arcpy.da.SearchCursor(layer, ["muid"], where_clause="%s IN (%s)" % (
                            oid_fieldname, ", ".join([str(l) for l in layer.getSelectionSet()])))]))
                    else:
                        new_definition_query = "%s %sIN (%s)" % (oid_fieldname, "NOT " if remove_selection else "",
                                                                 ", ".join([str(g) for g in layer.getSelectionSet()]))

                    setLabelQuery(layer, new_definition_query, append = append)
        else:
            for layer in layers:
                if specific_definition_query: # specific definition query
                    old_definition_query = layer.definitionQuery
                    if old_definition_query and append:
                        old_definition_query = layer.definitionQuery
                        if arcgis_pro:
                            setDefinitionQuery(layer, old_definition_query + " AND " + specific_definition_query)
                        else:
                            layer.definitionQuery = old_definition_query + " AND " + specific_definition_query
                    else:
                        if arcgis_pro:
                            setDefinitionQuery(layer, specific_definition_query)
                        else:
                            layer.definitionQuery = specific_definition_query
                    # layer.updateDefinitionQueries([specific_definition_query])

                else:
                    oid_fieldname = arcpy.Describe(layer).OIDFieldName
                    # arcpy.AddMessage([row for row in arcpy.da.SearchCursor(layer, ["muid"], where_clause = "objectid IN (%s)" % (", ".join([str(l) for l in layer.getSelectionSet()])))])
                    # arcpy.AddMessage("objectid IN (%s)" % (", ".join([str(l) for l in layer.getSelectionSet()])))
                    if "muid" in [field.name.lower() for field in arcpy.ListFields(layer)] and "CatchConLink" not in getattr(layer, "datasetName", ""):
                        new_definition_query = "muid %sIN ('%s')" % ("NOT " if remove_selection else "", "', '".join([row[0] for row in arcpy.da.SearchCursor(layer, ["muid"], where_clause = "%s IN (%s)" % (oid_fieldname, ", ".join([str(l) for l in layer.getSelectionSet()])))]))
                    else:
                        new_definition_query = "%s %sIN (%s)" % (oid_fieldname, "NOT " if remove_selection else "", ", ".join([str(g) for g in layer.getSelectionSet()]))


                    old_definition_query = layer.definitionQuery
                    if old_definition_query and append:
                        if arcgis_pro:
                            setDefinitionQuery(layer, old_definition_query + " AND " + new_definition_query)
                        else:
                            layer.definitionQuery = old_definition_query + " AND " + new_definition_query

                    else:
                        if arcgis_pro:
                            setDefinitionQuery(layer, new_definition_query)
                        else:
                            layer.definitionQuery = new_definition_query

        return

class SummarizeSelection(object):
    def __init__(self):
        self.label = "Summarize Selected Features"
        self.description = (
            "Summarizes the selected features in a chosen layer. "
            "Calculates total length for polylines or total area for polygons."
        )
        self.canRunInBackground = False

    def getParameterInfo(self):

        layer = arcpy.Parameter(
            displayName="Layer",
            name="layer",
            datatype="GPFeatureLayer",
            parameterType="Required",
            direction="Input"
        )

        return [layer]

    def isLicensed(self):
        return True

    def updateParameters(self, parameters):
        pass

    def updateMessages(self, parameters):
        pass

    def execute(self, parameters, messages):
        layer = parameters[0].valueAsText

        if not layer:
            raise arcpy.ExecuteError("No layer selected.")

        desc = arcpy.Describe(layer)

        # Check selection
        selected_count = int(arcpy.management.GetCount(layer)[0])

        if selected_count == 0:
            raise arcpy.ExecuteError(
                "The selected layer has no selected features."
            )

        messages.addMessage(
            "Layer: {}".format(desc.name)
        )
        messages.addMessage(
            "Selected features: {}".format(selected_count)
        )

        # ---------------------------------------------------------
        # GEOMETRY
        # ---------------------------------------------------------

        if desc.shapeType == "Polyline":

            total_length = 0.0

            with arcpy.da.SearchCursor(
                    layer,
                    ["SHAPE@LENGTH"]
            ) as cursor:

                for row in cursor:
                    if row[0] is not None:
                        total_length += row[0]

            messages.addMessage(
                "Total length: {:.2f} m".format(total_length)
            )

        elif desc.shapeType == "Polygon":

            total_area = 0.0

            with arcpy.da.SearchCursor(
                    layer,
                    ["SHAPE@AREA"]
            ) as cursor:

                for row in cursor:
                    if row[0] is not None:
                        total_area += row[0]

            messages.addMessage(
                "Total area: {:.2f} m²".format(total_area)
            )

        elif desc.shapeType == "Point":
            # No geometry total for points
            pass

        else:

            raise arcpy.ExecuteError(
                "Layer geometry type '{}' is not supported. "
                "Only points, polylines and polygons are supported.".format(
                    desc.shapeType
                )
            )

        # ---------------------------------------------------------
        # SUM NUMERIC FIELDS
        # ---------------------------------------------------------

        numeric_types = [
            "SmallInteger",
            "Integer",
            "Single",
            "Double"
        ]

        numeric_fields = []

        for field in arcpy.ListFields(layer):

            if field.type in numeric_types:
                numeric_fields.append(field.name)

        if numeric_fields:

            messages.addMessage("")
            messages.addMessage("Numeric field totals:")

            field_totals = {}

            for field in numeric_fields:
                field_totals[field] = 0.0

            with arcpy.da.SearchCursor(
                    layer,
                    numeric_fields
            ) as cursor:

                for row in cursor:

                    for i, value in enumerate(row):

                        if value is not None:
                            field_totals[numeric_fields[i]] += value

            for field in numeric_fields:
                messages.addMessage(
                    "{}: {:.4g}".format(
                        field,
                        field_totals[field]
                    )
                )

        else:

            messages.addMessage(
                "No numeric fields found."
            )

class CopyInExpression(object):
    def __init__(self):
        self.label = "Copy MUID IN Expression"
        self.description = (
            "Copies a SQL IN expression based on the selected features."
        )
        self.canRunInBackground = False

    def getParameterInfo(self):
        param0 = arcpy.Parameter(
            displayName="Input Layer",
            name="input_layer",
            datatype="GPTableView",
            parameterType="Required",
            direction="Input"
        )

        return [param0]

    def isLicensed(self):
        return True

    def updateParameters(self, parameters):
        # Autofill with the first layer that has a selection
        if not parameters[0].altered:
            try:
                aprx = arcpy.mp.ArcGISProject("CURRENT")
                maps = aprx.listMaps()

                for m in maps:
                    for lyr in m.listLayers():
                        if not lyr.isFeatureLayer:
                            continue

                        try:
                            count = int(
                                arcpy.GetCount_management(lyr).getOutput(0)
                            )

                            # GetCount respects the current selection
                            if count > 0:
                                parameters[0].value = lyr
                                return

                        except Exception:
                            pass

            except Exception:
                pass

    def updateMessages(self, parameters):
        pass

    def execute(self, parameters, messages):

        layer = parameters[0].valueAsText

        if not layer:
            raise arcpy.ExecuteError("No input layer selected.")

        desc = arcpy.Describe(layer)

        # Find MUID, otherwise use OBJECTID
        field_names = [f.name.upper() for f in arcpy.ListFields(layer)]

        if "MUID" in field_names:
            field = "MUID"
        else:
            # Find the actual ObjectID field name
            oid_field = desc.OIDFieldName

            if not oid_field:
                raise arcpy.ExecuteError(
                    "Could not find either MUID or OBJECTID field."
                )

            field = oid_field

        values = []

        with arcpy.da.SearchCursor(layer, [field]) as cursor:
            for row in cursor:
                value = row[0]

                if value is None:
                    continue

                # Escape single quotes for SQL
                value = str(value).replace("'", "''")

                values.append("'" + value + "'")

        if not values:
            raise arcpy.ExecuteError(
                "The input layer has no selected features."
            )

        expression = field + " IN (" + ",".join(values) + ")"
        import subprocess
        def copy_to_clipboard(txt):
            cmd = 'echo ' + txt.strip() + '|clip'
            return subprocess.check_call(cmd, shell=True)

        copy_to_clipboard(expression)
        arcpy.AddMessage(expression)