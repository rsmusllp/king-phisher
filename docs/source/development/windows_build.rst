Windows Build
=============

Each release of King Phisher includes an MSI build of the client for easy use
on Windows systems. Creating this build is one of the last steps prior to
creating a new version release. The build is created using the Python
`cx_Freeze <https://pypi.python.org/pypi/cx_Freeze>`_ package.

Before the build can be created the `PyGObject for Windows
<http://sourceforge.net/projects/pygobjectwin32/>`_ package must be installed.
While installing this package, it prompts for which GNOME libraries are to be
included. When the prompt appears the following packages should be selected.

- Base packages
- ATK
- GConf
- GDK-Pixbuf
- GTK+
- GTKSourceView
- GXML
- Pango
- Soup
- WebkitGTK

Once all packages have been installed and the King Phisher client is running
with Python, the "tools/build_msi.bat" script can be executed to create the
build. The build process will take a few minutes, but once completed an MSI
installer file will be created in a new "dist" directory in the projects root
folder.

Version Information
-------------------

After building the MSI file you will need to add custom properties.
By right clicking on the MSI file, select properties, and then the
custom tab you can add custom fields. You will need to add
the Python Version, and PyGI-AIO version utilized in making the build
as text entries. Below is the name fields and example values.

+--------------------------------+---------------------------------+
| Name                           | Example Value                   |
+================================+=================================+
| Python Version                 | 3.4                             |
+--------------------------------+---------------------------------+
| PyGI-AIO Version               | 3.14.0 rev22                    |
+--------------------------------+---------------------------------+

Python 3.4 Build
----------------

As of King Phisher Version 1.8, the windows client is built with Python 3.4.
To install basemaps for Python 3.4 you will have to compile geos one windows.
On top of installing the requirements for pip that are not included in the
requirements.txt file are pypiwin32api, and numpy.

For information on how to build goes on windows with CMake visit:
https://trac.osgeo.org/geos/wiki/BuildingOnWindowsWithCMake

A difference in the instructions in the above link, we use the geos package
that comes with basemaps, just copy out the folder and compile with the same steps.

Once geos is complied copy the two generated DLLs `geos.dll` and `geos_c.dll`
to `[python34]\libs\site-packages\`

*Note if you are using C++ 2010 Express or older, you might have to add in
functions for floor and ceiling into the geos code, as the library it utilizes
for these functions is not available.

CX Freeze version 5.0.1
-----------------------

After building and installing the MSI, if the short cut link fails because it cannot `from . import xxx`,
it is because the working directory for the shortcut is not set.

To change this so builds have the working directory set automatically, you need to change the last
`None` to `"TARGETDIR"` on line 62 of `[python34]\Lib\site-packages\cx_Freeze\windist.py`.

The ouput example of lines 52-62 of cx_freeze's `windist.py` file, with change applied.
```
for index, executable in enumerate(self.distribution.executables):
    if executable.shortcutName is not None \
            and executable.shortcutDir is not None:
        baseName = os.path.basename(executable.targetName)
        msilib.add_data(self.db, "Shortcut",
                [("S_APP_%s" % index, executable.shortcutDir,
                        executable.shortcutName, "TARGETDIR",
                        "[TARGETDIR]%s" % baseName, None, None, None,
                        None, None, None, "TARGETDIR")])
```