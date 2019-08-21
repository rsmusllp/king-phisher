#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  king_phisher/client/plugins.py
#
#  Redistribution and use in source and binary forms, with or without
#  modification, are permitted provided that the following conditions are
#  met:
#
#  * Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
#  * Redistributions in binary form must reproduce the above
#    copyright notice, this list of conditions and the following disclaimer
#    in the documentation and/or other materials provided with the
#    distribution.
#  * Neither the name of the project nor the names of its
#    contributors may be used to endorse or promote products derived from
#    this software without specific prior written permission.
#
#  THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
#  "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
#  LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
#  A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
#  OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
#  SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
#  LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
#  DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
#  THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
#  (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
#  OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#

import collections
import datetime
import os
import tempfile
import weakref

from king_phisher import catalog
from king_phisher import constants
from king_phisher import plugins
from king_phisher.client import gui_utilities
from king_phisher.client import mailer
from king_phisher.client.widget import extras
from king_phisher.serializers import JSON

from gi.repository import Gtk
import jinja2.exceptions

def _split_menu_path(menu_path):
	menu_path = [path_item.strip() for path_item in menu_path.split('>')]
	menu_path = [path_item for path_item in menu_path if path_item]
	if menu_path[0][0] != '_':
		menu_path[0] = '_' + menu_path[0]
	return menu_path

class ClientOptionMixin(object):
	"""
	A mixin for options used by plugins for the client application. It provides
	additional methods for creating GTK widgets for the user to set the option's
	value as well as retrieve it.
	"""
	def __init__(self, name, *args, **kwargs):
		"""
		:param str name: The name of this option.
		:param str description: The description of this option.
		:param default: The default value of this option.
		:param str display_name: The name to display in the UI to the user for this option.
		"""
		self.display_name = kwargs.pop('display_name', name)
		super(ClientOptionMixin, self).__init__(name, *args, **kwargs)

	def get_widget(self, application, value):
		"""
		Create a widget suitable for configuring this option. This is meant to
		allow subclasses to specify and create an appropriate widget type.

		:param application: The parent application for this object.
		:type application: :py:class:`Gtk.Application`
		:param value: The initial value to set for this widget.
		:return: The widget for the user to set the option with.
		:rtype: :py:class:`Gtk.Widget`
		"""
		raise NotImplementedError()

	def get_widget_value(self, widget):
		"""
		Get the value of a widget previously created with
		:py:meth:`~.ClientOptionMixin.get_widget`.

		:param widget: The widget from which to retrieve the value from for this option.
		:type widget: :py:class:`Gtk.Widget`
		:return: The value for this option as set in the widget.
		"""
		raise NotImplementedError()

	def set_widget_value(self, widget, value):
		"""
		Set the value of a widget.

		:param widget: The widget whose value is to set for this option.
		:type widget: :py:class:`Gtk.Widget`
		"""
		raise NotImplementedError()

# base option types
class ClientOptionBoolean(ClientOptionMixin, plugins.OptionBoolean):
	def get_widget(self, _, value):
		widget = Gtk.Switch()
		widget.set_hexpand(True)
		widget.set_property('halign', Gtk.Align.START)
		self.set_widget_value(widget, value)
		return widget

	def get_widget_value(self, widget):
		return widget.get_active()

	def set_widget_value(self, widget, value):
		widget.set_active(bool(value))
		return widget

class ClientOptionEnum(ClientOptionMixin, plugins.OptionEnum):
	def __init__(self, name, *args, **kwargs):
		"""
		:param str name: The name of this option.
		:param str description: The description of this option.
		:param tuple choices: The supported values for this option.
		:param default: The default value of this option.
		:param str display_name: The name to display in the UI to the user for this option
		"""
		super(ClientOptionEnum, self).__init__(name, *args, **kwargs)

	def get_widget(self, _, value):
		widget = Gtk.ComboBoxText()
		widget.set_hexpand(True)
		for choice in self.choices:
			widget.append_text(choice)
		self.set_widget_value(widget, value)
		return widget

	def get_widget_value(self, widget):
		return widget.get_active_text()

	def set_widget_value(self, widget, value):
		if value in self.choices:
			widget.set_active(self.choices.index(value))
		elif self.default is not None:
			widget.set_active(self.choices.index(self.default))
		else:
			widget.set_active(0)
		return widget

