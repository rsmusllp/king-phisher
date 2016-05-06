Plugin Compatibility
====================

Due to the way in which plugins are defined as classes with meta-data provided
in their attributes, they need to be able to be imported regardless of
compatibility restraints. The base :py:class:`~king_phisher.plugins.PluginBase`
class offers a number of attributes which can be defined to indicate it's
compatibility requirements.

Minimum King Phisher Version
----------------------------

A minimum required version of King Phisher can be specified in the
:py:attr:`~king_phisher.plugins.PluginBase.req_min_version` attribute. This
should be used to indicate the version in which API changes were made that the
plugin relies upon. The value of this attribute must be a string which can be
parsed with Python's :py:class:`distutils.version.StrictVersion` class for
comparison.

The default class value is the first version of King Phisher which introduced
the plugin API.

Required Python Packages
------------------------

Sometimes modules may need additional Python packages and modules to be
available in order to function properly. This can be problematic as the modules
often need to be imported at the top level which normally would prevent the
plugin from loading. In order to avoid this, plugin authors must wrap the import
statement using Python's exception handling and define a variable to indicate
whether or not the module is available.

This variable then needs to be added to the
:py:attr:`~king_phisher.plugins.PluginBase.req_packages` attribute. This
attribute is a dictionary whose keys are the names of packages which are
required with values of their availability. Using this method a plugin which
requires the externally provided package "foo" can be loaded into King Phisher
allowing it to correctly alert the user in the event that the "foo" package can
not be loaded. It's highly recommended that the required packages be described
in the plugins description.

Example
-------

The following is a commented example of a basic client plugin with compatibility
requirements.

.. code-block:: python

   import king_phisher.client.plugins as plugins
   import king_phisher.client.gui_utilities as gui_utilities

   try:
       import foobar
   except ImportError:
       has_foobar = False  # catch the standard ImportError and set has_foobar to False
   else:
       has_foobar = True   # no errors occurred so foobar was able to be imported

   class Plugin(plugins.ClientPlugin):
       authors = ['Spencer McIntyre']
       title = 'Compatibility Demo'
       description = """
       A basic plugin which has compatibility requirements. It needs the 'foobar'
       Python package to be installed.
       """
       req_min_version = '1337.0'  # this is the required minimum version of King Phisher
       req_packages {
           'foobar': has_foobar    # whether or not foobar was able to be imported
       }
       # plugin method definitions continue
