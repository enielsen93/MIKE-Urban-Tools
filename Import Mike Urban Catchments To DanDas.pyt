# Created by Emil Nielsen
# Contact: 
# E-mail: enielsen93@hotmail.com

import arcpy
import os
import re
import numpy as np
import copy

import pythonaddins
import subprocess
from xml.dom import minidom
import xml.etree.ElementTree as ET  

import datetime

class Toolbox(object):
    def __init__(self):
        self.label =  "Import MU Catchments to DanDas"
        self.alias  = "Import MU Catchments to DanDas"

        # List of tool classes associated with this toolbox
        self.tools = [CreateXML] 

class CreateXML(object):
    def __init__(self):
        self.label       = "Import MU Catchments to DanDas"
        self.description = "Import MU Catchments to DanDas"
        self.canRunInBackground = False

    def getParameterInfo(self):
        #Define parameter definitions

        # Input Features parameter
        catchments = arcpy.Parameter(
            displayName="Catchment layer",
            name="catchments",
            datatype="GPFeatureLayer",
            parameterType="Required",
            direction="Input")
        catchments.filter.list = ["Polygon"]
        
        xmlfile = arcpy.Parameter(
            displayName="Output DanDas XML file",
            name="xmlfile",
            datatype="File",
            parameterType="Required",
            direction="Output")
        xmlfile.filter.list = ["xml"]
        
        nodes = arcpy.Parameter(
            displayName="MOUSE Manholes whose catchments will be deleted in DanDas",
            name="nodes",
            datatype="GPFeatureLayer",
            parameterType="Optional",
            direction="Input")
        
        initials = arcpy.Parameter(
            displayName="Initials of the author",
            name="initials",
            datatype="GPString",
            parameterType="Optional",
            direction="Input")
        initials.filter.list = ["cli","eni","gra","tho"]
        
        date = arcpy.Parameter(
            displayName="Date for the GIS analysis",
            name="date",
            datatype="GPString",
            parameterType="Optional",
            direction="Input")
        
        analysisCode = arcpy.Parameter(
            displayName="Was the imperviousness analyzed using GIS?",
            name="analysisCode",
            datatype="GPBoolean",
            parameterType="Optional",
            direction="Input")
        analysisCode.value = True
        
        parameters = [catchments, xmlfile, nodes, initials, date, analysisCode]
        
        return parameters

    def isLicensed(self): #optional
        return True

    def updateParameters(self, parameters): #optional
        if parameters[4].Value == None:
            nu = datetime.datetime.now()
            parameters[4].Value = nu.strftime("%Y-%m-%d")
        return

    def updateMessages(self, parameters): #optional
       
        return

    def execute(self, parameters, messages):
        initials = parameters[3].ValueAsText
        nu = datetime.datetime.now()
        catchmentsFC = parameters[0].ValueAsText
        xmlFile = parameters[1].ValueAsText
        nodesFC = parameters[2].ValueAsText
        date = parameters[4].ValueAsText + "T00:00:00"
        analysisCode = parameters[5].Value

        MUDatabase = os.path.dirname(arcpy.Describe(catchmentsFC).path)
        msm_CatchCon = MUDatabase + r"\\" + "msm_CatchCon"
        msm_HModA = MUDatabase + r"\\" + "msm_HModA"

        class Catchment:
            def __init__(self, MUID):
                self.MUID = MUID
                self.node = None
                self.impArea = None
                self.area = None
                self.persons = None
                self.description = None
                self.coordinates = []

        getXY = re.compile("([\d\.]+)")
        catchments = {}
        with arcpy.da.SearchCursor(catchmentsFC, ['MUID','SHAPE@AREA','Persons','SHAPE@','Description']) as cursor:
                for row in cursor:
                    catchments[row[0]] = Catchment(row[0])
                    catchments[row[0]].area = row[1]
                    catchments[row[0]].persons = row[2]
                    catchments[row[0]].description = row[4]
                    matches = getXY.findall(row[3].WKT)
                    xy = np.empty((len(matches)/2,2))
                    j = 0
                    for i in np.arange(0,len(matches),2):
                        xy[j,0:2] = (float(matches[i]), float(matches[i+1]))
                        j = j+1
                    catchments[row[0]].coordinates = xy

        nodes = {}
        with arcpy.da.SearchCursor(msm_CatchCon, ['CatchID','NodeID']) as cursor:
                for row in cursor:
                    if row[0] in catchments:
                        catchments[row[0]].node = row[1]    
                        if row[1] not in nodes:
                            nodes[row[1]] = [row[0]]
                        else:
                            nodes[row[1]].append(row[0])
                        
                        
        with arcpy.da.SearchCursor(msm_HModA, ['CatchID','ImpArea']) as cursor:
                for row in cursor:
                    if row[0] in catchments:
                        catchments[row[0]].impArea = row[1]
        
        getXY = re.compile("([\d\.]+)")
        getSubShapes = re.compile("\(([^\(^\)]+)\)")
        with arcpy.da.SearchCursor(catchmentsFC, ['MUID', 'SHAPE@']) as cursor:
            for row in cursor:
                subShapes = getSubShapes.findall(row[1].WKT)
                if len(subShapes)>1:
                    for subShapesi in np.arange(1,len(subShapes)):
                        catchments[row[0] + "_p%d" % (subShapesi+1)] = copy.copy(catchments[row[0]])
                        matches = getXY.findall(subShapes[subShapesi])
                        xy = np.empty((len(matches)/2,2))
                        j = 0
                        for i in np.arange(0,len(matches),2):
                            xy[j,0:2] = (float(matches[i]), float(matches[i+1]))
                            j = j+1
                        catchments[row[0] + "_p%d" % (subShapesi+1)].coordinates = xy
                        catchments[row[0] + "_p%d" % (subShapesi+1)].area = 0.5*np.abs(np.dot(xy[:,0],np.roll(xy[:,1],1))-np.dot(xy[:,1],np.roll(xy[:,0],1)))
                        nodes[catchments[row[0]].node].append(row[0] + "_p%d" % (subShapesi+1))
                    matches = getXY.findall(subShapes[0])
                    xy = np.empty((len(matches)/2,2))
                    j = 0
                    for i in np.arange(0,len(matches),2):
                        xy[j,0:2] = (float(matches[i]), float(matches[i+1]))
                        j = j+1
                    catchments[row[0]].coordinates = xy
                    catchments[row[0]].area = 0.5*np.abs(np.dot(xy[:,0],np.roll(xy[:,1],1))-np.dot(xy[:,1],np.roll(xy[:,0],1)))
        
        # Begynd at skrive XML-fil
        #Indledende junk
        root = ET.Element("KnudeGroup")
        root.set("xmlns","http://www.danva.dk/xml/schemas/dandas/20120102")
        Referencesys = ET.SubElement(root,"Referencesys")
        ET.SubElement(Referencesys,"KoordinatsysKode").text = "9"
        ET.SubElement(Referencesys,"KotesysKode").text = "1"
        arcpy.SetProgressor("step","Creating nodes and catchments in XML-file", 0, int(len(nodes)), 1)        
        # Begynd at tilføje knuder
        for node, deloplande in nodes.items():
            arcpy.SetProgressorPosition(i)
            i = i+1
            Knude = ET.SubElement(root,"Knude")
            # Tilføj info om knuden
            Knude.set("Knudenavn",node)
            
            # Tilføj deloplande til pågældende knude
            DeloplandItems = ET.SubElement(Knude,"DeloplandItems")
            for deloplandnr, delopland in enumerate(deloplande):
                Delopland = ET.SubElement(DeloplandItems,"Delopland")
                Delopland.set("Deloplandnr","%d" % (deloplandnr+1))
                ET.SubElement(Delopland,"Areal").text = "%1.4f" % (catchments[delopland].area/10000)
                ET.SubElement(Delopland,"BefaestelsePct").text = "%d" % catchments[delopland].impArea
                ET.SubElement(Delopland,"Bemaerkninger").text = catchments[delopland].description
                ET.SubElement(Delopland,"DatoOpdateret").text = nu.strftime("%Y-%m-%dT%H:%M:%S")
                ET.SubElement(Delopland,"DatoOprettet").text = nu.strftime("%Y-%m-%dT%H:%M:%S")
                ET.SubElement(Delopland,"Initialer").text = initials 
                
                # Tilføj tekstfelt
                ET.SubElement(Delopland,"TekstjusteringKode").text = "4"
                ET.SubElement(Delopland,"Tekstvinkel").text = "0"
                if not catchments[delopland].persons == None:
                    ET.SubElement(Delopland,"PE").text = "%1.1f" % catchments[delopland].persons
                # Beregn Midtpunkt til placering af tekstfelt
                ET.SubElement(Delopland,"XLabel").text = "%1.3f" % (np.mean(catchments[delopland].coordinates[:,0]))
                ET.SubElement(Delopland,"YLabel").text = "%1.3f" % (np.mean(catchments[delopland].coordinates[:,1]))
                ET.SubElement(Delopland,"TekstFaktor").text = "1.00"		
                ET.SubElement(Delopland,"DatoBefaestelsePct").text = date
                
                if analysisCode:
                    ET.SubElement(Delopland,"OprindBefStatusKode").text = "1"
                # Tilføj geometri til delopland
                DeloplandKoordItems = ET.SubElement(Delopland,"DeloplandKoordItems")
                for coordi in range(len(catchments[delopland].coordinates[:,0])):
                    DeloplandKoord = ET.SubElement(DeloplandKoordItems,"DeloplandKoord")
                    DeloplandKoord.set("Sortering","%d" % (coordi+1))
                    ET.SubElement(DeloplandKoord,"Xkoordinat").text = "%1.2f" % catchments[delopland].coordinates[coordi,0]
                    ET.SubElement(DeloplandKoord,"Ykoordinat").text = "%1.2f" % catchments[delopland].coordinates[coordi,1]

        # Skriv XML-fil
        ET.tostring(root,encoding="UTF-8",  method='xml')
        with open(xmlFile,"w+") as f:
            f.write(minidom.parseString(ET.tostring(root,encoding="UTF-8")).toprettyxml().encode("utf-8"))
      
        if nodesFC:
            if pythonaddins.MessageBox("Copy selected manholes to clipboard?", "Copy manholes", 1) == "OK":
                MUIDs = []
                with arcpy.da.SearchCursor(nodesFC, ['MUID']) as cursor:
                    for row in cursor:
                        MUIDs.append(row[0])
                txt = "('" + "', '".join(MUIDs) + "')"
                cmd='echo '+txt.strip()+'|clip'
                subprocess.check_call(cmd, shell=True)

        return
        