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
import functools
import weakref

from king_phisher import plugins
from king_phisher.client import gui_utilities

from gi.repository import Gtk

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

	def get_widget(self, value):
		"""
		Create a widget suitable for configuring this option. This is meant to
		allow subclasses to specify and create an appropriate widget type.

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

# base option types
class ClientOptionBoolean(ClientOptionMixin, plugins.OptionBoolean):
	def get_widget(self, value):
		widget = Gtk.Switch()
		widget.set_active(bool(value))
		widget.set_property('halign', Gtk.Align.START)
		return widget

	def get_widget_value(self, widget):
		return widget.get_active()

class ClientOptionEnum(ClientOptionMixin, plugins.OptionEnum):
	"""
	:param str name: The name of this option.
	:param str description: The description of this option.
	:param tuple choices: The supported values for this option.
	:param default: The default value of this option.
	:param str display_name: The name to display in the UI to the user for this option
	"""
	def get_widget(self, value):
		widget = Gtk.ComboBoxText()
		widget.set_hexpand(True)
		for choice in self.choices:
			widget.append_text(choice)
		if value in self.choices:
			widget.set_active(self.choices.index(value))
		elif self.default is not None:
			widget.set_active(self.choices.index(self.default))
		else:
			widget.set_active(0)
		return widget

	def get_widget_value(self, widget):
		return widget.get_active_text()

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
		self.display_name = kwargs.pop('display_name', name)
		self.adjustment = kwargs.pop('adjustment', Gtk.Adjustment(0, -0x7fffffff, 0x7fffffff, 1, 10, 0))
		super(ClientOptionInteger, self).__init__(name, *args, **kwargs)

	def get_widget(self, value):
		self.adjustment.set_value(int(round(value)))
		widget = Gtk.SpinButton()
		widget.set_hexpand(True)
		widget.set_adjustment(self.adjustment)
		widget.set_numeric(True)
		widget.set_update_policy(Gtk.SpinButtonUpdatePolicy.IF_VALID)
		return widget

	def get_widget_value(self, widget):
		return widget.get_value_as_int()

class ClientOptionString(ClientOptionMixin, plugins.OptionString):
	def get_widget(self, value):
		widget = Gtk.Entry()
		widget.set_hexpand(True)
		widget.set_text((value if value else ''))
		return widget

	def get_widget_value(self, widget):
		return widget.get_text()

# extended option types
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
		for widget in self._widgets:
			widget.destroy()
		self._widgets.clear()

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

	def add_menu_item(self, menu_path, handler):
		"""
		Add a new item into the main menu bar of the application. Menu items
		created through this method are automatically removed when the plugin is
		disabled.

		:param str menu_path: The path to the menu item, delimited with > characters.
		:param handler: The callback function to be connected to the new :py:class:`Gtk.MenuItem` instance's activate signal.
		:return: The newly created and added menu item.
		:rtype: :py:class:`Gtk.MenuItem`
		"""
		menu_path = [path_item.strip() for path_item in menu_path.split('>')]
		menu_path = [path_item for path_item in menu_path if path_item]
		if menu_path[0][0] != '_':
			menu_path[0] = '_' + menu_path[0]
		menu_item = Gtk.MenuItem.new_with_label(menu_path.pop())
		self.signal_connect('activate', handler, gobject=menu_item)

		menu_bar = self.application.main_window.menu_bar.menubar
		gui_utilities.gtk_menu_insert_by_path(menu_bar, menu_path, menu_item)
		menu_item.show()
		self._widgets.append(menu_item)
		return menu_item

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
			handler itself and react as necessary.

		:param str name: The name of the signal.
		:param handler: The function to be invoked with the signal is emitted.
		:param list event_types: A list of sub-types for the corresponding event.
		:param list attributes: A list of attributes of the event object to be sent to the client.
		"""
		server_events = self.application.server_events
		server_events.subscribe(name, event_types, attributes)
		self._server_event_subscriptions.append((name, event_types, attributes))
		self.signal_connect(name, handler, gobject=server_events)

class ClientPluginManager(plugins.PluginManagerBase):
	"""
	The manager for plugins loaded into the King Phisher client application.
	"""
	_plugin_klass = ClientPlugin
	def __init__(self, path, application):
		super(ClientPluginManager, self).__init__(path, (application,))
