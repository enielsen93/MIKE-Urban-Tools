import arcpy

MU_database = r"K:\Hydrauliske modeller\Flora\Truust\Faarvang\Faarvang_1.9_testB.mdb"
node = "FRD200R"
dfs0File = r"K:\Hydrauliske modeller\Flora\Truust\Faarvang\FRD200R.dfs0"

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
                        row2[2] = "Water Level"
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
        timeseriesName = node
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
        
        
        