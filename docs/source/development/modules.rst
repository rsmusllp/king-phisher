Modules
=======

The projects code base is split among multiple Python modules under the primary
:py:mod:`king_phisher` package. Code which is not specific to either the client
or server code bases is directly in the root of the :py:mod:`king_phisher`
package with code that is specific to either the client or server being under
either the :py:mod:`king_phisher.client` sub-package or
:py:mod:`king_phisher.server` sub-package respectively.

Special Modules
---------------

Some modules have special designations to identify them as having particular
qualities.

.. _clean-room-modules:

Clean Room Modules
^^^^^^^^^^^^^^^^^^

Modules that qualify for the "Clean Room" classification are suitable for use
during the early phases of the application's initialization. They may also be
used for general purposes.

* Modules must not import any code which is not either included in the Python
  standard library or packaged with King Phisher.
* Modules may only import other King Phisher modules which also have the "Clean
  Room" classification.

Modules with this designation have the following comment banner included in
their source file just below the standard splat.

.. code-block:: none

   ################################################################################
   #
   # CLEAN ROOM MODULE
   #
   # This module is classified as a "Clean Room" module and is subject to
   # restrictions on what it may import.
   #
   # See: https://king-phisher.readthedocs.io/en/latest/development/modules.html#clean-room-modules
   #
   ################################################################################
