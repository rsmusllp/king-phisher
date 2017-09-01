#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  king_phisher/client/dialogs/configuration.py
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
import logging
import string

from king_phisher import utilities
from king_phisher.client import graphs
from king_phisher.client import gui_utilities

from gi.repository import GObject
from gi.repository import Gtk

__all__ = ('ConfigurationDialog',)

if isinstance(Gtk.Frame, utilities.Mock):
	_Gtk_Frame = type('Gtk.Frame', (object,), {'__module__': ''})
else:
	_Gtk_Frame = Gtk.Frame

OptionWidget = collections.namedtuple('OptionWidget', ('option', 'widget'))

class PluginsConfigurationFrame(_Gtk_Frame):
	def __init__(self, application, plugin_klass):
		super(PluginsConfigurationFrame, self).__init__()
		self.application = application
		self.config = application.config
		self.plugin_klass = plugin_klass
		self.option_widgets = {}
		self.logger = logging.getLogger('KingPhisher.Client.' + self.__class__.__name__)
		plugin_config = self.config['plugins'].get(plugin_klass.name) or {}  # use or instead of get incase the value is actually None

		grid = Gtk.Grid()
		self.add(grid)
		if Gtk.check_version(3, 12, 0):
			grid.set_property('margin-left', 12)
		else:
			grid.set_property('margin-start', 12)
		grid.set_property('column-spacing', 3)
		grid.set_property('row-spacing', 3)
		grid.insert_column(0)
		grid.insert_column(0)
		grid.attach(self._get_title_box(), 0, 0, 2, 1)
		for row, opt in enumerate(plugin_klass.options, 1):
			grid.insert_row(row)

			name_label = Gtk.Label()
			name_label.set_property('tooltip-text', opt.description)
			name_label.set_property('width-request', 175)
			name_label.set_text(opt.display_name)
			grid.attach(name_label, 0, row, 1, 1)

			widget = opt.get_widget(self.application, plugin_config.get(opt.name, opt.default))
			widget.set_property('tooltip-text', opt.description)
			grid.attach(widget, 1, row, 1, 1)
			self.option_widgets[opt.name] = OptionWidget(opt, widget)
		self.show_all()

	def _get_title_box(self):
		menu = Gtk.Menu()
		menu.set_property('valign', Gtk.Align.START)
		menu_item = Gtk.MenuItem.new_with_label('Restore Default Options')
		menu_item.connect('activate', self.signal_activate_plugin_reset, self.plugin_klass)
		menu.append(menu_item)
		menu.show_all()
		self.menu = menu

		plugin_menu_button = Gtk.MenuButton()
		plugin_menu_button.set_property('direction', Gtk.ArrowType.LEFT)
		plugin_menu_button.set_popup(menu)

		title_box = Gtk.Box(Gtk.Orientation.HORIZONTAL, 3)
		title_box.pack_start(Gtk.Label(label=self.plugin_klass.title), False, True, 0)
		title_box.pack_end(plugin_menu_button, False, False, 0)
		return title_box

	def signal_activate_plugin_reset(self, _, plugin_klass):
		self.logger.info("restoring the default options for plugin: {0}".format(plugin_klass.name))
		default_config = {}
		for option_widget in self.option_widgets.values():
			option = option_widget.option
			widget = option_widget.widget
			default_config[option.name] = option.default
			option.set_widget_value(widget, option.default)
		self.application.config['plugins'][plugin_klass.name] = default_config

