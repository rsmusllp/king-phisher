#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  king_phisher/client/windows/rpc_terminal.py
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


import logging
import os
import signal
import sys
import datetime

from king_phisher import its
from king_phisher import utilities
from king_phisher.constants import ColorHexCode
from king_phisher.client.assistants import CampaignAssistant
from king_phisher.client import gui_utilities
from king_phisher.client.widget import managers
from king_phisher.client.graphs import CampaignCompGraph

from gi.repository import GLib
from gi.repository import Gtk
from gi.repository import Gdk


if its.py_v2:
	import cgi as html
else:
	import html

class CampaignCompWindow(gui_utilities.GladeGObject):
	dependencies = gui_utilities.GladeDependencies(
		children=(
			'notebook_main',
			'box_internal',
			'box_info',
			'label_status',
			'scrolledwindow',
			'label_list',
			'label_graph',
			'treeview_campaigns'
		),

	)
	top_gobject = 'window'
	def __init__(self, *args, **kwargs):
		super(CampaignCompWindow, self).__init__(*args, **kwargs)
		treeview = self.gobjects['treeview_campaigns']
		self.campaigns_enabled = list()
		tvm = managers.TreeViewManager(
			treeview,
			cb_refresh=self.load_campaigns
		)
		toggle_renderer = Gtk.CellRendererToggle()
		toggle_renderer.connect('toggled', self.signal_renderer_toggled)
		b = Gtk.CellRendererText()
		tvm.set_column_titles(
			('Selected', 'Name', 'Company', 'Type', 'Created By', 'Creation Date', 'Expiration'),
			column_offset=1,
			renderers=(toggle_renderer, b, b, b, b, b, b)
		)
		self._model = Gtk.ListStore(str, bool, str, str, str, str, str, str,  Gdk.RGBA, Gdk.RGBA, str)
		self._model.set_sort_column_id(2, Gtk.SortType.DESCENDING)
		treeview.set_model(self._model)
		self.load_campaigns()


		self.window.show()


	def load_campaigns(self):
		"""Load campaigns from the remote server and populate the :py:class:`Gtk.TreeView`."""
		store = self._model
		store.clear()
		style_context = self.window.get_style_context()
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
				False,
				campaign.name,
				company,
				campaign_type,
				campaign.user_id,
				created_ts,
				expiration_ts,
				(bg_color),
				(fg_color),
				(html.escape(campaign.description, quote=True) if campaign.description else None)
			))
		self.gobjects['label_status'].set_text("Showing {0} Campaign{1}".format(
			len(self._model),
			('' if len(self._model) == 1 else 's')
		))

	def signal_renderer_toggled(self, _, path):
		name = self._model[path][2]
		if self._model[path][1]:
			self._model[path][1] = False
			self.campaigns_enabled.remove(name)
		else:
			self._model[path][1] = True
			self.campaigns_enabled.append(name)
		self.init_graph()

	def init_graph(self):
		campaigns = list()
		for campaign in self.application.rpc.remote_table('campaigns'):
			if campaign.name in self.campaigns_enabled:
				campaigns.append(campaign)
		comp_graph = CampaignCompGraph()
		comp_graph.show()
		print campaigns
