#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  king_phisher/client/tabs/campaign.py
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
#  * Neither the name of the  nor the names of its
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
import os
import urlparse

from king_phisher.client.mailer import format_message, MailSenderThread
from king_phisher.client import export
from king_phisher.client import utilities

from gi.repository import Gdk
from gi.repository import Gtk

class CampaignViewGenericTab(utilities.UtilityGladeGObject):
	gobject_ids = [
		'button_refresh',
		'treeview_campaign'
	]
	top_gobject = 'box'
	remote_table_name = ''
	label_text = 'Unknown'
	view_columns = { }
	def __init__(self, *args, **kwargs):
		self.label = Gtk.Label(self.label_text)
		super(CampaignViewGenericTab, self).__init__(*args, **kwargs)
		treeview = self.gobjects['treeview_campaign']
		treeview.get_selection().set_mode(Gtk.SelectionMode.SINGLE)
		columns = self.view_columns
		for column_id in range(1, len(columns) + 1):
			column_name = columns[column_id]
			column = Gtk.TreeViewColumn(column_name, Gtk.CellRendererText(), text = column_id)
			column.set_sort_column_id(column_id)
			treeview.append_column(column)

	def load_campaign_information(self):
		# override me
		pass

	def signal_button_clicked_refresh(self, button):
		self.load_campaign_information()

	def signal_button_clicked_export(self, button):
		dialog = utilities.UtilityFileChooser('Export Data', self.parent)
		file_name = self.config['campaign_name'] + '.csv'
		response = dialog.run_quick_save(file_name)
		dialog.destroy()
		if not response:
			return
		destination_file = response['target_filename']
		export.treeview_liststore_to_csv(self.gobjects['treeview_campaign'], destination_file)

	def signal_treeview_button_pressed(self, widget, event):
		if not (event.type == Gdk.EventType.BUTTON_PRESS and event.button == 3):
			return
		menu = Gtk.Menu.new()
		menu_item = Gtk.MenuItem.new_with_label('Delete')
		menu_item.connect('activate', self.signal_treeview_popup_menu_delete)
		menu.append(menu_item)
		menu.show_all()
		pos_func = lambda m, d: (event.get_root_coords()[0], event.get_root_coords()[1], True)
		menu.popup(None, None, pos_func, None, event.button, event.time)
		return

	def signal_treeview_key_pressed(self, widget, event):
		if event.type != Gdk.EventType.KEY_PRESS:
			return
		if event.get_keyval()[1] == Gdk.KEY_F5:
			self.load_campaign_information()

	def signal_treeview_popup_menu_delete(self, action):
		treeview = self.gobjects['treeview_campaign']
		selection = treeview.get_selection()
		(model, tree_iter) = selection.get_selected()
		if not tree_iter:
			return
		row_id = model.get_value(tree_iter, 0)
		if not utilities.show_dialog_yes_no('Delete This Row?', self.parent, 'This information will be lost'):
			return
		self.parent.rpc(self.remote_table_name + '/delete', row_id)
		self.load_campaign_information()

class CampaignViewDeaddropTab(CampaignViewGenericTab):
	remote_table_name = 'deaddrop_connections'
	label_text = 'Deaddrop'
	view_columns = {
		1:'Destination',
		2:'Visit Count',
		3:'External IP',
		4:'Username',
		5:'Hostname',
		6:'Local IP Addresses',
		7:'First Hit',
		8:'Last Hit'
	}
	def load_campaign_information(self):
		treeview = self.gobjects['treeview_campaign']
		store = treeview.get_model()
		if store == None:
			store = Gtk.ListStore(str, str, str, str, str, str, str, str, str)
			treeview.set_model(store)
		else:
			store.clear()
		for connection in self.parent.rpc.remote_table('campaign/deaddrop_connections', self.config['campaign_id']):
			deploy_id = connection['deployment_id']
			deploy_details = self.parent.rpc.remote_table_row('deaddrop_deployments', deploy_id, cache = True)
			deploy_dest = deploy_details['destination']
			store.append([str(connection['id']), deploy_dest, str(connection['visit_count']), connection['visitor_ip'], connection['local_username'], connection['local_hostname'], connection['local_ip_addresses'], connection['first_visit'], connection['last_visit']])

