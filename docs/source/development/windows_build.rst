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

After building the MSI file, the custom properties will need to be added. These
are added by right clicking on the MSI file, selecting properties, and then the
custom tab where custom fields can be created. These need to include the Python
version, and PyGI-AIO version utilized in making the build as text entries.
Below is the name fields and example values.

+--------------------------------+---------------------------------+
| Name                           | Example Value                   |
+================================+=================================+
| Python Version                 | 3.4                             |
+--------------------------------+---------------------------------+
| PyGI-AIO Version               | 3.14.0 rev22                    |
+--------------------------------+---------------------------------+

Python 3.4 Build
----------------

As of King Phisher :release:`1.8.0`, the Windows client is built with Python
3.4. To install basemaps for Python 3.4 geos will need to be compiled for
Windows. In addition to the packages in the "requirements.txt" file,
``pypiwin32api``, and ``numpy`` will need to be installed manually.

For information on how to build geos on Windows with CMake visit:
`<https://trac.osgeo.org/geos/wiki/BuildingOnWindowsWithCMake>`_.

It is important that the same version of geos be built that is used with
basemaps.

Once geos is complied the two generated DLLs ``geos.dll`` and ``geos_c.dll``
need to be copied to "[python34]\libs\site-packages\".

.. note::
   C++ 2010 Express and older will need to have the ``floor`` and ``ceil``
   functions defined. These two functions are required by the geos library but
   are unavailable in older versions of the standard library.

CX Freeze version 5.0.1
-----------------------

After building and installing the MSI file, if the short cut link fails because
it cannot ``from . import xxx``, it is because the working directory for the
shortcut is not set. To change this so builds have the working directory set
automatically, the last line of
"[python34]\Lib\site-packages\cx_Freeze\windist.py" needs to be updated from
``None`` to ``"TARGETDIR"``.

The ouput example of lines 52-62 of cx_freeze's "windist.py" file, with change
applied.

.. code-block:: python

   for index, executable in enumerate(self.distribution.executables):
       if executable.shortcutName is not None \
               and executable.shortcutDir is not None:
           baseName = os.path.basename(executable.targetName)
           msilib.add_data(self.db, "Shortcut",
                   [("S_APP_%s" % index, executable.shortcutDir,
                           executable.shortcutName, "TARGETDIR",
                           "[TARGETDIR]%s" % baseName, None, None, None,
                           None, None, None, "TARGETDIR")])

