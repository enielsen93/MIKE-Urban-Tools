# Tool for reading DFS0 or KM2 files and creating LTS files from it
# Created by Emil Nielsen
# Contact: 
# E-mail: enielsen93@hotmail.com

import os
import sys
import numpy as np
thisFolder = os.path.dirname(__file__)
scriptFolder = os.path.join(thisFolder, r"scripts")
sys.path.append(scriptFolder)
import re
import copy
from shutil import copyfile
import subprocess
import time
import multiprocessing as mp

def run_mex(mouse_sim_launch, mex_file, parallel = False):
    run_cmd = r'"%s" "%s" "HD" "Run" "Close" "NoPrompt" "-wait"' % (mouse_sim_launch, mex_file)
    if parallel:
        subprocess.Popen(run_cmd)
    else: 
        subprocess.call(run_cmd)

class Toolbox(object):
    def __init__(self):
        """Define the toolbox (the name of the toolbox is the name of the
        .pyt file)."""
        self.label = "Batch Simulations"
        self.alias = ""

        # List of tool classes associated with this toolbox
        self.tools = [BatchSimulations]
    
    
class BatchSimulations(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Run Mex Files"
        self.description = "Run Mex Files. \n\nCreated by: Emil Nielsen \nContact: enielsen93@hotmail.com"
        self.canRunInBackground = True

    def getParameterInfo(self):
        #Define parameter definitions
        LTSCount = arcpy.Parameter(
            displayName="Run this many simulations parallel?",
            name="LTSCount",
            datatype="Long",
            parameterType="Required",
            direction="Input")
        LTSCount.value = 4
        
        RunoffFile = arcpy.Parameter(
            displayName="Runoff file (for making dupilcates)",
            name="RunoffFile",
            datatype="File",
            parameterType="Optional",
            direction="Input",)
        RunoffFile.filter.list=["crf", "res1d"]
        
        mex_file = arcpy.Parameter(
            displayName="Network Setup File",
            name="mex_file",
            datatype="File",
            parameterType="Required",
            direction="Input")
        mex_file.filter.list=["mex", "m1dx"]
        
        parameter = arcpy.Parameter(
            displayName="Values for parameter (separate by commas)",
            name="parameter",
            datatype="String",
            parameterType="Required",
            direction="Input")

        mouse_sim_launch = arcpy.Parameter(
            displayName="MOUSE Sim Launch Executable path",
            name="mouse_sim_launch",
            datatype="File",
            parameterType="Optional",
            direction="Input")
        mouse_sim_launch.filter.list=["exe"]
        
        mouse_sim_launch_paths = [r"C:\Program Files (x86)\DHI\2020\bin\x64\MOUSESimLaunch.exe"]
        for path in mouse_sim_launch_paths:
            for year in reversed(range(2010,2030)):
                if os.path.exists(path.replace("2020",str(year))):
                    mouse_sim_launch.value = path.replace("2020",str(year))
                    break

        mike1d_launch = arcpy.Parameter(
            displayName="MIKE1Ds Launch Executable path",
            name="mike1d_launch",
            datatype="File",
            parameterType="Optional",
            direction="Input")
        mike1d_launch.filter.list = ["exe"]

        mike1d_paths = [r"C:\Program Files (x86)\DHI\2020\bin\x64\DHI.Mike1D.Application.exe"]
        for path in mike1d_paths:
            for year in reversed(range(2010, 2030)):
                if os.path.exists(path.replace("2020", str(year))):
                    mike1d_launch.value = path.replace("2020", str(year))
                    break
        
        
        params = [LTSCount, RunoffFile, mex_file, parameter, mouse_sim_launch, mike1d_launch]

        return params

    def isLicensed(self):
        return True

    def updateParameters(self, parameters):
        return

    def updateMessages(self, parameters):
        if parameters[2].Value and ".mex" in parameters[2].ValueAsText:
            with open(parameters[2].ValueAsText,"r") as f:
                mex_file_text = f.read()
            if "par1" not in mex_file_text:
                parameters[2].setErrorMessage("No paramater 'par1' in mex-file")
        return

    def execute(self, parameters, messages):
        LTSCount = int(parameters[0].ValueAsText)
        RunoffFile = parameters[1].ValueAsText
        mex_file = parameters[2].ValueAsText
        parameter = parameters[3].ValueAsText
        mouse_sim_launch = parameters[4].ValueAsText
        mike1d_launch = parameters[5].ValueAsText
        
        parameters = re.findall("[\d\.]+", parameter)
        
        
        with open(mex_file,"r") as f:
            mex_file_text = f.readlines()
        mex_file_parameter_lineno = [lineno for lineno,line in enumerate(mex_file_text) if "par1" in line]
        if RunoffFile and "mex" in mex_file:
            mex_file_text_CRF_lineno = [lineno for lineno,line in enumerate(mex_file_text) if "CRF_file" in line][0]
        elif RunoffFile:
            mex_file_text_CRF_lineno = [lineno for lineno, line in enumerate(mex_file_text) if "RR.res1d" in line][0]
        
        mex_files = []
        processes = []
        for job in range(len(parameters)):
            if RunoffFile:
                arcpy.AddMessage("Copying %s" % RunoffFile)
                if ".mex" in mex_file:
                    RunoffFileNew = RunoffFile[0:-4] + "_Split%d.CRF" % (job+1)
                else:
                    RunoffFileNew = RunoffFile[0:-4] + "_Split%d.res1d" % (job + 1)
                copyfile(RunoffFile, RunoffFileNew)

            if ".mex" in mex_file:
                mex_file_new = copy.deepcopy(mex_file.replace(".mex","_par1-%s.mex" % (parameters[job])))
            else:
                mex_file_new = copy.deepcopy(mex_file.replace(".m1dx", "_par1-%s.m1dx" % (parameters[job])))
            mex_files.append(mex_file_new)
            
            mex_file_new_text = copy.deepcopy(mex_file_text)
            for lineno in mex_file_parameter_lineno:
                mex_file_new_text[lineno] = re.sub("par1", parameters[job], mex_file_new_text[lineno])
            
            if RunoffFile:
                mex_file_new_text[mex_file_text_CRF_lineno] = re.sub("'[^']*'", "'%s'" % RunoffFileNew, mex_file_new_text[mex_file_text_CRF_lineno])
            else:
                mex_file_new_text[mex_file_text_CRF_lineno] = re.sub("'[^']*'", "'%s'" % mex_file_new.replace(".mex",".CRF"), mex_file_new_text[mex_file_text_CRF_lineno])
            
            with open(mex_file_new,'w+') as f:
                f.writelines(mex_file_new_text)
            
            if mouse_sim_launch and ".mex" in mex_file:
               
                while len(processes)>0 and not np.sum([1 for process in processes if process.poll() is None]) < LTSCount:
                    time.sleep(5)
                if not RunoffFile:
                    run_cmd = r'"%s" "%s" "RO" "Run" "Close" "NoPrompt" "-wait"' % (mouse_sim_launch, mex_file_new)
                    subprocess.check_output(run_cmd)
                run_cmd = r'"%s" "%s" "HD" "Run" "Close" "NoPrompt" "-wait"' % (mouse_sim_launch, mex_file_new)
                processes.append(subprocess.Popen(run_cmd))
                time.sleep(1)
            elif mike1d_launch and "m1dx" in mex_file:
                while len(processes)>0 and not np.sum([1 for process in processes if process.poll() is None]) < LTSCount:
                    time.sleep(5)

                run_cmd = '"%s" "%s"' % (mike1d_launch, mex_file_new)
                processes.append(subprocess.Popen(run_cmd))
                time.sleep(1)

        return
        