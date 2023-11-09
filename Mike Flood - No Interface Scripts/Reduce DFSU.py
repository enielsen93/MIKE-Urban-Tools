import mikeio

dfsu_filepath = r"C:\Users\ELNN\OneDrive - Ramboll\Documents\Aarhus Vand\Vesterbro Torv\MIKE_URBAN\05_RESULTS\03_FLOOD\GA\2023-10-30\VBT_STATUS_002_GA_m21fm - Result Files\VBT_STATUS_CDS_20_138_FM_GABaseDefault_2D_overland.dfsu"
print(dfsu_filepath)
dfs = mikeio.dfsu.Dfsu2DH(dfsu_filepath)

step = 6

timesteps = dfs.time[0::step]
data = dfs.read(time = timesteps)

dfsu_output_filepath = dfsu_filepath.replace(".dfsu", "_reduced.dfsu")
dfs.write(filename = dfsu_output_filepath, data = data)

print("BOB")