#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  king_phisher/client/client.py
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

import copy
import json
import logging
import os
import random
import shutil
import socket
import time

from king_phisher import find
from king_phisher import utilities
from king_phisher import version
from king_phisher.client import export
from king_phisher.client import graphs
from king_phisher.client import gui_utilities
from king_phisher.client import tools
from king_phisher.client.login import KingPhisherClientLoginDialog
from king_phisher.client.client_rpc import KingPhisherRPCClient
from king_phisher.client.tabs.campaign import CampaignViewTab
from king_phisher.client.tabs.mail import MailSenderTab
from king_phisher.ssh_forward import SSHTCPForwarder
from king_phisher.third_party.AdvancedHTTPServer import AdvancedHTTPServerRPCError

from gi.repository import Gdk
from gi.repository import GdkPixbuf
from gi.repository import GLib
from gi.repository import GObject
from gi.repository import Gtk
import paramiko

CONFIG_FILE_PATH = '~/.king_phisher.json'
"""The default search location for the client configuration file."""

if isinstance(Gtk.Window, utilities.Mock):
	_Gtk_Window = type('Gtk.Window', (object,), {})
	_Gtk_Window.__module__ = ''
else:
	_Gtk_Window = Gtk.Window

class KingPhisherClientCampaignSelectionDialog(gui_utilities.UtilityGladeGObject):
	"""
	Display a dialog which allows a new campaign to be created or an
	existing campaign to be opened.
	"""
	gobject_ids = [
		'button_new_campaign',
		'entry_new_campaign_name',
		'treeview_campaigns'
	]
	top_gobject = 'dialog'
	def __init__(self, *args, **kwargs):
		super(KingPhisherClientCampaignSelectionDialog, self).__init__(*args, **kwargs)
		treeview = self.gobjects['treeview_campaigns']
		columns = ['Campaign Name', 'Created By', 'Creation Date']
		for column_id in range(len(columns)):
			column_name = columns[column_id]
			column_id += 1
			column = Gtk.TreeViewColumn(column_name, Gtk.CellRendererText(), text=column_id)
			column.set_sort_column_id(column_id)
			treeview.append_column(column)
		treeview.get_selection().set_mode(Gtk.SelectionMode.SINGLE)
		self.load_campaigns()

	def _highlight_campaign(self, campaign_name):
		treeview = self.gobjects['treeview_campaigns']
		store = treeview.get_model()
		store_iter = store.get_iter_first()
		while store_iter:
			if store.get_value(store_iter, 1) == campaign_name:
				treeview.set_cursor(store.get_path(store_iter), None, False)
				return True
			store_iter = store.iter_next(store_iter)
		return False

	def load_campaigns(self):
		"""Load campaigns from the remote server and populate the :py:class:`Gtk.TreeView`."""
		treeview = self.gobjects['treeview_campaigns']
		store = treeview.get_model()
		if store == None:
			store = Gtk.ListStore(str, str, str, str)
			treeview.set_model(store)
		else:
			store.clear()
		for campaign in self.parent.rpc.remote_table('campaigns'):
			store.append([str(campaign['id']), campaign['name'], campaign['user_id'], campaign['created'].strftime('%Y-%m-%d %H:%M:%S')])

	def signal_button_clicked(self, button):
		campaign_name_entry = self.gobjects['entry_new_campaign_name']
		campaign_name = campaign_name_entry.get_property('text')
		if not campaign_name:
			gui_utilities.show_dialog_warning('Invalid Campaign Name', self.dialog, 'Please specify a new campaign name')
			return
		try:
			self.parent.rpc('campaign/new', campaign_name)
		except:
			gui_utilities.show_dialog_error('Failed To Create New Campaign', self.dialog, 'Encountered an error creating the new campaign')
			return
		campaign_name_entry.set_property('text', '')
		self.load_campaigns()
		self._highlight_campaign(campaign_name)

	def signal_entry_new_campaign_name_activate(self, entry):
		self.gobjects['button_new_campaign'].emit('clicked')

	def signal_treeview_key_pressed(self, widget, event):
		if event.type != Gdk.EventType.KEY_PRESS:
			return
		keyval = event.get_keyval()[1]
		if keyval == Gdk.KEY_F5:
			self.load_campaigns()
			self._highlight_campaign(self.config.get('campaign_name'))
		elif keyval == Gdk.KEY_Delete:
			treeview = self.gobjects['treeview_campaigns']
			selection = treeview.get_selection()
			(model, tree_iter) = selection.get_selected()
			if not tree_iter:
				return
			campaign_id = model.get_value(tree_iter, 0)
			if self.config.get('campaign_id') == campaign_id:
				gui_utilities.show_dialog_warning('Can Not Delete Campaign', self.dialog, 'Can not delete the current campaign.')
				return
			if not gui_utilities.show_dialog_yes_no('Delete This Campaign?', self.dialog, 'This action is irreversible, all campaign data will be lost.'):
				return
			self.parent.rpc('campaign/delete', campaign_id)
			self.load_campaigns()
			self._highlight_campaign(self.config.get('campaign_name'))

	def interact(self):
		self._highlight_campaign(self.config.get('campaign_name'))
		self.dialog.show_all()
		response = self.dialog.run()
		old_campaign_id = self.config.get('campaign_id')
		old_campaign_name = self.config.get('campaign_name')
		while response != Gtk.ResponseType.CANCEL:
			treeview = self.gobjects['treeview_campaigns']
			selection = treeview.get_selection()
			(model, tree_iter) = selection.get_selected()
			if tree_iter:
				break
			gui_utilities.show_dialog_error('No Campaign Selected', self.dialog, 'Either select a campaign or create a new one.')
			response = self.dialog.run()
		if response != Gtk.ResponseType.CANCEL:
			campaign_id = model.get_value(tree_iter, 0)
			self.config['campaign_id'] = campaign_id
			campaign_name = model.get_value(tree_iter, 1)
			self.config['campaign_name'] = campaign_name
			if not (campaign_id == old_campaign_id and campaign_name == old_campaign_name):
				self.parent.emit('campaign_set', campaign_id)
		self.dialog.destroy()
		return response

