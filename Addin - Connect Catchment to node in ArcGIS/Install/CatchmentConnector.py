import arcpy
import pythonaddins
import numpy as np

class CatchmentLayer(object):
    """Implementation for CatchmentConnector.catchmentLayer (ComboBox)"""
    def __init__(self):
        self.items = ["item1", "item2", "item3", "item4", "item5"]
        self.editable = True
        self.enabled = True
        self.dropdownWidth = 'WWWWWWWWWWWWWWWWWW'
        self.width = 'WWWWWWWWWWWWWWWWWW'
        self.selectedLayer = None
    def onSelChange(self, selection):
        if selection != None:
            self.selectedLayer = selection
        else:
            self.selectedLayer = None
    def onEditChange(self, text):
        pass
    def onFocus(self, focused):
        if focused:
            self.mxd = arcpy.mapping.MapDocument("Current")
            layers = arcpy.mapping.ListLayers(self.mxd)
            self.items=[]
            if len(layers) != 0:
                for layer in layers:
                    if layer.isFeatureLayer and arcpy.Describe(layer).shapetype == "Polygon":
                        self.items.append(layer.longName)
    def onEnter(self):
        pass
    def refresh(self):
        pass

class ConnectCatchment(object):
    def __init__(self):
        self.enabled = True
        self.shape = "NONE" # Can set to "Line", "Circle" or "Rectangle" for interactive shape drawing and to activate the onLine/Polygon/Circle event sinks.
    def onMouseDown(self, x, y, button, shift):
        pass
    def onMouseDownMap(self, x, y, button, shift):
        mxd = arcpy.mapping.MapDocument("CURRENT")
        df = arcpy.mapping.ListDataFrames(mxd)[0]
        nodeLayer = [layer for layer in arcpy.mapping.ListLayers(mxd) if layer.longName == manholeLayer.selectedLayer][0]
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

        catchLayer = [layer for layer in arcpy.mapping.ListLayers(mxd) if layer.longName == catchmentLayer.selectedLayer][0]
        catchmentsSelected = []
        ID_fields = ["MUID","FID","OBJECTID","OID"]
        for ID_field in ID_fields:
            if ID_field in [field.name for field in arcpy.ListFields(catchLayer)]:
                break
        arcpy.AddMessage(ID_field)
        with arcpy.da.SearchCursor(catchLayer, [ID_field]) as cursor:
            for i,row in enumerate(cursor):
                catchmentsSelected.append(str(row[0]))
                
        if len(arcpy.ListFields(catchLayer,"NodeID"))>0:
            if pythonaddins.MessageBox("Assign %s to %s (SHP)?" % (", ".join(catchmentsSelected),node), "Confirm Assignment", 1) == "OK":
                arcpy.CalculateField_management(catchLayer, "NodeID", '"%s"' % node, "VB")
        else:
            if pythonaddins.MessageBox("Assign %s to %s (MDB)?" % (", ".join(catchmentsSelected),node), "Confirm Assignment", 1) == "OK":
                catchCon = catchLayer.workspacePath + "\\msm_CatchCon"
                for MUID in catchmentsSelected:
                    catchConExists = False
                    with arcpy.da.UpdateCursor(catchCon, ['CatchID','NodeID']) as cursor:
                        for row in cursor:
                            if row[0] == MUID:
                                row[1] = node
                                catchConExists = True
                            cursor.updateRow(row)
                    if not catchConExists:
                        with arcpy.da.InsertCursor(catchCon, ['CatchID','NodeID']) as cursor:
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

class ManholeLayer(object):
    """Implementation for CatchmentConnector.manholeLayer (ComboBox)"""
    def __init__(self):
        self.items = ["item1", "item2", "item3", "item4", "item5"]
        self.editable = True
        self.enabled = True
        self.dropdownWidth = 'WWWWWWWWWWWWWWWWWW'
        self.width = 'WWWWWWWWWWWWWWWWWW'
        self.selectedLayer = None
    def onSelChange(self, selection):
        if selection != None:
            self.selectedLayer = selection
        else: 
            self.selectedLayer = None
    def onEditChange(self, text):
        pass
    def onFocus(self, focused):
        if focused:
            self.mxd = arcpy.mapping.MapDocument("Current")
            layers = arcpy.mapping.ListLayers(self.mxd)
            self.items=[]
            if len(layers) != 0:
                for layer in layers:
                    if layer.isFeatureLayer and arcpy.Describe(layer).shapetype == "Point":
                        self.items.append(layer.longName)
    def onEnter(self):
        pass
    def refresh(self):
        pass