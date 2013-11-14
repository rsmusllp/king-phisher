#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  client.py
#

import copy
import json
import logging
import os
import random

from gi.repository import Gtk
from AdvancedHTTPServer import AdvancedHTTPServerRPCError, AdvancedHTTPServerRPCClient

from king_phisher.client.login import KingPhisherClientLoginDialog
from king_phisher.client.tabs.mail import MailSenderTab
from king_phisher.ssh_forward import SSHTCPForwarder
from king_phisher.utilities import server_parse, show_dialog_error, show_dialog_yes_no, UtilityGladeGObject

__version__ = '0.0.1'

UI_INFO = """
<ui>
	<menubar name="MenuBar">
		<menu action="FileMenu">
			<menuitem action="FileOpenCampaign" />
			<separator />
			<menuitem action="FileQuit" />
		</menu>
		<menu action="EditMenu">
			<menuitem action="EditPreferences" />
		</menu>
	</menubar>
</ui>
"""

CONFIG_FILE_PATH = '~/.king_phisher.json'
DEFAULT_CONFIG = """
{

}
"""

class KingPhisherClientCampaignSelectionDialog(UtilityGladeGObject):
	gobject_ids = [
		'button_new_campaign',
		'entry_new_campaign_name',
		'treeview_campaigns'
	]
	top_gobject = 'dialog'
	def __init__(self, *args, **kwargs):
		super(self.__class__, self).__init__(*args, **kwargs)
		treeview = self.gobjects['treeview_campaigns']
		column = Gtk.TreeViewColumn('Campaign', Gtk.CellRendererText(), text=1)
		treeview.append_column(column)
		treeview.get_selection().set_mode(Gtk.SelectionMode.SINGLE)
		self.load_campaigns()

	def load_campaigns(self):
		treeview = self.gobjects['treeview_campaigns']
		store = treeview.get_model()
		if store == None:
			store = Gtk.ListStore(int, str)
			treeview.set_model(store)
		else:
			store.clear()
		campaigns = self.parent.rpc('campaign/list')
		for campaign_id, campaign_name in campaigns.items():
			store.append([int(campaign_id), campaign_name])

	def signal_button_clicked(self, button):
		campaign_name_entry = self.gobjects['entry_new_campaign_name']
		campaign_name = campaign_name_entry.get_property('text')
		if not campaign_name:
			show_dialog_warning('Invalid Campaign Name', self.dialog, 'Please specify a new campaign name')
			return
		try:
			self.parent.rpc('campaign/new', campaign_name)
		except:
			show_dialog_error('Failed To Create New Campaign', self.dialog, 'Encountered an error creating the new campaign')
		else:
			campaign_name_entry.set_property('text', '')
			self.load_campaigns()

	def interact(self):
		self.dialog.show_all()
		response = self.dialog.run()
		if response != Gtk.ResponseType.CANCEL:
			treeview = self.gobjects['treeview_campaigns']
			selection = treeview.get_selection()
			(model, tree_iter) = selection.get_selected()
			if not tree_iter:
				show_dialog_error('No Campaign Selected', self.dialog, 'Either select a campaign or create a new one')
				self.dialog.destroy()
				return Gtk.ResponseType.CANCEL
			campaign_id = model.get_value(tree_iter, 0)
			self.config['campaign_id'] = campaign_id
			campaign_name = model.get_value(tree_iter, 1)
			self.config['campaign_name'] = campaign_name
		self.dialog.destroy()
		return response

class KingPhisherClientConfigDialog(UtilityGladeGObject):
	gobject_ids = [
			# Server Tab
			'entry_server',
			'entry_server_username',
			# SMTP Server Tab
			'entry_smtp_server',
			'checkbutton_smtp_ssl_enable',
			'checkbutton_smtp_ssh_enable',
			'entry_ssh_server',
			'entry_ssh_username'
	]
	top_gobject = 'dialog'
	def signal_smtp_ssh_enable(self, cbutton):
		active = cbutton.get_property('active')
		self.gobjects['entry_ssh_server'].set_sensitive(active)
		self.gobjects['entry_ssh_username'].set_sensitive(active)

	def interact(self):
		self.dialog.show_all()
		response = self.dialog.run()
		if response != Gtk.ResponseType.CANCEL:
			self.objects_save_to_config()
		self.dialog.destroy()
		return response

