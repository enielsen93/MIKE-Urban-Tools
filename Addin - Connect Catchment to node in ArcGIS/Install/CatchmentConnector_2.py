import arcpy
import pythonaddins
import numpy as np


class ComboBoxClass9(object):
    """Implementation for CatchmentConnector.combobox (ComboBox)"""
    def __init__(self):
        pass
    def onSelChange(self, selection):
        pass
    def onEditChange(self, text):
        pass
    def onFocus(self, focused):
        
        mxd = arcpy.mapping.MapDocument("CURRENT")
        df = arcpy.mapping.ListDataFrames(mxd)[0]
        layers = arcpy.mapping.ListLayers(mxd, "", df)
        print layers
        polygonLayers = []
        for layer in layers:
            if arcpy.Describe(layer).shapeType == "Polygon":
                polygonLayers.append(str(layer))
        self.items = polygonLayers
        self.editable = True
        self.enabled = True
        self.dropdownWidth = 'WWWWWW'
        self.width = 'WWWWWW'
        pass
    def onEnter(self):
        
        mxd = arcpy.mapping.MapDocument("CURRENT")
        df = arcpy.mapping.ListDataFrames(mxd)[0]
        layers = arcpy.mapping.ListLayers(mxd, "", df)
        polygonLayers = []
        for layer in layers:
            if arcpy.Describe(layer).shapeType == "Polygon":
                polygonLayers.append(str(layer))
        self.items = polygonLayers
        self.editable = True
        self.enabled = True
        self.dropdownWidth = 'WWWWWW'
        self.width = 'WWWWWW'
        pass
    def refresh(self):
        pass

class ConnectCatchment(object):
    """Implementation for toolbar1.btn1_1 (Tool)"""
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