class ClientOptionInteger(ClientOptionMixin, plugins.OptionInteger):
	def __init__(self, name, *args, **kwargs):
		"""
		:param str name: The name of this option.
		:param str description: The description of this option.
		:param default: The default value of this option.
		:param str display_name: The name to display in the UI to the user for this option.
		:param adjustment: The adjustment details of the options value.
		:type adjustment: :py:class:`Gtk.Adjustment`
		"""
		self.adjustment = kwargs.pop('adjustment', Gtk.Adjustment(0, -0x7fffffff, 0x7fffffff, 1, 10, 0))
		super(ClientOptionInteger, self).__init__(name, *args, **kwargs)

	def get_widget(self, _, value):
		widget = Gtk.SpinButton()
		widget.set_hexpand(True)
		widget.set_adjustment(self.adjustment)
		widget.set_numeric(True)
		widget.set_update_policy(Gtk.SpinButtonUpdatePolicy.IF_VALID)
		self.set_widget_value(widget, value)
		return widget

	def get_widget_value(self, widget):
		return widget.get_value_as_int()

	def set_widget_value(self, _, value):
		self.adjustment.set_value(int(round(value)))

class ClientOptionString(ClientOptionMixin, plugins.OptionString):
	def __init__(self, name, *args, **kwargs):
		"""
		.. versionchanged:: 1.9.0b5
			Added the *multiline* option.

		:param str name: The name of this option.
		:param str description: The description of this option.
		:param default: The default value of this option.
		:param str display_name: The name to display in the UI to the user for this option.
		:param bool multiline: Whether or not this option allows multiple lines of input.
		"""
		self.multiline = bool(kwargs.pop('multiline', False))
		super(ClientOptionString, self).__init__(name, *args, **kwargs)

	def get_widget(self, _, value):
		if self.multiline:
			scrolled_window = Gtk.ScrolledWindow()
			textview = extras.MultilineEntry()
			textview.set_property('hexpand', True)
			scrolled_window.add(textview)
			scrolled_window.set_property('height-request', 60)
			scrolled_window.set_property('vscrollbar-policy', Gtk.PolicyType.ALWAYS)
			widget = scrolled_window
		else:
			widget = Gtk.Entry()
			widget.set_hexpand(True)
		self.set_widget_value(widget, value)
		return widget

	def get_widget_value(self, widget):
		if self.multiline:
			widget = widget.get_child().get_child()
		return widget.get_property('text')

	def set_widget_value(self, widget, value):
		if value is None:
			value = ''
		if self.multiline:
			widget = widget.get_child().get_child()
		widget.set_property('text', value)
		return widget

# extended option types
class ClientOptionPath(ClientOptionString):
	def __init__(self, name, *args, **kwargs):
		"""
		:param str name: The name of this option.
		:param str description: The description of this option.
		:param default: The default value of this option.
		:param str display_name: The name to display in the UI to the user for this option.
		:param str path_type: The type of the path to select, either 'directory', 'file-open' or 'file-save'.
		"""
		self.path_type = kwargs.pop('path_type', 'file-open').lower()
		if self.path_type not in ('directory', 'file-open', 'file-save'):
			raise ValueError('path_type must be either \'directory\', \'file-open\', or \'file-save\'')
		self.file_filters = kwargs.pop('file_filters', None)
		super(ClientOptionPath, self).__init__(name, *args, **kwargs)

	def get_widget(self, application, value):
		entry_widget = super(ClientOptionPath, self).get_widget(application, value)
		entry_widget.set_property('editable', False)
		entry_widget.set_property('primary-icon-stock', 'gtk-file')
		entry_widget.connect('activate', self.signal_entry_activate, application)
		entry_widget.connect('backspace', self.signal_entry_backspace)

		button_widget = Gtk.Button.new_from_icon_name('document-open', Gtk.IconSize.BUTTON)
		button_widget.connect('clicked', self.signal_button_clicked, application, entry_widget)

		widget = Gtk.Box(Gtk.Orientation.HORIZONTAL, 3)
		widget.pack_start(entry_widget, True, True, 0)
		widget.pack_start(button_widget, False, False, 0)
		return widget

	def signal_button_clicked(self, _, application, entry_widget):
		self.select_path(application, entry_widget)

	def signal_entry_activate(self, entry_widget, application):
		self.select_path(application, entry_widget)

	def signal_entry_backspace(self, entry_widget):
		entry_widget.set_text('')

	def select_path(self, application, entry_widget):
		dialog = extras.FileChooserDialog('Select ' + self.path_type.capitalize(), application.get_active_window())
		if self.path_type.startswith('file-') and self.file_filters:
			for name, patterns in self.file_filters:
				dialog.quick_add_filter(name, patterns)
			dialog.quick_add_filter('All Files', '*')

		if self.path_type == 'directory':
			result = dialog.run_quick_select_directory()
		elif self.path_type == 'file-open':
			result = dialog.run_quick_open()
		elif self.path_type == 'file-save':
			result = dialog.run_quick_save()
		else:
			dialog.destroy()
			raise ValueError('path_type must be either \'directory\', \'file-open\', or \'file-save\'')
		dialog.destroy()
		if result is None:
			return
		entry_widget.set_text(result['target_path'])

	def get_widget_value(self, widget):
		entry_widget = widget.get_children()[0]
		return entry_widget.get_text()