# This is the top level class/window for the client side of the king-phisher
# application
class KingPhisherClient(Gtk.Window):
	def __init__(self):
		super(KingPhisherClient, self).__init__()
		self.logger = logging.getLogger('browser')
		self.load_config()
		self.set_property('title', 'King Phisher')
		vbox = Gtk.VBox()
		vbox.show()
		self.add(vbox)

		action_group = Gtk.ActionGroup("my_actions")
		self._add_menu_actions(action_group)
		uimanager = self._create_ui_manager()
		uimanager.insert_action_group(action_group)
		menubar = uimanager.get_widget("/MenuBar")
		vbox.pack_start(menubar, False, False, 0)

		# create notebook and tabs
		hbox = Gtk.HBox()
		hbox.show()
		self.notebook = Gtk.Notebook()
		self.notebook.set_scrollable(True)
		hbox.pack_start(self.notebook, True, True, 0)
		vbox.pack_start(hbox, True, True, 0)

		self.tabs = {}
		mailer_tab = MailSenderTab(self.config, self)
		mailer_tab.show()
		self.tabs['mailer'] = mailer_tab
		current_page = self.notebook.get_current_page()
		self.notebook.insert_page(mailer_tab, mailer_tab.label, current_page+1)
		self.notebook.set_current_page(current_page+1)

		self.set_size_request(800, 600)
		self.connect('destroy', self.signal_window_destroy)
		self.notebook.show()
		self.show()
		self.rpc = None

	def _add_menu_actions(self, action_group):
		# File Menu Actions
		action_filemenu = Gtk.Action("FileMenu", "File", None, None)
		action_group.add_action(action_filemenu)

		action_file_new_campaign = Gtk.Action("FileOpenCampaign", "_Open Campaign", "Open a Campaign", Gtk.STOCK_NEW)
		action_file_new_campaign.connect("activate", lambda x: self.select_campaign())
		action_group.add_action_with_accel(action_file_new_campaign, "<control>O")

		action_file_quit = Gtk.Action("FileQuit", None, None, Gtk.STOCK_QUIT)
		action_file_quit.connect("activate", lambda x: self.client_quit())
		action_group.add_action_with_accel(action_file_quit, "<control>Q")

		# Edit Menu Actions
		action_editmenu = Gtk.Action("EditMenu", "Edit", None, None)
		action_group.add_action(action_editmenu)

		action_edit_preferences = Gtk.Action("EditPreferences", "Preferences", "Edit preferences", Gtk.STOCK_EDIT)
		action_edit_preferences.connect("activate", lambda x: self.edit_preferences())
		action_group.add_action(action_edit_preferences)

	def _create_ui_manager(self):
		uimanager = Gtk.UIManager()
		uimanager.add_ui_from_string(UI_INFO)
		accelgroup = uimanager.get_accel_group()
		self.add_accel_group(accelgroup)
		return uimanager

	def signal_window_destroy(self, window):
		self.client_quit()

	def client_initialize(self):
		if not self.server_connect():
			return False
		campaign_id = self.config.get('campaign_id')
		if campaign_id == None:
			if not self.select_campaign():
				self.server_disconnect()
				return False
		return True

	def client_quit(self):
		self.server_disconnect()
		Gtk.main_quit()
		return

	def server_connect(self):
		import socket
		while True:
			login_dialog = KingPhisherClientLoginDialog(self.config, self)
			login_dialog.objects_load_from_config()
			response = login_dialog.interact()
			if response == Gtk.ResponseType.CANCEL:
				return False
			server = server_parse(self.config['server'], 22)
			username = self.config['server_username']
			password = self.config['server_password']
			server_remote_port = self.config.get('server_remote_port', 80)
			local_port = random.randint(2000, 6000)
			try:
				self.ssh_forwarder = SSHTCPForwarder(server, username, password, local_port, ('127.0.0.1', server_remote_port))
				self.ssh_forwarder.start()
			except:
				continue
			self.rpc = AdvancedHTTPServerRPCClient(('localhost', local_port), username = username, password = password)
			try:
				assert(self.rpc('ping'))
				return True
			except AdvancedHTTPServerRPCError as err:
				if err.status == 401:
					show_dialog_error('Invalid Credentials', self)
			except:
				pass

	def server_disconnect(self):
		self.ssh_forwarder.stop()
		return

	def load_config(self):
		config_file = os.path.expanduser(CONFIG_FILE_PATH)
		if not os.path.isfile(config_file):
			self.config = {}
			self.save_config()
		else:
			self.config = json.load(open(config_file, 'rb'))

	def save_config(self):
		config = copy.copy(self.config)
		for key in self.config.keys():
			if 'password' in key:
				del config[key]
		config_file = os.path.expanduser(CONFIG_FILE_PATH)
		config_file_h = open(config_file, 'wb')
		json.dump(config, config_file_h, sort_keys = True, indent = 4)

	def edit_preferences(self):
		dialog = KingPhisherClientConfigDialog(self.config, self)
		dialog.interact() != Gtk.ResponseType.CANCEL

	def select_campaign(self):
		dialog = KingPhisherClientCampaignSelectionDialog(self.config, self)
		return dialog.interact() != Gtk.ResponseType.CANCEL
