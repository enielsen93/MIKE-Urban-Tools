# -*- coding: utf-8 -*-
import os
import arcpy
import numpy as np
import re
from arcpy import env
arcpy.env.addOutputsToMap = False
import codecs
import sys
functionsPath = [r"K:\Hydrauliske modeller\Makroer & Beregningsark\Functions", r"C:\Dokumenter\Makroer\Functions", os.path.join(os.path.dirname(os.path.dirname(__file__)),"Functions")]
i = 0
while not os.path.exists(functionsPath[i]):
    i += 1
sys.path.append(functionsPath[i])
import readERF
import colebrookWhite
import networker
import codecs
m11extraPath = r"C:\Program Files (x86)\DHI\2016\bin\m11extra.exe"
i = 2030
while not os.path.exists(m11extraPath.replace("2016",str(i))):
    i -= 1
m11extraPath = m11extraPath.replace("2016",str(i))
from subprocess import call
from shutil import copyfile
import traceback

def getAvailableFilename(filepath):
    if arcpy.Exists(filepath):
        i = 1
        while arcpy.Exists(filepath + "%d" % i):
            i += 1
        return filepath + "%d" % i
    else: 
        return filepath
 
class Toolbox(object):
    def __init__(self):
        self.label =  "Display Mike Urban Results"
        self.alias  = "Display Mike Urban Results"

        # List of tool classes associated with this toolbox
        self.tools = [DisplayFloodReturnPeriodFun, DisplayWeirStatistics, DisplayFlowStatistics, DisplayQFullQMax] 

