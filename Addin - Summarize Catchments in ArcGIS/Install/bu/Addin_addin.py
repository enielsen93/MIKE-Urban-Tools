import arcpy
import pythonaddins
import numpy as np
import os

class CatchmentComboBox(object):
    """Implementation for Addin_addin.combobox (ComboBox)"""
    def __init__(self):
        self.items = ["item1", "item2", "item3", "item4", "item5"]
        self.editable = True
        self.enabled = True
        self.dropdownWidth = 'WWWWWWWWWWWWWWWWWW'
        self.width = 'WWWWWWWWWWWWWWWWWWWWWWWW'
    def onSelChange(self, selection):
        if selection != None:
            self.selectedlayer = selection
            combobox_1.enabled = True
        else:
            combobox_1.enabled = False
            self.selectedlayer = None
        pass
    def onEditChange(self, text):
        pass
    def onFocus(self, focused):
        #Populate the items list with the available layers
        if focused:
            self.mxd = arcpy.mapping.MapDocument("Current")
            layers = arcpy.mapping.ListLayers(self.mxd)
            self.items=[]
            if len(layers) != 0:
                for layer in layers:
                    if layer.isFeatureLayer and arcpy.Describe(layer).shapetype == "Polygon":
                        self.items.append(layer.longName)
        pass
    def onEnter(self):
        pass
    def refresh(self):
        pass

class ImpAreaComboBox(object):
    """Implementation for Addin_addin.combobox_1 (ComboBox)"""
    def __init__(self):
        self.items = ["item1", "item2", "item3", "item4", "item5"]
        self.editable = True
        self.enabled = True
        self.dropdownWidth = 'WWWWWW'
        self.width = 'WWWWWW'
        self.selectedfield = None
    def onSelChange(self, selection):
        self.selectedfield = selection

    def onEditChange(self, text):
        pass
    def onFocus(self, focused):
        layer = combobox.selectedlayer
        self.items = []
        self.items.append("From HModA")
        fields = arcpy.ListFields(layer)
        for field in fields:
            self.items.append(field.name)
        arcpy.AddMessage([field.name for field in fields])
        if "ImpArea" in [field.name for field in fields]:
            self.selectedField = "ImpArea"
        
    def onEnter(self):
        pass
    def refresh(self):
        pass

class SummarizeButton(object):
    """Implementation for Addin_addin.button (Button)"""
    def __init__(self):
        self.enabled = True
        self.checked = False
    def onClick(self):
        mxd = arcpy.mapping.MapDocument("CURRENT")
        df = arcpy.mapping.ListDataFrames(mxd)[0]
        catchmentLayer = [layer for layer in arcpy.mapping.ListLayers(mxd) if layer.longName == combobox.selectedlayer][0]
            
        impArea = []
        shapeArea = []
        red_factor = []
        if combobox_1.selectedfield not in [field.name for field in arcpy.ListFields(catchmentLayer)]:
            if ".mdb" in arcpy.Describe(catchmentLayer).path:
                msm_HModA = os.path.join(os.path.dirname(arcpy.Describe(catchmentLayer).path), "msm_HModA")
                msm_HParA = os.path.join(os.path.dirname(arcpy.Describe(catchmentLayer).path), "msm_HParA")
                MUIDs = [row[0] for row in arcpy.da.SearchCursor(catchmentLayer, ["MUID"])]      
                MUIDImpArea = {}
                HParA = {}
                MUIDRedFactor = {}
                with arcpy.da.SearchCursor(msm_HParA, ["MUID", "RedFactor"]) as cursor:
                    for row in cursor:
                        HParA[row[0]] = row[1]
                with arcpy.da.SearchCursor(msm_HModA, ["CatchID", "ImpArea", "LocalNo", "RFactor", "ParAID"], where_clause = "CatchID IN ('%s')" % ("', '".join(MUIDs))) as cursor:
                    for row in cursor:
                        MUIDImpArea[row[0]] = row[1]
                        if row[2] == 1:
                            MUIDRedFactor[row[0]] = row[3]
                        elif row[4] in HParA:
                            MUIDRedFactor[row[0]] = HParA[row[4]]
                        else:
                            MUIDRedFactor[row[0]] = 0
                impArea = []
                redArea = []
                with arcpy.da.SearchCursor(catchmentLayer, ["MUID", "SHAPE@AREA", "Area"]) as cursor:
                    for row in cursor:
                        if row[0] in MUIDImpArea:
                            impArea.append(MUIDImpArea[row[0]])
                            redArea.append(MUIDRedFactor[row[0]])
                        else:
                            impArea.append(0)
                            redArea.append(0)
                        if row[2]:
                            shapeArea.append(row[2]*1e4)
                        elif row[1] <> None:
                            shapeArea.append(row[1])
                        else:
                            shapeArea.append(row[0])
                        
            else:
                pythonaddins.MessageBox("Could not find field %s in layer %s" % (combobox_1.selectedfield, combobox.selectedlayer), "Catchment Summarize Error", 0)
        elif "Area" in arcpy.ListFields(catchmentLayer): # if selected field and discharge area
            with arcpy.da.SearchCursor(catchmentLayer, ["SHAPE@AREA", "Area", combobox_1.selectedfield]) as cursor:
                for row in cursor:
                    if row[2] <> None:
                        impArea.append(row[2])
                    else:
                        impArea.append(0)
                    if row[1]:
                        shapeArea.append(row[1])
                    else:
                        shapeArea.append(row[0])
        else:
            with arcpy.da.SearchCursor(catchmentLayer, ["SHAPE@AREA", combobox_1.selectedfield]) as cursor:
                for row in cursor:
                    if row[1] <> None:
                        impArea.append(row[1])
                    else:
                        impArea.append(0)
                    shapeArea.append(row[0])
        impArea = np.array(impArea)
        shapeArea = np.array(shapeArea)
        
        message_text = "Total area: %1.2f ha\nImpervious area: %1.2f ha (%1.0f%s)" % (np.sum(shapeArea)/1e4,np.sum(impArea*shapeArea)/1e6,np.sum(impArea*shapeArea)/1e6/(np.sum(shapeArea)/1e4)*1e2,"%")
        if ".mdb" in arcpy.Describe(catchmentLayer).path:
            redArea = np.array(redArea)
            message_text = "%s\nReduced area: %1.2f ha" % (message_text, np.sum(impArea*shapeArea*redArea)/1e6)
        pythonaddins.MessageBox(message_text, "Catchment summary", 0)