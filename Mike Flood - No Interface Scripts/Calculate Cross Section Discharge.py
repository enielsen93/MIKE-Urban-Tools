import mikeio
import arcpy
import numpy as np
import datetime
import matplotlib.pyplot as plt
import os

dfs2_files = [r"C:\Offline\VOR_Status\VOR_Status_CDS20_2dCDS20.m21 - Result Files\VOR_Status_CDS20_2dCDS20_15_Depth_Velocity_Flux.dfs2",
              r"C:\Offline\VOR_Status\VOR_Status_CDS10_2dCDS10.m21 - Result Files\VOR_Status_CDS10_2dCDS10_13_Depth_Velocity_Flux.dfs2",
              r"C:\Offline\VOR_Status\VOR_Status_CDS5_2dCDS5.m21 - Result Files\VOR_Status_CDS5_2dCDS5_17_Depth_Velocity_Flux.dfs2",
              r"C:\Offline\VOR_Status\VOR_Status_CDS100_2dCDS100.m21 - Result Files\VOR_Status_CDS100_2dCDS100_19_Depth_Velocity_Flux.dfs2"]

plt.figure()
for dfs2_file in dfs2_files:
    print(dfs2_file)
    dfs2 = mikeio.dfs2.Dfs2(dfs2_file)
    items = [item.name for item in dfs2.items]
    # data_flux = np.nan_to_num(dfs2.read(items=["Q Flux"]).data[0])
    data = dfs2.read(items=["H Water Depth", "U velocity", 'V velocity'])
    data_depth = np.nan_to_num(data[0].values)
    data_u_velocity = np.nan_to_num(data[1].values)
    data_v_velocity = np.nan_to_num(data[2].values)
    # data_flow = np.abs(data_u_velocity * dfs2.dx * data_depth) + (data_v_velocity * dfs2.dy * data_depth)

    dfs2_time = [dfs2.start_time + datetime.timedelta(seconds=t_i * dfs2.timestep) for t_i in range(dfs2.n_timesteps)]

    line_feature_class = r"C:\Offline\VOR_Status\Cross_section_discharge.shp"
    # points_feature_class = r"C:\Users\ELNN\OneDrive - Ramboll\Documents\ArcGIS\scratch.gdb\Points"
    # area_feature_class = r"C:\Users\ELNN\OneDrive - Ramboll\Documents\ArcGIS\scratch.gdb\Area"
    polyline_shape = [row[0] for row in arcpy.da.SearchCursor(line_feature_class, ["SHAPE@"])]
    # area_shape = [row[0] for row in arcpy.da.SearchCursor(area_feature_class, ["SHAPE@"])]

    dfs2_x = dfs2.geometry.x
    dfs2_y = dfs2.geometry.y

    dfs2_x, dfs2_y = np.meshgrid(dfs2.geometry.x, dfs2.geometry.y)
    dfs2_points = np.empty(dfs2_x.shape, dtype = object)

    # for x_i in range(dfs2_x.shape[0]):
    #     for y_i in range(dfs2_x.shape[1]):
    #         dfs2_points[x_i, y_i] = arcpy.Point(dfs2_x[x_i,y_i], dfs2_y[x_i,y_i])

    arcpy.env.overwriteOutput = True
    # new_line_feature_class = arcpy.management.CopyFeatures(line_feature_class, os.path.join(
    #     r"C:\Users\ELNN\OneDrive - Ramboll\Documents\ArcGIS\scratch.gdb", os.path.basename(dfs2_file).replace(".dfs2","")))[0]

    resolution = dfs2.dx/3

    for shape in polyline_shape:
        indices = np.empty((0, 2), dtype=int)
        indices_flow_direction = []
        cross_section_flow_u = np.zeros((data_u_velocity.shape[0]))
        cross_section_flow_v = np.zeros((data_u_velocity.shape[0]))
        for distance in np.arange(0, shape.length, resolution):
            point = shape.positionAlongLine(distance)
            match = [i[0] for i in dfs2.geometry.find_index(point.firstPoint.X, point.firstPoint.Y)]

            match.reverse()
            if match not in [list(index) for index in indices]:
                indices = np.append(indices, np.array([match]), axis=0)

        indices_flow_direction = np.ones(indices.shape, dtype=bool)
        for match_i, match in enumerate(indices):
            if list(match + [1, 0]) in [list(index) for index in indices]:
                indices_flow_direction[match_i, 0] = False
            if list(match + [0, 1]) in [list(index) for index in indices]:
                indices_flow_direction[match_i, 1] = False

        for match, flow_direction in zip(indices, indices_flow_direction):
            if flow_direction[0]:
                cross_section_flow_u += data_u_velocity[:, match[0], match[1]] * data_depth[:, match[0],
                                                                                 match[1]] * dfs2.dx
            if flow_direction[1]:
                cross_section_flow_v += data_v_velocity[:, match[0], match[1]] * data_depth[:, match[0],
                                                                                 match[1]] * dfs2.dx
        # plt.step(dfs2_time, cross_section_flow_u)
        # plt.step(dfs2_time, cross_section_flow_v)
        cross_section_flow_u = -cross_section_flow_u if np.sum(cross_section_flow_u) < 0 else cross_section_flow_u
        cross_section_flow_v = -cross_section_flow_v if np.sum(cross_section_flow_v) < 0 else cross_section_flow_v
        plt.step(dfs2_time, (cross_section_flow_u + cross_section_flow_v) * 1e3, label = os.path.basename(dfs2_file))
    dfs2.close()
    # with arcpy.da.UpdateCursor(new_line_feature_class, ["SHAPE@", "MaxFlow", "TotalFlow"]) as cursor:
    #     for row in cursor:
    #         shape = row[0]
    #         plt.figure()
    #         indices = np.empty((0,2), dtype = int)
    #         indices_flow_direction = []
    #         cross_section_flow_u = np.zeros((data_flux.shape[0]))
    #         cross_section_flow_v = np.zeros((data_flux.shape[0]))
    #         for distance in np.arange(0, shape.length, resolution):
    #             point = shape.positionAlongLine(distance)
    #             # points.append(point)
    #             match = [i[0] for i in dfs2.geometry.find_index(point.firstPoint.X, point.firstPoint.Y)]
    #
    #             # for timestep in range(data_flux.shape[0]):
    #             #     # cross_section_flow[timestep] += data_flux[timestep, int(match[0]), int(match[1])]
    #             #     cross_section_flow[timestep] += ((np.abs(data_v_velocity[timestep, int(match[0]), int(match[1])]*dfs2.dx)
    #             #                                      + np.abs(data_u_velocity[timestep, int(match[0]), int(match[1])]*dfs2.dx))*
    #             #                                      data_depth[timestep, int(match[0]), int(match[1])])
    #             match.reverse()
    #             if not match in [list(index) for index in indices]:
    #                 indices = np.append(indices, np.array([match]), axis=0)
    #         indices_flow_direction = np.ones(indices.shape, dtype=bool)
    #         for match_i, match in enumerate(indices):
    #             if list(match+[1,0]) in [list(index) for index in indices]:
    #                 indices_flow_direction[match_i, 0] = False
    #             if list(match+[0,1]) in [list(index) for index in indices]:
    #                 indices_flow_direction[match_i, 1] = False
    #
    #         for match, flow_direction in zip(indices, indices_flow_direction):
    #             if flow_direction[0]:
    #                 cross_section_flow_u += data_u_velocity[:, match[0], match[1]] * data_depth[:, match[0], match[1]] * dfs2.dx
    #             if flow_direction[1]:
    #                 cross_section_flow_v += data_v_velocity[:, match[0], match[1]] * data_depth[:, match[0], match[1]] * dfs2.dx
    #         # cross_section_flows.append(cross_section_flow)
    #         # # for timestep in range(data_flux.shape[0]):
    #         # #     for index in indices:
    #         # #         print(data_depth[timestep, int(index[0]), int(index[1])])
    #         # #         values[timestep] += data_flux[timestep, int(index[0]), int(index[1])] * 1e3
    #         plt.step(dfs2_time, cross_section_flow_u)
    #         plt.step(dfs2_time, cross_section_flow_v)
    #         cross_section_flow_u = -cross_section_flow_u if np.sum(cross_section_flow_u)<0 else cross_section_flow_u
    #         cross_section_flow_v = -cross_section_flow_v if np.sum(cross_section_flow_v) < 0 else cross_section_flow_v
    #         plt.step(dfs2_time, (cross_section_flow_u+cross_section_flow_v)*1e3)
    #         row[1] = np.max((cross_section_flow_u+cross_section_flow_v)*1e3)
    #         row[2] = np.sum((cross_section_flow_u+cross_section_flow_v)*1e3*dfs2.timestep)
    #         cursor.updateRow(row)

