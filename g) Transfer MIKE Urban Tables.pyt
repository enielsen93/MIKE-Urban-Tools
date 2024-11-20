# Created by Emil Nielsen
# Contact: 
# E-mail: enielsen93@hotmail.com

import arcpy
import numpy as np
from arcpy import env
import re
import os

class Toolbox(object):
    def __init__(self):
        self.label =  "Transfer Mike Urban Project Settings"
        self.alias  = "Transfer Mike Urban Project Settings"

        # List of tool classes associated with this toolbox
        self.tools = [TransferMikeUrbanSettingsCustom] #TransferMikeUrbanSettings

class TransferMikeUrbanSettings(object):
    def __init__(self):
        self.label       = "Transfer Mike Urban Project Settings"
        self.description = "Transfer Mike Urban Project Settings"
        self.canRunInBackground = True

    def getParameterInfo(self):
        #Define parameter definitions

        # Input Features parameter
        target_database = arcpy.Parameter(
            displayName="Target Mike Urban database",
            name="database",
            datatype="DEWorkspace",
            parameterType="Required",
            direction="Input")
        
        reference_database = arcpy.Parameter(
            displayName="Reference Mike Urban database",
            name="reference_database",
            datatype="DEWorkspace",
            parameterType="Required",
            direction="Input")
        
        transfer_lts = arcpy.Parameter(
            displayName="Transfer LTS result settings as well",
            name="transfer_lts",
            datatype="Boolean",
            parameterType="Optional",
            direction="Input")
            
        tables = arcpy.Parameter(
            displayName="Transfer LTS result settings as well",
            name="tables",
            datatype="GPString",
            multiValue = "True",
            parameterType="Optional",
            direction="Input")
           
        tables.filter.list = [u'm_Address', u'm_CFGCExtId', u'm_CFGCExtRelation', u'm_CFGCExtSequencer', u'm_CFGDomainValues', u'm_CFGNoModelAttribute', u'm_CFGProcessData', u'm_CFGSMReport', u'm_CFGUEnvAttr', u'm_CFGUEnvInfo', u'm_CFGUEnvItem', u'm_CFGVersion', u'm_Measurement', u'm_Operator', u'm_Owner', u'm_RESStatisticsCommon', u'm_RESStatisticsIndividual', u'm_RESStatisticsResult', u'm_RESStatisticsStorage', u'ms_2DBoundary', u'ms_CRS', u'ms_CRSD', u'ms_DPPattern', u'ms_DPPatternD', u'ms_DPProfile', u'ms_DPProfileD', u'ms_DPSchedule', u'ms_DPSpecDay', u'ms_LULandUse', u'ms_Material', u'ms_Tab', u'ms_TabD', u'ms_Topo', u'ms_TopoD', u'msa_LinkType', u'msa_NodeType', u'msa_SubSystem', u'msa_System', u'msm_2DOverland', u'msm_ADComponent', u'msm_ADComponentIni', u'msm_ADDispersion', u'msm_ADDispersionLocal', u'msm_BBoundary', u'msm_BItem', u'msm_CatchCon', u'msm_ECOLABCoeff', u'msm_ECOLABCoeffLocal', u'msm_ECOLABComponent', u'msm_ECOLABForcing', u'msm_ECOLABForcingLocal', u'msm_ECOLABTemplate', u'msm_Empt', u'msm_HACDelay', u'msm_HACMeasure', u'msm_HACModel', u'msm_HACParam', u'msm_HModA', u'msm_HModB', u'msm_HModC', u'msm_HModCRC', u'msm_HModUHM', u'msm_HParA', u'msm_HParB', u'msm_HParC', u'msm_HParRDII', u'msm_LAAggrLoad', u'msm_LIDcontrol', u'msm_LIDusage', u'msm_LinkAdv', u'msm_LossPar', u'msm_LTSInit', u'msm_LTSInito', u'msm_LTSJobStart', u'msm_LTSJobStop', u'msm_LTSResult', u'msm_LTSResultL', u'msm_LTSResultN', u'msm_LTSRunM', u'msm_LTSRunS', u'msm_OnGrade', u'msm_OnGradeD', u'msm_Option', u'msm_PasReg', u'msm_Project', u'msm_Project2DParam', u'msm_RESCatchment', u'msm_RESLink', u'msm_RESNode', u'msm_RESOrifice', u'msm_RESPump', u'msm_RESWeir', u'msm_RS', u'msm_RSLink', u'msm_RSNode', u'msm_RSOrifice', u'msm_RSPump', u'msm_RSValve', u'msm_RSWeir', u'msm_RTCCondition', u'msm_RTCConditionD', u'msm_RTCDevice', u'msm_RTCDeviceD', u'msm_RTCFunction', u'msm_RTCFunctionD', u'msm_RTCPID', u'msm_RTCSensor', u'msm_SRQ', u'msm_SRQAttachPol', u'msm_SRQGullyData', u'msm_ST', u'msm_STFraction', u'msm_STInitDepthLocal', u'msm_STRemovalBasin', u'msm_STRemovalWeir', u'msm_SWQLocTreat_Coeff', u'msm_SWQLocTreat_Node', u'msm_SWQPollutant', u'msm_WQProcess', u'mss_Adjustment', u'mss_Aquifer', u'mss_Buildup', u'mss_CatchModel', u'mss_Coverage', u'mss_DWF', u'mss_DWFD', u'mss_Evaporation', u'mss_Groundwater', u'mss_Hydrograph', u'mss_HydrographD', u'mss_Inflow', u'mss_InflowD', u'mss_Landuse', u'mss_LIDcontrol', u'mss_LIDusage', u'mss_Loading', u'mss_Pattern', u'mss_Pollutant', u'mss_Project', u'mss_RDII', u'mss_RESCatchment', u'mss_RESLink', u'mss_RESNode', u'mss_RESOrifice', u'mss_RESPump', u'mss_RESWeir', u'mss_Rule', u'mss_RuleD', u'mss_SnowPack', u'mss_Tab', u'mss_TabD', u'mss_Temperature', u'mss_Timeseries', u'mss_TimeseriesD', u'mss_Transect', u'mss_TransectD', u'mss_Treatment', u'mss_Washoff', u'mw_CFloCon', u'mw_CGlobal', u'mw_CGroup', u'mw_CGroupC', u'mw_Control', u'mw_CPreCon', u'mw_Curve', u'mw_CurveD', u'mw_DemStat', u'mw_DPPattern', u'mw_DPPatternD', u'mw_DPProfile', u'mw_DPProfileD', u'mw_DZone', u'mw_Energy', u'mw_EPA_Sum', u'mw_FireFlow', u'mw_Friction', u'mw_Global', u'mw_Loss', u'mw_MDemand', u'mw_OnCalcDem', u'mw_OnCalcFCV', u'mw_OnDemZone', u'mw_OnDemZoneD', u'mw_OnFromDIMS', u'mw_OnSettings', u'mw_OnToDIMS', u'mw_OnWaterAge', u'mw_PID', u'mw_PipeRel', u'mw_Project', u'mw_PZone', u'mw_Quality', u'mw_Reaction', u'mw_Reliability', u'mw_RemCapacity', u'mw_Report', u'mw_RESInfo', u'mw_RESJunction', u'mw_RESLink', u'mw_RESNode', u'mw_RESPipe', u'mw_RESPipeRel', u'mw_RESPump', u'mw_RESSusNode', u'mw_RESSusPipe', u'mw_RESTank', u'mw_RESValve', u'mw_Rule', u'mw_Source', u'mw_Time', u'mw_Water_Src', u'mw_WH_Boundary', u'mw_WH_Options', u'mwa_LinkType', u'mwa_SubSystem', u'mwa_System', u'zs_Group', u'zs_GroupData', u'zs_ScenarioManagerData']
        
        
        parameters = [reference_database, target_database, transfer_lts]
        
        return parameters

    def isLicensed(self): #optional
        return True

    def updateParameters(self, parameters): #optional
        return

    def updateMessages(self, parameters): #optional
       
        return

    def execute(self, parameters, messages):
        arcpy.env.overwriteOutput = True
        arcpy.TableToTable_conversion(in_rows=parameters[0].ValueAsText + r"\msm_Project", out_path=parameters[1].ValueAsText, out_name="msm_Project")
        
        tables = ["msm_LTSInit", "msm_LTSInito", "msm_LTSJobStart", "msm_LTSJobStop", "msm_LTSResult", "msm_LTSResultL", "msm_LTSResultN", "msm_LTSRunM", "msm_LTSRunS"]
        if parameters[2].Value:
            for table in tables:
                arcpy.TableToTable_conversion(in_rows=parameters[0].ValueAsText + r"\\" + table, out_path=parameters[1].ValueAsText, out_name=table)
                
        
        return

