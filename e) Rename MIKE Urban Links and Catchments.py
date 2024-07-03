import re
import numpy as np
import arcpy
import os

MUProject = r"C:\Dokumenter\Hovedspildevandsmodel\Ans\Ans_2.3.mdb"
linksFile = MUProject + r"\mu_Geometry\msm_Link"
catchmentsFile = MUProject + r"\mu_Geometry\ms_Catchment"
catchConFile = MUProject + r"\msm_CatchCon"
hModAFile = MUProject + r"\msm_HModA"

links = {}
with arcpy.da.SearchCursor(linksFile, ["MUID","FROMNODE","TONODE"]) as cursor:
    for row in cursor:
        links[row[0]] = row[1]
        
linksNewNames = {}

existingNames = []
for link in links:
    linkID = 1
    while links[link] + "l%1.0f" % linkID in existingNames:
        linkID += 1
    linksNewNames[link] = links[link] + "l%1.0f" % linkID
    existingNames.append(links[link] + "l%1.0f" % linkID)


edit = arcpy.da.Editor(MUProject)
edit.startEditing(False, False) 
edit.startOperation()  
# with arcpy.da.UpdateCursor(linksFile, ["MUID"]) as cursor:
    # for i,row in enumerate(cursor):
        # if row[0] in linksNewNames:
            # if row[0] != linksNewNames[row[0]]:
                # row[0] = linksNewNames[row[0]]
                # try:
                    # cursor.updateRow(row)
                # except:
                    # pass
        # print i
edit.stopOperation()  
edit.stopEditing(True)  


catchments = {}
catchmentsCatchID = {}
with arcpy.da.SearchCursor(catchConFile, ["MUID","CatchID","NodeID"]) as cursor:
    for row in cursor:
        catchments[row[0]] = row[2]
        catchmentsCatchID[row[1]] = row[0]

catchmentsNewNames = {}
existingNames = []
for catchment in catchments:
    catchmentID = 1
    while catchments[catchment] + "_c%1.0f" % catchmentID in existingNames:
        catchmentID += 1
    catchmentsNewNames[catchment] = catchments[catchment] + "_c%1.0f" % catchmentID
    existingNames.append(catchments[catchment] + "_c%1.0f" % catchmentID)

with arcpy.da.UpdateCursor(hModAFile, ["CatchID"]) as cursor:
    for row in cursor:
        if row[0] != catchmentsNewNames[catchmentsCatchID[row[0]]]:
            
            row[0] = catchmentsNewNames[catchmentsCatchID[row[0]]]
            try:
                cursor.updateRow(row)
            except:
                pass
        
with arcpy.da.UpdateCursor(catchmentsFile, ["MUID"]) as cursor:
    for row in cursor:
        if row[0] != catchmentsNewNames[catchmentsCatchID[row[0]]]:
            row[0] = catchmentsNewNames[catchmentsCatchID[row[0]]]
            try:
                cursor.updateRow(row)
            except:
                pass
            
with arcpy.da.UpdateCursor(catchConFile, ["MUID","CatchID"]) as cursor:
    for row in cursor:
        if row[1] != catchmentsNewNames[row[0]] or row[0] != catchmentsNewNames[row[0]]:
            row[1] = catchmentsNewNames[row[0]]
            row[0] = catchmentsNewNames[row[0]]
            try:
                cursor.updateRow(row)
            except:
                pass            