class ClientOptionPort(ClientOptionInteger):
	def __init__(self, *args, **kwargs):
		"""
		:param str name: The name of this option.
		:param str description: The description of this option.
		:param default: The default value of this option.
		:param str display_name: The name to display in the UI to the user for this option.
		"""
		kwargs['adjustment'] = Gtk.Adjustment(1, 1, 0xffff, 1, 10, 0)
		super(ClientOptionPort, self).__init__(*args, **kwargs)

# plugin base class
class ClientPlugin(plugins.PluginBase):
	"""
	The base object to be inherited by plugins that are loaded into the King
	Phisher client. This provides a convenient interface for interacting with
	the runtime.
	"""
	_logging_prefix = 'KingPhisher.Plugins.Client.'
	def __init__(self, application):
		self.application = application
		"""A reference to the :py:class:`~king_phisher.client.application.KingPhisherClientApplication`."""
		super(ClientPlugin, self).__init__()
		self._server_event_subscriptions = collections.deque()
		self._signals = collections.deque()
		self._widgets = collections.deque()

	def _cleanup(self):
		# cleanup connected gobject signals
		for ref, handler_id in self._signals:
			gobject = ref()
			if gobject is None:
				continue
			gobject.disconnect(handler_id)
		self._signals.clear()
		# cleanup server event subscriptions
		while self._server_event_subscriptions:
			self.application.server_events.unsubscribe(*self._server_event_subscriptions.pop())
		self._server_event_subscriptions.clear()
		# destroy widgets
		for widget in reversed(self._widgets):
			widget.destroy()
		self._widgets.clear()

	def _insert_menu_item(self, menu_path, menu_item):
		menu_bar = self.application.main_window.menu_bar.menubar
		gui_utilities.gtk_menu_insert_by_path(menu_bar, menu_path, menu_item)
		menu_item.show()
		self._widgets.append(menu_item)
		return menu_item

	@property
	def config(self):
		"""
		A dictionary that can be used by this plugin for persistent storage of
		it's configuration.
		"""
		config = self.application.config['plugins'].get(self.name)
		if config is None:
			config = {}
			self.application.config['plugins'][self.name] = config
		return config

	def add_menu_item(self, menu_path, handler=None):
		"""
		Add a new item into the main menu bar of the application. Menu items
		created through this method are automatically removed when the plugin
		is disabled. If no *handler* is specified, the menu item will be a
		separator, otherwise *handler* will automatically be connected to the
		menu item's ``activate`` signal.

		:param str menu_path: The path to the menu item, delimited with > characters.
		:param handler: The optional callback function to be connected to the new :py:class:`Gtk.MenuItem` instance's activate signal.
		:return: The newly created and added menu item.
		:rtype: :py:class:`Gtk.MenuItem`
		"""
		menu_path = _split_menu_path(menu_path)
		if handler is None:
			menu_item = Gtk.SeparatorMenuItem()
		else:
			menu_item = Gtk.MenuItem.new_with_label(menu_path.pop())
			self.signal_connect('activate', handler, gobject=menu_item)
		return self._insert_menu_item(menu_path, menu_item)

	def add_submenu(self, menu_path):
		"""
		Add a submenu into the main menu bar of the application. Submenus
		created through this method are automatically removed when the plugin
		is disabled.

		:param str menu_path: The path to the submenu, delimited with > characters.
		:return: The newly created and added menu item.
		:rtype: :py:class:`Gtk.MenuItem`
		"""
		menu_path = _split_menu_path(menu_path)
		menu_item = Gtk.MenuItem.new_with_label(menu_path.pop())
		menu_item.set_submenu(Gtk.Menu.new())
		return self._insert_menu_item(menu_path, menu_item)

	def render_template_string(self, template_string, target=None, description='string', log_to_mailer=True):
		"""
		Render the specified *template_string* in the message environment. If
		an error occurs during the rendering process, a message will be logged
		and ``None`` will be returned. If *log_to_mailer* is set to ``True``
		then a message will also be displayed in the message send tab of the
		client.

		.. versionadded:: 1.9.0b5

		:param str template_string: The string to render as a template.
		:param target: An optional target to pass to the rendering environment.
		:type target: :py:class:`~king_phisher.client.mailer.MessageTarget`
		:param str description: A keyword to use to identify the template string in error messages.
		:param bool log_to_mailer: Whether or not to log to the message send tab as well.
		:return: The rendered string or ``None`` if an error occurred.
		:rtype: str
		"""
		mailer_tab = self.application.main_tabs['mailer']
		text_insert = mailer_tab.tabs['send_messages'].text_insert
		try:
			template_string = mailer.render_message_template(template_string, self.application.config, target=target)
		except jinja2.exceptions.TemplateSyntaxError as error:
			self.logger.error("jinja2 syntax error ({0}) in {1}: {2}".format(error.message, description, template_string))
			if log_to_mailer:
				text_insert("Jinja2 syntax error ({0}) in {1}: {2}\n".format(error.message, description, template_string))
			return None
		except jinja2.exceptions.UndefinedError as error:
			self.logger.error("jinj2 undefined error ({0}) in {1}: {2}".format(error.message, description, template_string))
			if log_to_mailer:
				text_insert("Jinja2 undefined error ({0}) in {1}: {2}".format(error.message, description, template_string))
			return None
		except ValueError as error:
			self.logger.error("value error ({0}) in {1}: {2}".format(error, description, template_string))
			if log_to_mailer:
				text_insert("Value error ({0}) in {1}: {2}\n".format(error, description, template_string))
			return None
		return template_string

	def signal_connect(self, name, handler, gobject=None, after=False):
		"""
		Connect *handler* to a signal by *name* to an arbitrary GObject. Signals
		connected through this method are automatically cleaned up when the
		plugin is disabled. If no GObject is specified, the
		:py:attr:`~.ClientPlugin.application` instance is used.

		.. warning::
			If the signal needs to be disconnected manually by the plugin, this
			method should not be used. Instead the handler id should be kept as
			returned by the GObject's native connect method.

		:param str name: The name of the signal.
		:param handler: The function to be invoked with the signal is emitted.
		:type handler: function
		:param gobject: The object to connect the signal to.
		:param bool after: Whether to call the user specified handler after the default signal handler or before.
		"""
		gobject = gobject or self.application
		if after:
			handler_id = gobject.connect_after(name, handler)
		else:
			handler_id = gobject.connect(name, handler)
		self._signals.append((weakref.ref(gobject), handler_id))

	def signal_connect_server_event(self, name, handler, event_types, attributes):
		"""
		Connect *handler* to the server signal with *name*. This method is
		similar to :py:meth:`~.signal_connect` but also sets up the necessary
		event subscriptions to ensure that the handler will be called. These
		event subscriptions are automatically cleaned up when the plugin is
		disabled.

		.. warning::
			Server events are emitted based on the client applications event
			subscriptions. This means that while *handler* will be called for
			the event types specified, it may also be called for additional
			unspecified event types if other plugins have subscribed to them.
			This means that it is important to check the event type within the
			handler itself and react as necessary. To avoid this simply use the
			:py:func:`~king_phisher.client.server_events.event_type_filter`
			decorator for the *handler* function.

		:param str name: The name of the signal.
		:param handler: The function to be invoked with the signal is emitted.
		:param list event_types: A list of sub-types for the corresponding event.
		:param list attributes: A list of attributes of the event object to be sent to the client.
		"""
		server_events = self.application.server_events
		server_events.subscribe(name, event_types, attributes)
		self._server_event_subscriptions.append((name, event_types, attributes))
		self.signal_connect(name, handler, gobject=server_events)

