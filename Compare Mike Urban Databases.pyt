# Created by Emil Nielsen
# Contact: 
# E-mail: enielsen93@hotmail.com

import arcpy
if "mapping" in dir(arcpy):
    import arcpy.mapping as apmapping
    from arcpy.mapping  import MapDocument as MapDocument
    from arcpy.mapping  import MapDocument as MapDocument
else: 
    import arcpy.mp as apmapping
    from arcpy.mp import ArcGISProject as MapDocument
    from arcpy.mapping  import MapDocument as MapDocument
import numpy as np
import csv
import os
import traceback
import re

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
        self.label =  "Compare Mike Urban Databases"
        self.alias  = "Compare Mike Urban Databases"

        # List of tool classes associated with this toolbox
        self.tools = [CompareMikeUrbanDatabases] 

class DisplayMikeUrban(object):
    def __init__(self):
        self.label       = "Compare Mike Urban Databases"
        self.description = "Compare Mike Urban Databases"
        self.canRunInBackground = False

    def getParameterInfo(self):
        #Define parameter definitions

        # Input Features parameter
        MU_database1 = arcpy.Parameter(
            displayName="Mike Urban database 1",
            name="database1",
            datatype="DEFile",
            parameterType="Required",
            direction="Input")
            
        MU_database2 = arcpy.Parameter(
            displayName="Mike Urban database 2",
            name="database2",
            datatype="DEFile",
            parameterType="Required",
            direction="Input")
        
        
        parameters = [MU_database1, MU_database2]
        
        return parameters

    def isLicensed(self): #optional
        return True

    def updateParameters(self, parameters): #optional
        return

    def updateMessages(self, parameters): #optional
       
        return

    def execute(self, parameters, messages):        
        MU_database1 = parameters[0].ValueAsText
        MU_database2 = parameters[1].ValueAsText
        
        
        compare_result = arcpy.TableCompare_management(
                                base_table, test_table, sort_field, compare_type, ignore_option, 
                                attribute_tolerance, omit_field, continue_compare, compare_file)
        return
  