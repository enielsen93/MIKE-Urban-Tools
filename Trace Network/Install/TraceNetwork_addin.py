# -*- coding: utf-8 -*-     
import arcpy
import pythonaddins
import numpy as np
import os

class Node:
    def __init__(self, MUID, shape):
        self.MUID = MUID
        self.shape = shape

class ButtonClass21(object):
    """Implementation for TraceNetwork_addin.find_all_connected_catchments (Button)"""
    def __init__(self):
        self.enabled = True
        self.checked = False
    def onClick(self):
        nodes_MUID = [row[0] for row in arcpy.da.SearchCursor(group_layer.msm_Node, ["MUID"])]
        print(nodes_MUID)
        catchments = group_layer.graph.find_connected_catchments(nodes_MUID)
        catchments_MUID = [catchment.MUID for catchment in catchments]

        print("MUID IN ('%s')" % ("', '".join(catchments_MUID)))
        arcpy.SelectLayerByAttribute_management(group_layer.ms_Catchment.longName, "ADD_TO_SELECTION",
                                                "MUID IN ('%s')" % ("', '".join(catchments_MUID)))

        pass
        
class ButtonClass25(object):
    """Implementation for TraceNetwork_addin.find_all_unconnected_catchments (Button)"""
    def __init__(self):
        self.enabled = True
        self.checked = False
    def onClick(self):
        group_layer.graph._read_catchments()
        nodes_MUID = [row[0] for row in arcpy.da.SearchCursor(os.path.join(group_layer.msm_Node.workspacePath, "msm_Node"), ["MUID"])]
        catchments_MUID = [catchment.MUID for catchment in group_layer.graph.catchments_dict.values() if not catchment.nodeID and catchment.nodeID not in nodes_MUID]
        print("MUID IN ('%s')" % ("', '".join(catchments_MUID)))
        arcpy.SelectLayerByAttribute_management(group_layer.ms_Catchment.longName, "ADD_TO_SELECTION",
                                                "MUID IN ('%s')" % ("', '".join(catchments_MUID)))
        pass

class GroupComboBoxClass1(object):
    """Implementation for TraceNetwork_addin.combobox (ComboBox)"""
    def __init__(self):
        self.items = ["item1", "item2","item1", "item2","item1", "item2"]
        self.editable = True
        self.enabled = True
        self.dropdownWidth = 'WWWWWWWWWWWWWWWWWW'
        self.width = 'WWWWWWWWWWWWWWWWWW'
        self.msm_Node = None
        self.msm_Link = None
        self.ms_Catchment = None
        self.layers_in_group = []

    def onSelChange(self, selection):
        self.selected_group = selection
        self.layers_in_group = [layer for layer in arcpy.mapping.ListLayers(self.mxd) if self.selected_group + "\\" in layer.longName]
        print([layer.longName for layer in self.layers_in_group])
        msm_Node_layer = [layer for layer in self.layers_in_group if
                    u"Br??nd" in layer.longName or "msm_Node" in layer.longName and layer.visible]
        print(msm_Node_layer)
        self.msm_Node = msm_Node_layer[0] if msm_Node_layer else None

        msm_Link_layer = [layer for layer in self.layers_in_group if
         "Ledning" in layer.longName or "msm_Link" in layer.longName and layer.visible]
        print(msm_Link_layer)
        self.msm_Link = msm_Link_layer[0] if msm_Link_layer else None

        ms_Catchment_layer = [layer for layer in self.layers_in_group if
         "Delopland" in layer.longName or "Catchment" in layer.longName and layer.visible]
        print(ms_Catchment_layer)
        self.ms_Catchment = ms_Catchment_layer[0] if ms_Catchment_layer else None

        import mikegraph
        self.graph = mikegraph.Graph(self.msm_Node.workspacePath)
        self.graph.map_network()
        pass
    def onEditChange(self, text):
        pass
    def onFocus(self, focused):
        if focused:
            self.mxd = arcpy.mapping.MapDocument("Current")
            self.df = arcpy.mapping.ListDataFrames(self.mxd)[0]

            group_layers = [layer for layer in arcpy.mapping.ListLayers(self.mxd) if layer.isGroupLayer]
            self.items = []
            if len(group_layers) != 0:
                for layer in group_layers:
                    self.items.append(layer.longName)

        pass
    def onEnter(self):
        pass
    def refresh(self):
        pass

class TraceDownstreamToolClass18(object):
    """Implementation for TraceNetwork_addin.tool_1 (Tool)"""
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
    """Implementation for TraceNetwork_addin.tool (Tool)"""
    def __init__(self):
        self.enabled = True
        self.shape = "NONE" # Can set to "Line", "Circle" or "Rectangle" for interactive shape drawing and to activate the onLine/Polygon/Circle event sinks.
    def onMouseDown(self, x, y, button, shift):
        pass
    def onMouseDownMap(self, x, y, button, shift):
        points_xy = np.zeros((int(arcpy.management.GetCount(os.path.join(group_layer.msm_Node.workspacePath, "msm_Node"))[0]),2))
        points_muid = []

        with arcpy.da.SearchCursor(os.path.join(group_layer.msm_Node.workspacePath, "msm_Node"), ["MUID", "SHAPE@"]) as cursor:
            for i,row in enumerate(cursor):
                points_xy[i,:] = [row[1].firstPoint.X, row[1].firstPoint.Y]
                points_muid.append(row[0])

        def findClosestNode(coord):
            distances = np.sum(np.abs(points_xy-[coord[0], coord[1]]),axis=1)
            index_closest = np.argmin(distances)
            muid = points_muid[index_closest]
            return muid


        target = findClosestNode([x,y])

        upstream_nodes = group_layer.graph.find_upstream_nodes([target])[0]

        print("MUID IN ('%s')" % ("', '".join(upstream_nodes)))
        if group_layer.msm_Node:
            arcpy.SelectLayerByAttribute_management(group_layer.msm_Node.longName, "ADD_TO_SELECTION", "MUID IN ('%s')" % ("', '".join(upstream_nodes)))

        if group_layer.msm_Link:
            links_MUID = [link.MUID for link in group_layer.graph.network.links.values() if
                          link.fromnode in upstream_nodes and link.tonode in upstream_nodes]
            arcpy.SelectLayerByAttribute_management(group_layer.msm_Link.longName, "ADD_TO_SELECTION",
                                                    "MUID IN ('%s')" % ("', '".join(links_MUID)))

        if group_layer.ms_Catchment:
            total_catchments = []

            catchments = group_layer.graph.find_connected_catchments(upstream_nodes)
            for catchment in catchments:
                total_catchments.append(catchment.MUID)

            arcpy.SelectLayerByAttribute_management(group_layer.ms_Catchment.longName, "ADD_TO_SELECTION",
                                                    "MUID IN ('%s')" % ("', '".join(total_catchments)))

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