# extended plugin classes
class ClientPluginMailerAttachment(ClientPlugin):
	"""
	The base object to be inherited by plugins that intend to modify attachment
	files such as for inserting the tracking URL into them. Plugins which
	inherit from this base class must override the
	:py:meth:`.process_attachment_file` method which will automatically be
	called for each target a user is sending messages to.
	"""
	def __init__(self, *args, **kwargs):
		super(ClientPluginMailerAttachment, self).__init__(*args, **kwargs)
		mailer_tab = self.application.main_tabs['mailer']
		self.signal_connect('target-create', self._signal_send_target, gobject=mailer_tab)

	def _signal_send_target(self, _, target):
		config = self.application.config
		input_path = config.get('mailer.attachment_file.post_processing')
		output_path = input_path
		if not input_path:
			input_path = config.get('mailer.attachment_file')
			if not input_path:
				return
			output_path = os.path.join(tempfile.gettempdir(), os.path.basename(input_path))

		self.logger.debug('processing the attachment file')
		try:
			new_output_path = self.process_attachment_file(input_path, output_path, target) or output_path
		except Exception as error:
			# delete the output file if process_attachment_file failed
			if os.access(output_path, os.W_OK):
				os.remove(output_path)
			raise error

		if new_output_path != output_path:
			if os.access(output_path, os.W_OK):
				os.remove(output_path)
			if not os.path.isfile(new_output_path):
				self.logger.warning('plugin returned a new output path, but the file does not exist')
		output_path = new_output_path

		# set the config option if the output file was created
		if os.path.isfile(output_path):
			config['mailer.attachment_file.post_processing'] = output_path

	def process_attachment_file(self, input_path, output_path, target):
		"""
		This function is automatically called for each target that a user is
		sending messages to. This method is intended to process the specified
		attachment file. This method removes the need to manually cleanup the
		*output_path* because it is handled automatically as necessary.

		:param str input_path: The path to the input file to process. This path
			is guaranteed to be an existing file that is readable.
		:param str output_path: The path to optionally write the output file
			to. This path may or may not be the same as *input_path*. If the
			plugin needs to rename the file, to for example change the
			extension, then the new output_path must be returned.
		:param target: The target information for the messages intended recipient.
		:type target: :py:class:`.MessageTarget`
		:return: None or an updated value for *output_path* in the case that
			the plugin renames it.
		"""
		raise NotImplementedError('the process_attachment_file method must be defined by the plugin')

