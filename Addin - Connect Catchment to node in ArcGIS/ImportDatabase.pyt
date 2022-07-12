# Created by Emil Nielsen
# Contact: 
# E-mail: enielsen93@hotmail.com

import arcpy
import numpy as np
import os

from arcpy import env
class Toolbox(object):
    def __init__(self):
        self.label =  "Import Mike Urban Database"
        self.alias  = "Import Mike Urban Database"

        # List of tool classes associated with this toolbox
        self.tools = [MikeUrbanDatabase] 

class MikeUrbanDatabase(object):
    def __init__(self):
        self.label       = "Import Mike Urban Database"
        self.description = "Import Mike Urban Database"
        self.canRunInBackground = False

    def getParameterInfo(self):
        #Define parameter definitions

        # Input Features parameter
        MU_database = arcpy.Parameter(
            displayName="Mike Urban database",
            name="database",
            datatype="DEWorkspace",
            parameterType="Required",
            direction="Input")
        
        parameters = [MU_database]
        
        return parameters

    def isLicensed(self): #optional
        return True

    def updateParameters(self, parameters): #optional
        return

    def updateMessages(self, parameters): #optional
       
        return

    def execute(self, parameters, messages):
        MU_database = parameters[0].ValueAsText
        mxd = arcpy.mapping.MapDocument("CURRENT")
        df = arcpy.mapping.ListDataFrames(mxd)[0]
        arcpy.env.addOutputsToMap = False
        groupLayer = arcpy.mapping.Layer(os.path.dirname(os.path.realpath(__file__)) + "\Data\Database.lyr")
        groupLayer = arcpy.mapping.AddLayer(df, groupLayer)
        groupLayer = arcpy.mapping.ListLayers(mxd, groupLayer, df)[0]
        for layer in groupLayer:
            #arcpy.AddMessage(MU_database)
            #arcpy.AddMessage(unicode(layer.datasetName))
            layer.replaceDataSource(MU_database, 'ACCESS_WORKSPACE', unicode(layer.datasetName))     
            
        msm_CatchCon = arcpy.mapping.TableView(MU_database + r"\msm_CatchCon")
        arcpy.mapping.AddTableView(df, msm_CatchCon)  
        arcpy.RefreshTOC()
        arcpy.RefreshActiveView()
      
        
        return
        
        