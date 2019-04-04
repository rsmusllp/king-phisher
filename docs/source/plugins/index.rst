Plugins
=======

Starting with version :release:`1.3.0` King Phisher includes a plugin system.
Both client and server plugins are supported with the common functionality for
the two being provided by the :py:mod:`plugins` module and then extended by
the irrespective implementations in :py:mod:`king_phisher.client.plugins` and
:py:mod:`king_phisher.server.plugins`.

King Phisher supports loading plugins to allow the user to add additional
features out side of what is supported by the main-stream application. These
plugins are implemented as Python modules which define a ``Plugin`` class that
is the respective plugins entry point as well as the host for various pieces of
metadata in the form of class-attributes.

.. toctree::
   :maxdepth: 1
   :titlesonly:

   compatibility.rst
   client.rst
   server.rst
