Plugins
=======

Starting with version :release:`1.3.0` King Phisher includes a plugin system. At
this time only client plugins are supported with server side plugins slated for
a future release. The common functionality for the two is provided by the
:py:mod:`plugins` module and then extended by the respective implementation.

King Phisher supports loading plugins to allow the user to add additional
features out side of what is supported by the main-stream application. These
plugins are implemented as Python modules which define a `Plugin` class that is
the respective plugins entry point.

.. toctree::
   :maxdepth: 1
   :titlesonly:

   compatibility.rst
   client.rst
   server.rst
