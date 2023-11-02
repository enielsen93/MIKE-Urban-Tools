import mikeio

dfsu_filepath = r"C:\Users\ELNN\OneDrive - Ramboll\Documents\Aarhus Vand\Vesterbro Torv\MIKE_URBAN\05_RESULTS\03_FLOOD\Plan\VBT_STATUS_002_v4_m21fm - Result Files\VBT_STATUS_CDS_20_138_FMBaseDefault_2D_overland.dfsu"

dfs = mikeio.dfsu.Dfsu2DH(dfsu_filepath)

step = 6

timesteps = dfs.time[0::step]
data = dfs.read(time = timesteps)

dfsu_output_filepath = dfsu_filepath.replace(".dfsu", "_reduced.dfsu")
dfs.write(filename = dfsu_output_filepath, data = data)

print("BOB")