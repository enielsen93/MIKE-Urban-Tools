# -*- coding: utf-8 -*-
"""
Created on Mon Dec  5 08:06:16 2022

@author: ELNN
"""
import re
import os
import arcpy

mdb_filepath = r"C:\Papirkurv\VOR_Plan_023.mdb"
msm_Node = os.path.join(mdb_filepath, "msm_Node")

couple_filepaths = ["C:\Papirkurv\VOR_Plan_CDS5_2dCDS5.couple"]

for couple_filepath in couple_filepaths:
# couple_filepath = couple_filepaths[0]

    with open(couple_filepath, 'r') as f:
        txt = f.readlines()

    txt_output = txt

    muids_lineno = [i for i,line in enumerate(txt) if "Urban_ID" in line]
    points_x_lineno = [i for i,line in enumerate(txt) if "points_x" in line]
    class Node:
        x = None
        y = None
        points_x_lineno = None

    nodes = {}
    for i, lineno in enumerate(muids_lineno):
        muid = re.findall("'([^']+)'", txt[lineno])[0]
        nodes[muid] = Node()
        nodes[muid].points_x_lineno = points_x_lineno[i]


    with arcpy.da.SearchCursor(msm_Node, ["MUID", "SHAPE@XY"]) as cursor:
        for row in cursor:
            if row[0] in nodes:
                nodes[row[0]].x, nodes[row[0]].y = row[1]

    for muid in nodes:
        node = nodes[muid]
        if muid in ['Node_177', 'Node_178', 'Node_179', 'Node_180']:
            txt_output[node.points_x_lineno-1] = re.sub(r"(.+=).+", r"\1 4", txt_output[node.points_x_lineno-1])
            txt_output[node.points_x_lineno] = re.sub(r"(.+=).+", r"\1 %1.2f, %1.2f, %1.2f, %1.2f" % (
                                                                                            node.x - 1,
                                                                                            node.x + 1,
                                                                                            node.x + 1,
                                                                                            node.x -1
                                                                                        ), txt_output[node.points_x_lineno])
            txt_output[node.points_x_lineno+1] = re.sub(r"(.+=).+", r"\1 %1.2f, %1.2f, %1.2f, %1.2f" % (
                                                                                            node.y - 1,
                                                                                            node.y - 1,
                                                                                            node.y + 1,
                                                                                            node.y + 1
                                                                                        ), txt_output[node.points_x_lineno+1])

            txt_output[node.points_x_lineno+2] = re.sub(r"(.+=).+", r"\1 0.0, 0.0, 0.0, 0.0", txt_output[node.points_x_lineno+2])

    with open(couple_filepath, 'w') as f:
        f.writelines(txt_output)
        # i = [i for i,id in enumerate(nodes.keys())]

print("Break")