import os
from shutil import copyfile
from subprocess import call
import re
import sys
from datetime import datetime


#m11extraPath = r"C:\Program Files (x86)\DHI\2016\bin\m11extra.exe"
#prfFile = r"K:\Hydrauliske modeller\Flora\Truust\Faarvang\StoreRoerBBase.PRF"
node = "FRA440R"
dfs0File = node + ".dfs0"
workingDir = os.path.dirname(__file__)
#print os.path.dirname(__file__)
#prfFileCopy = workingDir + "\prffile.PRF"
#copyfile(prfFile,prfFileCopy)

sys.path.append(workingDir + "\clr")
import clr
clr.AddReference(workingDir + r"\DHI MIKE SDK\DHI.Generic.MikeZero.DFS.dll")
clr.AddReference(workingDir + r"\DHI MIKE SDK\DHI.Generic.MikeZero.EUM.dll")
clr.AddReference(workingDir + r"\DHI MIKE SDK\MatlabDfsUtil.2016.dll")
import MatlabDfsUtil
import DHI.Generic.MikeZero
import DHI.Generic.MikeZero.DFS
import DHI.Generic.MikeZero.DFS.dfs0
import DHI.Generic.MikeZero.DFS.dfs123
from System import Array, Char
import System
#
#call([m11extraPath, prfFileCopy])
#M11OUT = workingDir + "\M11.OUT"
#M11IN = workingDir + "\M11.IN"
#
#lines = ""
#with open(M11OUT,'r') as M11OUTFile:
#    for line in M11OUTFile:
#        if "Node_WL:  <%s>" % node in line:
#            line = re.sub("^0","1",line)
#        lines += line
#            
#with open(M11IN.replace(".OUT",".IN"),'w') as M11INFile:
#    M11INFile.write(lines)
#csvFile = "%s.csv" % node
#call([m11extraPath, "prffile.PRF", csvFile, "/NOHEADER"])
#readCSVRe = re.compile('(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) +([\d\.]+)')
#dates = []
#clocks = []
#waterlevels = []
#with open(csvFile,"r") as f:
#    for line in f:
#        matches = readCSVRe.findall(line)
#        dates.append(matches[0][0])
#        waterlevels.append(matches[0][1])
#datesDT = [datetime.strptime(a,"%Y-%m-%d %H:%M:%S") for a in dates]
#
## Building .dfs0
#factory = DHI.Generic.MikeZero.DFS.DfsFactory()
#builder = DHI.Generic.MikeZero.DFS.DfsBuilder.Create(
#        'Python dfs0 file', 'Python DFS', 0)
#starttimeDT = System.DateTime(
#    *
#    datesDT[0].timetuple()[
#        :6],
#    kind=System.DateTimeKind.Utc)
#timeSeconds = [0]
#for i in range(len(datesDT)-1):
#    timeSeconds.append((datesDT[i+1]-datesDT[0]).seconds)
#    
#builder.SetDataType(0)
#builder.SetGeographicalProjection(
#    factory.CreateProjectionGeoOrigin(
#        'UTM-33', 12, 54, 2.6))
#builder.SetTemporalAxis(
#    factory.CreateTemporalNonEqCalendarAxis(
#        DHI.Generic.MikeZero.eumUnit.eumUsec,
#        starttimeDT))
#
#item1 = builder.CreateDynamicItemBuilder()
#dfsdataType = DHI.Generic.MikeZero.DFS.DfsSimpleType.Float
#item1.Set(
#    'Vandniveau',
#    DHI.Generic.MikeZero.eumQuantity(
#        DHI.Generic.MikeZero.eumItem.eumIWaterLevel,
#        DHI.Generic.MikeZero.eumUnit.eumUmeter),
#    dfsdataType)
#        
#item1.SetValueType(DHI.Generic.MikeZero.DFS.DataValueType.Instantaneous)
#item1.SetAxis(factory.CreateAxisEqD0())
#builder.AddDynamicItem(item1.GetDynamicItemInfo())
#
#builder.CreateFile(workingDir + "\\" + dfs0File)
#dfs = builder.GetFile()
#
#waterlevelsArr = System.Array.CreateInstance(float, len(waterlevels), 1)
#for i, val in enumerate(waterlevels):
#    waterlevelsArr[i, 0] = val
#
#MatlabDfsUtil.DfsUtil.WriteDfs0DataDouble(
#        dfs, Array[float](timeSeconds), waterlevelsArr)
#dfs.Close()

#for f in [csvFile,M11IN,M11OUT,prfFileCopy]:
#    if os.path.isfile(f):
#        os.remove(f)