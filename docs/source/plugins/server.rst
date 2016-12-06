Server Plugins
==============

Server plugins need to inherit from the
:py:class:`~king_phisher.server.plugins.ServerPlugin` class which provides the
basic outline. Server plugins have access to their respective configurations
from the :py:attr:`~king_phisher.server.plugins.ServerPlugin.config` attribute.
This configuration can be changed at runtime, but changes will not be kept after
the server has stopped.

Server plugins can hook functionality by utilizing the :py:mod:`~server.signals`
module. This allows plugins to provide functionality for specific events.

Example
-------

The following is a commented example of a basic "Hello World" plugin.

.. code-block:: python

   import king_phisher.plugins as plugin_opts
   import king_phisher.server.plugins as plugins
   import king_phisher.server.signals as signals

   # this is the main plugin class, it is necessary to inherit from plugins.ServerPlugin
   class Plugin(plugins.ServerPlugin):
       authors = ['Spencer McIntyre']  # the plugins author
       title = 'Hello World!'
       description = """
       A 'hello world' plugin to serve as a basic template and demonstration.
       """
       homepage = 'https://github.com/securestate/king-phisher-plugins'
       options = [  # specify options which need to be set through the configuration file
           plugin_opts.OptionString(
               'name',               # the options name
               'the name to greet',  # a basic description of the option
               default=None          # a default value can be specified to
           )
       ]
       req_min_version = '1.4.0'     # (optional) specify the required minimum version of king phisher
       version = '1.0'               # (optional) specify this plugin's version
       def initialize(self):
           self.logger.warning('hello ' + self.config['name'] + '!')
           # connect to a signal via it's object in the signals module
           signals.server_initialized.connect(self.on_server_initialized)
           return True

       def on_server_initialized(self, server):
           self.logger.warning('the server has been initialized')