class KingPhisherClientConfigDialog(gui_utilities.UtilityGladeGObject):
	"""
	Display the King Phisher client configuration dialog. Running this
	dialog via the :py:func:`.interact` method will cause some server
	settings to be loaded.
	"""
	gobject_ids = [
		# Server Tab
		'entry_server',
		'entry_server_username',
		'entry_sms_phone_number',
		'combobox_sms_carrier',
		# SMTP Server Tab
		'entry_smtp_server',
		'spinbutton_smtp_max_send_rate',
		'switch_smtp_ssl_enable',
		'switch_smtp_ssh_enable',
		'entry_ssh_server',
		'entry_ssh_username'
	]
	top_gobject = 'dialog'
	top_level_dependencies = [
		'SMSCarriers',
		'SMTPSendRate'
	]
	def signal_switch_smtp_ssh(self, switch, _):
		active = switch.get_property('active')
		self.gobjects['entry_ssh_server'].set_sensitive(active)
		self.gobjects['entry_ssh_username'].set_sensitive(active)

	def signal_toggle_alert_subscribe(self, cbutton):
		active = cbutton.get_property('active')
		if active:
			remote_method = 'campaign/alerts/subscribe'
		else:
			remote_method = 'campaign/alerts/unsubscribe'
		self.parent.rpc(remote_method, self.config['campaign_id'])

	def signal_toggle_reject_after_credentials(self, cbutton):
		self.parent.rpc('campaigns/set', self.config['campaign_id'], 'reject_after_credentials', cbutton.get_property('active'))

	def interact(self):
		cb_subscribed = self.gtk_builder_get('checkbutton_alert_subscribe')
		cb_reject_after_creds = self.gtk_builder_get('checkbutton_reject_after_credentials')
		entry_beef_hook = self.gtk_builder_get('entry_server_beef_hook')
		server_config = self.parent.rpc('config/get', ['beef.hook_url', 'server.require_id', 'server.secret_id'])
		entry_beef_hook.set_property('text', server_config.get('beef.hook_url', ''))
		self.config['server_config']['server.require_id'] = server_config['server.require_id']
		self.config['server_config']['server.secret_id'] = server_config['server.secret_id']
		# older versions of GObject.signal_handler_find seem to have a bug which cause a segmentation fault in python
		if GObject.pygobject_version < (3, 10):
			cb_subscribed.set_property('active', self.parent.rpc('campaign/alerts/is_subscribed', self.config['campaign_id']))
			cb_reject_after_creds.set_property('active', self.parent.rpc.remote_table_row('campaigns', self.config['campaign_id'])['reject_after_credentials'])
		else:
			with gui_utilities.gobject_signal_blocked(cb_subscribed, 'toggled'):
				cb_subscribed.set_property('active', self.parent.rpc('campaign/alerts/is_subscribed', self.config['campaign_id']))
				cb_reject_after_creds.set_property('active', self.parent.rpc.remote_table_row('campaigns', self.config['campaign_id'])['reject_after_credentials'])

		cb_reject_after_creds.set_sensitive(self.config['server_config']['server.require_id'])

		self.dialog.show_all()
		response = self.dialog.run()
		if response != Gtk.ResponseType.CANCEL:
			self.objects_save_to_config()
			self.verify_sms_settings()
			self.parent.rpc('config/set', {'beef.hook_url': entry_beef_hook.get_property('text').strip()})
		self.dialog.destroy()
		return response

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
			phone_number = filter(lambda x: x in map(str, range(0, 10)), phone_number)
			if len(phone_number) != 10:
				gui_utilities.show_dialog_warning('Invalid Phone Number', self.parent, 'The phone number must contain exactly 10 digits')
				return
			username = self.config['server_username']
			self.parent.rpc('users/set', username, ('phone_number', 'phone_carrier'), (phone_number, self.config['sms_carrier']))

