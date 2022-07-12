import arcpy
import numpy as np
import pandas as pd
import os

MikeUrbanModel = r"K:\Hydrauliske modeller\Flora\Hovedspildevandsmodel Truust\Samlet model\Truust_v5.4.mdb"
msm_Link = os.path.join(MikeUrbanModel,"msm_Link")
msm_Node = os.path.join(MikeUrbanModel,"msm_Node")
msm_Orifice = os.path.join(MikeUrbanModel,"msm_Orifice")
msm_Weir = os.path.join(MikeUrbanModel,"msm_Weir")
msm_Pump = os.path.join(MikeUrbanModel,"msm_Pump")
msm_CatchCon = os.path.join(MikeUrbanModel,"msm_CatchCon")
msm_HModA = os.path.join(MikeUrbanModel,"msm_HModA")
ms_Catchment = os.path.join(MikeUrbanModel,"ms_Catchment")
rows = int(np.sum([1 for i in arcpy.da.SearchCursor(msm_Link,"OBJECTID")]) + 
           np.sum([1 for i in arcpy.da.SearchCursor(msm_Orifice,"OBJECTID")]) + 
           np.sum([1 for i in arcpy.da.SearchCursor(msm_Weir,"OBJECTID")]) + 
           np.sum([1 for i in arcpy.da.SearchCursor(msm_Pump,"OBJECTID")]))

### Map Network (links, orifices, pumps and weirs)

networkDataFrame = pd.DataFrame(columns=["MUID","FromNode","ToNode","Type"], index = range(rows))

outlets = []
with arcpy.da.SearchCursor(msm_Node, "MUID", where_clause = "TypeNo = 3") as cursor:
    for row in cursor:
        outlets.append(row[0])

i = 0
with arcpy.da.SearchCursor(msm_Link,
                           ["MUID","FromNode","ToNode"]) as cursor:
    for row in cursor:
        networkDataFrame.loc[i] = row+("Link",)
        i += 1
        
with arcpy.da.SearchCursor(msm_Orifice,
                   ["MUID","FromNode","ToNode"]) as cursor:
    for row in cursor:
        networkDataFrame.loc[i] = row+("Orifice",)
        i += 1
        
with arcpy.da.SearchCursor(msm_Weir,
                   ["MUID","FromNode","ToNode"]) as cursor:
    for row in cursor:
        networkDataFrame.loc[i] = row+("Weir",)
        i += 1

with arcpy.da.SearchCursor(msm_Pump,
                   ["MUID","FromNode","ToNode"]) as cursor:
    for row in cursor:
        networkDataFrame.loc[i] = row+("Pump",)
        i += 1

### Read catchments
catchmentRows = int(np.sum([1 for i in arcpy.da.SearchCursor(ms_Catchment,"OBJECTID",where_clause = "NetTypeNo IN (2,3)")]))
msm_CatchmentDataFrame = pd.DataFrame(columns=["CatchID", "NodeID", "Area","Imperviousness"], index = range(catchmentRows))

with arcpy.da.SearchCursor(ms_Catchment,
                           ["MUID","SHAPE@AREA","Area"], where_clause = "NetTypeNo IN (2,3)") as cursor:
    for i,row in enumerate(cursor):
        msm_CatchmentDataFrame.loc[i].CatchID = row[0]
        if row[2]:
            msm_CatchmentDataFrame.loc[i].Area = 0#row[2]*1e4
        else:
            msm_CatchmentDataFrame.loc[i].Area = row[1]

with arcpy.da.SearchCursor(msm_CatchCon,
                           ["CatchID","NodeID"], where_clause = "CatchID IN ('%s')" % "','".join(msm_CatchmentDataFrame.CatchID)) as cursor:
    for row in cursor:
        idx = [i for i,a in enumerate(msm_CatchmentDataFrame.CatchID) if a==row[0]][0]
        msm_CatchmentDataFrame.loc[idx].NodeID = row[1]

with arcpy.da.SearchCursor(msm_HModA,
                           ["CatchID","ImpArea"], where_clause = "CatchID IN ('%s')" % "','".join(msm_CatchmentDataFrame.CatchID)) as cursor:
    for row in cursor:
        idx = [i for i,a in enumerate(msm_CatchmentDataFrame.CatchID) if a==row[0]][0]
        msm_CatchmentDataFrame.loc[idx].Imperviousness = row[1]
        
#####################

def getUpstreamLinks(networkDataFrame, index, indexes):
    idx = networkDataFrame.index[networkDataFrame.ToNode == networkDataFrame.iloc[index].FromNode].tolist()
    if len(idx)>0:
        for i in idx:
            if len(indexes)==0 or not i in indexes:
                indexes.update([i])
                indexes = getUpstreamLinks(networkDataFrame, i, indexes)
    return indexes

#####################

