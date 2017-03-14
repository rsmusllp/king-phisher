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
| Python Version                 | 2.7.11                          |
+--------------------------------+---------------------------------+
| PyGI-AIO Version               | 3.14.0 rev22                    |
+--------------------------------+---------------------------------+
