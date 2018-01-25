#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  king_phisher/client/windows/compare_campaigns.py
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

import os

from king_phisher import find
from king_phisher import utilities
from king_phisher.client import gui_utilities
from king_phisher.client.widget import managers
from king_phisher.client.graphs import CampaignCompGraph

from gi.repository import Gtk

class CampaignCompWindow(gui_utilities.GladeGObject):
	"""
	The window which allows the user to select campaigns and compare the data
	using graphical representation.
	"""
	dependencies = gui_utilities.GladeDependencies(
		children=(
			'treeview_campaigns',
			'scrolledwindow_compare',
			'scrolledwindow_select',
			'stackswitcher',
			'box_compare',
			'box_select',
			'stack_main'
		),
	)
	top_gobject = 'window'
	def __init__(self, *args, **kwargs):
		super(CampaignCompWindow, self).__init__(*args, **kwargs)
		self.comp_graph = CampaignCompGraph(self.application, style_context=self.application.style_context)
		self.gobjects['scrolledwindow_compare'].add(self.comp_graph.canvas)
		self.gobjects['box_compare'].pack_end(self.comp_graph.navigation_toolbar, False, False, 0)
		self.comp_graph.navigation_toolbar.hide()
		treeview = self.gobjects['treeview_campaigns']
		tvm = managers.TreeViewManager(
			treeview,
			cb_refresh=self.load_campaigns
		)
		toggle_renderer = Gtk.CellRendererToggle()
		toggle_renderer.connect('toggled', self.signal_renderer_toggled)
		self.stack = self.gobjects['stack_main']
		self.prev_child = self.stack.get_visible_child()
		b = Gtk.CellRendererText()
		tvm.set_column_titles(
			('Compare', 'Name', 'Company', 'Type', 'Created By', 'Creation Date', 'Expiration'),
			column_offset=1,
			renderers=(toggle_renderer, b, b, b, b, b, b)
		)
		self._model = Gtk.ListStore(str, bool, str, str, str, str, str, str)
		self._model.set_sort_column_id(2, Gtk.SortType.ASCENDING)
		treeview.set_model(self._model)
		self.load_campaigns()
		self.window.show()

	def load_campaigns(self):
		"""Load campaigns from the remote server and populate the :py:class:`Gtk.TreeView`."""
		store = self._model
		store.clear()
		campaigns = self.application.rpc.graphql_file(find.data_file(os.path.join('queries', 'get_campaigns.graphql')))
		for campaign in campaigns['db']['campaigns']['edges']:
			campaign = campaign['node']
			company = campaign['company']['name'] if campaign['company'] else None
			created_ts = utilities.datetime_utc_to_local(campaign['created'])
			created_ts = utilities.format_datetime(created_ts)
			campaign_type = campaign['campaignType']['name'] if campaign['campaignType'] else None
			expiration_ts = campaign['expiration']
			if expiration_ts is not None:
				expiration_ts = utilities.datetime_utc_to_local(expiration_ts)
				expiration_ts = utilities.format_datetime(expiration_ts)
			store.append((
				campaign['id'],
				False,
				campaign['name'],
				company,
				campaign_type,
				campaign['user']['name'],
				created_ts,
				expiration_ts
			))

	def signal_renderer_toggled(self, _, path):
		campaign = self._model[path]  # pylint: disable=unsubscriptable-object
		campaign[1] = not campaign[1]

	def signal_stackswitcher_button_release(self, widget, event):
		view = self.stack.get_visible_child()
		if view == self.gobjects['box_compare'] and self.prev_child == self.gobjects['box_select']:
			campaigns = [campaign for campaign in self._model if campaign[1]]  # pylint: disable=not-an-iterable
			campaigns = sorted(campaigns, key=lambda campaign: campaign[6])
			campaigns = [campaign[0] for campaign in campaigns]
			self.comp_graph.load_graph(campaigns)
		self.prev_child = view