weirs = ['O302', 'O303', 'O323', 'O301', 'O306', 'ODemstrupAfsk', 'O804', 'O803', 'O810', 'O701', 'O805', 'O703', 
         'A302W', 'O801', 'O802', 'O311', 'O312', 'O318', 'O314', 'O304', 'O313', 'O322', 'O305', 'O316', 'O402', 
         'O307', 'O321', 'O320', 'O310', 'TRUUST O2', 'P308W', 'B708W']
recipientDataFrame = pd.DataFrame(columns=["Recipient", "Catchments", "Area","Impervious area"], 
                                  index = range(len([j for j,a in enumerate(networkDataFrame.MUID) if a in weirs])-1))

i = 0
for networki in [j for j,a in enumerate(networkDataFrame.MUID) if a in weirs]:
    parent = networki
    idx = getUpstreamLinks(networkDataFrame, parent, set())
    idx.update([parent])
    nodes = networkDataFrame.FromNode[idx].values
    recipientDataFrame.at[i,'Recipient'] = networkDataFrame.iloc[networki].MUID
    recipientDataFrame.at[i,'Catchments'] = [a.CatchID for _,a in msm_CatchmentDataFrame.iterrows() if a.NodeID in nodes]
    
    i += 1

# Separate catchments so that they only lead to one weir
idxSort = np.argsort([len(a) for a in recipientDataFrame.Catchments])
usedCatchments = []
for i in range(len(idxSort)):
    if i < len(idxSort)-1 and not recipientDataFrame.at[idxSort[i],'Catchments'] == recipientDataFrame.at[idxSort[i+1],'Catchments']:
        recipientDataFrame.at[idxSort[i],'Catchments'] = [a for a in recipientDataFrame.at[idxSort[i],'Catchments'] if a not in usedCatchments]
        usedCatchments += recipientDataFrame.at[idxSort[i],'Catchments']
    else:
        recipientDataFrame.at[idxSort[i],'Catchments'] = [a for a in recipientDataFrame.at[idxSort[i],'Catchments'] if a not in usedCatchments]

i = 0
for networki in [j for j,a in enumerate(networkDataFrame.MUID) if a in weirs]:
    recipientDataFrame.at[i,'Area'] = np.sum([catchment.Area/1e4 for _,catchment in msm_CatchmentDataFrame.iterrows() 
        if catchment.CatchID in recipientDataFrame.at[i,'Catchments']])
    recipientDataFrame.at[i,'Impervious area'] = np.sum([catchment.Area*catchment.Imperviousness/1.0e2/1e4 for _,catchment in msm_CatchmentDataFrame.iterrows() 
        if catchment.CatchID in recipientDataFrame.at[i,'Catchments']])
    i += 1

#catchmentsTotal = []
#for Catchments in recipientDataFrame.Catchments:
#    catchmentsTotal += Catchments

#for _,catchment in msm_CatchmentDataFrame.iterrows():
#    if catchment.CatchID not in catchmentsToRecipient:
#        catchmentsToRecipient[catchment.CatchID] = "Could not trace to a weir" 

#for recipient,catchments in recipientCatchments.iteritems():
#    row[2] = np.sum([catchment.Area/1e4 for _,catchment in msm_CatchmentDataFrame.iterrows() if catchmentsToOutlets[catchment.CatchID] == row[1]])
#    row[4] = np.sum([catchment.Area*catchment.Imperviousness/1.0e2 /1e4

#arcpy.AddField_management(ms_Catchment,"Outlet","TEXT")    
#with arcpy.da.UpdateCursor(ms_Catchment,["MUID","Outlet"]) as cursor: # where_clause = "MUID IN ('%s')" % ("','".join(catchments))
#    for i, row in enumerate(cursor):
#        print "%d/%d" % (i,catchmentRows)
#        if row[0] in catchmentsToOutlets:
#            row[1] = catchmentsToOutlets[row[0]]
#        cursor.updateRow(row)
#
#for field in ["Opland","ImpArea"]:
#    try:
#        arcpy.AddField_management(vandfoeringShape,field,"DOUBLE",8,4)
#    except:
#        pass
#    
#with arcpy.da.UpdateCursor(vandfoeringShape, ["MUID", "TONODE", "Opland", "TypeNo", "ImpArea"], where_clause = "TONODE IN ('%s')" % ("', '".join(outlets))) as cursor:
#    for row in cursor:
#        row[2] = np.sum([catchment.Area/1e4 for _,catchment in msm_CatchmentDataFrame.iterrows() if catchmentsToOutlets[catchment.CatchID] == row[1]])
#        row[4] = np.sum([catchment.Area*catchment.Imperviousness/1.0e2 /1e4
#           for _,catchment in msm_CatchmentDataFrame.iterrows() if catchmentsToOutlets[catchment.CatchID] == row[1]])
#        cursor.updateRow(row)
#