plt.legend()
plt.show()
print("break")
#
# plt.figure()
# plt.step(dfs2_time, np.abs(cross_section_flows[0]) - np.abs(cross_section_flows[1]))
# plt.show()
#
# volume = np.zeros((len(dfs2_time)))
# for shape in area_shape:
#     for x_i in range(dfs2_x.shape[0]):
#         for y_i in range(dfs2_x.shape[1]):
#             if shape.contains(dfs2_points[x_i, y_i]):
#                 volume += data_depth[:, x_i, y_i] * dfs2.dx * dfs2.dy
# plt.figure()
# plt.step(dfs2_time, np.abs(cross_section_flows[0]) - np.abs(cross_section_flows[1]))
#
#
# plt.step(dfs2_time[1:], np.diff(volume))
# plt.show()
#
#
#
#
# # with arcpy.da.InsertCursor(points_feature_class, ["SHAPE@"]) as cursor:
# #     for index in indices:
# #         cursor.insertRow([arcpy.Point(dfs2_x[index[0], index[1]], dfs2_y[index[0], index[1]])])
#
#
# plt.show()
#
# # new_item_names = dfs2.items[:3]
# # names = []
# # for item in dfs2.items:
# #     names.append(item.name)
# #     item.name = item.name[0]
# # dfs2.write(r"C:\Offline\VOR_Status\VOR_Status_CDS10_2dCDS10.m21 - Result Files\Test.dfs2",
# #            data = dfs2.read(items = ["H Water Depth", "P Flux", "Q Flux"]).data, items = new_item_names)
# print("break")