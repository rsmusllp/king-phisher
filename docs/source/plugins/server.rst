Server Plugins
==============

Server plugins need to inherit from the
:py:class:`~king_phisher.server.plugins.ServerPlugin` class which provides the
basic outline. Server plugins have access to their respective configurations
from the :py:attr:`~king_phisher.server.plugins.ServerPlugin.config` attribute.
This data is loaded from the server's configuration file and while it can be
changed at runtime, the changes will not be kept after the server has stopped.

A plugin that needs to store data persistently can use the
:py:attr:`~king_phisher.server.plugins.ServerPlugin.storage` attribute which
acts as a simple key value store and is backed by the database. Values stored
in this must be able to be serialized making it impossible to directly store
custom objects.

Server plugins can hook functionality by utilizing the :py:mod:`~server.signals`
module. This allows plugins to provide functionality for specific events.

Adding RPC Methods
------------------

Server plugins can provide new RPC methods that are available to client plugins
and the client's RPC terminal. This allows server plugins to provide extended
functionality for use by these other components.

Registering new RPC methods is as simple as calling the
:py:meth:`~king_phisher.server.plugins.ServerPlugin.register_rpc` method. This
function, like signal handlers, takes a method as an argument for use as a
call back. This method is then called when the RPC function is invoked. The
return value of this method is then returned to the caller of the RPC function.
The method will automatically be passed the current
:py:class:`~king_phisher.server.server.KingPhisherRequestHandler` instance as
the first argument (after the standard "self" argument for class methods as
applicable). Additional arguments after that accepted from the RPC invocation.

The following is an example of two custom RPC methods.

.. code-block:: python

   # ... other initialization code
   class Plugin(plugins.ServerPlugin):
       # ... other initialization code
       def initialize(self):
            self.register_rpc('add', self.rpc_add)
            self.register_rpc('greet', self.rpc_greet)
            return True

       # this example takes two arguments to be invoked and returns their sum
       # >>> rpc('plugins/example/add', 1, 2)
       # 3
       def rpc_add(self, handler, number_1, number_2):
           return number_1 + number_2

       # this example takes no arguments but accesses the rpc_session to
       # retrieve the current user name
       # >>> rpc('plugins/example/greet')
       # 'Hello steiner'
       def rpc_greet(self, handler):
           rpc_session = handler.rpc_session
           return 'Hello ' + rpc_session.user

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
