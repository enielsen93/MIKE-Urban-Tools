import os
import numpy as np
import re

class Toolbox(object):
    def __init__(self):
        self.label = "Set Definition Query to Selection"
        self.alias = "Set Definition Query to Selection"
        self.canRunInBackground = True
        # List of tool classes associated with this toolbox
        self.tools = [SetDefinitionQuery]


class SetDefinitionQuery(object):
    def __init__(self):
        self.label = "Set Definition Query to Selection"
        self.description = "Set Definition Query to Selection"
        self.canRunInBackground = False



    def getParameterInfo(self):
        # Define parameter definitions

        layer = arcpy.Parameter(
            displayName="Layer",
            name="folder",
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

        parameters = [layer, append, remove_selection, specific_definition_query]
        return parameters

    def isLicensed(self):
        return True

    def updateParameters(self, parameters):
        if not parameters[0].Values:
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

        for layer in layers:
            if specific_definition_query: # specific definition query
                old_definition_query = layer.definitionQuery
                if old_definition_query and append:
                    old_definition_query = layer.definitionQuery
                    layer.definitionQuery = old_definition_query + " AND " + specific_definition_query
                else:
                    layer.definitionQuery = specific_definition_query
            else:
                oid_fieldname = arcpy.Describe(layer).OIDFieldName
                # arcpy.AddMessage([row for row in arcpy.da.SearchCursor(layer, ["muid"], where_clause = "objectid IN (%s)" % (", ".join([str(l) for l in layer.getSelectionSet()])))])
                # arcpy.AddMessage("objectid IN (%s)" % (", ".join([str(l) for l in layer.getSelectionSet()])))
                if "muid" in [field.name.lower() for field in arcpy.ListFields(layer)] and "CatchConLink" not in layer.datasetName:
                    arcpy.AddMessage((layer.getSelectionSet()))
                    new_definition_query = "muid %sIN ('%s')" % ("NOT " if remove_selection else "", "', '".join([row[0] for row in arcpy.da.SearchCursor(layer, ["muid"], where_clause = "%s IN (%s)" % (oid_fieldname, ", ".join([str(l) for l in layer.getSelectionSet()])))]))
                else:
                    new_definition_query = "%s %sIN (%s)" % (oid_fieldname, "NOT " if remove_selection else "", ", ".join([str(g) for g in layer.getSelectionSet()]))


                old_definition_query = layer.definitionQuery
                if old_definition_query and append:
                    layer.definitionQuery = old_definition_query + " AND " + new_definition_query
                else:
                    layer.definitionQuery = new_definition_query

        return
