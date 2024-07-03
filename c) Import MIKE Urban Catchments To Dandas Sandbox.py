import arcpy
import os
import re
import numpy as np

from xml.dom import minidom
import xml.etree.ElementTree as ET  

import datetime
nu = datetime.datetime.now()

initials = "eni"
catchmentsFC = r"C:\Dokumenter\Hovedspildevandsmodel\NoerreKnudstrup\NoerreKnudstrup_06.mdb\mu_Geometry\ms_Catchment"
xmlFile = r"K:\Hydrauliske modeller\Makroer & Beregningsark\Import MU Catchments to DanDas\Deloplande.xml"
MUDatabase = os.path.dirname(arcpy.Describe(catchmentsFC).path)
msm_CatchCon = MUDatabase + r"\\" + "msm_CatchCon"
msm_HModA = MUDatabase + r"\\" + "msm_HModA"

class Catchment:
    def __init__(self, MUID):
        self.MUID = MUID
        self.node = None
        self.impArea = None
        self.area = None
        self.PE = None
        self.persons = None
        self.description = None
        self.coordinates = []

getXY = re.compile("([\d\.]+)")
getSubShapes = re.compile("([\d\.]+)")
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
                catchments[row[0] + "_p%d" % (subShapesi+1)] = catchments[row[0]]
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

# Begynd at tilføje knuder
for node, deloplande in nodes.items():
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
		# Beregn Midtpunkt til placering af tekstfelt
		ET.SubElement(Delopland,"XLabel").text = "%1.3f" % (np.mean(catchments[delopland].coordinates[:,0]))
		ET.SubElement(Delopland,"YLabel").text = "%1.3f" % (np.mean(catchments[delopland].coordinates[:,1]))
		ET.SubElement(Delopland,"TekstFaktor").text = "1.00"		
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