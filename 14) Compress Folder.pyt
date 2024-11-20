# -*- coding: utf-8 -*-
import os
import zipfile
import numpy as np
import re
import sys
import shutil

if sys.version_info < (3, 5):
    try:
        from scandir import scandir
    except ImportError:
        raise ImportError("The scandir module is required for Python versions below 3.5. Please install it using 'pip install scandir'.")
else:
    from os import scandir

class Toolbox(object):
    def __init__(self):
        self.label = "Compress Folder"
        self.alias = "Compress Folder"
        self.canRunInBackground = True
        # List of tool classes associated with this toolbox
        self.tools = [CompressFolder, CopyFolder]


class CompressFolder(object):
    def __init__(self):
        self.label = "Compress Folder to Zip"
        self.description = "Compress Folder to Zip"
        self.canRunInBackground = False



    def getParameterInfo(self):
        # Define parameter definitions

        folder = arcpy.Parameter(
            displayName="Folder",
            name="folder",
            datatype="DEFolder",
            parameterType="Required",
            direction="Input")

        include_subfolders = arcpy.Parameter(
            displayName="Include Subfolders",
            name="include_subfolders",
            datatype="GPBoolean",
            parameterType="Optional",
            direction="Input")
        include_subfolders.value = True

        file_formats = arcpy.Parameter(
            displayName="Include the following file extensions:",
            name="file_formats",
            datatype="GPString",
            parameterType="Optional",
            multiValue=True,
            direction="Input")
        #ignore_fields.value = ["msm_Catchment", "msm_Node", "msm_Link", "msm_Weir", "msm_Orifice"]

        output_file = arcpy.Parameter(
            displayName="Output Zip Archive:",
            name="output_file",
            datatype="DEFile",
            parameterType="Required",
            direction="Output")
        output_file.filter.list = ["zip"]

        delete_files = arcpy.Parameter(
            displayName="Delete Original Files upon compressing",
            name="delete_files",
            datatype="GPBoolean",
            parameterType="Optional",
            direction="Input")
        delete_files.value = False

        delete_files = arcpy.Parameter(
            displayName="Delete Original Files upon compressing",
            name="delete_files",
            datatype="GPBoolean",
            parameterType="Optional",
            direction="Input")
        delete_files.value = False

        separate_archives = arcpy.Parameter(
            displayName="Create archive for each file",
            name="separate_archives",
            datatype="GPBoolean",
            parameterType="Optional",
            direction="Input")

        parameters = [folder, include_subfolders, file_formats, output_file, delete_files, separate_archives]
        return parameters

    def isLicensed(self):
        return True

    def updateParameters(self, parameters):
        folder = parameters[0].ValueAsText
        if folder and not parameters[2].filter.list:
            include_subfolders = parameters[1].Value
            file_extensions = set()
            file_extensions_total_filesize = {}
            for (dir_path, dir_names, filenames) in os.walk(folder):
                for filename in filenames:
                    extension = os.path.splitext(filename)[-1].lower()
                    if extension in file_extensions_total_filesize:
                        file_extensions_total_filesize[extension] += os.path.getsize(os.path.join(dir_path, filename))
                    else:
                        file_extensions_total_filesize[extension] = os.path.getsize(os.path.join(dir_path, filename))
                    file_extensions.add(extension)

                if not include_subfolders:
                    break
            file_extensions = list(file_extensions)
            file_extensions.sort()
            parameters[2].filter.list = ["%s (%d MB)" % (ext, file_extensions_total_filesize[ext]/1e6) for ext in file_extensions if ext]
            # if not parameters[2].value:
            #     default_formats = [".mdb", ".dfs0", ".mjl"]
            #     parameters[2].value = [format for format in default_formats if format in file_extensions]
            if not parameters[5].Value and not parameters[4].Value:
                parameters[3].Value = os.path.join(os.path.dirname(folder), os.path.basename(folder) + ".zip")

        if parameters[5].Value:
            parameters[3].enabled = False
        else:
            parameters[3].enabled = True
        return

    def updateMessages(self, parameters):  # optional
        return

    def execute(self, parameters, messages):
        folder = parameters[0].ValueAsText
        include_subfolders = parameters[1].Value
        file_formats = [re.findall("^.(.+) \([^)]+\)", ext)[0] for ext in parameters[2].ValueAsText.split(";")]
        arcpy.AddMessage(file_formats)
        output_file = parameters[3].ValueAsText
        delete_files = parameters[4].Value
        separate_archives = parameters[5].Value

        arcpy.AddMessage(file_formats)

        files = []
        folders = []
        file_sizes = []
        for (dir_path, dir_names, filenames) in os.walk(folder):
            for filename in filenames:
                if os.path.splitext(filename)[-1].lower() in file_formats:
                    files.append(os.path.join(dir_path, filename))
                    file_sizes.append(float(os.path.getsize(os.path.join(dir_path, filename))))
                    folders.append(dir_path)
            if not include_subfolders:
                break

        arcpy.AddMessage(output_file)
        file_sizes = [float(f) for f in file_sizes]

        total_filesize = float(np.sum(file_sizes))
        arcpy.AddMessage(("step", "Compressing files...",
                            0, total_filesize, 1))

        arcpy.SetProgressor("step", "Compressing files...",
                            0, 100, 1)

        completed_filesize = 0

        if separate_archives:
            for file, file_folder, file_size in zip(files, folders, file_sizes):
                with zipfile.ZipFile(os.path.splitext(file)[-2] + ".zip", "w", allowZip64=True, compression=zipfile.ZIP_DEFLATED) as new_zip:
                    # arcpy.AddMessage((file_folder, folder))
                    # arcpy.AddMessage(os.path.relpath(file_folder, folder))
                    arcname = os.path.basename(file)
                    arcpy.AddMessage(arcname)
                    new_zip.write(file, arcname = arcname)
                    if delete_files:
                        arcpy.AddMessage("Deleting %s" % (file))
                        os.remove(file)

                    completed_filesize += int(file_size)
                    arcpy.SetProgressorPosition(int(completed_filesize/total_filesize*100))
        else:
            with zipfile.ZipFile(output_file, "w", allowZip64 = True, compression = zipfile.ZIP_DEFLATED) as new_zip:
                for file, file_folder, file_size in zip(files, folders, file_sizes):
                    # arcpy.AddMessage((file_folder, folder))
                    # arcpy.AddMessage(os.path.relpath(file_folder, folder))
                    arcname = os.path.join(os.path.relpath(file_folder, folder), os.path.basename(file))
                    arcpy.AddMessage(arcname)
                    new_zip.write(file, arcname = arcname)
                    if delete_files:
                        arcpy.AddMessage("Deleting %s" % (file))
                        os.remove(file)

                    completed_filesize += file_size
                    arcpy.SetProgressorPosition(int(completed_filesize/total_filesize*100))

        return

