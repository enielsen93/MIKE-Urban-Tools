# Tool for reading DFS0 or KM2 files and creating LTS files from it
# Created by Emil Nielsen
# Contact: 
# E-mail: enielsen93@hotmail.com

import os
import sys
import numpy as np
import sqlite3
# import pythonaddins


class Toolbox(object):
    def __init__(self):
        """Define the toolbox (the name of the toolbox is the name of the
        .pyt file)."""
        self.label = "SQLITE Field Calculator"
        self.alias = ""

        # List of tool classes associated with this toolbox
        self.tools = [FieldCalculator]
    
    
class FieldCalculator(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Calculate Field"
        self.description = "Calculate Field"
        self.canRunInBackground = False

    def getParameterInfo(self):
        #Define parameter definitions
        featureclass = arcpy.Parameter(
            displayName="Feature Class",
            name="featureclass",
            datatype="GPFeatureLayer",
            parameterType="Required",
            direction="Input")
        
        field = arcpy.Parameter(
			displayName= "Field to assign value to",
			name="field",
			datatype="GPString",
			parameterType="Required",
			direction="Input")
        
        value = arcpy.Parameter(
            displayName="Value",
            name="value",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
        
        params = [featureclass, field, value]

        return params

    def isLicensed(self):
        return True

    def updateParameters(self, parameters):
        if not parameters[0].Value:
            mxd = arcpy.mapping.MapDocument("CURRENT")
            featureclass = [lyr.longName for lyr in arcpy.mapping.ListLayers(mxd) if
                     lyr.getSelectionSet() and "muid" in [field.name.lower() for field in arcpy.ListFields(lyr)]][0]
            if featureclass:
                parameters[0].value = featureclass
        if parameters[0].Value and not parameters[1].Value:
            parameters[1].filter.list = [f.name for f in arcpy.Describe(parameters[0].Value).fields]


        return

    def updateMessages(self, parameters):
        return

    def execute(self, parameters, messages):
        featureclass = parameters[0].ValueAsText
        field = parameters[1].ValueAsText
        value = parameters[2].ValueAsText

        MU_database = os.path.dirname(arcpy.Describe(featureclass).catalogPath).replace("\mu_Geometry", "").replace("!delete!","")
        featureclass_name = arcpy.Describe(featureclass).name
        arcpy.AddMessage(featureclass)
        selection = [row[0] for row in arcpy.da.SearchCursor(featureclass, ["muid"])]
        arcpy.AddMessage("Confirm Query - Might be hidden behind window!")
        # userquery = pythonaddins.MessageBox(
        #     "Assign value to %d features?" % (len(selection)),
        #     "Confirm Assignment", 4)

        # if userquery == "Yes":
        arcpy.AddMessage(MU_database)
        try:
            connection = sqlite3.connect(
                        MU_database)
            update_cursor = connection.cursor()
            update_query = "UPDATE %s SET %s = %s WHERE MUID IN %s" % (featureclass_name.replace("main.",""), field, value,
                                                                         "('%s')" % ("','".join(selection)))
            update_cursor.execute(update_query)
            connection.commit()
            connection.close()
        except Exception as e:
            import traceback
            arcpy.AddWarning(traceback.format_exc())
            raise (e)

        finally:
            if connection:
                connection.close()
        return
        