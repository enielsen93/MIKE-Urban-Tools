import mikeio
from datetime import datetime

dfsu_filepath = r"C:\Papirkurv\CDS_100_Yr_2D_New_GLBaseDefault_2D_overland.dfsu"

print("Reading %s" % dfsu_filepath)
dfs = mikeio.dfsu.Dfsu2DH(dfsu_filepath)

filter_start = datetime.strptime("%s 01:30" % dfs.time[0].strftime("%Y.%m.%d"), "%Y.%m.%d %H:%M")

step = int(60/dfs.timestep) if 60>dfs.timestep else 1

timesteps = dfs.time[-2:]
#timesteps = dfs.time[dfs.time>filter_start]
#timesteps = timesteps[0::step]
# print("Reading %d timesteps" % len(timesteps))
data = dfs.read(time = timesteps)

dfsu_output_filepath = dfsu_filepath.replace(".dfsu", "_reduced.dfsu")
print("Writing %s" % dfsu_output_filepath)
dfs.write(filename = dfsu_output_filepath, data = data)

print("BOB")