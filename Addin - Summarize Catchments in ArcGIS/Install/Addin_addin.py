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
        
        class Catchment:
            area = 0
            persons = None
            
            imperviousness = 0
            reduction_factor = 0
            initial_loss = 0
            concentration_time = 0
            connection = None
            nettypeno = None
            
            def __init__(self, MUID):
                self.MUID = MUID
            
            @property
            def impervious_area(self):
                return self.area*self.imperviousness/1e2
            
            @property
            def reduced_area(self):
                return self.area*self.imperviousness/1e2*self.reduction_factor
        
        catchments = {}
        
        HParA_redfactor = {}
        HParA_initloss = {}
        HParA_conctime = {}
        
        if combobox_1.selectedfield not in [field.name for field in arcpy.ListFields(catchmentLayer)]:
            try:
                MUIDs = [row[0] for row in arcpy.da.SearchCursor(catchmentLayer, ["MUID"])]
            except RuntimeError:
                fidset = map(int, arcpy.Describe(catchmentLayer).FIDset.split("; "))
                MUIDs = [row[0] for i, row in enumerate(arcpy.da.SearchCursor(arcpy.Describe(catchmentLayer).catalogPath, ["MUID"])) if i in fidset]
            
            # If there's more than 500 catchments, the length of the where_clause might exceed memory. If so, then ignore where_clause.
            if len(MUIDs)<500:
                where_clause = "MUID IN ('%s')" % ("', '".join(MUIDs))
                filter_catchments = False
            else:
                where_clause = ""
                filter_catchments = True
            
            if ".mdb" in arcpy.Describe(catchmentLayer).path:
                msm_HModA = os.path.join(os.path.dirname(arcpy.Describe(catchmentLayer).path), "msm_HModA")
                msm_HParA = os.path.join(os.path.dirname(arcpy.Describe(catchmentLayer).path), "msm_HParA")
                msm_CatchCon = os.path.join(os.path.dirname(arcpy.Describe(catchmentLayer).path), "msm_CatchCon")

                with arcpy.da.SearchCursor(msm_HParA, ["MUID", "RedFactor", "InitLoss", "ConcTime"]) as cursor:
                    for row in cursor:
                        HParA_redfactor[row[0]] = row[1]
                        HParA_initloss[row[0]] = row[2]
                        HParA_conctime[row[0]] = row[3]
                        
                with arcpy.da.SearchCursor(msm_HModA, ["CatchID", "ImpArea", "LocalNo", "RFactor", "ParAID", "ILoss", "ConcTime"], where_clause = where_clause.replace("MUID","CatchID")) as cursor:
                    for row in cursor:
                        catchments[row[0]] = Catchment(row[0])
                        catchments[row[0]].imperviousness = row[1]
                        if row[2] == 1:
                            catchments[row[0]].reduction_factor = row[3]
                            catchments[row[0]].initial_loss = row[5]
                            catchments[row[0]].concentration_time = row[6]
                            
                        elif row[4] in HParA_redfactor:
                            catchments[row[0]].reduction_factor = HParA_redfactor[row[4]]
                            catchments[row[0]].initial_loss = HParA_initloss[row[4]]
                            catchments[row[0]].concentration_time = HParA_conctime[row[4]]

                connected_node = None
                if len(MUIDs) == 1:
                    matches = [row[0] for row in arcpy.da.SearchCursor(msm_CatchCon, ["NodeID"], where_clause = "CatchID = '%s'" % (MUIDs[0]))]
                    if matches:
                        connected_node = matches[0]
                    
                with arcpy.da.SearchCursor(arcpy.Describe(catchmentLayer).catalogPath, ["MUID", "SHAPE@AREA", "Area"], where_clause = where_clause) as cursor:
                    for row in cursor:
                        if row[2]:
                            catchments[row[0]].area = row[2]*1e4
                        else:
                            catchments[row[0]].area = row[1]
                            
            elif ".sqlite" in arcpy.Describe(catchmentLayer).path:
                msm_HParA = os.path.join(arcpy.Describe(catchmentLayer).path, "main.msm_HParA")
                with arcpy.da.SearchCursor(msm_HParA, ["muid", "redfactor", "initloss", "conctime"]) as cursor:
                    for row in cursor:
                        HParA_redfactor[row[0]] = row[1]
                        HParA_initloss[row[0]] = row[2]
                        HParA_conctime[row[0]] = row[3]
                        
                with arcpy.da.SearchCursor(arcpy.Describe(catchmentLayer).catalogPath, ["muid", "SHAPE@AREA", "area", "ModelAImpArea", "ModelAParAID", "modelalocalno", "ModelARFactor", "ModelAILoss", "ModelAConcTime"], where_clause = where_clause) as cursor:
                    for row in cursor:
                        catchments[row[0]] = Catchment(row[0])
                        if row[2]:
                            catchments[row[0]].area = row[2]
                        else:
                            catchments[row[0]].area = abs(row[1])
                            
                        catchments[row[0]].imperviousness = row[3]*1e2
                        if row[4] == 2:
                            catchments[row[0]].reduction_factor = row[5]
                            catchments[row[0]].initial_loss = row[7]
                            catchments[row[0]].concentration_time = row[8]/60
                        elif row[4] in HParA_redfactor:
                            catchments[row[0]].reduction_factor = HParA_redfactor[row[4]]
                            catchments[row[0]].initial_loss = HParA_initloss[row[4]]
                            catchments[row[0]].concentration_time = HParA_conctime[row[4]]/60
            else:
                pythonaddins.MessageBox("Could not find field %s in layer %s" % (combobox_1.selectedfield, combobox.selectedlayer), "Catchment Summarize Error", 0)
            
            # for catchment in catchments.values():
                # pythonaddins.MessageBox((catchment.area, catchment.imperviousness, catchment.reduction_factor), "Catchment summary", 0)
            
            if where_clause or filter_catchments:
                catchments_selected = {MUID: catchments[MUID] for MUID in MUIDs}
            else: 
                catchments_selected = catchments

            catchment_area = np.sum([catchment.area for catchment in catchments_selected.values()])
            catchment_impervious_area = np.sum([catchment.impervious_area for catchment in catchments_selected.values()])
            catchment_reduced_area = np.sum([catchment.reduced_area for catchment in catchments_selected.values()])
            catchment_initial_loss = [catchment.initial_loss for catchment in catchments_selected.values()]
            catchment_concentration_time = [catchment.concentration_time for catchment in catchments_selected.values()]
            
            message_text = "Total area: %1.2f ha\nImpervious area: %1.2f ha (%1.0f%s)\nReduced area: %1.2f ha" % (
                            catchment_area/1e4, catchment_impervious_area/1e4, catchment_impervious_area/catchment_area*1e2, "%", catchment_reduced_area/1e4)
            message_text += "\nConnection: %s" % (connected_node) if connected_node else ""
            # message_text += "\nInitial loss: %s mm\nConcentration time: %s min\n" % ("%d",
            #                                                                               np.min([catchment.concentration_time for catchment in catchments.values()]),
            #                                                                               np.max([catchment.concentration_time for catchment in catchments.values()]))
        else:
            impArea = []
            shapeArea = []
            if "Area" in arcpy.ListFields(catchmentLayer): # if selected field and discharge area
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
                message_text = "Total area: %1.2f ha\nImpervious area: %1.2f ha (%1.0f%s)" % (np.sum(shapeArea)/1e4,np.sum(impArea*shapeArea)/1e6,np.sum(impArea*shapeArea)/1e6/(np.sum(shapeArea)/1e4)*1e2,"%")
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
            
        pythonaddins.MessageBox(message_text, "Catchment summary", 0)