class CopyFolder(object):
    def __init__(self):
        self.label = "Copy Folder"
        self.description = "Copy Folder"
        self.canRunInBackground = False



    def getParameterInfo(self):
        # Define parameter definitions

        folder = arcpy.Parameter(
            displayName="Folder",
            name="folder",
            datatype="DEFolder",
            parameterType="Required",
            direction="Input")

        include_subfolders = arcpy.Parameter(
            displayName="Include Subfolders",
            name="include_subfolders",
            datatype="GPBoolean",
            parameterType="Optional",
            direction="Input")
        include_subfolders.value = True

        file_formats = arcpy.Parameter(
            displayName="Include the following file extensions:",
            name="file_formats",
            datatype="GPString",
            parameterType="Optional",
            multiValue=True,
            direction="Input")
        #ignore_fields.value = ["msm_Catchment", "msm_Node", "msm_Link", "msm_Weir", "msm_Orifice"]


        output_folder = arcpy.Parameter(
            displayName="Output Location:",
            name="output_folder",
            datatype="DEFolder",
            parameterType="Required",
            direction="Input")

        output_file = arcpy.Parameter(
            displayName="Output Zip Archive:",
            name="output_file",
            datatype="DEFile",
            parameterType="Optional",
            direction="Output")

        second_output_folder = arcpy.Parameter(
            displayName="Move to this folder instead:",
            name="second_output_folder",
            datatype="DEFolder",
            parameterType="Optional",
            direction="Input")

        keep_newest = arcpy.Parameter(
            displayName="Only replace file if it has a newer modified date:",
            name="keep_newest",
            datatype="Boolean",
            parameterType="Optional",
            direction="Output")

        parameters = [folder, include_subfolders, file_formats, output_folder, output_file, second_output_folder, keep_newest]
        return parameters

    def isLicensed(self):
        return True

    def updateParameters(self, parameters):
        folder = parameters[0].ValueAsText
        if folder and not parameters[2].filter.list:
            include_subfolders = parameters[1].Value
            file_extensions = set()
            file_extensions_total_filesize = {}
            for (dir_path, dir_names, filenames) in os.walk(folder):
                for filename in filenames:
                    extension = os.path.splitext(filename)[-1].lower()
                    if extension in file_extensions_total_filesize:
                        file_extensions_total_filesize[extension] += os.path.getsize(os.path.join(dir_path, filename))
                    else:
                        file_extensions_total_filesize[extension] = os.path.getsize(os.path.join(dir_path, filename))
                    file_extensions.add(extension)

                if not include_subfolders:
                    break
            file_extensions = list(file_extensions)
            file_extensions.sort()
            parameters[2].filter.list = ["%s (%d MB)" % (ext, file_extensions_total_filesize[ext]/1e6) for ext in file_extensions if ext]
            # if not parameters[2].value:
            #     default_formats = [".mdb", ".dfs0", ".mjl"]
            #     parameters[2].value = [format for format in default_formats if format in file_extensions]

        return

    def updateMessages(self, parameters):  # optional
        return

    def execute(self, parameters, messages):
        folder = parameters[0].ValueAsText
        include_subfolders = parameters[1].Value
        file_formats = [re.findall("^.(.+) \([^)]+\)", ext)[0] for ext in parameters[2].ValueAsText.split(";")] if ";" in parameters[2].ValueAsText else re.findall("^.(.+) \([^)]+\)", parameters[2].ValueAsText)[0]
        arcpy.AddMessage(file_formats)
        output_folder = parameters[3].ValueAsText
        output_file = parameters[4].ValueAsText
        second_output_folder = parameters[5].ValueAsText
        keep_newest = parameters[6].Value

        arcpy.AddMessage("Mapping source folder")

        class File:
            def __init__(self, mtime, size):
                self.mtime = mtime
                self.size = size

        # files = []
        # folders = []
        # file_sizes = []
        input_files = {}

        def list_files_scandir_input(path):
            for entry in scandir(path):
                if entry.is_file() and os.path.splitext(entry.path)[-1].lower() in file_formats:
                    input_files[entry.path] = File(entry.stat().st_mtime, entry.stat().st_size)
                elif include_subfolders and entry.is_dir():
                    list_files_scandir_input(entry.path)

        list_files_scandir_input(folder)

        # for (dir_path, dir_names, filenames) in os.walk(folder):
        #     for filename in filenames:
        #         if os.path.splitext(filename)[-1].lower() in file_formats:
        #             files.append(os.path.join(dir_path, filename))
        #             file_sizes.append(float(os.path.getsize(os.path.join(dir_path, filename))))
        #             folders.append(dir_path)
        #     if not include_subfolders:
        #         break

        file_sizes = [float(input_file.size) for input_file in input_files.values()]

        total_filesize = float(np.sum(file_sizes))
        # arcpy.AddMessage(("step", "Moving files...",
        #                     0, total_filesize, 1))
        #
        # arcpy.SetProgressor("step", "Moving files...",
        #                     0, 100, 1)

        # if output_file:
        #     new_zip = zipfile.ZipFile(output_file, "w", allowZip64=True, compression=zipfile.ZIP_DEFLATED)
        # obj = scandir(output_folder)

        output_files = {}

        def list_files_scandir_output(path):
            for entry in scandir(path):
                if entry.is_file() and os.path.splitext(entry.path)[-1].lower() in file_formats:
                    output_files[entry.path] = File(entry.stat().st_mtime, entry.stat().st_size)
                elif include_subfolders and entry.is_dir():
                    list_files_scandir_output(entry.path)

        # Specify the directory path you want to start from
        directory_path = output_folder
        list_files_scandir_output(directory_path)

        # Process each input file for copying or skipping based on conditions
        completed_filesize = 0  # Track cumulative copied file size for progress tracking
        for input_filepath in input_files:
            # Get file name, folder path, and file size
            file, file_folder, file_size = os.path.basename(input_filepath), os.path.dirname(input_filepath), \
            input_files[input_filepath].size

            # If output file is set, add file to zip archive if conditions are met
            if output_file:
                new_file_folder = os.path.join(output_folder, os.path.relpath(file_folder, os.path.dirname(folder)))
                new_filepath = os.path.join(new_file_folder, os.path.basename(file))

                # Check if file should be copied to zip based on mtime (keep newest condition)
                if keep_newest == 0 or not new_filepath in output_files.keys() or input_files[input_filepath].mtime > \
                        output_files[new_filepath].mtime:
                    arcname = os.path.join(os.path.relpath(file_folder, folder), os.path.basename(file))
                    arcpy.AddMessage(arcname)
                    new_zip.write(file, arcname=arcname)

            elif second_output_folder:
                new_file_folder = os.path.join(output_folder, os.path.relpath(file_folder, os.path.dirname(folder)))
                new_filepath = os.path.join(new_file_folder, os.path.basename(file))
                # Copy if conditions on file age and size are met
                if not keep_newest or not new_filepath in output_files.keys() or input_files[
                    input_filepath].mtime - 120 > output_files[new_filepath].mtime or (
                        input_files[input_filepath].mtime > output_files[new_filepath].mtime - 120 and input_files[
                    input_filepath].size != output_files[new_filepath].size):
                    # If output folder does not exist, create it
                    if not os.path.exists(new_file_folder.replace(output_folder, second_output_folder)):
                        os.makedirs(new_file_folder.replace(output_folder, second_output_folder))
                    arcpy.AddMessage("Copying %s to %s" % (input_filepath, new_filepath.replace(output_folder, second_output_folder)))
                    arcpy.AddMessage((output_folder,second_output_folder))
                    shutil.copy2(input_filepath, new_filepath.replace(output_folder, second_output_folder))

            else:
                new_file_folder = os.path.join(output_folder, os.path.relpath(file_folder, os.path.dirname(folder)))
                new_filepath = os.path.join(new_file_folder, os.path.basename(file))
                # Copy if conditions on file age and size are met
                if not keep_newest or not new_filepath in output_files.keys() or input_files[
                    input_filepath].mtime - 120 > output_files[new_filepath].mtime or (
                        input_files[input_filepath].mtime > output_files[new_filepath].mtime - 120 and input_files[
                    input_filepath].size != output_files[new_filepath].size):
                    # If output folder does not exist, create it
                    if not new_filepath in output_files.keys() and not os.path.exists(new_file_folder):
                        os.makedirs(new_file_folder)
                    arcpy.AddMessage("Copying %s to %s" % (os.path.join(file_folder, file), new_filepath))
                    shutil.copy2(input_filepath, new_filepath)
                else:
                    # If conditions not met, skip file
                    arcpy.AddMessage("Skipping %s" % os.path.join(file_folder, file))

            # Update progress
            completed_filesize += file_size
            arcpy.SetProgressorPosition(int(completed_filesize / max(1, total_filesize) * 100))

        # Close resources if necessary
        return
