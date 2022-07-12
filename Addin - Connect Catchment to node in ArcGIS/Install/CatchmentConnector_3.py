import arcpy
import pythonaddins
import numpy as np

class ConnectCatchment(object):
    """Implementation for toolbar1.btn1_1 (Tool)"""
    """Implementation for Connect Catchments To Node (alpha)_addin.tool (Tool)"""
    def __init__(self):
        self.enabled = True
        self.shape = "NONE" # Can set to "Line", "Circle" or "Rectangle" for interactive shape drawing and to activate the onLine/Polygon/Circle event sinks.
    def onMouseDown(self, x, y, button, shift):
        pass
    def onMouseDownMap(self, x, y, button, shift):
        mxd = arcpy.mapping.MapDocument("CURRENT")
        df = arcpy.mapping.ListDataFrames(mxd)[0]
        nodeLayer = arcpy.mapping.ListLayers(mxd, "Manholes", df)[0]
        nodesCount = int(arcpy.GetCount_management(nodeLayer)[0])
        nodes = np.empty(nodesCount,dtype=object)
        nodesX = np.empty(nodesCount)
        nodesY = np.empty(nodesCount)
        if len(arcpy.ListFields(nodeLayer,"MUID"))>0:
            with arcpy.da.SearchCursor(nodeLayer, ['MUID','SHAPE@XY']) as cursor:
                for i,row in enumerate(cursor):
                    nodes[i] = row[0]
                    nodesX[i] = row[1][0]
                    nodesY[i] = row[1][1]
        else:
            with arcpy.da.SearchCursor(nodeLayer, ['NodeID','SHAPE@XY']) as cursor:
                for i,row in enumerate(cursor):
                    nodes[i] = row[0]
                    nodesX[i] = row[1][0]
                    nodesY[i] = row[1][1]

        dist = np.sqrt(np.power(nodesX-x,2)+np.power(nodesY-y,2))
        node = nodes[np.argmin(dist)]

        catchmentLayer = arcpy.mapping.ListLayers(mxd, "Catchments", df)[0]
        catchmentsSelected = []
        with arcpy.da.SearchCursor(catchmentLayer, ['MUID']) as cursor:
            for i,row in enumerate(cursor):
                catchmentsSelected.append(row[0])
                
        if len(arcpy.ListFields(catchmentLayer,"NodeID"))>0:
            if pythonaddins.MessageBox("Assign %s to %s?" % (", ".join(catchmentsSelected),node), "Confirm Assignment", 1) == "OK":
                arcpy.CalculateField_management(catchmentLayer, "NodeID", '"%s"' % node, "VB")
        else:
            if pythonaddins.MessageBox("Assign %s to %s?" % (", ".join(catchmentsSelected),node), "Confirm Assignment", 1) == "OK":
                catchCon = nodeLayer.workspacePath + "\\msm_CatchCon"
                for MUID in catchmentsSelected:
                    catchConExists = False
                    with arcpy.da.UpdateCursor("msm_CatchCon", ['CatchID','NodeID']) as cursor:
                        for row in cursor:
                            if row[0] == MUID:
                                row[1] = node
                                catchConExists = True
                            cursor.updateRow(row)
                    if not catchConExists:
                        with arcpy.da.InsertCursor("msm_CatchCon", ['CatchID','NodeID']) as cursor:
                            cursor.insertRow([MUID,node])
        pass
    def onMouseUp(self, x, y, button, shift):
        pass
    def onMouseUpMap(self, x, y, button, shift):
        pass
    def onMouseMove(self, x, y, button, shift):
        pass
    def onMouseMoveMap(self, x, y, button, shift):
        pass
    def onDblClick(self):
        pass
    def onKeyDown(self, keycode, shift):
        pass
    def onKeyUp(self, keycode, shift):
        pass
    def deactivate(self):
        pass
    def onCircle(self, circle_geometry):
        pass
    def onLine(self, line_geometry):
        pass
    def onRectangle(self, rectangle_geometry):
        pass