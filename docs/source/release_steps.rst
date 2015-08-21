Release Steps
=============

This document contains the steps that are followed for each point version
release of King Phisher.

Pre Release Steps
-----------------

#. Test and fix any issues with the Windows MSI build
#. Ensure unit tests pass with Python 2.7 & Python 3.4
#. Remove the version label
#. Create the final Windows MSI build
#. Update the change log

Release Steps
-------------

#. Create a final signed commit on the dev branch and push it to GitHub
#. Merge dev into master and push master to GitHub
#. Create and push a signed tag of the release commit
#. Create a new release on GitHub

   #. Upload the final Windows build
   #. Insert the changes from the change log

#. Update the Docker build
#. Publicize the release

Post Release Steps
------------------

#. Increment the version number on the dev branch and re-set the version label
#. Update Python packages with pip
