Client Plugins
==============

Client plugins need to inherit from the
:py:class:`~king_phisher.client.plugins.ClientPlugin` class which provides the
basic outline. Client plugins have access to a dictionary for persistent
configuration storage through the
:py:attr:`~king_phisher.client.plugins.ClientPlugin.config` attribute. In order
for the plugin's meta-data to be available to the GUI, class attributes are
used. This allows information such as the title, description, etc. to be
accessed without initializing the class.

Plugin Manager
--------------

When the Plugin Manager window is loaded, all available plugins are loaded in
order for their information to be retrieved from the class attributes. This is
the effective equivalent of importing the module in Python. When the module is
enabled, an instance of the Plugin class created allowing it to fulfill its
intended purpose.

Plugin modules and classes can be "reloaded" to allow changes made to the plugin
on disk to take effect. This can be accomplished by right clicking the plugin
and selecting the "Reload" option from the manager window. If an enabled plugin
is reloaded, it will first be disabled before being re-enabled causing it to
lose any state information it may have been storing.

Plugin Options
--------------

Client plugins have special `ClientOption` classes available to them for
specifying options that the user can set. The
:py:meth:`king_phisher.client.plugins.ClientOptionMixin.__init__` method offers
additional parameters such as *display_name* to configure the information shown
to the end user in the configuration widget.

The following are the different option classes available for client plugins:

- :py:class:`~king_phisher.client.plugins.ClientOptionBoolean`
- :py:class:`~king_phisher.client.plugins.ClientOptionEnum`
- :py:class:`~king_phisher.client.plugins.ClientOptionInteger`
- :py:class:`~king_phisher.client.plugins.ClientOptionPort`
- :py:class:`~king_phisher.client.plugins.ClientOptionString`

Example
-------

The following is a commented example of a basic "Hello World" plugin.

.. code-block:: python

   import king_phisher.client.plugins as plugins
   import king_phisher.client.gui_utilities as gui_utilities

   # this is the main plugin class, it is necessary to inherit from plugins.ClientPlugin
   class Plugin(plugins.ClientPlugin):
       authors = ['Spencer McIntyre']  # the plugins author
       title = 'Hello World!'          # the title of the plugin to be shown to users
       description = """
       A 'hello world' plugin to serve as a basic template and demonstration. This
       plugin will display a message box when King Phisher exits.
       """                             # a description of the plugin to be shown to users
       homepage = 'https://github.com/securestate/king-phisher-plugins'  # an optional home page
       options = [  # specify options which can be configured through the GUI
           plugins.ClientOptionString(
               'name',                               # the name of the option as it will appear in the configuration
               'The name to which to say goodbye.',  # the description of the option as shown to users
               default='Alice Liddle',               # a default value for the option
               display_name='Your Name'              # a name of the option as shown to users
           )
           plugins.ClientOptionBoolean(
               'validiction',
               'Whether or not this plugin say good bye.',
               default=True,
               display_name='Say Good Bye'
           )
       ]
       # this is the primary plugin entry point which is executed when the plugin is enabled
       def initialize(self):
           print('Hello World!')
           self.signal_connect('exit', self.signal_exit)
           # it is necessary to return True to indicate that the initialization was successful
           # this allows the plugin to check its options and return false to indicate a failure
           return True

       # this is a cleanup method to allow the plugin to close any open resources
       def finalize(self):
           print('Good Bye World!')

      # the plugin connects this handler to the applications 'exit' signal
      def signal_exit(self, app):
           # check the 'validiction' option in the configuration
           if not self.config['validiction']:
               return
           gui_utilities.show_dialog_info(
               "Good bye {0}!".format(self.config['name']),
               app.get_active_window()
           )
