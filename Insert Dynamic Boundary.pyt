# -*- coding: utf-8 -*-
"""
Created on Fri Jan 10 07:02:03 2020

@author: eni
"""

import arcpy
import os
from shutil import copyfile
from subprocess import call
import subprocess
import re
import sys
from datetime import datetime
import codecs
import mikeio

        
workingDir = os.path.dirname(__file__)
prfFileCopy = workingDir + "\prffile.PRF"
M11OUT = workingDir + "\M11.OUT"
M11IN = workingDir + "\M11.IN"

class Toolbox(object):
    def __init__(self):
        self.label =  "Insert Dynamic Boundary from PRF"
        self.alias  = "Insert Dynamic Boundary from PRF"

        # List of tool classes associated with this toolbox
        self.tools = [InsertWaterLevelBoundary,InsertFlowBoundary] 

class InsertWaterLevelBoundary(object):
    def __init__(self):
        self.label       = "Insert Water Level Boundary into Mike Urban model"
        self.description = "Insert Water Level Boundary into Mike Urban model"
        self.canRunInBackground = True

    def getParameterInfo(self):
        #Define parameter definitions

        # Input Features parameter
        PFRFile = arcpy.Parameter(
            displayName="Input PRF File:",
            name="PFRFile",
            datatype="File",
            parameterType="Required",
            direction="Input")
        PFRFile.filter.list=["PRF"]
        
        node = arcpy.Parameter(
            displayName= "Node to retrieve water level from:",  
            name="node",  
            datatype="GPString",  
            parameterType="Required", 
            direction="Input") 
        
        dfs0File = arcpy.Parameter(
            displayName="Output DFS0 File:",
            name="dfs0File",
            datatype="File",
            parameterType="Required",
            direction="Output")
        dfs0File.filter.list=["dfs0"]
        
        MU_database = arcpy.Parameter(
            displayName="Insert External Water Level into Mike Urban database",
            name="database",
            datatype="DEWorkspace",
            parameterType="Optional",
            direction="Input")
            
        m11extra_path = arcpy.Parameter(
            displayName="m11extra Executable path",
            name="m11extra_path",
            datatype="File",
            parameterType="Required",
            direction="Input")
        m11extra_path.filter.list=["exe"]
        
        m11extra_paths = [r"C:\Program Files (x86)\DHI\2020\bin\m11extra.exe"]
        for path in m11extra_paths:
            for year in reversed(range(2010,2030)):
                if os.path.exists(path.replace("2020",str(year))):
                    m11extra_path.value = path.replace("2020",str(year))
                    break
            
        parameters = [PFRFile, node, dfs0File, MU_database, m11extra_path]
        
        return parameters

    def isLicensed(self): #optional
        return True

    def updateParameters(self, parameters): #optional
        m11extra_path = parameters[4].ValueAsText
        if parameters[0].altered and len(parameters[1].filter.list)==0:
            prfFile = parameters[0].ValueAsText
            copyfile(prfFile,prfFileCopy)
            try:
                call([m11extra_path, prfFileCopy])
            except Exception as e:
                raise(Exception([m11extra_path, prfFileCopy]))
            with codecs.open(M11OUT,'r','cp1252') as M11OUTFile:
                matches = re.findall("Node_WL:  <([^>]+)>",M11OUTFile.read())
            nodes = []
            for match in matches:
                nodes.append(match)
            nodes.sort()
            parameters[1].filter.list = nodes
        if parameters[0].altered or parameters[1].altered:
            if parameters[0].ValueAsText and parameters[1].ValueAsText and not parameters[2].ValueAsText:
                parameters[2].Value = os.path.dirname(parameters[0].ValueAsText) + "\\" + parameters[1].ValueAsText + ".dfs0"
        return

    def updateMessages(self, parameters): #optional
        return

    def execute(self, parameters, messages):
        node = parameters[1].ValueAsText
        dfs0File = parameters[2].ValueAsText
        prfFile = parameters[0].ValueAsText
        MU_database = parameters[3].ValueAsText
        m11extra_path = parameters[4].ValueAsText
        
        copyfile(prfFile,prfFileCopy)

        lines = ""
        with codecs.open(M11OUT,'r','cp1252') as M11OUTFile:
            for linei,line in enumerate(M11OUTFile):
                try:
                    if "Node_WL:  <%s>" % node in line:
                        line = re.sub("^0","1",line)
                    lines += line
                except UnicodeDecodeError:
                    lines += line
                    arcpy.AddWarning(u"Line no. %d in file %s contains illegal character." % (linei,M11OUT))
                except Exception as e:
                    raise(e)
                       
        with codecs.open(M11IN.replace(".OUT",".IN"),'w','cp1252') as M11INFile:
            M11INFile.write(lines)
        csvFile = "%s.csv" % node
        os.chdir(workingDir)
        call([m11extra_path, "prffile.PRF", csvFile, "/NOHEADER"])
        readCSVRe = re.compile('(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) +([\d\.]+)')
        dates = []
        waterlevels = []
        
        with open(csvFile,"r") as f:
            for line in f:
                matches = readCSVRe.findall(line)
                dates.append(matches[0][0])
                waterlevels.append(matches[0][1])
        datesDT = [datetime.strptime(a,"%Y-%m-%d %H:%M:%S") for a in dates]        
        
        # Building .dfs0
        # factory = DHI.Generic.MikeZero.DFS.DfsFactory()
        # builder = DHI.Generic.MikeZero.DFS.DfsBuilder.Create(
                # 'Python dfs0 file', 'Python DFS', 0)
        # starttimeDT = System.DateTime(
            # *
            # datesDT[0].timetuple()[
                # :6],
            # kind=System.DateTimeKind.Utc)
        # timeSeconds = [0]
        # for i in range(len(datesDT)-1):
            # timeSeconds.append((datesDT[i+1]-datesDT[0]).seconds + (datesDT[i+1]-datesDT[0]).days*24*60*60)
        
        # builder.SetDataType(0)
        # builder.SetGeographicalProjection(
            # factory.CreateProjectionGeoOrigin(
                # 'UTM-33', 12, 54, 2.6))
        # builder.SetTemporalAxis(
            # factory.CreateTemporalNonEqCalendarAxis(
                # DHI.Generic.MikeZero.eumUnit.eumUsec,
                # starttimeDT))
        
        # item1 = builder.CreateDynamicItemBuilder()
        # dfsdataType = DHI.Generic.MikeZero.DFS.DfsSimpleType.Double
        # item1.Set(
            # 'Vandniveau',
            # DHI.Generic.MikeZero.eumQuantity(
                # DHI.Generic.MikeZero.eumItem.eumIWaterLevel,
                # DHI.Generic.MikeZero.eumUnit.eumUmeter),
            # dfsdataType)
                
        # item1.SetValueType(DHI.Generic.MikeZero.DFS.DataValueType.Instantaneous)
        # item1.SetAxis(factory.CreateAxisEqD0())
        # builder.AddDynamicItem(item1.GetDynamicItemInfo())
        # builder.CreateFile(dfs0File)
        # dfs = builder.GetFile()

        # waterlevelsArr = System.Array.CreateInstance(float, len(waterlevels), 1)
        # for i, val in enumerate(waterlevels):
            # waterlevelsArr[i, 0] = val
        
        dfs0_file = mikeio.dfs0.Dfs0(dfs0File)
        dfs0_file.write(dfs0File, data = [np.array(waterlevels)], start_time = datesDT[0], dt = 60, 
                        items = [mikeio.eum.ItemInfo("Vandniveau", itemtype = mikeio.eum.EUMType.Water_Level, unit = mikeio.eum.EUMUnit.meter)], datetimes = datesDT, title = node)
        
        # MatlabDfsUtil.DfsUtil.WriteDfs0DataDouble(
                # dfs, Array[float](timeSeconds), waterlevelsArr)
        # dfs.Close()
        if MU_database:
            with arcpy.da.SearchCursor(MU_database + r"\msm_BBoundary",['NodeID','MUID']) as cursor:
                nodeInBBoundary = False
                for row in cursor:
                    if row[0] == node:
                        nodeInBBoundary = True
                        BoundaryID = row[1]
                        with arcpy.da.UpdateCursor(MU_database + "\msm_BItem",["BoundaryID",'TSConnection','DataTypeName','TimeseriesName']) as cursor2: 
                            itemInBItem = False
                            for row2 in cursor2:
                                if row2[0] == BoundaryID:
                                    row2[1] = dfs0File
                                    row2[2] = "Vandniveau"
                                    row2[3] = node
                                    itemInBItem = True
                            if not itemInBItem:
                                raise(Exception("Found external water level setting but no matching item"))
                        break
                        
                        
            if not nodeInBBoundary:
                with arcpy.da.InsertCursor(MU_database + r"\msm_BBoundary",['MUID', 'ApplyBoundaryNo', 'GroupNo', 'TypeNo', 'ConnectionTypeNo', 'SourceLocationNo', 'IndividualConnectionNo', 'NodeID', 'NodeLoadTypeNo', 'CatchLoadNo', 'OpenBoundaryNo', 'Kmix', 'DistributeNo', 'LoadCategoryNo', 'GridTypeNo']) as cursor:
                    MUID = node + "_WL"
                    applyBoundaryNo = 1
                    groupNo = 3
                    typeNo = 12
                    connectionTypeNo = 3
                    sourceLocationNo = 0
                    individualConnectionNo = 1
                    nodeLoadTypeNo = 1
                    catchLoadNo = 0
                    openBoundary = 0
                    kMix = 0.5
                    distributeNo = 0
                    loadCategoryNo = 1
                    gridTypeNo = 1
                    cursor.insertRow([
                        MUID,
                        applyBoundaryNo,
                        groupNo,
                        typeNo,
                        connectionTypeNo,
                        sourceLocationNo,
                        individualConnectionNo,
                        node,
                        nodeLoadTypeNo,
                        catchLoadNo,
                        openBoundary,
                        kMix,
                        distributeNo,
                        loadCategoryNo,
                        gridTypeNo
                        ])
                with arcpy.da.InsertCursor(MU_database + "\msm_BItem",['MUID', 'BoundaryID', 'BoundaryType', 'TypeNo', 'Fraction', 'LoadTypeNo', 'VariationNo', 'StartUpNo', 'StartUpTime', 'BridgeTypeNo', 'TSConnection', 'DataTypeName', 'TimeseriesName', 'WholeFileNo', 'ValidityIntervalNo', 'ValidityBegin', 'ValidityEnd']) as cursor: 
                    MUID = node + "_WLItem"
                    boundaryID = node + "_WL"
                    boundaryType = 12
                    typeNo = 1
                    fraction = 1
                    loadTypeNo = 1
                    variationNo = 3
                    startUpNo = 0
                    startUpTime = 60
                    bridgeTypeNo = 2
                    tSConnection = dfs0File
                    dataTypeName = "Water Level"
                    timeseriesName = "Vandniveau"
                    wholeFileNo = 1
                    validityIntervalNo = 0
                    validityBegin = "01-01-1900"
                    validityEnd = "01-01-2100"
                    cursor.insertRow([
                            MUID,
                            boundaryID,
                            boundaryType,
                            typeNo,
                            fraction,
                            loadTypeNo,
                            variationNo,
                            startUpNo,
                            startUpTime,
                            bridgeTypeNo,
                            tSConnection,
                            dataTypeName,
                            timeseriesName,
                            wholeFileNo,
                            validityIntervalNo,
                            validityBegin,
                            validityEnd
                            ])
        
        for f in [csvFile,prfFileCopy]:
            if os.path.isfile(f):
                os.remove(f)
                
        
        return

