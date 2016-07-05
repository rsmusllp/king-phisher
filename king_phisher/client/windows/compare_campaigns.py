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

from king_phisher import its
from king_phisher import utilities
from king_phisher.constants import ColorHexCode
from king_phisher.client import gui_utilities
from king_phisher.client.widget import managers
from king_phisher.client.graphs import CampaignCompGraph

from gi.repository import Gtk
from gi.repository import Gdk

class CampaignCompWindow(gui_utilities.GladeGObject):
	"""
	The window which allows the user to select campaigns and compare the data
	using graphical representation.
	"""
	dependencies = gui_utilities.GladeDependencies(
		children=(
			'treeview_campaigns',
			'scrolledwindow',
			'stackswitcher',
			'box_stack',
			'stack_1'
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
		stack_switcher = self.gobjects['stackswitcher']
		stack_switcher.connect('button-release-event', self.show_options)
		self.box_stack = self.gobjects['box_stack']
		self.stack = self.gobjects['stack_1']
		self.signal_ready = False
		b = Gtk.CellRendererText()
		tvm.set_column_titles(
			('Compare', 'Name', 'Company', 'Type', 'Created By', 'Creation Date', 'Expiration'),
			column_offset=1,
			renderers=(toggle_renderer, b, b, b, b, b, b)
		)
		self._model = Gtk.ListStore(str, bool, str, str, str, str, str, str, Gdk.RGBA, Gdk.RGBA, str)
		self._model.set_sort_column_id(2, Gtk.SortType.DESCENDING)
		treeview.set_model(self._model)
		self.load_campaigns()
		self.window.resize(750, 500)
		self.window.show_all()


	def load_campaigns(self):
		"""Load campaigns from the remote server and populate the :py:class:`Gtk.TreeView`."""
		store = self._model
		store.clear()
		style_context = self.window.get_style_context()
		bg_color = gui_utilities.gtk_style_context_get_color(style_context, 'theme_color_tv_bg', default=ColorHexCode.WHITE)
		fg_color = gui_utilities.gtk_style_context_get_color(style_context, 'theme_color_tv_fg', default=ColorHexCode.BLACK)
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
			if expiration_ts is not None:
				expiration_ts = utilities.datetime_utc_to_local(campaign.expiration)
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

	def signal_renderer_toggled(self, _, path):
		name = self._model[path][2]  # pylint: disable=unsubscriptable-object
		if self._model[path][1]:  # pylint: disable=unsubscriptable-object
			self._model[path][1] = False  # pylint: disable=unsubscriptable-object
			self.campaigns_enabled.remove(name)
		else:
			self._model[path][1] = True  # pylint: disable=unsubscriptable-object
			self.campaigns_enabled.append(name)
		self.signal_ready = False
		if len(self.campaigns_enabled) > 1:
			self.signal_ready = True
		self.init_graph()

	def init_graph(self):
		"""
		Initialize the graph instance of campaign comparison upon a
		change in the number and data of campaigns toggled.
		"""
		campaigns = list()
		for campaign in self.application.rpc.remote_table('campaigns'):
			if campaign.name in self.campaigns_enabled:
				campaigns.append(campaign)
		comp_graph = CampaignCompGraph(self.application, style_context=self.application.style_context)
		for i in self.gobjects['scrolledwindow']:
			self.gobjects['scrolledwindow'].remove(i)
		self.gobjects['scrolledwindow'].add(comp_graph._load_graph(campaigns))
		self.window.show_all()

	def show_options(self, _, path):
		"""
		Disables the user from rendering a graph with only one campaign
		selected.
		"""
		if not self.signal_ready:
			self.stack.set_visible_child(self.box_stack)