class DisplayFloodReturnPeriodFun(object):
    def __init__(self):
        self.label       = "Display Flood Return Period"
        self.description = "Display Flood Return Period"
        self.canRunInBackground = False

    def getParameterInfo(self):
        #Define parameter definitions

        # Input Features parameter
        erfFile = arcpy.Parameter(
            displayName="ERF file",
            name="erfFile",
            datatype="File",
            parameterType="Required",
            direction="Input")
        erfFile.filter.list=["erf"]
        
        observationPeriod = arcpy.Parameter(
            displayName="Observation period of ERF file",
            name="observationPeriod",
            datatype="Double",
            parameterType="Required",
            direction="Input")      
        
        MU_database = arcpy.Parameter(
            displayName="Mike Urban Database",
            name="database",
            datatype="DEWorkspace",
            parameterType="Required",
            direction="Input")
        
        exportShape = arcpy.Parameter(
            displayName="Output manholes with Flood Return Period",
            name="exportShape",
            datatype="DEShapefile",
            parameterType="Required",
            direction="Output")
            
        exportBasins = arcpy.Parameter(
            displayName="Output basins with Flood Return Period",
            name="exportBasins",
            datatype="DEShapefile",
            parameterType="Required",
            direction="Output")
            
        flowFile = arcpy.Parameter(
            displayName="Include PRF file in order to show maximum discharge from basins and permanent water volume",
            name="flowFile",
            datatype="File",
            parameterType="Optional",
            direction="Input")
        flowFile.filter.list=["prf"]
        
        traceNetwork = arcpy.Parameter(
            displayName="Calculate connected catchment area for each basin",
            name="traceNetwork",
            datatype="Boolean",
            parameterType="Optional",
            direction="Input")
        traceNetwork.category = "Get Catchment Area"
        
        reaches = arcpy.Parameter(
            displayName="Trace network through:",
            name="reaches",
            datatype="GPString",
            parameterType="Optional",
            multiValue=True,
            direction="Input")
        reaches.filter.type = "ValueList"  
        reaches.filter.list = ["Orifice","Weir","Pump", "Basin"]
        reaches.value = ["Orifice","Weir","Pump", "Basin"]
        reaches.category = "Get Catchment Area"
        
        breakChainOnNodes = arcpy.Parameter(
            displayName="End each trace at following node MUIDs (each node should by delimited by a comma: node1, node2)",
            name="breakChainOnNodes",
            datatype="GPString",
            parameterType="optional",
            direction="Input")
        breakChainOnNodes.category = "Additional settings"
        breakChainOnNodes.category = "Get Catchment Area"
            
        parameters = [erfFile, observationPeriod, MU_database, exportShape, exportBasins, flowFile, traceNetwork, reaches, breakChainOnNodes]
        
        return parameters

    def isLicensed(self): #optional
        return True

    def updateParameters(self, parameters): #optional
        if parameters[0].altered and parameters[0].value and not parameters[1].value:
            with open(parameters[0].ValueAsText,"r") as f:
                txt = f.read()
                observationPeriod = float(re.findall(r"Observation_period =[^,]+,[^,]+,([^\n]+)",txt)[0])
                parameters[1].value = observationPeriod
        return

    def updateMessages(self, parameters): #optional
        return

    def execute(self, parameters, messages):
        erfFile = parameters[0].ValueAsText
        observationPeriod = float(parameters[1].ValueAsText)
        MUDatabase = parameters[2].ValueAsText
        msm_Node = MUDatabase + "\msm_Node"
        msm_Link = MUDatabase + "\msm_Link"
        msm_Weir = MUDatabase + "\msm_Weir"
        msm_Orifice = MUDatabase + "\msm_Orifice"
        msm_Pump = os.path.join(MUDatabase,"msm_Pump")
        msm_CatchCon = os.path.join(MUDatabase,"msm_CatchCon")
        ms_Catchment = os.path.join(MUDatabase,"ms_Catchment")
        msm_HModA = os.path.join(MUDatabase,"msm_HModA")
        msm_HParA = os.path.join(MUDatabase,"msm_HParA")
        
        exportShape = parameters[3].ValueAsText
        exportBasins = parameters[4].ValueAsText
        flowFile = parameters[5].ValueAsText
        traceNetwork = parameters[6].ValueAsText
        reaches = parameters[7].ValueAsText
        
        arcpy.SetProgressorLabel("Getting critical level for manholes")
        MUIDsHCrit = {}
        with arcpy.da.SearchCursor(msm_Node,["MUID","GroundLevel","CriticalLevel"]) as cursor:
            for row in cursor:
                if row[2]:
                    MUIDsHCrit[row[0]] = row[2]
                else:
                    MUIDsHCrit[row[0]] = row[1]
        MUIDs = MUIDsHCrit.keys()
        if flowFile:
            arcpy.SetProgressorLabel("Getting Discharge from Basins")
            workingDir = os.path.dirname(__file__)
            M11OUT = workingDir + "\M11.OUT"
            M11IN = workingDir + "\M11.IN"

            prfFileCopy = workingDir + "\prffile.PRF"
            resultFile = workingDir + "\ResultFile.txt"
            
            copyfile(flowFile,prfFileCopy)
            call([m11extraPath, prfFileCopy])

            lines = ""
            links = []
            with codecs.open(M11OUT,'r','cp1252') as M11OUTFile:
                for linei,line in enumerate(M11OUTFile):
                    try:
                        if ("Link_Q" in line or "Weir_Q" in line or "Orifice_Q" in line) and re.findall("<([^>]+)>",line)[0] not in links:		
                            links.append(re.findall("<([^>]+)>",line)[0])
                            line = re.sub("^0","1",line)
                        lines += line
                    except UnicodeDecodeError:
                        lines += line
                        arcpy.AddWarning(u"Line no. %d in file %s contains illegal character." % (linei,M11OUT))
                    except Exception as e:
                        raise(e)
                           
            with codecs.open(M11IN,'w','cp1252') as M11INFile:
                M11INFile.write(lines)

            call([m11extraPath, prfFileCopy, resultFile])

            linksFlow = []
            with codecs.open(resultFile,'r','cp1252') as M11OUTFile:
                txt = M11OUTFile.readlines()

            linksFlow = {}
            for link in links:
                linksFlow[link] = []
            lines = range([i for i,line in enumerate(txt) if "M11 DATA" in line][0]+1,len(txt))
            for i in lines:
                line = txt[i]
                values = line.split("  ")
                for valuei in range(1,len(values)):
                    linksFlow[links[valuei-1]].append(float(values[valuei]))
            os.remove(resultFile)
            os.remove(M11IN)
            
            lines = ""
            nodes = []
            basins = [row[0] for row in arcpy.da.SearchCursor(msm_Node, "MUID", where_clause = "TypeNo = 2")]
            with codecs.open(M11OUT,'r','cp1252') as M11OUTFile:
                for linei,line in enumerate(M11OUTFile):
                    try:
                        if "Node_WL" in line and re.findall("<([^>]+)>",line)[0] in basins:		
                            nodes.append(re.findall("<([^>]+)>",line)[0])
                            line = re.sub("^0","1",line)
                        lines += line
                    except UnicodeDecodeError:
                        lines += line
                        arcpy.AddWarning(u"Line no. %d in file %s contains illegal character." % (linei,M11OUT))
                    except Exception as e:
                        raise(e)
                           
            with codecs.open(M11IN,'w','cp1252') as M11INFile:
                M11INFile.write(lines)
            
            call([m11extraPath, prfFileCopy, resultFile])
            nodesMinWL = {}
            with codecs.open(resultFile,'r','cp1252') as M11OUTFile:
                txt = M11OUTFile.readlines()
            
            findValues = re.compile(r" ([\d\.]+)")
            for vali,val in enumerate(findValues.findall(txt[[i for i,line in enumerate(txt) if "M11 DATA" in line][0]+1])[1:]):
                nodesMinWL[nodes[vali]] = float(val)
            
            os.remove(prfFileCopy)
            os.remove(M11OUT)
            os.remove(resultFile)
            os.remove(M11IN)
            
            msm_LinkFromNode = {}
            msm_LinkToNode = {}
            with arcpy.da.SearchCursor(msm_Link,["MUID","FromNode","ToNode"]) as cursor:
                for row in cursor:
                    msm_LinkFromNode[row[0]] = row[1]
                    msm_LinkToNode[row[0]] = row[2]
            with arcpy.da.SearchCursor(msm_Weir,["MUID","FromNode","ToNode"]) as cursor:
                for row in cursor:
                    msm_LinkFromNode[row[0]] = row[1]
                    msm_LinkToNode[row[0]] = row[2]
            with arcpy.da.SearchCursor(msm_Orifice,["MUID","FromNode","ToNode"]) as cursor:
                for row in cursor:
                    msm_LinkFromNode[row[0]] = row[1]
                    msm_LinkToNode[row[0]] = row[2]
        arcpy.SetProgressorLabel("Reading ERF-file")
        dataTables = readERF.readERF(erfFile,"MaxLevel_Ranked",MUIDs)
        
        arcpy.SetProgressorLabel("Getting return period of flooding")
        MUIDsTCrit = {}
        for i,MUID in enumerate(MUIDs):
            nodeH = dataTables[i]["col2"]
            if MUIDsHCrit[MUID]>np.max(nodeH):
                MUIDsTCrit[MUID] = 1000
            elif MUIDsHCrit[MUID]<np.min(nodeH):
                MUIDsTCrit[MUID] = 0
            else:
                MUIDsTCrit[MUID] = np.interp(MUIDsHCrit[MUID],
                      np.flipud(nodeH),
                      np.flipud(float(observationPeriod)/(np.array(range(len(nodeH)))+1)))
        
        arcpy.SetProgressorLabel("Creating manhole result file")
        msm_NodeNew = arcpy.CopyFeatures_management(msm_Node,exportShape)

        arcpy.AddField_management (msm_NodeNew, "TCrit", "DOUBLE", 10, 5)
        with arcpy.da.UpdateCursor(msm_NodeNew,["MUID","TCrit"]) as cursor:
            for row in cursor:
                if row[0] in MUIDsTCrit:
                    row[1] = MUIDsTCrit[row[0]]
                cursor.updateRow(row)
                
        mxd = arcpy.mapping.MapDocument("CURRENT")
        df = arcpy.mapping.ListDataFrames(mxd)[0]
        arcpy.env.addOutputsToMap = False
        nodeLayer = arcpy.mapping.Layer(os.path.dirname(os.path.realpath(__file__)) + "\Data\msm_Node.lyr")
        nodeLayer = arcpy.mapping.AddLayer(df, nodeLayer)
        nodeLayer = arcpy.mapping.ListLayers(mxd, nodeLayer, df)[0]
        nodeLayer.replaceDataSource(os.path.dirname(exportShape), "SHAPEFILE_WORKSPACE", os.path.basename(exportShape).split(".")[0])
        
        arcpy.SetProgressorLabel("Creating basin result file")
        arcpy.Select_analysis(MUDatabase + r"\mu_Geometry\msm_Node", exportBasins, where_clause = "TypeNo = 2")
        fields = ["MUID", "GeometryID","CriticalLe", "Volume", "TCrit", "CatchArea", "CatchImpA"]
        if flowFile:
            arcpy.AddField_management(exportBasins, "Discharge", "FLOAT")
            fields.append("Discharge")
        arcpy.AddField_management(exportBasins, "Volume", "FLOAT")
        arcpy.AddField_management(exportBasins, "TCrit", "FLOAT")
        arcpy.AddField_management(exportBasins, "CatchArea", "FLOAT")
        arcpy.AddField_management(exportBasins, "CatchImpA", "FLOAT")
        
        class Basin:
            def __init__(self, MUID):
                self.MUID = MUID
                self.discharge = None
                self.volume = None
                self.t_crit = None
                self.direct_catchment_area = None
                self.direct_catchment_area_impervious = None
                self.total_catchment_area = None
                self.total_catchment_area_impervious = None
        
        basins = {}
        for basin in [row[0] for row in arcpy.da.SearchCursor(exportBasins, ["MUID"])]:
            basins[basin] = Basin(basin)
        
        if traceNetwork:
            arcpy.SetProgressorLabel("Creating basin result file - analyzing basin catchment area")
            import networkx as nx
            breakChainOnNodes = parameters[8].ValueAsText
            networkLinks = [msm_Link]
            networkLinks.append(msm_Orifice) if "Orifice" in reaches else None
            networkLinks.append(msm_Weir) if "Weir" in reaches else None
            networkLinks.append(msm_Pump) if "Pump" in reaches else None
            
            network = nx.DiGraph()
            
            hParADict = {}
            with arcpy.da.SearchCursor(msm_HParA,["MUID","RedFactor"]) as cursor:
                for row in cursor:
                    hParADict[row[0]] = row[1]
                    
            catchmentImperviousnessDict = {}
            catchmentReductionFactor = {}
            with arcpy.da.SearchCursor(msm_HModA, ["CatchID", "ImpArea", "ParAID", "LocalNo", "RFactor"]) as cursor:
                for row in cursor:
                    catchmentImperviousnessDict[row[0]] = row[1]
                    catchmentReductionFactor[row[0]] = hParADict[row[2]] if row[3] == 0 else row[4]
                    
            catchmentConnectionDict = {}
            with arcpy.da.SearchCursor(msm_CatchCon, ["CatchID", "NodeID"]) as cursor:
                for row in cursor:
                    if row[1] not in catchmentConnectionDict:
                        catchmentConnectionDict[row[1]] = [row[0]]
                    else:
                        catchmentConnectionDict[row[1]].append(row[0])
                    
            catchmentAreaDict = {}
            catchmentPersonsDict = {}
            catchmentImperviousAreaDict = {}
            catchmentReducedAreaDict = {}
            catchmentNetTypeNoDict = {}
            catchmentStatus = {}
            with arcpy.da.SearchCursor(ms_Catchment, ['MUID','SHAPE@AREA','Area','Persons',"NetTypeNo", 'Element_S']) as cursor:
                for row in cursor:
                    catchmentPersonsDict[row[0]] = row[3] if row[3] is not None else 0
                    catchmentAreaDict[row[0]] = row[2]*1e4 if row[2] is not None else row[1]
                    catchmentNetTypeNoDict[row[0]] = row[4]
                    catchmentStatus[row[0]] = row[5]
                    if row[0] in catchmentImperviousnessDict:
                        catchmentImperviousAreaDict[row[0]] = catchmentImperviousnessDict[row[0]]/100 * catchmentAreaDict[row[0]]
                        catchmentReducedAreaDict[row[0]] = catchmentImperviousnessDict[row[0]]/100 * catchmentAreaDict[row[0]] * catchmentReductionFactor[row[0]]
                    else:
                        arcpy.AddWarning("Warning: Could not find model record for Catchment %s" % (row[0]))
                    
            nodeTypeDict = {}
            nodeTypes = {1:u"Brønd",2:"Bassin",3:u"Udløb"}
            with arcpy.da.SearchCursor(msm_Node,["MUID","TypeNo"]) as cursor:
                for row in cursor:
                    network.add_node(row[0])
                    nodeTypeDict[row[0]] = nodeTypes[row[1]]
                    
            weights = {"msm_Link":1, "msm_Pump":1e4, "msm_Orifice":1e4, "msm_Weir":1e4}
            for networkLink in networkLinks:
                weight = weights[os.path.basename(networkLink)]
                with arcpy.da.SearchCursor(networkLink,["FromNode","ToNode","SHAPE@LENGTH"]) as cursor:
                    for row in cursor:
                        network.add_edge(row[0],row[1], weight = weight*row[2])
            
            
            if not "Basin" in reaches:
                for basin in basins.values():
                    for edge in network.out_edges(basin.MUID):
                        network.remove_edge(basin.MUID,edge[1])
                        arcpy.AddMessage("Removed edge %s-%s because tracing through basins is disabled" % (basin.MUID,edge[1]))            
            
            if breakChainOnNodes:
                breakEdges = [edge for edge in network.edges if edge[0] in re.findall("([^'^(),; \n]+)",breakChainOnNodes)]
                network.remove_edges_from(breakEdges)
                for edge in breakEdges:
                    arcpy.AddMessage("Removed edge %s-%s because %s is included in list of nodes to end trace at" % (edge[0],edge[1]))
            
            outlets = []        
            junctions = []
            for node in list(network.nodes):
                if node:
                    if not network.out_edges(node):
                        outlets.append(node)
                    if len(network.out_edges(node))>1:
                        junctions.append(node)
            
            for source in junctions:
                if source != None:
                    lengths = np.ones((len(outlets),1))*1e9
                    for i,target in enumerate(outlets):
                        try:
                            if nx.has_path(network, source, target):
                                lengths[i] = (nx.bellman_ford_path_length(network, source, target, weight="weight"))
                        except:
                            arcpy.AddError("Failed upon tracing network from %s to %s" % (source,target))
                    toNode = nx.bellman_ford_path(network, source, outlets[np.argmin(lengths)])[1]
                    for edge in network.out_edges(source):
                        if not edge[1] == toNode:
                            network.remove_edge(source,edge[1])
                            arcpy.AddMessage("Removed edge %s-%s so that node %s exclusively leads to outlet %s" % (source,edge[1],source,outlets[np.argmin(lengths)]))
                            
            for basin in [row[0] for row in arcpy.da.SearchCursor(exportBasins, ["MUID"])]:
                nodesUpstream = nx.ancestors(network,basin)
                nodesUpstream.add(basin)
                catchIDs = [catchmentConnectionDict[n] for n in nodesUpstream if n in catchmentConnectionDict]
                catchIDs = [catchID for sublist in catchIDs for catchID in sublist]
                
                basins[basin].total_catchment_area = round(np.sum([catchmentAreaDict[catchID] for catchID in catchIDs])/1e4*100)/100
                basins[basin].total_catchment_area_impervious = round(np.sum([catchmentImperviousAreaDict[catchID] for catchID in catchIDs])/1e4*100)/100
                
        arcpy.SetProgressorLabel("Creating basin result file - analyzing basin volume")
        with arcpy.da.UpdateCursor(exportBasins, fields) as cursor:
            for row in cursor:
                with arcpy.da.SearchCursor(MUDatabase + r"\ms_TabD", ["Value1","Value3"],where_clause = "TabID = '%s'" % (row[1])) as msTabCursor:
                    basinH = []
                    basinA = []
                    for msTabRow in msTabCursor:
                        basinH.append(msTabRow[0])
                        basinA.append(msTabRow[1])
                        
                idxSort = np.argsort(basinH)
                basinH = np.array(basinH)
                basinA = np.array(basinA)
                basinH = basinH[idxSort]
                basinA = basinA[idxSort]
                if not row[2]:
                    try:
                        row[2] = np.max(basinH)
                    except Exception as e:
                        arcpy.AddError(row)
                        arcpy.AddError("ERROR: Failed to find a match for geomeotryID")
                        raise(e)
                basinHCrit = [a for a in basinH if a<row[2]] + [row[2]]
                basinACrit = np.interp([a for a in basinH if a<row[2]] + [row[2]],basinH,basinA)
                row[3] = np.trapz(basinACrit,basinHCrit)
                if flowFile:
                    basinHCrit = [a for a in basinH if a<nodesMinWL[row[0]]] + [nodesMinWL[row[0]]]
                    basinACrit = np.interp([a for a in basinH if a<nodesMinWL[row[0]]] + [nodesMinWL[row[0]]], basinH, basinA)
                    row[3] -= np.trapz(basinACrit,basinHCrit)
                try:
                    row[4] = MUIDsTCrit[row[0]]
                except Exception as e:
                    arcpy.AddWarning("Failed to find %s in General Report" % row[0])
                if flowFile:
                    row[7] = 0
                    flow = np.array(())
                    for link in [MUID for MUID,FromNode in msm_LinkFromNode.iteritems() if FromNode==row[0]]:
                        if len(flow) == 0:
                            flow = np.array(linksFlow[link])
                        else:
                            flow = flow + np.array(linksFlow[link])
                    if len(flow)==0:
                        arcpy.AddMessage("Could not find link that discharges from basin %s (%s). Assuming intlet is also outlet." % (row[0],row[1]))
                        for link in [MUID for MUID,ToNode in msm_LinkToNode.iteritems() if ToNode==row[0]]:
                            if len(flow) == 0:
                                flow = np.array([a*(-1) for a in linksFlow[link]])
                            else:
                                flow = flow + np.array([a*(-1) for a in linksFlow[link]])
                    # arcpy.AddMessage(flow)
                    row[7] += np.max(flow)
                    
                row[5] = basins[row[0]].total_catchment_area if basins[row[0]].total_catchment_area else 0
                row[6] = basins[row[0]].total_catchment_area_impervious if basins[row[0]].total_catchment_area_impervious else 0
                cursor.updateRow(row)
        
        if flowFile:
            basinLayer = arcpy.mapping.Layer(os.path.dirname(os.path.realpath(__file__)) + "\Data\MOUSE Basin Discharge.lyr")
        else:
            basinLayer = arcpy.mapping.Layer(os.path.dirname(os.path.realpath(__file__)) + "\Data\MOUSE Basin.lyr")
        basinLayer = arcpy.mapping.AddLayer(df, basinLayer)
        basinLayer = arcpy.mapping.ListLayers(mxd, basinLayer, df)[0]
        basinLayer.replaceDataSource(os.path.dirname(exportBasins), "SHAPEFILE_WORKSPACE", os.path.basename(exportBasins).split(".")[0])
        arcpy.RefreshTOC()
        arcpy.RefreshActiveView()
        return

