import numpy as np
import arcpy
import re

couple_file = r"C:\Users\ELNN\Downloads\VOR_Plan_CDS20_2dCDS20.couple"
cell_connections_filepath = r"C:\Papirkurv\cell_connections.shp"

with open(couple_file, 'r') as f:
    txt_lines = f.readlines()

class Connection:
    def __init__(self):
        self.x_coords = []
        self.y_coords = []
        self.urban_ID = None

connections = []
get_coords = re.compile("([\d\.]+)")
for line_i in [line_i for line_i, line in enumerate(txt_lines) if "points_x" in line]:
    connection = Connection()
    for coord in get_coords.findall(txt_lines[line_i]):
        connection.x_coords.append(float(coord))
        print((line_i, coord))
    for coord in get_coords.findall(txt_lines[line_i+1]):
        connection.y_coords.append(float(coord))

    connections.append(connection)
    del connection

for i, line in enumerate([line for line in txt_lines if "Urban_ID" in line]):
    connections[i].urban_ID = re.findall("'([^']+)'", line)[0]

with arcpy.da.InsertCursor(cell_connections_filepath, ["SHAPE@", "MUID"]) as cursor:
    for connection in connections:
        if len(connection.x_coords) > 2:
            points = []
            for x_coord, y_coord in zip(connection.x_coords, connection.y_coords):
                points.append(arcpy.Point(x_coord, y_coord))
            polygon = arcpy.Polygon(arcpy.Array(points))

            cursor.insertRow([polygon, connection.urban_ID])


print("Break")