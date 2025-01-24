<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>MIKE Urban Tools</title>
</head>
<body>
    <h1>MIKE Urban Tools</h1>
    <p>Enhance your workflows with tools for DHI MIKE Urban through ArcGIS.</p>

    <h2>Installation Guide</h2>

    <h3>1. Install the Tools</h3>
    <p>Follow these steps to set up the MIKE Urban Tools in ArcGIS:</p>
    <ol>
        <li><a href="https://github.com/enielsen93/MIKE-Urban-Tools/archive/refs/heads/main.zip" target="_blank">Download the ZIP file</a>.</li>
        <li>Extract the ZIP file to a folder on your computer.</li>
        <li>Open <strong>ArcMap</strong> or <strong>ArcGIS Pro</strong>.</li>
        <li>In the Catalog pane:
            <ul>
                <li>Navigate to the folder where you extracted the tools.</li>
                <li>The tools will now be available for use.</li>
            </ul>
        </li>
    </ol>

    <h3>2. Install the Python Requirements</h3>
    <p>To use the tools, you'll need to install a few Python libraries. Run the following commands in a terminal:</p>
    <pre>
python -m pip install https://github.com/enielsen93/networker/tarball/master
python -m pip install https://github.com/enielsen93/ColebrookWhite/tarball/master
python -m pip install https://github.com/enielsen93/mikegraph/tarball/master
    </pre>

    <h4>Note:</h4>
    <p>If <strong>ArcGIS</strong> does not use your default Python interpreter, you'll need to specify the Python path. Replace <code>python</code> with the full path to your ArcGIS Python installation. For example:</p>
    <pre>
"C:\Python27\ArcGIS10.7\python.exe" -m pip install https://github.com/enielsen93/ColebrookWhite/tarball/master
    </pre>


    <h2>Questions or Issues?</h2>
    <p>Feel free to <a href="https://github.com/enielsen93/MIKE-Urban-Tools/issues" target="_blank">open an issue</a> on this repository for help or feedback!</p>
</body>
</html>