class KingPhisherClient(_Gtk_Window):
	"""
	This is the top level King Phisher client object. It contains the
	custom GObject signals, keeps all the GUI references, and manages
	the RPC client object. This is also the parent window for most
	GTK objects.

	:GObject Signals: :ref:`gobject-signals-kingphisher-client-label`
	"""
	__gsignals__ = {
		'campaign_set': (GObject.SIGNAL_RUN_FIRST, None, (str,)),
		'exit': (GObject.SIGNAL_RUN_CLEANUP, None, ())
	}
	def __init__(self, config_file=None):
		"""
		:param str config_file: The path to the configuration file to load.
		"""
		super(KingPhisherClient, self).__init__()
		self.logger = logging.getLogger('KingPhisher.Client')
		# print version information for debugging purposes
		self.logger.debug("gi.repository GLib version: {0}".format('.'.join(map(str, GLib.glib_version))))
		self.logger.debug("gi.repository GObject version: {0}".format('.'.join(map(str, GObject.pygobject_version))))
		if tools.has_vte:
			self.logger.debug("gi.repository VTE version: {0}".format(tools.Vte._version))
		if graphs.has_matplotlib:
			self.logger.debug("matplotlib version: {0}".format(graphs.matplotlib.__version__))
		self.config_file = (config_file or CONFIG_FILE_PATH)
		"""The file containing the King Phisher client configuration."""
		self.ssh_forwarder = None
		"""The :py:class:`.SSHTCPForwarder` instance used for tunneling traffic."""
		self.config = None
		"""The main King Phisher client configuration."""
		self.load_config()
		self.set_property('title', 'King Phisher')
		vbox = Gtk.Box()
		vbox.set_property('orientation', Gtk.Orientation.VERTICAL)
		vbox.show()
		self.add(vbox)
		default_icon_file = find.find_data_file('king-phisher-icon.svg')
		if default_icon_file:
			icon_pixbuf = GdkPixbuf.Pixbuf.new_from_file(default_icon_file)
			self.set_default_icon(icon_pixbuf)

		action_group = Gtk.ActionGroup("client_window_actions")
		self._add_menu_actions(action_group)
		uimanager = self._create_ui_manager()
		uimanager.insert_action_group(action_group)
		self.uimanager = uimanager
		menubar = uimanager.get_widget("/MenuBar")
		vbox.pack_start(menubar, False, False, 0)

		# create notebook and tabs
		self.notebook = Gtk.Notebook()
		"""The primary :py:class:`Gtk.Notebook` that holds the top level taps of the client GUI."""
		self.notebook.connect('switch-page', self._tab_changed)
		self.notebook.set_scrollable(True)
		vbox.pack_start(self.notebook, True, True, 0)

		self.tabs = {}
		current_page = self.notebook.get_current_page()
		self.last_page_id = current_page

		mailer_tab = MailSenderTab(self.config, self)
		self.tabs['mailer'] = mailer_tab
		self.notebook.insert_page(mailer_tab.box, mailer_tab.label, current_page + 1)
		self.notebook.set_current_page(current_page + 1)

		campaign_tab = CampaignViewTab(self.config, self)
		campaign_tab.box.show()
		self.tabs['campaign'] = campaign_tab
		self.notebook.insert_page(campaign_tab.box, campaign_tab.label, current_page + 2)

		self.set_size_request(800, 600)
		self.connect('destroy', lambda _: self.emit('exit'))
		self.notebook.show()
		self.show()
		self.rpc = None # needs to be initialized last
		"""The :py:class:`.KingPhisherRPCClient` instance."""

	def _add_menu_actions(self, action_group):
		# File Menu Actions
		action = Gtk.Action('FileMenu', 'File', None, None)
		action_group.add_action(action)

		action = Gtk.Action('FileOpenCampaign', '_Open Campaign', 'Open a Campaign', Gtk.STOCK_NEW)
		action.connect('activate', lambda x: self.show_campaign_selection())
		action_group.add_action_with_accel(action, '<control>O')

		action = Gtk.Action('FileImportMenu', 'Import', None, None)
		action_group.add_action(action)

		action = Gtk.Action('FileImportMessageData', 'Message Data', 'Message Data', None)
		action.connect('activate', lambda x: self.tabs['mailer'].import_message_data())
		action_group.add_action(action)

		action = Gtk.Action('FileExportMenu', 'Export', None, None)
		action_group.add_action(action)

		action = Gtk.Action('FileExportCampaignXML', 'Campaign XML', 'Campaign XML', None)
		action.connect('activate', lambda x: self.export_campaign_xml())
		action_group.add_action(action)

		action = Gtk.Action('FileExportMessageData', 'Message Data', 'Message Data', None)
		action.connect('activate', lambda x: self.tabs['mailer'].export_message_data())
		action_group.add_action(action)

		action = Gtk.Action('FileQuit', None, None, Gtk.STOCK_QUIT)
		action.connect('activate', lambda x: self.client_quit())
		action_group.add_action_with_accel(action, '<control>Q')

		# Edit Menu Actions
		action = Gtk.Action('EditMenu', 'Edit', None, None)
		action_group.add_action(action)

		action = Gtk.Action('EditPreferences', 'Preferences', 'Edit preferences', Gtk.STOCK_EDIT)
		action.connect('activate', lambda x: self.edit_preferences())
		action_group.add_action(action)

		action = Gtk.Action('EditDeleteCampaign', 'Delete Campaign', 'Delete Campaign', None)
		action.connect('activate', lambda x: self.delete_campaign())
		action_group.add_action(action)

		action = Gtk.Action('EditStopService', 'Stop Service', 'Stop Remote King-Phisher Service', None)
		action.connect('activate', lambda x: self.stop_remote_service())
		action_group.add_action(action)

		# Tools Menu Action
		action = Gtk.Action('ToolsMenu', 'Tools', None, None)
		action_group.add_action(action)

		action = Gtk.Action('ToolsRPCTerminal', 'RPC Terminal', 'RPC Terminal', None)
		action.connect('activate', lambda x: tools.KingPhisherClientRPCTerminal(self.config, self))
		action_group.add_action(action)

		# Help Menu Actions
		action = Gtk.Action('HelpMenu', 'Help', None, None)
		action_group.add_action(action)

		if graphs.has_matplotlib:
			action = Gtk.Action('ToolsGraphMenu', 'Create Graph', None, None)
			action_group.add_action(action)

			for graph_name in graphs.get_graphs():
				action_name = 'ToolsGraph' + graph_name
				action = Gtk.Action(action_name, graph_name, graph_name, None)
				action.connect('activate', lambda _: self.show_campaign_graph(graph_name))
				action_group.add_action(action)

		action = Gtk.Action('HelpAbout', 'About', 'About', None)
		action.connect('activate', lambda x: self.show_about_dialog())
		action_group.add_action(action)

		action = Gtk.Action('HelpWiki', 'Wiki', 'Wiki', None)
		action.connect('activate', lambda x: utilities.open_uri('https://github.com/securestate/king-phisher/wiki'))
		action_group.add_action(action)

	def _create_ui_manager(self):
		uimanager = Gtk.UIManager()
		with open(find.find_data_file('ui_info/client_window.xml')) as ui_info_file:
			ui_data = ui_info_file.read()
		uimanager.add_ui_from_string(ui_data)
		if graphs.has_matplotlib:
			merge_id = uimanager.new_merge_id()
			uimanager.add_ui(merge_id, '/MenuBar/ToolsMenu', 'ToolsGraphMenu', 'ToolsGraphMenu', Gtk.UIManagerItemType.MENU, False)
			for graph_name in graphs.get_graphs():
				action_name = 'ToolsGraph' + graph_name
				uimanager.add_ui(merge_id, '/MenuBar/ToolsMenu/ToolsGraphMenu', action_name, action_name, Gtk.UIManagerItemType.MENUITEM, False)
		accelgroup = uimanager.get_accel_group()
		self.add_accel_group(accelgroup)
		return uimanager

	def _tab_changed(self, notebook, current_page, index):
		previous_page = notebook.get_nth_page(self.last_page_id)
		self.last_page_id = index
		mailer_tab = self.tabs.get('mailer')
		campaign_tab = self.tabs.get('campaign')

		notebook = None
		if mailer_tab and current_page == mailer_tab.box:
			notebook = mailer_tab.notebook
		elif campaign_tab and current_page == campaign_tab.box:
			notebook = campaign_tab.notebook

		if notebook:
			index = notebook.get_current_page()
			notebook.emit('switch-page', notebook.get_nth_page(index), index)

	def do_campaign_set(self, campaign_id):
		self.rpc.cache_clear()
		self.logger.info("campaign set to {0} (id: {1})".format(self.config['campaign_name'], self.config['campaign_id']))

	def do_exit(self):
		gui_utilities.gtk_widget_destroy_children(self)
		gui_utilities.gtk_sync()
		self.server_disconnect()
		self.save_config()
		Gtk.main_quit()
		return

	def init_connection(self):
		"""
		Initialize a connection to the King Phisher server. This will
		connect to the server and load necessary information from it.

		:return: Whether or not the connection attempt was successful.
		:rtype: bool
		"""
		if not self.server_connect():
			return False
		self.load_server_config()
		campaign_id = self.config.get('campaign_id')
		if campaign_id == None:
			if not self.show_campaign_selection():
				self.server_disconnect()
				return False
		campaign_info = self.rpc.remote_table_row('campaigns', self.config['campaign_id'], cache=True)
		if campaign_info == None:
			if not self.show_campaign_selection():
				self.server_disconnect()
				return False
			campaign_info = self.rpc.remote_table_row('campaigns', self.config['campaign_id'], cache=True, refresh=True)
		self.config['campaign_name'] = campaign_info['name']
		self.emit('campaign_set', self.config['campaign_id'])
		return True

	def client_quit(self, destroy=True):
		"""Quit the client and perform any necessary clean up operations."""
		self.destroy()
		return

	def server_connect(self):
		"""
		Perform the connection setup as part of the server connection
		initialization process. This will display a GUI window requesting
		the connection information. An :py:class:`.SSHTCPForwarder` instance
		is created and configured for tunneling traffic to the King Phisher
		server. This also verifies that the RPC API version running on
		the server is compatible with the client.

		:return: Whether or not the connection attempt was successful.
		:rtype: bool
		"""
		import socket
		server_version_info = None
		title_ssh_error = 'Failed To Connect To The SSH Service'
		title_rpc_error = 'Failed To Connect To The King Phisher RPC Service'
		while True:
			if self.ssh_forwarder:
				self.ssh_forwarder.stop()
				self.ssh_forwarder = None
				self.logger.info('stopped ssh port forwarding')
			login_dialog = KingPhisherClientLoginDialog(self.config, self)
			login_dialog.objects_load_from_config()
			response = login_dialog.interact()
			if response == Gtk.ResponseType.CANCEL:
				return False
			server = utilities.server_parse(self.config['server'], 22)
			username = self.config['server_username']
			password = self.config['server_password']
			server_remote_port = self.config.get('server_remote_port', 80)
			local_port = random.randint(2000, 6000)
			try:
				self.ssh_forwarder = SSHTCPForwarder(server, username, password, local_port, ('127.0.0.1', server_remote_port), preferred_private_key=self.config.get('ssh_preferred_key'))
				self.ssh_forwarder.start()
				time.sleep(0.5)
				self.logger.info('started ssh port forwarding')
			except paramiko.AuthenticationException:
				self.logger.warning('failed to authenticate to the remote ssh server')
				gui_utilities.show_dialog_error(title_ssh_error, self, 'The server responded that the credentials are invalid')
				continue
			except socket.error as error:
				error_number, error_message = error.args
				if error_number == 111:
					gui_utilities.show_dialog_error(title_ssh_error, self, 'The server refused the connection')
				else:
					gui_utilities.show_dialog_error(title_ssh_error, self, "Socket error #{0} ({1})".format((error_number or 'NOT-SET'), error_message))
				continue
			except Exception:
				self.logger.warning('failed to connect to the remote ssh server')
				gui_utilities.show_dialog_error(title_ssh_error, self)
				continue
			self.rpc = KingPhisherRPCClient(('localhost', local_port), username=username, password=password, use_ssl=self.config.get('server_use_ssl'))
			try:
				server_version_info = self.rpc('version')
				assert(self.rpc('client/initialize'))
			except AdvancedHTTPServerRPCError as err:
				if err.status == 401:
					self.logger.warning('failed to authenticate to the remote king phisher service')
					gui_utilities.show_dialog_error(title_rpc_error, self, 'The server responded that the credentials are invalid')
				else:
					self.logger.warning('failed to connect to the remote rpc server with http status: ' + str(err.status))
					gui_utilities.show_dialog_error(title_rpc_error, self, 'The server responded with HTTP status: ' + str(err.status))
				continue
			except:
				self.logger.warning('failed to connect to the remote rpc service')
				gui_utilities.show_dialog_error(title_rpc_error, self, 'Ensure that the King Phisher Server is currently running')
				continue
			break
		assert(server_version_info != None)
		server_rpc_api_version = server_version_info.get('rpc_api_version', -1)
		self.logger.info("successfully connected to the king phisher server (version: {0} rpc api version: {1})".format(server_version_info['version'], server_rpc_api_version))
		self.server_local_port = local_port
		if server_rpc_api_version != version.rpc_api_version:
			if version.rpc_api_version < server_rpc_api_version:
				secondary_text = 'The local client is not up to date with the server version.'
			else:
				secondary_text = 'The remote server is not up to date with the client version.'
			secondary_text += '\nPlease ensure that both the client and server are fully up to date.'
			gui_utilities.show_dialog_error('The RPC API Versions Are Incompatible', self, secondary_text)
			self.server_disconnect()
			return False
		return True

	def server_disconnect(self):
		"""Clean up the SSH TCP connections and disconnect from the server."""
		if self.ssh_forwarder:
			self.ssh_forwarder.stop()
			self.ssh_forwarder = None
			self.logger.info('stopped ssh port forwarding')
		return

	def load_config(self):
		"""Load the client configuration from disk and set the :py:attr:`~.KingPhisherClient.config` attribute."""
		self.logger.info('loading the config from disk')
		config_file = os.path.expanduser(self.config_file)
		if not os.path.isfile(config_file):
			shutil.copy(find.find_data_file('client_config.json'), config_file)
		self.config = json.load(open(config_file, 'rb'))

	def load_server_config(self):
		"""Load the necessary values from the server's configuration."""
		self.config['server_config'] = self.rpc('config/get', ['server.require_id', 'server.secret_id', 'server.tracking_image'])
		return

	def save_config(self):
		"""Write the client configuration to disk."""
		self.logger.info('writing the config to disk')
		config = copy.copy(self.config)
		for key in self.config.keys():
			if 'password' in key or key == 'server_config':
				del config[key]
		config_file = os.path.expanduser(self.config_file)
		config_file_h = open(config_file, 'wb')
		json.dump(config, config_file_h, sort_keys=True, indent=4)

	def delete_campaign(self):
		"""
		Delete the campaign on the server. A confirmation dialog will be
		displayed before the operation is performed. If the campaign is
		deleted and a new campaign is not selected with
		:py:meth:`.show_campaign_selection`, the client will quit.
		"""
		if not gui_utilities.show_dialog_yes_no('Delete This Campaign?', self, 'This action is irreversible, all campaign data will be lost.'):
			return
		self.rpc('campaign/delete', self.config['campaign_id'])
		if not self.show_campaign_selection():
			gui_utilities.show_dialog_error('A Campaign Must Be Selected', self, 'Now exiting')
			self.client_quit()

	def edit_preferences(self):
		"""
		Display a :py:class:`.KingPhisherClientConfigDialog` instance and
		save the config to disk if cancel is not selected.
		"""
		dialog = KingPhisherClientConfigDialog(self.config, self)
		if dialog.interact() != Gtk.ResponseType.CANCEL:
			self.save_config()

	def export_campaign_xml(self):
		"""Export the current campaign to an XML data file."""
		dialog = gui_utilities.UtilityFileChooser('Export Campaign XML Data', self)
		file_name = self.config['campaign_name'] + '.xml'
		response = dialog.run_quick_save(file_name)
		dialog.destroy()
		if not response:
			return
		destination_file = response['target_path']
		export.campaign_to_xml(self.rpc, self.config['campaign_id'], destination_file)

	def show_about_dialog(self):
		"""
		Display the about dialog showing details about the programs version,
		license etc.
		"""
		license_text = None
		if os.path.splitext(__file__)[1] == '.py':
			source_file_h = open(__file__, 'r')
			source_code = []
			source_code.append(source_file_h.readline())
			while source_code[-1].startswith('#'):
				source_code.append(source_file_h.readline())
			source_code = source_code[5:-1]
			source_code = map(lambda x: x.strip('# '), source_code)
			license_text = ''.join(source_code)
		logo_pixbuf = None
		logo_file_path = find.find_data_file('king-phisher-icon.svg')
		if logo_file_path:
			logo_pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_size(logo_file_path, 128, 128)
		about_dialog = Gtk.AboutDialog()
		about_dialog.set_transient_for(self)
		about_dialog_properties = {
			'authors': ['Spencer McIntyre', 'Jeff McCutchan', 'Brandan Geise'],
			'comments': 'Phishing Campaign Toolkit',
			'copyright': '(c) 2013 SecureState',
			'license-type': Gtk.License.BSD,
			'program-name': 'King Phisher',
			'version': version.version,
			'website': 'https://github.com/securestate/king-phisher',
			'website-label': 'GitHub Home Page',
			'wrap-license': False,
		}
		if license_text:
			about_dialog_properties['license'] = license_text
		if logo_pixbuf:
			about_dialog_properties['logo'] = logo_pixbuf
		for property_name, property_value in about_dialog_properties.items():
			about_dialog.set_property(property_name, property_value)
		about_dialog.connect('activate-link', lambda _, url: utilities.open_uri(url))
		about_dialog.show_all()
		about_dialog.run()
		about_dialog.destroy()

	def show_campaign_graph(self, graph_name):
		"""
		Create a new :py:class:`.CampaignGraph` instance and make it into
		a window. *graph_name* must be the name of a valid, exported
		graph provider.

		:param str graph_name: The name of the graph to make a window of.
		"""
		Klass = graphs.get_graph(graph_name)
		graph_inst = Klass(self.config, self)
		graph_inst.load_graph()
		window = graph_inst.make_window()
		window.show_all()

	def show_campaign_selection(self):
		"""
		Display the campaign selection dialog in a new
		:py:class:`.KingPhisherClientCampaignSelectionDialog` instance.

		:return: The status of the dialog.
		:rtype: bool
		"""
		dialog = KingPhisherClientCampaignSelectionDialog(self.config, self)
		return dialog.interact() != Gtk.ResponseType.CANCEL

	def stop_remote_service(self):
		"""
		Stop the remote King Phisher server. This will request that the
		server stop processing new requests and exit. This will display
		a confirmation dialog before performing the operation. If the
		remote service is stopped, the client will quit.
		"""
		if not gui_utilities.show_dialog_yes_no('Stop The Remote King Phisher Service?', self, 'This will stop the remote King Phisher service and\nnew incoming requests will not be processed.'):
			return
		self.rpc('shutdown')
		self.logger.info('the remote king phisher service has been stopped')
		gui_utilities.show_dialog_error('The Remote Service Has Been Stopped', self, 'Now exiting')
		self.client_quit()
		return
