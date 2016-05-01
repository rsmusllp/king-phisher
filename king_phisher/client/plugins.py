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

import weakref

from king_phisher import plugins

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
	def get_widget(self, value):
		widget = Gtk.SpinButton()
		widget.set_hexpand(True)
		widget.set_adjustment(Gtk.Adjustment(int(round(value)), -0x7fffffff, 0x7fffffff, 1, 10, 0))
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
		self._signals = []

	def _cleanup(self):
		while self._signals:
			ref, handler_id = self._signals.pop()
			gobject = ref()
			if gobject is None:
				continue
			gobject.disconnect(handler_id)

	@property
	def config(self):
		"""
		A dictionary that can be used by this plugin for persistent storage of it's configuration.
		"""
		config = self.application.config['plugins'].get(self.name)
		if config is None:
			config = {}
			self.application.config['plugins'][self.name] = config
		return config

	def signal_connect(self, name, handler, gobject=None):
		"""
		Connect *handler* to a signal by *name* to an arbitrary GObject. Signals
		connected through this method are automatically cleaned up when the
		plugin is disabled. If not GObject is specified, the application is
		used.

		.. warning::
			If the signal needs to be disconnected manually by the plugin, this
			method should not be used. Instead the handler id should be kept as
			returned by the GObject's native connect method.

		:param str name: The name of the signal.
		:param handler: The function to be invoked with the signal is emitted.
		:type handler: function
		:param gobject: The object to connect the signal to.
		"""
		gobject = gobject or self.application
		handler_id = gobject.connect(name, handler)
		self._signals.append((weakref.ref(gobject), handler_id))

class ClientPluginManager(plugins.PluginManagerBase):
	"""
	The manager for plugins loaded into the King Phisher client application.
	"""
	_plugin_klass = ClientPlugin
	def __init__(self, path, application):
		super(ClientPluginManager, self).__init__(path, (application,))
