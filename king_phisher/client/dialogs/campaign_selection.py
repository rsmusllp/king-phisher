#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  king_phisher/client/dialogs/campaign_selection.py
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

from king_phisher import utilities
from king_phisher.client import gui_utilities

from gi.repository import Gdk
from gi.repository import Gtk

__all__ = ['KingPhisherClientCampaignSelectionDialog']

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
			created_ts = utilities.datetime_utc_to_local(campaign.created)
			created_ts = utilities.format_datetime(created_ts)
			store.append([str(campaign.id), campaign.name, campaign.user_id, created_ts])

	def signal_button_clicked(self, button):
		campaign_name_entry = self.gobjects['entry_new_campaign_name']
		campaign_name = campaign_name_entry.get_property('text')
		if not campaign_name:
			gui_utilities.show_dialog_warning('Invalid Campaign Name', self.dialog, 'Please specify a new campaign name')
			return
		try:
			self.parent.rpc('campaign/new', campaign_name)
		#_TODO: this should probably be an RPC exception
		except Exception:
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

		treeview = self.gobjects['treeview_campaigns']
		keyval = event.get_keyval()[1]
		if event.get_state() == Gdk.ModifierType.CONTROL_MASK:
			if keyval == Gdk.KEY_c:
				gui_utilities.gtk_treeview_selection_to_clipboard(treeview)
		elif keyval == Gdk.KEY_F5:
			self.load_campaigns()
			self._highlight_campaign(self.config.get('campaign_name'))
		elif keyval == Gdk.KEY_Delete:
			treeview_selection = treeview.get_selection()
			(model, tree_iter) = treeview_selection.get_selected()
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
		if response == Gtk.ResponseType.APPLY:
			campaign_id = model.get_value(tree_iter, 0)
			self.config['campaign_id'] = campaign_id
			campaign_name = model.get_value(tree_iter, 1)
			self.config['campaign_name'] = campaign_name
			if not (campaign_id == old_campaign_id and campaign_name == old_campaign_name):
				self.parent.emit('campaign-set', campaign_id)
		self.dialog.destroy()
		return response