class DisplayWeirStatistics(object):
    def __init__(self):
        self.label       = "Display Weir Statistics"
        self.description = "Display Weir Statistics"
        self.canRunInBackground = False

    def getParameterInfo(self):
        #Define parameter definitions

        # Input Features parameter
        htmlFile = arcpy.Parameter(
            displayName="Input LTS ERF File",
            name="htmlFile",
            datatype="File",
            parameterType="Required",
            direction="Input")
        htmlFile.filter.list=["html"]
        
        MU_database = arcpy.Parameter(
            displayName="Mike Urban Database",
            name="database",
            datatype="DEWorkspace",
            parameterType="Required",
            direction="Input")
            
        parameters = [htmlFile, MU_database]
        return parameters

    def isLicensed(self): #optional
        return True

    def updateParameters(self, parameters): #optional
        return

    def updateMessages(self, parameters): #optional
        return

    def execute(self, parameters, messages):
        htmlFile = parameters[0].ValueAsText
        MUDatabase = parameters[1].ValueAsText
        arcpy.env.addOutputsToMap = False
        msm_weir = arcpy.CopyFeatures_management(MUDatabase + "\msm_Weir", getAvailableFilename(arcpy.env.scratchGDB + "\msm_Weir"))

        weirs = {}
        arcpy.SetProgressorLabel("Getting FROMNODE and TONODE for pipes")
        link_network = networker.NetworkLinks(MUDatabase, map_only = "weir")
        with arcpy.da.SearchCursor(MUDatabase + "\msm_Weir",["MUID"]) as cursor:
            try:
                for row in cursor:
                    arcpy.AddMessage(row[0])
                    fromnode = link_network.weirs[row[0]].fromnode
                    tonode = link_network.weirs[row[0]].tonode if link_network.weirs[row[0]].tonode is not None else "0"
                    weirs["%s-%s" % (fromnode,tonode)] = row[0]
                    arcpy.AddMessage("%s-%s" % (fromnode,tonode))
            except Exception as e:
                arcpy.AddError(traceback.format_exc())
                raise(e)
                
        arcpy.SetProgressorLabel("Reading HTML-file")
        with codecs.open(htmlFile,'r',encoding='mbcs') as f:
            htmlFileTxt = f.read().split("\r\n")
            htmlFileTxt = np.array(htmlFileTxt)
            for line in htmlFileTxt:
                line = unicode(line)

        weirStart = [i for i,a in enumerate(htmlFileTxt) if "<H3>General statistics in weirs" in a][0]
        weirEnd = [i for i,a in enumerate(htmlFileTxt) if "TABLE" in a and i > weirStart][0]
        #nodeEnd = [i for i,a in enumerate(htmlFileTxt) if "TABLE" in a][1]
        htmlFileTxtWeirs = htmlFileTxt[weirStart:weirEnd]

        arcpy.SetProgressorLabel("Writing Shapefile")
        if "fromnode" not in [f.name for f in arcpy.ListFields(msm_weir[0])]:
            arcpy.AddField_management(msm_weir[0],"fromnode","TEXT")
        if "tonode" not in [f.name for f in arcpy.ListFields(msm_weir[0])]:
            arcpy.AddField_management(msm_weir[0],"tonode","TEXT")
        arcpy.AddField_management(msm_weir[0],"QVol","FLOAT")
        arcpy.AddField_management(msm_weir[0],"QNo","FLOAT")
        arcpy.AddField_management(msm_weir[0],"QHour","FLOAT")
        
        MUIDsQVol = {}
        MUIDsQNo = {}
        MUIDsQHours = {}

        getMUIDRe = re.compile(r"ALIGN=LEFT>([^<]+)")
        getQs = re.compile(r"<TD>([0-9 <>\.]+)<\/TD><TD>([0-9 <>\.]+)<\/TD><TD>([0-9 <>\.]+)<\/TD><\/TR>$")
        for line in htmlFileTxtWeirs:
            if "ALIGN=LEFT" in line:
                arcpy.AddMessage(weirs["%s-%s" % (getMUIDRe.findall(line)[0],getMUIDRe.findall(line)[1])])
                arcpy.AddMessage("%s-%s" % (getMUIDRe.findall(line)[0],getMUIDRe.findall(line)[1]))
                MUIDsQVol[weirs["%s-%s" % (getMUIDRe.findall(line)[0],getMUIDRe.findall(line)[1])]] = float(getQs.findall(line)[0][0])
                MUIDsQNo[weirs["%s-%s" % (getMUIDRe.findall(line)[0],getMUIDRe.findall(line)[1])]] = float(getQs.findall(line)[0][1])
                MUIDsQHours[weirs["%s-%s" % (getMUIDRe.findall(line)[0],getMUIDRe.findall(line)[1])]] = float(getQs.findall(line)[0][2])
        
        with arcpy.da.UpdateCursor(msm_weir[0],["MUID", "QVol", "QNo", "QHour", "fromnode", "tonode"]) as cursor:
            for row in cursor:
                if row[0] not in MUIDsQVol:
                    arcpy.AddError("Error: Could not find results of weir %s in result file" % (row[0]))
                else:
                    row[1] = MUIDsQVol[row[0]]
                    row[2] = MUIDsQNo[row[0]]
                    row[3] = MUIDsQHours[row[0]]
                    row[4] = link_network.weirs[row[0]].fromnode
                    row[5] = link_network.weirs[row[0]].tonode
                    cursor.updateRow(row)
                
        mxd = arcpy.mapping.MapDocument("CURRENT")
        df = arcpy.mapping.ListDataFrames(mxd)[0]
        arcpy.env.addOutputsToMap = False
        weirLayer = arcpy.mapping.Layer(os.path.dirname(os.path.realpath(__file__)) + "\Data\msm_Weir.lyr")
        weirLayer = arcpy.mapping.AddLayer(df, weirLayer,'TOP')
        weirLayer = arcpy.mapping.ListLayers(mxd, weirLayer, df)[0]
        weirLayer.replaceDataSource(os.path.dirname(msm_weir[0]), "FILEGDB_WORKSPACE", os.path.basename(msm_weir[0]).split(".")[0])
        
        weirLayer.name = os.path.splitext(os.path.basename(htmlFile))[0] + u" Weir Discharge"
        arcpy.RefreshTOC()
        
        return
        
