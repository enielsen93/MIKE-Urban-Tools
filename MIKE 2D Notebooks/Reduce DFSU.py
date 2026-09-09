import mikeio
from datetime import datetime

dfsu_filepath = r"C:\Users\ELNN.RAMBOLL.000\OneDrive - Ramboll\Documents\Mosagergroeften\MIKE\MOS_PLAN_016\MOS_PLAN_016_m21fm - Result Files\MOS_STATUS_016_CDS_10_107BaseDefault_2D_overland.dfsu"

print("Reading %s" % dfsu_filepath)
dfs = mikeio.dfsu.Dfsu2DH(dfsu_filepath)

filter_start = datetime.strptime("%s 01:45" % dfs.time[0].strftime("%Y.%m.%d"), "%Y.%m.%d %H:%M")

step = 3#int(60/dfs.timestep) if 60>dfs.timestep else 1

# timesteps = dfs.time[-2:]
timesteps = dfs.time[dfs.time>filter_start]
timesteps = timesteps[0::step]
print("Reading %d timesteps" % len(timesteps))
data = dfs.read(time = timesteps)

dfsu_output_filepath = dfsu_filepath.replace(".dfsu", "_reduced.dfsu")
print("Writing %s" % dfsu_output_filepath)
mikeio.dfsu.write_dfsu(filename = dfsu_output_filepath, data = data)

# print("BOB")/