class CampaignViewCredentialsTab(CampaignViewGenericTab):
	remote_table_name = 'credentials'
	label_text = 'Credentials'
	view_columns = {
		1:'Email',
		2:'Username',
		3:'Password',
		4:'Submitted'
	}
	def load_campaign_information(self):
		treeview = self.gobjects['treeview_campaign']
		store = treeview.get_model()
		if store == None:
			store = Gtk.ListStore(str, str, str, str, str)
			treeview.set_model(store)
		else:
			store.clear()
		for credential in self.parent.rpc.remote_table('campaign/credentials', self.config['campaign_id']):
			msg_id = credential['message_id']
			msg_details = self.parent.rpc.remote_table_row('messages', msg_id, cache = True)
			credential_email = msg_details['target_email']
			store.append([str(credential['id']), credential_email, credential['username'], credential['password'], credential['submitted']])

class CampaignViewVisitsTab(CampaignViewGenericTab):
	remote_table_name = 'visits'
	label_text = 'Visits'
	view_columns = {
		1:'Email',
		2:'Visitor IP',
		3:'Visitor Details',
		4:'Visit Count',
		5:'First Visit',
		6:'Last Visit'
	}
	def load_campaign_information(self):
		treeview = self.gobjects['treeview_campaign']
		store = treeview.get_model()
		if store == None:
			store = Gtk.ListStore(str, str, str, str, str, str, str)
			treeview.set_model(store)
		else:
			store.clear()
		for visit in self.parent.rpc.remote_table('campaign/visits', self.config['campaign_id']):
			msg_id = visit['message_id']
			msg_details = self.parent.rpc.remote_table_row('messages', msg_id, cache = True)
			visitor_email = msg_details['target_email']
			store.append([visit['id'], visitor_email, visit['visitor_ip'], visit['visitor_details'], str(visit['visit_count']), visit['first_visit'], visit['last_visit']])

class CampaignViewMessagesTab(CampaignViewGenericTab):
	remote_table_name = 'messages'
	label_text = 'Messages'
	view_columns = {
		1:'Email',
		2:'Sent',
		3:'Opened'
	}
	def load_campaign_information(self):
		treeview = self.gobjects['treeview_campaign']
		store = treeview.get_model()
		if store == None:
			store = Gtk.ListStore(str, str, str, str)
			treeview.set_model(store)
		else:
			store.clear()
		for message in self.parent.rpc.remote_table('campaign/messages', self.config['campaign_id']):
			store.append([message['id'], message['target_email'], message['sent'], message['opened']])

class CampaignViewTab(object):
	def __init__(self, config, parent):
		self.config = config
		self.parent = parent
		self.box = Gtk.VBox()
		self.box.show()
		self.label = Gtk.Label('View Campaign')

		self.notebook = Gtk.Notebook()
		self.notebook.connect('switch-page', self._tab_changed)
		self.notebook.set_scrollable(True)
		self.box.pack_start(self.notebook, True, True, 0)

		self.tabs = {}
		current_page = self.notebook.get_current_page()
		self.last_page_id = current_page

		messages_tab = CampaignViewMessagesTab(self.config, self.parent)
		self.tabs['messages'] = messages_tab
		self.notebook.append_page(messages_tab.box, messages_tab.label)

		visits_tab = CampaignViewVisitsTab(self.config, self.parent)
		self.tabs['visits'] = visits_tab
		self.notebook.append_page(visits_tab.box, visits_tab.label)

		credentials_tab = CampaignViewCredentialsTab(self.config, self.parent)
		self.tabs['credentials'] = credentials_tab
		self.notebook.append_page(credentials_tab.box, credentials_tab.label)

		deaddrop_connections_tab = CampaignViewDeaddropTab(self.config, self.parent)
		self.tabs['deaddrop_connections'] = deaddrop_connections_tab
		self.notebook.append_page(deaddrop_connections_tab.box, deaddrop_connections_tab.label)

		for tab in self.tabs.values():
			tab.box.show()
		self.notebook.show()

	def _tab_changed(self, notebook, current_page, index):
		if not hasattr(self.parent, 'rpc'):
			return
		previous_page = notebook.get_nth_page(self.last_page_id)
		self.last_page_id = index

		for tab_name, tab in self.tabs.items():
			if isinstance(tab, CampaignViewGenericTab) and current_page == tab.box:
				tab.load_campaign_information()