class ConfigurationDialog(gui_utilities.GladeGObject):
	"""
	Display the King Phisher client configuration dialog. Running this dialog
	via the :py:meth:`.interact` method will cause some server settings to be
	loaded.
	"""
	dependencies = gui_utilities.GladeDependencies(
		children=(
			# Server Tab
			'entry_server',
			'entry_server_username',
			'entry_sms_phone_number',
			'combobox_sms_carrier',
			# SMTP Server Tab
			'entry_smtp_server',
			'entry_smtp_username',
			'frame_smtp_ssh',
			'spinbutton_smtp_max_send_rate',
			'switch_smtp_ssl_enable',
			'switch_smtp_ssh_enable',
			'entry_sftp_client',
			'entry_ssh_server',
			'entry_ssh_username',
			# Client Tab
			'combobox_spf_check_level',
			# Plugins Tab
			'box_plugin_options'
		),
		top_level=(
			'SMSCarriers',
			'SMTPSendRate',
			'SPFCheckLevels'
		)
	)
	top_gobject = 'dialog'
	def __init__(self, *args, **kwargs):
		super(ConfigurationDialog, self).__init__(*args, **kwargs)
		smtp_ssh_enabled = self.gobjects['switch_smtp_ssh_enable'].get_active()
		self.gobjects['entry_smtp_server'].set_sensitive(not smtp_ssh_enabled)
		self.gobjects['frame_smtp_ssh'].set_sensitive(smtp_ssh_enabled)
		# connect to the signal here so the settings can be loaded with modifications
		self.gobjects['switch_smtp_ssh_enable'].connect('notify::active', self.signal_switch_smtp_ssh)
		self._plugin_option_widgets = collections.defaultdict(dict)

	def signal_switch_smtp_ssh(self, switch, _):
		active = switch.get_property('active')
		entry = self.gobjects['entry_smtp_server']
		self.gtk_builder_get('frame_smtp_ssh').set_sensitive(active)
		if active:
			entry.set_sensitive(False)
			current_text = entry.get_text()
			if current_text.startswith('!'):
				entry.set_text(current_text[1:])
			else:
				entry.set_text('localhost:25')
		else:
			entry.set_sensitive(True)

	def signal_toggle_alert_subscribe(self, cbutton):
		active = cbutton.get_property('active')
		if active:
			remote_method = 'campaign/alerts/subscribe'
		else:
			remote_method = 'campaign/alerts/unsubscribe'
		self.application.rpc(remote_method, self.config['campaign_id'])

	def signal_toggle_reject_after_credentials(self, cbutton):
		self.application.rpc('db/table/set', 'campaigns', self.config['campaign_id'], 'reject_after_credentials', cbutton.get_property('active'))

	def signal_changed_spf_check_level(self, combobox):
		ti = combobox.get_active_iter()
		if not ti:
			return
		model = combobox.get_model()
		label = self.gtk_builder_get('label_spf_level_description')
		level_description = model[ti][2]
		label.set_text(level_description)

	def _configure_settings_dashboard(self):
		if not graphs.has_matplotlib:
			self.gtk_builder_get('frame_dashboard').set_sensitive(False)
			return
		graph_providers = Gtk.ListStore(str, str)
		for graph in graphs.get_graphs():
			graph = graphs.get_graph(graph)
			graph_providers.append([graph.name_human, graph.name])
		for dash_position in ['top_left', 'top_right', 'bottom']:
			combobox = self.gtk_builder_get('combobox_dashboard_' + dash_position)
			combobox.set_model(graph_providers)
			ti = gui_utilities.gtk_list_store_search(graph_providers, self.config.get('dashboard.' + dash_position), column=1)
			combobox.set_active_iter(ti)

	def _configure_settings_plugin_options(self, plugin_klass):
		frame = PluginsConfigurationFrame(self.application, plugin_klass)
		self.gobjects['box_plugin_options'].pack_start(frame, True, True, 0)
		self._plugin_option_widgets[plugin_klass.name] = frame.option_widgets

	def _configure_settings_plugins(self):
		pm = self.application.plugin_manager
		plugin_klasses = [klass for _, klass in pm if klass.options and klass.is_compatible]
		plugin_klasses = sorted(plugin_klasses, key=lambda k: k.title)
		for plugin_klass in plugin_klasses:
			self._configure_settings_plugin_options(plugin_klass)

	def _configure_settings_server(self):
		cb_subscribed = self.gtk_builder_get('checkbutton_alert_subscribe')
		cb_reject_after_creds = self.gtk_builder_get('checkbutton_reject_after_credentials')
		entry_beef_hook = self.gtk_builder_get('entry_server_beef_hook')
		server_config = self.application.rpc('config/get', ['beef.hook_url', 'server.require_id', 'server.secret_id'])
		entry_beef_hook.set_property('text', server_config.get('beef.hook_url', ''))
		self.config['server_config']['server.require_id'] = server_config['server.require_id']
		self.config['server_config']['server.secret_id'] = server_config['server.secret_id']
		# older versions of GObject.signal_handler_find seem to have a bug which cause a segmentation fault in python
		if GObject.pygobject_version < (3, 10):
			cb_subscribed.set_property('active', self.application.rpc('campaign/alerts/is_subscribed', self.config['campaign_id']))
			cb_reject_after_creds.set_property('active', self.application.rpc.remote_table_row('campaigns', self.config['campaign_id']).reject_after_credentials)
		else:
			with gui_utilities.gobject_signal_blocked(cb_subscribed, 'toggled'):
				cb_subscribed.set_property('active', self.application.rpc('campaign/alerts/is_subscribed', self.config['campaign_id']))
				cb_reject_after_creds.set_property('active', self.application.rpc.remote_table_row('campaigns', self.config['campaign_id']).reject_after_credentials)
		cb_reject_after_creds.set_sensitive(self.config['server_config']['server.require_id'])

	def _finialize_settings_dashboard(self):
		dashboard_changed = False
		for dash_position in ['top_left', 'top_right', 'bottom']:
			combobox = self.gtk_builder_get('combobox_dashboard_' + dash_position)
			ti = combobox.get_active_iter()
			if not ti:
				continue
			graph_providers = combobox.get_model()
			graph_name = graph_providers[ti][1]
			if self.config.get('dashboard.' + dash_position) == graph_name:
				continue
			self.config['dashboard.' + dash_position] = graph_name
			dashboard_changed = True
		if dashboard_changed:
			gui_utilities.show_dialog_info('The dashboard layout has been updated.', self.parent, 'The new settings will be applied the next time the application starts.')

	def interact(self):
		self._configure_settings_dashboard()
		self._configure_settings_plugins()
		self._configure_settings_server()
		self.gtk_builder_get('combobox_spf_check_level').emit('changed')

		self.dialog.show_all()
		response = self.dialog.run()
		if response != Gtk.ResponseType.CANCEL:
			self.objects_save_to_config()
			self.save_plugin_options()
			self.verify_sms_settings()
			entry_beef_hook = self.gtk_builder_get('entry_server_beef_hook')
			self.application.rpc('config/set', {'beef.hook_url': entry_beef_hook.get_property('text').strip()})
			if graphs.has_matplotlib:
				self._finialize_settings_dashboard()
		self.dialog.destroy()
		return response

	def save_plugin_options(self):
		for name, option_widgets in self._plugin_option_widgets.items():
			if name not in self.config['plugins']:
				self.config['plugins'][name] = {}
			plugin_config = self.config['plugins'][name]  # use or instead of get incase the value is actually None
			for option_name, option_widget in option_widgets.items():
				plugin_config[option_name] = option_widget.option.get_widget_value(option_widget.widget)

	def verify_sms_settings(self):
		phone_number = gui_utilities.gobject_get_value(self.gobjects['entry_sms_phone_number'])
		phone_number_set = bool(phone_number)
		sms_carrier_set = bool(self.gobjects['combobox_sms_carrier'].get_active() > 0)
		if phone_number_set ^ sms_carrier_set:
			gui_utilities.show_dialog_warning('Missing Information', self.parent, 'Both a phone number and a valid carrier must be specified')
			if 'sms_phone_number' in self.config:
				del self.config['sms_phone_number']
			if 'sms_carrier' in self.config:
				del self.config['sms_carrier']
		elif phone_number_set and sms_carrier_set:
			phone_number = ''.join(d for d in phone_number if d in string.digits)
			if len(phone_number) != 10:
				gui_utilities.show_dialog_warning('Invalid Phone Number', self.parent, 'The phone number must contain exactly 10 digits')
				return
			username = self.config['server_username']
			self.application.rpc('db/table/set', 'users', username, ('phone_number', 'phone_carrier'), (phone_number, self.config['sms_carrier']))