class InsertFlowBoundary(object):
    def __init__(self):
        self.label       = "Insert Flow Boundary into Mike Urban model"
        self.description = "Insert Flow Boundary into Mike Urban model"
        self.canRunInBackground = True

    def getParameterInfo(self):
        #Define parameter definitions

        # Input Features parameter
        PFRFile = arcpy.Parameter(
            displayName="Input PRF File:",
            name="PFRFile",
            datatype="File",
            parameterType="Required",
            direction="Input")
        PFRFile.filter.list=["PRF"]
        
        link = arcpy.Parameter(
            displayName= "Link to retrieve flow from:",  
            name="link",  
            datatype="GPString",  
            parameterType="Required",
            direction="Input") 
        
        dfs0File = arcpy.Parameter(
            displayName="Output DFS0 File:",
            name="dfs0File",
            datatype="File",
            parameterType="Required",
            direction="Output")
        dfs0File.filter.list=["dfs0"]
        
        MU_database = arcpy.Parameter(
            displayName="Insert External Water Level into Mike Urban database",
            name="database",
            datatype="DEWorkspace",
            parameterType="Optional",
            direction="Input")
            
        parameters = [PFRFile, link, dfs0File, MU_database]
        
        return parameters

    def isLicensed(self): #optional
        return True

    def updateParameters(self, parameters): #optional
        if parameters[0].altered and len(parameters[1].filter.list)==0:
            prfFile = parameters[0].ValueAsText
            copyfile(prfFile,prfFileCopy)
            call([m11extraPath, prfFileCopy])
            with codecs.open(M11OUT,'r','cp1252') as M11OUTFile:
                matches = re.findall("Link_Q:   <([^>]+)>",M11OUTFile.read())
            nodes = []
            for match in matches:
                nodes.append(match)
            nodes.sort()
            parameters[1].filter.list = nodes
        if parameters[0].altered or parameters[1].altered:
            if parameters[0].ValueAsText and parameters[1].ValueAsText and not parameters[2].ValueAsText:
                parameters[2].Value = os.path.dirname(parameters[0].ValueAsText) + "\\" + parameters[1].ValueAsText + ".dfs0"
        return

    def updateMessages(self, parameters): #optional
        return

    def execute(self, parameters, messages):
        pipeID = parameters[1].ValueAsText
        dfs0File = parameters[2].ValueAsText
        prfFile = parameters[0].ValueAsText
        MU_database = parameters[3].ValueAsText
        
        copyfile(prfFile,prfFileCopy)
        sys.path.append(workingDir + "\clr")
        import clr
        clr.AddReference(workingDir + r"\DHI MIKE SDK\DHI.Generic.MikeZero.DFS.dll")
        clr.AddReference(workingDir + r"\DHI MIKE SDK\DHI.Generic.MikeZero.EUM.dll")
        clr.AddReference(workingDir + r"\DHI MIKE SDK\MatlabDfsUtil.2016.dll")
        import MatlabDfsUtil
        import DHI.Generic.MikeZero
        import DHI.Generic.MikeZero.DFS
        import DHI.Generic.MikeZero.DFS.dfs0
        import DHI.Generic.MikeZero.DFS.dfs123
        from System import Array, Char
        import System

        lines = ""
        with codecs.open(M11OUT,'r','cp1252') as M11OUTFile:
            for linei,line in enumerate(M11OUTFile):
                try:
                    if "Link_Q:   <%s>" % pipeID in line:
                        line = re.sub("^0","1",line)
                    lines += line
                except UnicodeDecodeError:
                    lines += line
                    arcpy.AddWarning(u"Line no. %d in file %s contains illegal character." % (linei,M11OUT))
                except Exception as e:
                    raise(e)
                       
        with codecs.open(M11IN.replace(".OUT",".IN"),'w','cp1252') as M11INFile:
            M11INFile.write(lines)
        csvFile = "%s.csv" % pipeID
        os.chdir(workingDir)
        call([m11extraPath, "prffile.PRF", csvFile, "/NOHEADER"])
        readCSVRe = re.compile('(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) +([-\d\.]+)')
        dates = []
        flows = []

        with open(csvFile,"r") as f:
            for line in f:
                matches = readCSVRe.findall(line)
                dates.append(matches[0][0])
                flows.append(matches[0][1])
        datesDT = [datetime.strptime(a,"%Y-%m-%d %H:%M:%S") for a in dates]

        # Building .dfs0
        factory = DHI.Generic.MikeZero.DFS.DfsFactory()
        builder = DHI.Generic.MikeZero.DFS.DfsBuilder.Create(
                'Python dfs0 file', 'Python DFS', 0)
        starttimeDT = System.DateTime(
            *
            datesDT[0].timetuple()[
                :6],
            kind=System.DateTimeKind.Utc)
        timeSeconds = [0]
        for i in range(len(datesDT)-1):
            timeSeconds.append((datesDT[i+1]-datesDT[0]).seconds + (datesDT[i+1]-datesDT[0]).days*24*60*60)

        builder.SetDataType(0)
        builder.SetGeographicalProjection(
            factory.CreateProjectionGeoOrigin(
                'UTM-33', 12, 54, 2.6))
        builder.SetTemporalAxis(
            factory.CreateTemporalNonEqCalendarAxis(
                DHI.Generic.MikeZero.eumUnit.eumUsec,
                starttimeDT))

        item1 = builder.CreateDynamicItemBuilder()
        dfsdataType = DHI.Generic.MikeZero.DFS.DfsSimpleType.Double
        item1.Set(
            'Discharge',
            DHI.Generic.MikeZero.eumQuantity(
                DHI.Generic.MikeZero.eumItem.eumIDischarge,
                DHI.Generic.MikeZero.eumUnit.eumUm3PerSec),
            dfsdataType)
                
        item1.SetValueType(DHI.Generic.MikeZero.DFS.DataValueType.Instantaneous)
        item1.SetAxis(factory.CreateAxisEqD0())
        builder.AddDynamicItem(item1.GetDynamicItemInfo())
        builder.CreateFile(dfs0File)
        dfs = builder.GetFile()

        waterlevelsArr = System.Array.CreateInstance(float, len(flows), 1)
        for i, val in enumerate(flows):
            waterlevelsArr[i, 0] = val

        MatlabDfsUtil.DfsUtil.WriteDfs0DataDouble(
                dfs, Array[float](timeSeconds), waterlevelsArr)
        dfs.Close()

        if MU_database:
            if (pipeID + "_Flow") in [row[0] for row in arcpy.da.SearchCursor(MU_database + r"\msm_BBoundary","MUID")]:
                arcpy.AddWarning("Pipe %s already exists in network loads and will not be modified. " % (pipeID) +
                                 "Delete it from the Mike Urban model to update it")
            else:
                with arcpy.da.InsertCursor(MU_database + r"\msm_BBoundary",['MUID', 'ApplyBoundaryNo', 'GroupNo', 'TypeNo', 'ConnectionTypeNo', 'SourceLocationNo', 'IndividualConnectionNo', 'LinkID', 'NodeLoadTypeNo', 'CatchLoadNo', 'OpenBoundaryNo', 'Kmix', 'DistributeNo', 'LoadCategoryNo', 'GridTypeNo']) as cursor:
                            MUID = pipeID + "_Flow"
                            applyBoundaryNo = 1
                            groupNo = 2
                            typeNo = 5
                            connectionTypeNo = 3
                            sourceLocationNo = 0
                            individualConnectionNo = 2
                            nodeLoadTypeNo = 1
                            catchLoadNo = 0
                            openBoundary = 0
                            kMix = 0.5
                            distributeNo = 0
                            loadCategoryNo = 1
                            gridTypeNo = 1
                            cursor.insertRow([
                                MUID,
                                applyBoundaryNo,
                                groupNo,
                                typeNo,
                                connectionTypeNo,
                                sourceLocationNo,
                                individualConnectionNo,
                                pipeID,
                                nodeLoadTypeNo,
                                catchLoadNo,
                                openBoundary,
                                kMix,
                                distributeNo,
                                loadCategoryNo,
                                gridTypeNo
                                ])
                
            if (pipeID + "_FlowItem") in [row[0] for row in arcpy.da.SearchCursor(MU_database + r"\msm_BItem","MUID")]:
                arcpy.AddWarning("Pipe %s already exists in boundary items and will not be modified. " % (pipeID) +
                                 "Delete it from the Mike Urban model to update it")
            else:
                with arcpy.da.InsertCursor(MU_database + "\msm_BItem",['MUID', 'BoundaryID', 'BoundaryType', 'TypeNo', 'Fraction', 'LoadTypeNo', 'VariationNo', 'StartUpNo', 'StartUpTime', 'BridgeTypeNo', 'TSConnection', 'DataTypeName', 'TimeseriesName', 'WholeFileNo', 'ValidityIntervalNo', 'ValidityBegin', 'ValidityEnd']) as cursor: 
                    MUID = pipeID + "_FlowItem"
                    boundaryID = pipeID + "_Flow"
                    boundaryType = 5
                    typeNo = 1
                    fraction = 1
                    loadTypeNo = 1
                    variationNo = 3
                    startUpNo = 0
                    startUpTime = 60
                    bridgeTypeNo = 2
                    tSConnection = dfs0File
                    dataTypeName = "Discharge"
                    timeseriesName = "Discharge"
                    wholeFileNo = 1
                    validityIntervalNo = 0
                    validityBegin = "01-01-1900"
                    validityEnd = "01-01-2100"
                    cursor.insertRow([
                            MUID,
                            boundaryID,
                            boundaryType,
                            typeNo,
                            fraction,
                            loadTypeNo,
                            variationNo,
                            startUpNo,
                            startUpTime,
                            bridgeTypeNo,
                            tSConnection,
                            dataTypeName,
                            timeseriesName,
                            wholeFileNo,
                            validityIntervalNo,
                            validityBegin,
                            validityEnd
                            ])
        
        for f in [csvFile,prfFileCopy]:
            if os.path.isfile(f):
                os.remove(f)
                
        
        return
