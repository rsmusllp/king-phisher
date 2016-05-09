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

import datetime

from king_phisher import its
from king_phisher import utilities
from king_phisher.constants import ColorHexCode
from king_phisher.client.assistants import CampaignAssistant
from king_phisher.client import gui_utilities
from king_phisher.client.widget import managers

from gi.repository import Gdk
from gi.repository import Gtk

if its.py_v2:
	import cgi as html
else:
	import html

__all__ = ('CampaignSelectionDialog',)

class CampaignSelectionDialog(gui_utilities.GladeGObject):
	"""
	Display a dialog which allows a new campaign to be created or an
	existing campaign to be opened.
	"""
	dependencies = gui_utilities.GladeDependencies(
		children=(
			'button_new_campaign',
			'button_select',
			'drawingarea_color_key',
			'label_campaign_info',
			'menubutton_filter',
			'treeview_campaigns'
		),
		top_level=('StockAddImage',)
	)
	top_gobject = 'dialog'
	def __init__(self, *args, **kwargs):
		super(CampaignSelectionDialog, self).__init__(*args, **kwargs)
		treeview = self.gobjects['treeview_campaigns']
		self.treeview_manager = managers.TreeViewManager(treeview, cb_delete=self._prompt_to_delete_row, cb_refresh=self.load_campaigns)
		self.treeview_manager.set_column_titles(('Campaign Name', 'Company', 'Type', 'Created By', 'Creation Date', 'Expiration'), column_offset=1)
		self.treeview_manager.set_column_color(background=7, foreground=8)
		treeview.set_tooltip_column(9)
		self.popup_menu = self.treeview_manager.get_popup_menu()
		self._creation_assistant = None

		self._tv_model = Gtk.ListStore(str, str, str, str, str, str, str, Gdk.RGBA, Gdk.RGBA, str)
		# default sort is descending by campaign creation date
		self._tv_model.set_sort_column_id(5, Gtk.SortType.DESCENDING)
		# create and set the filter for expired campaigns
		self._tv_model_filter = self._tv_model.filter_new()
		self._tv_model_filter.set_visible_func(self._filter_campaigns)
		treeview.set_model(Gtk.TreeModelSort(model=self._tv_model_filter))

		# setup menus for filtering campaigns and load campaigns
		self.get_popup_filter_menu()
		self.load_campaigns()

	def get_popup_filter_menu(self):
		# create filter menu and menuitems
		filter_menu = Gtk.Menu()
		menu_item_expired = Gtk.CheckMenuItem('Expired campaigns')
		menu_item_user = Gtk.CheckMenuItem('Your campaigns')
		menu_item_other = Gtk.CheckMenuItem('Other campaigns')
		self.filter_menu_items = {
			'expired_campaigns': menu_item_expired,
			'your_campaigns': menu_item_user,
			'other_campaigns': menu_item_other
		}
		# set up the menuitems and add it to the menubutton
		for menus in self.filter_menu_items:
			filter_menu.append(self.filter_menu_items[menus])
			self.filter_menu_items[menus].connect('toggled', self.signal_checkbutton_toggled)
			self.filter_menu_items[menus].show()
		self.filter_menu_items['expired_campaigns'].set_active(self.config['filter.campaign.expired'])
		self.filter_menu_items['your_campaigns'].set_active(self.config['filter.campaign.user'])
		self.filter_menu_items['other_campaigns'].set_active(self.config['filter.campaign.other_users'])
		self.gobjects['menubutton_filter'].set_popup(filter_menu)
		filter_menu.connect('destroy', self._save_filter)

	def _save_filter(self, _):
		self.config['filter.campaign.expired'] = self.filter_menu_items['expired_campaigns'].get_active()
		self.config['filter.campaign.user'] = self.filter_menu_items['your_campaigns'].get_active()
		self.config['filter.campaign.other_users'] = self.filter_menu_items['other_campaigns'].get_active()

	def _filter_campaigns(self, model, tree_iter, _):
		expiration_ts = model[tree_iter][6]
		campaign_owner = model[tree_iter][4]
		username = self.config['server_username']
		if not self.filter_menu_items['your_campaigns'].get_active():
			if username == campaign_owner:
				return False
		if not self.filter_menu_items['other_campaigns'].get_active():
			if username != campaign_owner:
				return False
		if expiration_ts is None:
			return True
		if utilities.parse_datetime(expiration_ts) < datetime.datetime.now():
			if not self.filter_menu_items['expired_campaigns'].get_active():
				return False
		return True

	def _highlight_campaign(self, campaign_name):
		treeview = self.gobjects['treeview_campaigns']
		model = treeview.get_model()
		model_iter = gui_utilities.gtk_list_store_search(model, campaign_name, column=1)
		if model_iter:
			treeview.set_cursor(model.get_path(model_iter), None, False)
			return True
		return False

	def _prompt_to_delete_row(self, treeview, selection):
		(model, tree_iter) = selection.get_selected()
		if not tree_iter:
			return
		campaign_id = model.get_value(tree_iter, 0)
		if self.config.get('campaign_id') == campaign_id:
			gui_utilities.show_dialog_warning('Can Not Delete Campaign', self.dialog, 'Can not delete the current campaign.')
			return
		if not gui_utilities.show_dialog_yes_no('Delete This Campaign?', self.dialog, 'This action is irreversible, all campaign data will be lost.'):
			return
		self.application.rpc('db/table/delete', 'campaigns', campaign_id)
		self.application.emit('campaign-deleted', campaign_id)
		self.load_campaigns()
		self._highlight_campaign(self.config.get('campaign_name'))

	def load_campaigns(self):
		"""Load campaigns from the remote server and populate the :py:class:`Gtk.TreeView`."""
		store = self._tv_model
		store.clear()
		style_context = self.dialog.get_style_context()
		bg_color = gui_utilities.gtk_style_context_get_color(style_context, 'theme_color_tv_bg', default=ColorHexCode.WHITE)
		fg_color = gui_utilities.gtk_style_context_get_color(style_context, 'theme_color_tv_fg', default=ColorHexCode.BLACK)
		hlbg_color = gui_utilities.gtk_style_context_get_color(style_context, 'theme_color_tv_hlbg', default=ColorHexCode.LIGHT_YELLOW)
		hlfg_color = gui_utilities.gtk_style_context_get_color(style_context, 'theme_color_tv_hlfg', default=ColorHexCode.BLACK)
		now = datetime.datetime.now()
		for campaign in self.application.rpc.remote_table('campaigns'):
			company = campaign.company
			if company:
				company = company.name
			created_ts = utilities.datetime_utc_to_local(campaign.created)
			created_ts = utilities.format_datetime(created_ts)
			campaign_type = campaign.campaign_type
			if campaign_type:
				campaign_type = campaign_type.name
			expiration_ts = campaign.expiration
			is_expired = False
			if expiration_ts is not None:
				expiration_ts = utilities.datetime_utc_to_local(campaign.expiration)
				if expiration_ts < now:
					is_expired = True
				expiration_ts = utilities.format_datetime(expiration_ts)
			store.append((
				str(campaign.id),
				campaign.name,
				company,
				campaign_type,
				campaign.user_id,
				created_ts,
				expiration_ts,
				(hlbg_color if is_expired else bg_color),
				(hlfg_color if is_expired else fg_color),
				(html.escape(campaign.description, quote=True) if campaign.description else None)
			))
		self.gobjects['label_campaign_info'].set_text("Showing {0} of {1:,} Campaign{2}".format(
			len(self._tv_model_filter),
			len(self._tv_model),
			('' if len(self._tv_model) == 1 else 's')
		))

	def signal_assistant_destroy(self, _, campaign_creation_assistant):
		self._creation_assistant = None
		campaign_name = campaign_creation_assistant.campaign_name
		if not campaign_name:
			return
		self.load_campaigns()
		self._highlight_campaign(campaign_name)

	def signal_button_clicked(self, button):
		if self._creation_assistant is not None:
			gui_utilities.show_dialog_warning('Campaign Creation Assistant', self.dialog, 'The campaign creation assistant is already active.')
			return
		assistant = CampaignAssistant(self.application)
		assistant.assistant.set_transient_for(self.dialog)
		assistant.assistant.set_modal(True)
		assistant.assistant.connect('destroy', self.signal_assistant_destroy, assistant)
		assistant.interact()
		self._creation_assistant = assistant

	def signal_checkbutton_toggled(self, _):
		self._tv_model_filter.refilter()
		self.gobjects['label_campaign_info'].set_text("Showing {0} of {1:,} Campaign{2}".format(
			len(self._tv_model_filter),
			len(self._tv_model),
			('' if len(self._tv_model) == 1 else 's')
		))

	def signal_drawingarea_draw(self, drawingarea, context):
		width, height = drawingarea.get_size_request()
		context.rectangle(0, 0, width, height)
		context.stroke_preserve()
		style_context = self.dialog.get_style_context()
		hlbg_color = gui_utilities.gtk_style_context_get_color(style_context, 'theme_color_tv_hlbg', default=ColorHexCode.LIGHT_YELLOW)
		context.set_source_rgb(hlbg_color.red, hlbg_color.green, hlbg_color.blue)
		context.fill()

	def signal_treeview_row_activated(self, treeview, treeview_column, treepath):
		self.gobjects['button_select'].emit('clicked')

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
				self.application.emit('campaign-set', campaign_id)
		self.dialog.destroy()
		return response
