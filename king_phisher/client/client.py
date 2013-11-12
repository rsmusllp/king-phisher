#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  client.py
#

import copy
import json
import logging
import os

from gi.repository import Gtk

from king_phisher.utilities import show_dialog_yes_no, UtilityGladeGObject
from king_phisher.client.login import KingPhisherClientLoginDialog
from king_phisher.client.tabs.mail import MailSenderTab

__version__ = '0.0.1'

UI_INFO = """
<ui>
	<menubar name="MenuBar">
		<menu action="FileMenu">
			<menuitem action="FileNewCampaign" />
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
		self.connect('destroy', Gtk.main_quit)
		self.notebook.show()
		self.show()

	def _add_menu_actions(self, action_group):
		# File Menu Actions
		action_filemenu = Gtk.Action("FileMenu", "File", None, None)
		action_group.add_action(action_filemenu)

		action_file_new_campaign = Gtk.Action("FileNewCampaign", "_New Campaign", "Start a new Campaign", Gtk.STOCK_NEW)
		action_file_new_campaign.connect("activate", lambda x: self.start_new_campaign())
		action_group.add_action_with_accel(action_file_new_campaign, "<control>N")

		action_file_quit = Gtk.Action("FileQuit", None, None, Gtk.STOCK_QUIT)
		action_file_quit.connect("activate", lambda x: Gtk.main_quit())
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

	def server_connect(self):
		login_dialog = KingPhisherClientLoginDialog(self.config, self)
		login_dialog.objects_load_from_config()
		response = login_dialog.interact()
		return response != Gtk.ResponseType.CANCEL

	def server_disconnect(self):
		return show_dialog_yes_no("Are you sure you want to disconnect?", self)

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
		dialog.interact()

	def start_new_campaign(self):
		pass