class DisplayFlowStatistics(object):
    def __init__(self):
        self.label       = "Display Flow Statistics"
        self.description = "Display Flow Statistics"
        self.canRunInBackground = False

    def getParameterInfo(self):
        #Define parameter definitions

        # Input Features parameter
        erfFile = arcpy.Parameter(
            displayName="ERF file",
            name="erfFile",
            datatype="File",
            parameterType="Required",
            direction="Input")
        erfFile.filter.list=["erf"]
        
        observationPeriod = arcpy.Parameter(
            displayName="Observation period of ERF file",
            name="observationPeriod",
            datatype="Double",
            parameterType="Required",
            direction="Input")      
        
        MU_database = arcpy.Parameter(
            displayName="Mike Urban Database with links",
            name="database",
            datatype="DEWorkspace",
            parameterType="Required",
            direction="Input")
        
        exportShape = arcpy.Parameter(
            displayName="Output shapefile with link flow statistics",
            name="exportShape",
            datatype="DEShapefile",
            parameterType="Required",
            direction="Output")
            
        use_networker = arcpy.Parameter(
            displayName="Get fromnode and tonode attributes of pipes from spatial analysis?",
            name="use_networker",
            datatype="Boolean",
            category="Additional Settings",
            parameterType="Optional",
            direction="Input")
        use_networker.value = False
        
        export_cad = arcpy.Parameter(
            displayName="Export CAD File with results and outlet flows",
            name="export_cad",
            datatype="File",
            parameterType="Optional",
            category="Additional Settings",
            direction="Output")
        # export_cad.filter.list=["dxf"]
            
        parameters = [erfFile, observationPeriod, MU_database, exportShape, use_networker, export_cad]
        
        return parameters

    def isLicensed(self): #optional
        return True

    def updateParameters(self, parameters): #optional
        if parameters[0].altered and parameters[0].value and not parameters[1].value:
            with open(parameters[0].ValueAsText,"r") as f:
                txt = f.read()
                observationPeriod = float(re.findall(r"Observation_period =[^,]+,[^,]+,([^\n]+)",txt)[0])
                parameters[1].value = observationPeriod
        return

    def updateMessages(self, parameters): #optional
        return

    def execute(self, parameters, messages):
        arcpy.env.addOutputsToMap = False
        erfFile = parameters[0].ValueAsText
        MUDatabase = parameters[2].ValueAsText
        geometryFile = MUDatabase + "\mu_Geometry\msm_Link"
        msm_Weir = MUDatabase + "\mu_Geometry\msm_Weir"
        exportShape = parameters[3].ValueAsText
        observationPeriod = float(parameters[1].ValueAsText)
        use_networker = parameters[4].ValueAsText
        export_cad = parameters[5].ValueAsText
        
        MUIDs = {}
        if use_networker == "False":
            with arcpy.da.SearchCursor(geometryFile,["MUID","FROMNODE","TONODE"]) as cursor:
                for row in cursor:
                    MUIDs[row[0]] = "'%s', '%s'" % (row[1],row[2])
            with arcpy.da.SearchCursor(msm_Weir,["MUID","FROMNODE","TONODE"]) as cursor:
                for row in cursor:
                    MUIDs[row[0]] = "'%s', '%s'" % (row[1],row[2])
        else:
            link_network = networker.NetworkLinks(MUDatabase, map_only = "link weir").links
            for link in link_network.values():
                MUIDs[link.MUID] = "'%s', '%s'" % (link.fromnode, link.tonode)
            
        dataTables = readERF.readERF(erfFile, "MaxFlow_Ranked", MUIDs.values(), ignore = True)

        msmLinkNew = arcpy.CopyFeatures_management(geometryFile,exportShape)
        
        if "FROMNODE" not in [field.name for field in arcpy.ListFields(msmLinkNew)] and "TONODE" not in [field.name for field in arcpy.ListFields(msmLinkNew)]:
            arcpy.AddField_management(msmLinkNew, "FROMNODE", "TEXT")
            arcpy.AddField_management(msmLinkNew, "TONODE", "TEXT")
            
        RPs = [1, 2, 5, 10, 20, 1000]
        fields = ["T1", "T2", "T5", "T10", "T20", "TMax"]
        for field in fields:
            arcpy.AddField_management (msmLinkNew, field, "FLOAT", field_precision = 8, field_scale = 5)
            
        if use_networker:
            fromnodes = [link.fromnode for link in link_network.values()]
            outlet_MUIDs = [link.MUID for link in link_network.values() if link.tonode not in fromnodes]
        else:
            fromnodes = [row[0] for row in arcpy.da.SearchCursor(exportShape, ["FROMNODE"])]
            outlet_MUIDs = [row[0] for row in arcpy.da.SearchCursor(exportShape, ["MUID","TONODE"]) if row[1] not in fromnodes]
        
        with arcpy.da.UpdateCursor(msmLinkNew,["MUID"] + fields + ["FROMNODE", "TONODE"] + ["SHAPE@"]) as cursor:
            for row in cursor:
                try:
                    if row[0] in MUIDs.keys() and not dataTables[MUIDs.keys().index(row[0])] == None:
                            for i in range(len(RPs)):
                                try:
                                    flows = dataTables[MUIDs.keys().index(row[0])]["col2"]
                                    erfRPs = np.flipud(np.array(observationPeriod)/np.arange(1,len(flows)+1))
                                    row[i+1] = np.interp(RPs[i],erfRPs,np.flipud(flows))*1e3
                                    if use_networker:
                                        row[-3] = link_network[row[0]].fromnode
                                        row[-2] = link_network[row[0]].tonode
                                except Exception as e:
                                    arcpy.AddWarning(e)
                            
                # row[-3] = row[-1].projectAs(arcpy.SpatialReference("WGS 1984")).lastPoint.X
                # row[-2] = row[-1].projectAs(arcpy.SpatialReference("WGS 1984")).lastPoint.Y
                    cursor.updateRow(row)   
                except Exception as e:
                    arcpy.AddWarning("Failed on MUID %s: %s" % (row[0], e))
        
        with arcpy.da.InsertCursor(msmLinkNew, ["MUID"] + fields + ["FROMNODE", "TONODE"] + ["SHAPE@"]) as cursor:
                extra_fields = ["FROMNODE","TONODE"] if not use_networker else []                
                row = [None] * len(["MUID"] + fields + ["FROMNODE", "TONODE"] + ["SHAPE@"])
                with arcpy.da.SearchCursor(msm_Weir, ["MUID", "SHAPE@"] + extra_fields) as weir_cursor:
                    for weir_row in weir_cursor:
                        try:
                            if weir_row[0] in MUIDs.keys() and not dataTables[MUIDs.keys().index(weir_row[0])] == None:
                                row[0] = weir_row[0]
                                for i in range(len(RPs)):
                                    try:
                                        flows = dataTables[MUIDs.keys().index(weir_row[0])]["col2"]
                                        erfRPs = np.flipud(np.array(observationPeriod)/np.arange(1,len(flows)+1))
                                        row[i+1] = np.interp(RPs[i],erfRPs,np.flipud(flows))*1e3
                                        row[-1] = weir_row[1]
                                        if use_networker:
                                            row[-3] = link_network[weir_row[0]].fromnode
                                            row[-2] = link_network[weir_row[0]].tonode
                                    except Exception as e:
                                        arcpy.AddWarning(e)
                                    
                        # row[-3] = row[-1].projectAs(arcpy.SpatialReference("WGS 1984")).lastPoint.X
                        # row[-2] = row[-1].projectAs(arcpy.SpatialReference("WGS 1984")).lastPoint.Y
                                cursor.insertRow(row)   
                        except Exception as e:
                            arcpy.AddWarning("Failed on MUID %s: %s" % (weir_row[0], e))
                
        mxd = arcpy.mapping.MapDocument("CURRENT")
        df = arcpy.mapping.ListDataFrames(mxd)[0]
        
        add_layer = arcpy.mapping.Layer(exportShape)
        if (arcpy.mapping.ListLayers(mxd, os.path.splitext(os.path.basename(MUDatabase))) 
            and arcpy.mapping.ListLayers(mxd, os.path.splitext(os.path.basename(MUDatabase)))[0].isGroupLayer):
            group_layer = arcpy.mapping.ListLayers(mxd, os.path.splitext(os.path.basename(MUDatabase)))[0]
            arcpy.mapping.AddLayerToGroup(df, group_layer, add_layer, "TOP")
            update_layer = [layer for layer in arcpy.mapping.ListLayers(mxd, add_layer.name, df) if layer.longName == os.path.splitext(os.path.basename(MUDatabase))[0] + r"\\" + u"Vandføring"]
            
            arcpy.mapping.AddLayerToGroup(df, group_layer, add_layer, "TOP")
            update_layer_outlet = [layer for layer in arcpy.mapping.ListLayers(mxd, add_layer.name, df) if layer.longName == os.path.splitext(os.path.basename(MUDatabase))[0] + r"\\" + u"Vandføring udløb"]
            
            arcpy.AddMessage(os.path.splitext(os.path.basename(MUDatabase))[0] + r"\\" + u"Vandføring")
        else:
            arcpy.mapping.AddLayer(df, add_layer, "TOP")
            update_layer = arcpy.mapping.ListLayers(mxd, add_layer.name, df)[0]
            
            arcpy.mapping.AddLayer(df, add_layer, "TOP")
            update_layer_outlet = arcpy.mapping.ListLayers(mxd, add_layer.name, df)[0]
        source_layer = arcpy.mapping.Layer(os.path.dirname(os.path.realpath(__file__)) + "\Data\msm_LinkQMax.lyr")
        arcpy.mapping.UpdateLayer(df,update_layer,source_layer,False)
        update_layer.replaceDataSource(unicode(add_layer.workspacePath), 'SHAPEFILE_WORKSPACE', unicode(add_layer.datasetName))
        update_layer.definitionQuery = "MUID NOT IN ('%s')" % ("', '".join(outlet_MUIDs))
        
        source_layer = arcpy.mapping.Layer(os.path.dirname(os.path.realpath(__file__)) + "\Data\msm_LinkQMaxOutlet.lyr")
        arcpy.mapping.UpdateLayer(df,update_layer_outlet,source_layer,False)
        update_layer_outlet.replaceDataSource(unicode(add_layer.workspacePath), 'SHAPEFILE_WORKSPACE', unicode(add_layer.datasetName))
        update_layer_outlet.definitionQuery = "MUID IN ('%s')" % ("', '".join(outlet_MUIDs))
        
        arcpy.RefreshTOC()
        arcpy.RefreshActiveView()
        
        # if export_cad:
            # import ezdxf
            
            # tonodes = {}
            # if use_networker:
                # fromnodes = [link.fromnode for link in link_network.values()]
                # outlet_MUIDs = [link.MUID for link in link_network.values() if link.tonode not in fromnodes]
                # for link in link_network.values():
                    # tonodes[link.MUID] = link.tonode
            # else:
                # fromnodes = [row[0] for row in arcpy.da.SearchCursor(exportShape, ["FROMNODE"])]
                # outlet_MUIDs = [row[0] for row in arcpy.da.SearchCursor(exportShape, ["MUID","TONODE"]) if row[1] not in fromnodes]
                # with arcpy.da.SearchCursor(exportShape, ["FROMNODE", "MUID"], where_clause = "MUID IN ('%s')" % ("', '".join(outlet_MUIDs))):
                    # tonodes[row[1]] = row[0]
                
            
            # doc = ezdxf.new(dxfversion='R2010')
            # doc.layers.new(u'Udloeb', dxfattribs={'color': 255})
            # msp = doc.modelspace()
            # arcpy.AddMessage(outlet_MUIDs)
            # arcpy.AddMessage( "MUID IN ('%s')" % ("', '".join(outlet_MUIDs)))
            # with arcpy.da.SearchCursor(exportShape, ["SHAPE@", "MUID", "T1", "T2", "T5", "T10", "T20", "TMax"], where_clause = "MUID IN ('%s')" % ("', '".join(outlet_MUIDs))) as cursor:
                # for row in cursor:
                    # a = msp.add_mtext(
                    # 'ID: %s%sT1: %1.1f' % ("bay", "\n", ("%1.1f" % (max(row[2],0))).replace(".","."))) #tonodes[row[1]]
                    # a.set_location((row[0].lastPoint.X, row[0].lastPoint.Y))

        # # Save DXF document.
            # doc.saveas(export_cad)
        return
        
