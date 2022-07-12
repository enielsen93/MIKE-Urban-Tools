import re
import arcpy


class Toolbox(object):
    def __init__(self):
        self.label =  "Subtract MUS File from MUS File"
        self.alias  = "Subtract MUS File from MUS File"

        # List of tool classes associated with this toolbox
        self.tools = [SubtractMUSFile] 

class SubtractMUSFile(object):
    def __init__(self):
        self.label       = "Subtract MUS File from MUS File"
        self.description = "Subtract MUS File from MUS File"
        self.canRunInBackground = True

    def getParameterInfo(self):
        #Define parameter definitions

        # Input Features parameter
        sourceFile = arcpy.Parameter(
            displayName="Source MUS File:",
            name="sourceFile",
            datatype="File",
            parameterType="Required",
            direction="Input")
        sourceFile.filter.list=["mus"]
        
        subtractFile = arcpy.Parameter(
            displayName="MUS File with items to remove from source:",
            name="subtractFile",
            datatype="File",
            parameterType="Required",
            direction="Input")
        subtractFile.filter.list=["mus"]
            
        resultFile = arcpy.Parameter(
            displayName="Result MUS File:",
            name="resultFile",
            datatype="File",
            parameterType="Required",
            direction="Output")
        resultFile.filter.list=["mus"]
        
        fields = arcpy.Parameter(
            displayName= "Exclude the following in the resulting selection file:",  
            name="fields",  
            datatype="GPString",  
            multiValue="true",
            parameterType="Optional",  
            direction="Input")
        
        fields.filter.list = ['msm_Node', 'msm_Link', 'msm_Weir', 'msm_Orifice', 'ms_Catchment', 'msm_CatchConLink', 'msm_Coupled2DLine']
        fields.value = ['msm_CatchConLink']
        
        parameters = [sourceFile, subtractFile, resultFile, fields]
        
        return parameters

    def isLicensed(self): #optional
        return True

    def updateParameters(self, parameters): #optional
        return

    def updateMessages(self, parameters): #optional
        return

    def execute(self, parameters, messages):        
        musSource = parameters[0].ValueAsText
        musSubtract = parameters[1].ValueAsText
        musResult = parameters[2].ValueAsText
        fields = parameters[3].ValueAsText

        selectedSource = {}
        getTables = re.compile("\n\n(\w+)")
        with open(musSource,"r") as musSourceFile:
            musSourceTxt = "\n\n" + musSourceFile.read()
            tables = getTables.findall(musSourceTxt)
            musSourceTxtLines = musSourceTxt.split("\n")
            for table in tables:
                linei = [i for i,a in enumerate(musSourceTxtLines) if a == table]
                selectedSource[table] = []
                i = linei[0]+1
                while not musSourceTxtLines[i] == "":
                    selectedSource[table].append(musSourceTxtLines[i])
                    i += 1
                
        selectedSubtract = {}
        getTables = re.compile("\n\n(\w+)")
        with open(musSubtract,"r") as musSubtractFile:
            musSubtractTxt = "\n\n" + musSubtractFile.read()
            tables = getTables.findall(musSubtractTxt)
            musSubtractTxtLines = musSubtractTxt.split("\n")
            for table in tables:
                linei = [i for i,a in enumerate(musSubtractTxtLines) if a == table]
                selectedSubtract[table] = []
                i = linei[0]+1
                while not musSubtractTxtLines[i] == "":
                    selectedSubtract[table].append(musSubtractTxtLines[i])
                    i += 1

        for table,value in selectedSubtract.items():
            removed = 0
            for selection in value:
                if selection in selectedSource[table]:
                    selectedSource[table].remove(selection)
                    removed += 1
            if removed>0:
                arcpy.AddMessage("Removed %d items from table %s" % (removed,table))
        
        with open(musResult,"w") as musResultFile:
            for table,value in selectedSource.items():
                if not fields or not table in fields:
                    musResultFile.write(table + "\n")
                    for selection in value:
                        musResultFile.write(selection + "\n")
                    musResultFile.write("\n")
        return