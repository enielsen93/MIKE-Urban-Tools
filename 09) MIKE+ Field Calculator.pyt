# Tool for reading DFS0 or KM2 files and creating LTS files from it
# Created by Emil Nielsen
# Contact: 
# E-mail: enielsen93@hotmail.com

import os
import sys
import numpy as np
import sqlite3
import arcpy
import tkinter as tk
from collections import Counter

if "mapping" in dir(arcpy):
    arcgis_pro = False
    import arcpy.mapping as arcpymapping
    from arcpy.mapping import MapDocument as arcpyMapDocument
    from arcpy._mapping import Layer
    import pythonaddins
else:
    arcgis_pro = True
    import arcpy.mp as arcpymapping
    from arcpy.mp import ArcGISProject as arcpyMapDocument


class Toolbox(object):
    def __init__(self):
        """Define the toolbox (the name of the toolbox is the name of the
        .pyt file)."""
        self.label = "SQLITE Field Calculator"
        self.alias = ""

        # List of tool classes associated with this toolbox
        self.tools = [FieldCalculator]
    
    
class FieldCalculator(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Calculate Field"
        self.description = "Calculate Field"
        self.canRunInBackground = False

    def getParameterInfo(self):
        #Define parameter definitions
        featureclass = arcpy.Parameter(
            displayName="Feature Class",
            name="featureclass",
            datatype="GPFeatureLayer",
            parameterType="Required",
            multiValue = "True",
            direction="Input")

        field1 = arcpy.Parameter(
            displayName="Field 1 to assign value to",
            name="field1",
            datatype="GPString",
            parameterType="Optional",
            direction="Input")

        value1 = arcpy.Parameter(
            displayName="Value 1",
            name="value1",
            datatype="GPString",
            parameterType="Optional",
            direction="Input")

        field2 = arcpy.Parameter(
            displayName="Field 2 to assign value to",
            name="field2",
            datatype="GPString",
            parameterType="Optional",
            direction="Input")

        value2 = arcpy.Parameter(
            displayName="Value 2",
            name="value2",
            datatype="GPString",
            parameterType="Optional",
            direction="Input")

        field3 = arcpy.Parameter(
            displayName="Field 3 to assign value to",
            name="field3",
            datatype="GPString",
            parameterType="Optional",
            direction="Input")

        value3 = arcpy.Parameter(
            displayName="Value 3",
            name="value3",
            datatype="GPString",
            parameterType="Optional",
            direction="Input")

        # Combine all parameters
        params = [featureclass, field1, value1, field2, value2, field3, value3]

        return params

    def isLicensed(self):
        return True

    def _format_value(self, value):
        """Format selected value for use in the Value parameter."""

        if value is None:
            return None

        # Strings need quotes
        if isinstance(value, str):
            # Escape existing single quotes
            value = value.replace("'", "''")
            return "'{}'".format(value)

        # Numbers etc. don't need quotes
        return str(value)

    def _select_value_from_field(self, featureclass, fieldname):
        """
        Read all unique values from fieldname in the first feature class
        and let the user select one.
        """

        if not featureclass or not fieldname:
            return None

        values = set()

        try:
            with arcpy.da.SearchCursor(featureclass, [fieldname]) as cursor:
                for row in cursor:
                    value = row[0]

                    if value is None:
                        continue

                    value = str(value).strip()

                    if value:
                        values.add(value)

        except Exception as e:
            arcpy.AddWarning(
                "Could not read values from {}: {}".format(fieldname, e)
            )
            return None

        if not values:
            arcpy.AddWarning(
                "No values found in field '{}'.".format(fieldname)
            )
            return None

        # Sort alphabetically
        sorted_values = sorted(values, key=lambda x: x.lower())

        # --------------------------------------------------------------
        # TKINTER WINDOW
        # --------------------------------------------------------------

        root = tk.Tk()
        root.title("Select value")
        root.geometry("450x500")

        #force on top
        root.attributes("-topmost", True)
        root.lift()
        root.focus_force()
        root.update()

        selected_value = [None]

        label = tk.Label(
            root,
            text="Select value from '{}':".format(fieldname),
            anchor="w"
        )
        label.pack(fill="x", padx=10, pady=(10, 5))

        listbox = tk.Listbox(
            root,
            width=60,
            height=20
        )
        listbox.pack(
            fill="both",
            expand=True,
            padx=10,
            pady=5
        )

        # Populate listbox
        for value in sorted_values:
            listbox.insert(tk.END, value)

        # --------------------------------------------------------------
        # SELECT
        # --------------------------------------------------------------

        def select_value(event=None):
            selection = listbox.curselection()

            if not selection:
                return

            index = selection[0]
            selected_value[0] = sorted_values[index]

            root.destroy()

        def cancel():
            root.destroy()

        listbox.bind("<Double-Button-1>", select_value)
        root.bind("<Return>", select_value)

        button_frame = tk.Frame(root)
        button_frame.pack(fill="x", padx=10, pady=10)

        select_button = tk.Button(
            button_frame,
            text="Select",
            command=select_value
        )
        select_button.pack(side="left")

        cancel_button = tk.Button(
            button_frame,
            text="Cancel",
            command=cancel
        )
        cancel_button.pack(side="right")

        if sorted_values:
            listbox.selection_set(0)
            listbox.focus_set()

        root.mainloop()

        return selected_value[0]

    def updateParameters(self, parameters):

        # --------------------------------------------------------------
        # GET FEATURE CLASS
        # --------------------------------------------------------------

        if not parameters[0].Value:
            if arcgis_pro:
                # Reference the active map in the current project
                aprx = arcpymapping.ArcGISProject("CURRENT")
                map_view = aprx.activeMap

                if not parameters[0].value:
                    layers = []

                    for layer in map_view.listLayers():
                        try:
                            if layer.getSelectionSet():
                                layers.append(layer.longName)
                        except:
                            pass

                    parameters[0].value = "; ".join(layers)

            else:
                mxd = arcpy.mapping.MapDocument("CURRENT")

                featureclasses = [
                    lyr.longName
                    for lyr in arcpy.mapping.ListLayers(mxd)
                    if lyr.getSelectionSet()
                       and "muid" in [
                           field.name.lower()
                           for field in arcpy.ListFields(lyr)
                       ]
                ]

                if featureclasses:
                    parameters[0].value = "; ".join(featureclasses)

        # --------------------------------------------------------------
        # FIELDS
        # --------------------------------------------------------------

        if parameters[0].Value:

            first_layer = parameters[0].ValueAsText.split(";")[0]

            desc = arcpy.Describe(first_layer)

            if hasattr(desc, "catalogPath"):
                first_featureclass = desc.catalogPath
            else:
                first_featureclass = first_layer
            fields = [
                f.name
                for f in arcpy.Describe(first_featureclass).fields
            ]

            for i in [1, 3, 5]:
                if not parameters[i].Value:
                    parameters[i].filter.list = fields

        # --------------------------------------------------------------
        # ENABLE / DISABLE FIELD + VALUE PARAMETERS
        # --------------------------------------------------------------

        if parameters[1].Value:

            parameters[3].enabled = True
            parameters[4].enabled = True

            if parameters[3].Value:
                parameters[5].enabled = True
                parameters[6].enabled = True
            else:
                parameters[5].enabled = False
                parameters[6].enabled = False

        else:
            parameters[3].enabled = False
            parameters[4].enabled = False
            parameters[5].enabled = False
            parameters[6].enabled = False

        # --------------------------------------------------------------
        # "s" TRIGGER
        # --------------------------------------------------------------

        if not parameters[0].Value:
            return


        pairs = [
            (1, 2),  # field1 / value1
            (3, 4),  # field2 / value2
            (5, 6),  # field3 / value3
        ]

        for field_index, value_index in pairs:

            fieldname = parameters[field_index].Value
            value = parameters[value_index].Value

            if not fieldname or value is None:
                continue

            # User typed "s"
            if str(value).strip().lower() == "s":

                selected = self._select_value_from_field(
                    first_featureclass,
                    str(fieldname)
                )

                if selected is not None:
                    field = arcpy.ListFields(first_featureclass, fieldname)[0]

                    if field.type in ["String", "Guid"]:
                        formatted = "'{}'".format(selected.replace("'", "''"))
                    else:
                        formatted = str(selected)

                    parameters[value_index].value = formatted

                break

    def updateMessages(self, parameters):
        return

    def execute(self, parameters, messages):
        featureclasses = parameters[0].Values
        field1 = parameters[1].ValueAsText
        value1 = parameters[2].ValueAsText
        field2 = parameters[3].ValueAsText
        value2 = parameters[4].ValueAsText
        field3 = parameters[5].ValueAsText
        value3 = parameters[6].ValueAsText

        for featureclass in featureclasses:
            MU_database = os.path.dirname(arcpy.Describe(featureclass).catalogPath).replace("\mu_Geometry", "").replace("!delete!","")
            print(MU_database)
            featureclass_name = arcpy.Describe(featureclass).name
            arcpy.AddMessage(featureclass)

            arcpy.AddMessage("Confirm Query - Might be hidden behind window!")
            selection = [row[0] for row in arcpy.da.SearchCursor(featureclass, ["MUID"])]

            if arcgis_pro:
                import tkinter as tk
                from tkinter import messagebox

                def confirm_assignment(num_features):
                    root = tk.Tk()
                    root.withdraw()  # Hide the main window
                    result = messagebox.askyesno("Confirm Assignment", f"Assign value to {num_features} features?")
                    root.destroy()
                    return result

                userquery = confirm_assignment(len(selection))
                if userquery:
                    userquery = "Yes"
            else:
                userquery = pythonaddins.MessageBox(
                    "Assign value to %d features?" % (len(selection)),
                    "Confirm Assignment", 4)
                if len(selection)>100:
                    userquery = pythonaddins.MessageBox(
                        "Are you sure? Assign value to %d features?" % (len(selection)),
                        "Confirm Assignment", 4)

            if userquery == "Yes":
                arcpy.AddMessage(MU_database)
                if ".sqlite" in MU_database:
                    try:
                        connection = sqlite3.connect(
                            MU_database)
                        update_cursor = connection.cursor()
                        for field, value in zip([field1, field2, field3], [value1, value2, value3]):
                            if value:

                                arcpy.AddMessage("UPDATE %s SET %s = %s WHERE MUID IN %s" % (featureclass_name.replace("main.",""), field, value,
                                                                                             "('%s')" % ("','".join(selection))))
                                update_query = "UPDATE %s SET %s = %s WHERE MUID IN %s" % (featureclass_name.replace("main.",""), field, value,
                                                                                             "('%s')" % ("','".join(selection)))
                                update_cursor.execute(update_query)
                        connection.commit()
                        connection.close()
                    except Exception as e:
                        import traceback
                        arcpy.AddWarning(traceback.format_exc())
                        raise (e)

                    finally:
                        if connection:
                            connection.close()
                elif ".mdb" in MU_database:
                    for field, value in zip([field1, field2, field3], [value1, value2, value3]):
                        if value:
                            edit = arcpy.da.Editor(MU_database)
                            edit.startEditing(False, True)
                            edit.startOperation()
                            print(featureclass)
                            with arcpy.da.UpdateCursor(arcpy.Describe(featureclass).catalogPath, [field], where_clause = "MUID IN %s" % ("('%s')" % ("','".join(selection)))) as cursor:
                                for row in cursor:
                                    row[0] = value
                                    cursor.updateRow(row)

                            edit.stopOperation()
                            edit.stopEditing(True)
        return
        