class DisplayQFullQMax(object):
    def __init__(self):
        self.label       = "Display Filling Degree of Pipe"
        self.description = "Display Filling Degree of Pipe"
        self.canRunInBackground = False

    def getParameterInfo(self):
        #Define parameter definitions

        # Input Features parameter
        prfFile = arcpy.Parameter(
            displayName="PRF file",
            name="prfFile",
            datatype="File",
            parameterType="Required",
            direction="Input")
        prfFile.filter.list=["prf"]
        
        MU_database = arcpy.Parameter(
            displayName="Mike Urban Database with links",
            name="database",
            datatype="DEWorkspace",
            parameterType="Required",
            direction="Input")
        
        exportShape = arcpy.Parameter(
            displayName="Output shapefile with Filling Degree of Pipe",
            name="exportShape",
            datatype="DEShapefile",
            parameterType="Required",
            direction="Output")
        
        minimumSlope = arcpy.Parameter(
            displayName="Replace low slopes [o/oo]",
            name="minimumSlope",
            datatype="double",
            parameterType="Optional",
            direction="Input")
        minimumSlope.filter.list = [5, 10]
            
        parameters = [prfFile, MU_database, exportShape, minimumSlope]
        
        return parameters

    def isLicensed(self): #optional
        return True

    def updateParameters(self, parameters): #optional
        return

    def updateMessages(self, parameters): #optional
        return

    def execute(self, parameters, messages):
        arcpy.env.addOutputsToMap = False
        prfFile = parameters[0].ValueAsText
        MU_database = parameters[1].ValueAsText
        geometryFile = MU_database + "\mu_Geometry\msm_Link"
        exportShape = parameters[2].ValueAsText
        minimumSlope = float(parameters[3].ValueAsText)
        
        workingDir = os.path.dirname(__file__)
        M11OUT = workingDir + "\M11.OUT"
        M11IN = workingDir + "\M11.IN"

        prfFileCopy = workingDir + "\prffile.PRF"
        resultFile = workingDir + "\ResultFile.txt"
        replaceLowSlopes = 5

        if not minimumSlope:
            minimumSlope = 0
        copyfile(prfFile,prfFileCopy)
        call([m11extraPath, prfFileCopy])

        lines = ""
        links = []
        with codecs.open(M11OUT,'r','cp1252') as M11OUTFile:
            for linei,line in enumerate(M11OUTFile):
                try:
                    if "Link_Q" in line:		
                        links.append(re.findall("<([^>]+)>",line)[0])
                        line = re.sub("^0","1",line)
                    lines += line
                except UnicodeDecodeError:
                    lines += line
                    arcpy.AddWarning(u"Line no. %d in file %s contains illegal character." % (linei,M11OUT))
                except Exception as e:
                    raise(e)
                       
        with codecs.open(M11IN,'w','cp1252') as M11INFile:
            M11INFile.write(lines)

        call([m11extraPath, prfFileCopy, resultFile, "/MAX"])
        os.remove(prfFileCopy)
        os.remove(M11IN)
        os.remove(M11OUT)

        linksFlow = []
        with codecs.open(resultFile,'r','cp1252') as M11OUTFile:
            for linei,line in enumerate(M11OUTFile):
                linksFlow.append(float(re.findall(" +([\-\d\.]+)",line)[0]))
        os.remove(resultFile)
        
        arcpy.CopyFeatures_management(os.path.join(MU_database,"msm_Link"), exportShape)
        arcpy.AddField_management(exportShape, "QMax", "DOUBLE", field_scale = 5, field_precision = 10)
        arcpy.AddField_management(exportShape, "QFull", "DOUBLE", field_scale = 5, field_precision = 10)
        arcpy.AddField_management(exportShape, "Filldeg", "DOUBLE", field_scale = 5, field_precision = 10)
        with arcpy.da.UpdateCursor(exportShape, ["MUID","Diameter","Slope_C","MaterialID","QMax","QFull","FillDeg"]) as cursor:
            for row in cursor:
                try:
                    row[4] = linksFlow[[i for i,a in enumerate(links) if a == row[0]][0]]
                except Exception as e:
                    arcpy.AddMessage("Failed on row %s" % row)
                    raise(e)
                row[5] = colebrookWhite.QFull(row[1],max(row[2]*1e-2,minimumSlope*1e-3),row[3])
                row[6] = max(0,row[4]/row[5])
                cursor.updateRow(row)
            
        
                
        # mxd = arcpy.mapping.MapDocument("CURRENT")
        # df = arcpy.mapping.ListDataFrames(mxd)[0]
        # arcpy.env.addOutputsToMap = False
        # linkLayer = arcpy.mapping.Layer(os.path.dirname(os.path.realpath(__file__)) + "\Data\QmaxQFull.lyr.lyr")
        # linkLayer = arcpy.mapping.AddLayer(df, linkLayer)
        # linkLayer = arcpy.mapping.ListLayers(mxd, linkLayer, df)[0]
        # arcpy.AddMessage(os.path.dirname(exportShape))
        # arcpy.AddMessage(os.path.dirname(os.path.basename(exportShape).split(".")[0]))
        # linkLayer.replaceDataSource(os.path.dirname(exportShape), "FILEGDB_WORKSPACE", os.path.basename(exportShape).split(".")[0])
        return