class TransferMikeUrbanSettingsCustom(object):
    def __init__(self):
        self.label       = "Transfer Mike Urban tables"
        self.description = "Transfer Mike Urban tables"
        self.canRunInBackground = True

    def getParameterInfo(self):
        #Define parameter definitions

        # Input Features parameter
        target_database = arcpy.Parameter(
            displayName="Target Mike Urban database",
            name="database",
            datatype="DEWorkspace",
            parameterType="Required",
            direction="Input")
        
        reference_database = arcpy.Parameter(
            displayName="Reference Mike Urban database",
            name="reference_database",
            datatype="DEWorkspace",
            parameterType="Required",
            direction="Input")
            
        tables = arcpy.Parameter(
            displayName="Transfer LTS result settings as well",
            name="tables",
            datatype="GPString",
            multiValue = "True",
            parameterType="Optional",
            direction="Input")
           
        tables.filter.list = [u'msm_Project (Simulations)', u'msm_BBoundary (Catchment Loads, Network Loads and External Water Levels)', u'msm_BItem (Boundary Items)', u'msm_HModA (Time Area A)', u'msm_CatchCon (Catchment Connections)', u'msm_LTSJobStart (Job list criteria)', u'msm_LTSJobStop', u'msm_LTSRunM (Run time stop criteria - matrix)', u'msm_LTSResult (Statistics specifications - global)', u'msm_LTSResultL (Statistics specifications - links)', u'msm_LTSResultN (Statistics specifications - nodes)', u'ms_Tab (Curves & Relations primary table)', u'ms_TabD (Curves & Relations secondary table)', u'm_Address', u'm_CFGCExtId', u'm_CFGCExtRelation', u'm_CFGCExtSequencer', u'm_CFGDomainValues', u'm_CFGNoModelAttribute', u'm_CFGProcessData', u'm_CFGSMReport', u'm_CFGUEnvAttr', u'm_CFGUEnvInfo', u'm_CFGUEnvItem', u'm_CFGVersion', u'm_Measurement', u'm_Operator', u'm_Owner', u'm_RESStatisticsCommon', u'm_RESStatisticsIndividual', u'm_RESStatisticsResult', u'm_RESStatisticsStorage', u'ms_2DBoundary', u'ms_CRS', u'ms_CRSD', u'ms_DPPattern', u'ms_DPPatternD', u'ms_DPProfile', u'ms_DPProfileD', u'ms_DPSchedule', u'ms_DPSpecDay', u'ms_LULandUse', u'ms_Material', u'ms_Topo', u'ms_TopoD', u'msa_LinkType', u'msa_NodeType', u'msa_SubSystem', u'msa_System', u'msm_2DOverland', u'msm_ADComponent', u'msm_ADComponentIni', u'msm_ADDispersion', u'msm_ADDispersionLocal', u'msm_ECOLABCoeff', u'msm_ECOLABCoeffLocal', u'msm_ECOLABComponent', u'msm_ECOLABForcing', u'msm_ECOLABForcingLocal', u'msm_ECOLABTemplate', u'msm_Empt', u'msm_HACDelay', u'msm_HACMeasure', u'msm_HACModel', u'msm_HACParam', u'msm_HModB', u'msm_HModC', u'msm_HModCRC', u'msm_HModUHM', u'msm_HParA', u'msm_HParB', u'msm_HParC', u'msm_HParRDII', u'msm_LAAggrLoad', u'msm_LIDcontrol', u'msm_LIDusage', u'msm_LinkAdv', u'msm_LossPar', u'msm_LTSInit', u'msm_LTSInito', u'msm_LTSRunS', u'msm_OnGrade', u'msm_OnGradeD', u'msm_Option', u'msm_PasReg', u'msm_Project2DParam', u'msm_RESCatchment', u'msm_RESLink', u'msm_RESNode', u'msm_RESOrifice', u'msm_RESPump', u'msm_RESWeir', u'msm_RS', u'msm_RSLink', u'msm_RSNode', u'msm_RSOrifice', u'msm_RSPump', u'msm_RSValve', u'msm_RSWeir', u'msm_RTCCondition', u'msm_RTCConditionD', u'msm_RTCDevice', u'msm_RTCDeviceD', u'msm_RTCFunction', u'msm_RTCFunctionD', u'msm_RTCPID', u'msm_RTCSensor', u'msm_SRQ', u'msm_SRQAttachPol', u'msm_SRQGullyData', u'msm_ST', u'msm_STFraction', u'msm_STInitDepthLocal', u'msm_STRemovalBasin', u'msm_STRemovalWeir', u'msm_SWQLocTreat_Coeff', u'msm_SWQLocTreat_Node', u'msm_SWQPollutant', u'msm_WQProcess', u'mss_Adjustment', u'mss_Aquifer', u'mss_Buildup', u'mss_CatchModel', u'mss_Coverage', u'mss_DWF', u'mss_DWFD', u'mss_Evaporation', u'mss_Groundwater', u'mss_Hydrograph', u'mss_HydrographD', u'mss_Inflow', u'mss_InflowD', u'mss_Landuse', u'mss_LIDcontrol', u'mss_LIDusage', u'mss_Loading', u'mss_Pattern', u'mss_Pollutant', u'mss_Project', u'mss_RDII', u'mss_RESCatchment', u'mss_RESLink', u'mss_RESNode', u'mss_RESOrifice', u'mss_RESPump', u'mss_RESWeir', u'mss_Rule', u'mss_RuleD', u'mss_SnowPack', u'mss_Tab', u'mss_TabD', u'mss_Temperature', u'mss_Timeseries', u'mss_TimeseriesD', u'mss_Transect', u'mss_TransectD', u'mss_Treatment', u'mss_Washoff', u'mw_CFloCon', u'mw_CGlobal', u'mw_CGroup', u'mw_CGroupC', u'mw_Control', u'mw_CPreCon', u'mw_Curve', u'mw_CurveD', u'mw_DemStat', u'mw_DPPattern', u'mw_DPPatternD', u'mw_DPProfile', u'mw_DPProfileD', u'mw_DZone', u'mw_Energy', u'mw_EPA_Sum', u'mw_FireFlow', u'mw_Friction', u'mw_Global', u'mw_Loss', u'mw_MDemand', u'mw_OnCalcDem', u'mw_OnCalcFCV', u'mw_OnDemZone', u'mw_OnDemZoneD', u'mw_OnFromDIMS', u'mw_OnSettings', u'mw_OnToDIMS', u'mw_OnWaterAge', u'mw_PID', u'mw_PipeRel', u'mw_Project', u'mw_PZone', u'mw_Quality', u'mw_Reaction', u'mw_Reliability', u'mw_RemCapacity', u'mw_Report', u'mw_RESInfo', u'mw_RESJunction', u'mw_RESLink', u'mw_RESNode', u'mw_RESPipe', u'mw_RESPipeRel', u'mw_RESPump', u'mw_RESSusNode', u'mw_RESSusPipe', u'mw_RESTank', u'mw_RESValve', u'mw_Rule', u'mw_Source', u'mw_Time', u'mw_Water_Src', u'mw_WH_Boundary', u'mw_WH_Options', u'mwa_LinkType', u'mwa_SubSystem', u'mwa_System', u'zs_Group', u'zs_GroupData', u'zs_ScenarioManagerData']
        
        parameters = [reference_database, target_database, tables]
        
        return parameters

    def isLicensed(self): #optional
        return True

    def updateParameters(self, parameters): #optional
        return

    def updateMessages(self, parameters): #optional
       
        return

    def execute(self, parameters, messages):
        arcpy.env.overwriteOutput = True
        tables = parameters[2].values
        getRealTable = re.compile(r"([^ ]+)")
        for table in tables:
            table = getRealTable.findall(table)[0]
            try:
                arcpy.management.Delete(os.path.join(parameters[1].ValueAsText, table))
                arcpy.TableToTable_conversion(in_rows=parameters[0].ValueAsText + r"\\" + table, out_path=parameters[1].ValueAsText, out_name=table)
            except Exception as e:
                arcpy.AddError("Can't transfer table %s" % (table))
                raise(e)
            arcpy.AddMessage("Transfered table %s" % table)
        
        return