@echo off
setlocal enabledelayedexpansion
set "filename=%~1"
set "extension=!filename:~-4!"

if /i "!extension!"==".mex" (
        "C:\Program Files (x86)\DHI\2020\bin\x64\MOUSESimLaunch.exe" "%~1" "RO" "Run" "Close" "NoPrompt" "-wait"
		"C:\Program Files (x86)\DHI\2020\bin\x64\MOUSESimLaunch.exe" "%~1" "HD" "Run" "Close" "NoPrompt" "-wait"
    ) else (
        
		)