# plugin manager class
class ClientPluginManager(plugins.PluginManagerBase):
	"""
	The manager for plugins loaded into the King Phisher client application.
	"""
	_plugin_klass = ClientPlugin
	def __init__(self, path, application):
		super(ClientPluginManager, self).__init__(path, (application,))

class CatalogCacheManager(object):
	"""
	Manager to handle cache information for catalogs. Cache entries are stored
	as dictionaries with metadata information and the catalog data under the
	"value" key.
	"""
	cache_version = '2.0'
	def __init__(self, cache_file):
		self._cache_dict = {}
		self._data = {}
		self._cache_file = cache_file

		if os.path.isfile(self._cache_file):
			with open(cache_file, 'r') as file_h:
				try:
					self._cache_dict = JSON.load(file_h)
				except ValueError:
					self._cache_dict = {}
		if self._cache_dict and 'catalogs' in self._cache_dict:
			if self._cache_dict['catalogs'].get('version', None) != self.cache_version:
				self._cache_dict['catalogs'] = {}
			else:
				self._data = self._cache_dict['catalogs']['value']
		else:
			self._cache_dict['catalogs'] = {}

	def __setitem__(self, key, value):
		self._data[key] = value

	def __getitem__(self, key):
		return self._data[key]

	def __delitem__(self, key):
		del self._data[key]

	def __len__(self):
		return len(self._data)

	def __iter__(self):
		return iter(self._data)

	def get_catalog_by_id(self, catalog_id):
		"""
		Return the catalog cache data for the specified catalog ID.

		:param str catalog_id: The ID of the catalog to look up in the cache.
		:return: The cache entry for the catalog or None if the catalog was not found.
		:rtype: dict
		"""
		return self._data.get(catalog_id)

	def pop_catalog_by_id(self, catalog_id):
		return self._data.pop(catalog_id)

	def get_catalog_by_url(self, catalog_url):
		"""
		Return the catalog cache data for the specified catalog URL.

		:param str catalog_url: The URL of the catalog to look up in the cache.
		:return: The cache entry for the catalog or None if the catalog was not found.
		:rtype: dict
		"""
		return next((catalog_ for catalog_ in self._data.values() if catalog_.get('url') == catalog_url), None)

	def pop_catalog_by_url(self, catalog_url, default=constants.DISABLED):
		for key, catalog_ in self._data.items():
			if catalog_.get('url') == catalog_url:
				break
		else:
			if default is not constants.DISABLED:
				return default
			raise KeyError(catalog_url)
		del self._data[key]
		return catalog_

	def save(self):
		self._cache_dict['catalogs']['value'] = self._data
		self._cache_dict['catalogs']['created'] = datetime.datetime.utcnow()
		self._cache_dict['catalogs']['version'] = self.cache_version
		with open(self._cache_file, 'w') as file_h:
			JSON.dump(self._cache_dict, file_h)

