import arcpy
import os

mdb_database = r"C:\pwwork\ramdk\ramboll_elnn\d0833277\M-TF-E-62-1.mdb"
use_pipe_catalogue = r"C:\Makroer & Beregningsark\Mike Urban Tools\Data\ExportToCad\Pipe_Catalogue.dbf"
dimension = 'Top'

pipe_catalogue = []
class PipeSize:
    def __init__(self, material, internal_diameter, thickness_side, thickness_top, thickness_bottom):
        self.material = material
        self.internal_diameter = internal_diameter
        self.thickness_side = thickness_side
        self.thickness_top = thickness_top
        self.thickness_bottom = thickness_bottom

if use_pipe_catalogue:
    with arcpy.da.SearchCursor(use_pipe_catalogue, ["Material", "Intern_dia", "Thick_side", "Thick_top", "Thick_bot"]) as cursor:
        for row in cursor:
            pipe_catalogue.append(PipeSize(row[0], row[1], row[2], row[3], row[4]))

delledning = os.path.join(mdb_database, "Delledning")

materiale_koder = {1: "Concrete", 5: "Plastic", 8: "GAP"}

with arcpy.da.UpdateCursor(delledning, ['Handelsmaal', 'Godstykkelse', 'MaterialeKode']) as cursor:
    for row in cursor:
        if row[2] in materiale_koder:
            material = materiale_koder[row[2]]

            matching_pipe = [pipesize for pipesize in pipe_catalogue if pipesize.material == material and pipesize.internal_diameter == row[0]]
            if matching_pipe:
                if dimension.lower() == "top":
                    row[1] = matching_pipe[0].thickness_top
                elif dimension.lower() == "side":
                    row[1] = matching_pipe[0].thickness_side
                elif dimension.lower() == "bottom":
                    row[1] = matching_pipe[0].thickness_bottom

                cursor.updateRow(row)