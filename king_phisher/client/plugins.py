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
import distutils.version
import collections
import json
import os
import tempfile
import weakref
import pip

from king_phisher import plugins
from king_phisher import catalog
from king_phisher import version
from king_phisher.client import gui_utilities
from king_phisher.client import mailer
from king_phisher.client.widget import extras

from gi.repository import Gtk
import jinja2.exceptions
from gi.repository import GLib

DEFAULT_CONFIG_PATH = os.path.join(GLib.get_user_config_dir(), 'king-phisher')

StrictVersion = distutils.version.StrictVersion

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
		self.signal_connect('send-target', self._signal_send_target, gobject=mailer_tab)

	def _signal_send_target(self, _, target):
		config = self.application.config
		input_path = config.get('mailer.attachment_file.post_processing')
		output_path = input_path
		if not input_path:
			input_path = config.get('mailer.attachment_file')
			if not input_path:
				return
			output_path = os.path.join(tempfile.gettempdir(), os.path.basename(input_path))

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

class RepoCache(object):
	"""
	RepoCache is used to hold basic information on repos that is to be cached, or pulled from cache.
	"""
	__slots__ = ('_id', 'title', 'collections_types', 'url')

	def __init__(self, _id, title, collections_types, url):
		self._id = _id
		self.title = title
		self.collections_types = collections_types
		self.url = url

	@property
	def id(self):
		return self._id

	@property
	def collections(self):
		return self.collections_types

	def to_dict(self):
		repo_cache_values = {
			'id': self._id,
			'title': self.title,
			'collections': self.collections_types,
			'url': self.url
		}
		return repo_cache_values

class CatalogCache(object):
	"""
	CatalogCache is used to hold basic information on catalogs that is to be cached or pulled from cache.
	"""
	__slots__ = ('_id', 'repos')

	def __init__(self, _id, repos):
		self._id = _id
		self.repos = {}
		for repo in repos:
			self.repos[repo['id']] = RepoCache(
				repo['id'],
				repo['title'],
				repo['collections'],
				repo['url']
			)

	def __getitem__(self, key):
		return self.repos[key]

	def __iter__(self):
		for repo in self.repos:
			yield self.repos[repo]

	@property
	def id(self):
		return self._id

	def to_dict(self):
		catalog_cache_dict = {
			'id': self._id,
			'repos': [self.repos[repo].to_dict() for repo in self.repos]
		}
		return catalog_cache_dict

class CatalogCacheManager(collections.MutableMapping):
	"""
	Manager to handle cache information for catalogs
	"""
	def __init__(self, cache_file):
		self._data = {}
		self._cache_dict = {}
		self._cache_cat = {}
		self._cache_file = cache_file

		if os.path.isfile(cache_file):
			with open(cache_file) as file_h:
				try:
					self._cache_dict = json.load(file_h)
				except ValueError:
					self._cache_dict = {}

		if not self._cache_dict or 'catalogs' not in self._cache_dict:
			self._cache_dict['catalogs'] = {}
		else:
			cache_cat = self._cache_dict['catalogs']
			for catalog_ in cache_cat:
				self[catalog_] = CatalogCache(
					cache_cat[catalog_]['id'],
					cache_cat[catalog_]['repos']
				)

	def __setitem__(self, key, value):
		self._data[key] = value

	def __getitem__(self, key):
		return self._data[key]

	def __delitem__(self, key):
		del self._data[key]

	def __len__(self):
		return len(self._data)

	def __iter__(self):
		for key in self._data.keys():
			yield key

	def add_catalog_cache(self, cat_id, repos):
		self[cat_id] = CatalogCache(
			cat_id,
			repos
		)

	def to_dict(self):
		cache = {}
		for key in self:
			cache[key] = self._data[key].to_dict()
		return cache

	def save(self):
		self._cache_dict['catalogs'] = self.to_dict()
		with open(self._cache_file, 'w+') as file_h:
			json.dump(self._cache_dict, file_h, sort_keys=True, indent=4)

class PluginCatalogManager(catalog.CatalogManager):
	"""
	Base manager for handling Catalogs
	"""

	def __init__(self, plugin_type, *args, **kwargs):
		self._catalog_cache = CatalogCacheManager(os.path.join(DEFAULT_CONFIG_PATH, 'cache.json'))
		super(PluginCatalogManager, self).__init__(*args, **kwargs)
		self.manager_type = 'plugins/' + plugin_type

	def get_collection(self, catalog_id, repo_id):
		"""
		Returns the manager type of the plugin collection of the requested catalog and repository.

		:param str catalog_id: The name of the catalog the repo belongs to
		:param repo_id: The id of the repository requested.
		:return: The the collection of manager type from the specified catalog and repository.
		:rtype:py:class:
		"""
		if self.manager_type not in self.get_repo(catalog_id, repo_id).collections:
			return
		return self.get_repo(catalog_id, repo_id).collections[self.manager_type]

	def install_plugin(self, catalog_id, repo_id, plugin_id, install_path):
		self.get_repo(catalog_id, repo_id).get_item_files(self.manager_type, plugin_id, install_path)

	def save_catalog_cache(self):
		for catalog_ in self.catalogs:
			if catalog_ not in self._catalog_cache:
				self._catalog_cache.add_catalog_cache(
					self.catalogs[catalog_].id,
					self.get_repos_to_cache(catalog_),
				)
		self._catalog_cache.save()

	def add_catalog_url(self, url):
		super().add_catalog_url(url)
		if self.catalogs:
			self.save_catalog_cache()

	def is_compatible(self, catalog_id, repo_id, plugin_name):
		plugin = self.get_collection(catalog_id, repo_id)[plugin_name]
		requirements = plugin['requirements']
		if requirements['minimum-version'] is not None:
			if StrictVersion(requirements['minimum-version']) > StrictVersion(version.distutils_version):
				return False
		if requirements['packages']:
			if not all(self._package_check(requirements['packages'])):
				return False
		return True

	def _package_check(self, packages):
		installed_packages = sorted(i.key for i in pip.get_installed_distributions())
		for package in packages:
			if package not in installed_packages:
				yield False
			else:
				yield True

	def get_repos_to_cache(self, catalog_):
		repo_cache_info = []
		for repo in self.get_repos(catalog_):
			repo_cache_info.append({
				'id': repo.id,
				'title': repo.title,
				'collections': [collection_ for collection_ in repo.collections],
				'url': repo.url_base
			})
		return repo_cache_info

	def get_cache(self):
		return self._catalog_cache

	def get_cache_catalog_ids(self):
		for item in self._catalog_cache:
			yield item

	def get_cache_repos(self, catalog_id):
		for repos in self._catalog_cache[catalog_id]:
			yield repos
