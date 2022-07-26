# -*- coding: utf-8 -*-     
import arcpy
import pythonaddins
import mikegraph

class Node:
    def __init__(self, MUID, shape):
        self.MUID = MUID
        self.shape = shape

class GroupComboBoxClass1(object):
    """Implementation for Addin - Trace Network_addin.combobox (ComboBox)"""
    def __init__(self):
        self.items = ["item1", "item2"]
        self.editable = True
        self.enabled = True
        self.dropdownWidth = 'WWWWWWWWWWWWWWWWWW'
        self.width = 'WWWWWWWWWWWWWWWWWW'
    def onSelChange(self, selection):
        self.selected_group = selection
        layers_in_group = [layer for layer in arcpy.mapping.ListLayers(mxd) if GroupComboBoxClass1.selected_group + "\\" in layer.longName]

        self.msm_Node = [layer for layer in layers_in_group if u"Brønd" in layer]
        self.msm_Link = [layer for layer in layers_in_group if "Ledning" in layer]
        self.ms_Catchment = [layer for layer in layers_in_group if "Delopland" in layer]

        self.graph = mikegraph.Graph(self.msm_Node.workspacePath)
        self.graph.map_network()
        pass
    def onEditChange(self, text):
        pass
    def onFocus(self, focused):
        if focused:
            self.mxd = arcpy.mapping.MapDocument("Current")
            self.df = arcpy.mapping.ListDataFrames(mxd)[0]

            group_layers = [layer for layer in arcpy.mapping.ListLayers(mxd) if layer.isGroupLayer]
            self.items = []
            if len(layers) != 0:
                for layer in group_layers:
                    self.items.append(layer.longName)
        pass
    def onEnter(self):
        pass
    def refresh(self):
        pass

class TraceDownstreamToolClass18(object):
    """Implementation for Addin - Trace Network_addin.tool_1 (Tool)"""
    def __init__(self):
        self.enabled = True
        self.shape = "NONE" # Can set to "Line", "Circle" or "Rectangle" for interactive shape drawing and to activate the onLine/Polygon/Circle event sinks.
    def onMouseDown(self, x, y, button, shift):
        pass
    def onMouseDownMap(self, x, y, button, shift):
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

class TraceUpstreamToolClass16(object):
    """Implementation for Addin - Trace Network_addin.tool (Tool)"""
    def __init__(self):
        self.enabled = True
        self.shape = "NONE" # Can set to "Line", "Circle" or "Rectangle" for interactive shape drawing and to activate the onLine/Polygon/Circle event sinks.
    def onMouseDown(self, x, y, button, shift):
        pass
    def onMouseDownMap(self, x, y, button, shift):
        points_xy = np.zeros((int(arcpy.management.GetCount(GroupComboBoxClass1.msm_Node)[0]),2))
        points_muid = []

        with arcpy.da.SearchCursor(msm_Node, ["MUID", "SHAPE@"]) as cursor:
            for i,row in enumerate(cursor):
                nodes[row[0]] = self.Node(row[0], row[1])
                points_xy[i,:] = [row[1].firstPoint.X, row[1].firstPoint.Y]
                points_muid.append(row[0])

        def findClosestNode(coord):
            distances = np.sum(np.abs(points_xy-[coord[0], coord[1]]),axis=1)
            index_closest = np.argmin(distances)
            muid = points_muid[index_closest]
            return muid

        target = findClosestNode([x,y])

        upstream_nodes = self.graph.find_upstream_nodes([target])

        arcpy.SelectLayerByAttribute_management(GroupComboBoxClass1.msm_Node, "ADD_TO_SELECTION", "MUID IN ('%s')" % ("', '".join(upstream_nodes)))

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