class ClientCatalogManager(catalog.CatalogManager):
	"""
	Base manager for handling Catalogs.
	"""
	def __init__(self, user_data_path, manager_type='plugins/client', *args, **kwargs):
		self._catalog_cache = CatalogCacheManager(os.path.join(user_data_path, 'cache.json'))
		super(ClientCatalogManager, self).__init__(*args, **kwargs)
		self.manager_type = manager_type

	def get_collection(self, catalog_id, repo_id):
		"""
		Returns the manager type of the plugin collection of the requested catalog and repository.

		:param str catalog_id: The name of the catalog the repo belongs to
		:param str repo_id: The id of the repository requested.
		:return: The the collection of manager type from the specified catalog and repository.
		"""
		return self.catalogs[catalog_id].repositories[repo_id].collections.get(self.manager_type)

	def install_plugin(self, catalog_id, repo_id, plugin_id, install_path):
		"""
		Installs the specified plugin to the desired plugin path.

		:param str catalog_id: The id of the catalog of the desired plugin to install.
		:param str repo_id: The id of the repository of the desired plugin to install.
		:param str plugin_id: The id of the plugin to install.
		:param str install_path: The path to install the plugin too.
		"""
		self.catalogs[catalog_id].repositories[repo_id].get_item_files(self.manager_type, plugin_id, install_path)

	def save_cache(self, catalog, catalog_url):
		"""
		Saves the catalog or catalogs in the manager to the cache.

		:param catalog: The :py:class:`~king_phisher.catalog.Catalog` to save.
		"""
		self._catalog_cache[catalog.id] = {
			'created': datetime.datetime.utcnow(),
			'id': catalog.id,
			'url': catalog_url,
			'value': catalog.to_dict()
		}
		self._catalog_cache.save()

	def add_catalog(self, catalog, catalog_url, cache=False):
		"""
		Adds the specified catalog to the manager and stores the associated
		source URL for caching.

		:param catalog: The catalog to add to the cache manager.
		:type catalog: :py:class:`~king_phisher.catalog.Catalog`
		:param str catalog_url: The URL from which the catalog was loaded.
		:param bool cache: Whether or not the catalog should be saved to the cache.
		:return: The catalog.
		:rtype: :py:class:`~king_phisher.catalog.Catalog`
		"""
		self.catalogs[catalog.id] = catalog
		if cache and catalog_url:
			self.save_cache(catalog=catalog, catalog_url=catalog_url)
		return catalog

	def is_compatible(self, catalog_id, repo_id, plugin_name):
		"""
		Checks the compatibility of a plugin.

		:param catalog_id: The catalog id associated with the plugin.
		:param repo_id: The repository id associated with the plugin.
		:param plugin_name: The name of the plugin.
		:return: Whether or not it is compatible.
		:rtype: bool
		"""
		plugin = self.get_collection(catalog_id, repo_id)[plugin_name]
		return plugins.Requirements(plugin['requirements']).is_compatible

	def compatibility(self, catalog_id, repo_id, plugin_name):
		"""
		Checks the compatibility of a plugin.

		:param str catalog_id: The catalog id associated with the plugin.
		:param str repo_id: The repository id associated with the plugin.
		:param str plugin_name: The name of the plugin.
		:return: Tuple of packages and if the requirements are met.
		:rtype: tuple
		"""
		plugin = self.get_collection(catalog_id, repo_id)[plugin_name]
		return plugins.Requirements(plugin['requirements']).compatibility

	def get_cache(self):
		"""
		Returns the catalog cache.

		:return: The catalog cache.
		:rtype: :py:class:`.CatalogCacheManager`
		"""
		return self._catalog_cache
