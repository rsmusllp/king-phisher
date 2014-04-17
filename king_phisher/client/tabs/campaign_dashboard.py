#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  king_phisher/client/tabs/campaign_dashboard.py
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

import datetime
import time

from king_phisher import utilities
from king_phisher.client import gui_utilities

from gi.repository import Gtk

try:
	import matplotlib
except ImportError:
	has_matplotlib = False
else:
	has_matplotlib = True
	from matplotlib import dates
	from matplotlib import pyplot
	from matplotlib.figure import Figure
	from matplotlib.backends.backend_gtk3agg import FigureCanvasGTK3Agg as FigureCanvas
	from matplotlib.backends.backend_gtk3 import NavigationToolbar2GTK3 as NavigationToolbar

class CampaignViewGraph(object):
	def __init__(self, config, parent):
		self.config = config
		self.parent = parent
		self.figure, ax = pyplot.subplots()
		self.axes = self.figure.get_axes()
		self.canvas = FigureCanvas(self.figure)
		self.canvas.set_size_request(*self.size_request)
		self.canvas.mpl_connect('button_press_event', self.mpl_signal_canvas_button_pressed)
		self.canvas.show()
		self.navigation_toolbar = NavigationToolbar(self.canvas, self.parent)
		self.navigation_toolbar.hide()
		self.popup_menu = Gtk.Menu.new()

		menu_item = Gtk.MenuItem.new_with_label('Export')
		menu_item.connect('activate', self.signal_activate_popup_menu_export)
		self.popup_menu.append(menu_item)

		menu_item = Gtk.MenuItem.new_with_label('Refresh')
		menu_item.connect('activate', lambda action: self.refresh())
		self.popup_menu.append(menu_item)

		menu_item = Gtk.CheckMenuItem.new_with_label('Show Toolbar')
		menu_item.connect('toggled', self.signal_toggled_popup_menu_show_toolbar)
		self.popup_menu.append(menu_item)
		self.popup_menu.show_all()

	def mpl_signal_canvas_button_pressed(self, event):
		if event.button != 3:
			return
		pos_func = lambda m, d: (event.x, event.y, True)
		self.popup_menu.popup(None, None, None, None, event.button, Gtk.get_current_event_time())
		return True

	def signal_activate_popup_menu_export(self, action):
		dialog = gui_utilities.UtilityFileChooser('Export Graph', self.parent)
		file_name = self.config['campaign_name'] + '.png'
		response = dialog.run_quick_save(file_name)
		dialog.destroy()
		if not response:
			return
		destination_file = response['target_filename']
		self.figure.savefig(destination_file, format = 'png')

	def signal_toggled_popup_menu_show_toolbar(self, widget):
		if widget.get_property('active'):
			self.navigation_toolbar.show()
		else:
			self.navigation_toolbar.hide()

class CampaignViewOverviewGraph(CampaignViewGraph):
	size_request = (400, 200)
	def refresh(self):
		rpc = self.parent.rpc
		cid = self.config['campaign_id']
		bars = []
		bars.append(rpc('campaign/messages/count', cid))
		bars.append(rpc('campaign/visits/count', cid))
		bars.append(rpc('campaign/credentials/count', cid))

		width = 0.25
		ax = self.axes[0]
		ax.clear()
		ax.bar(range(len(bars)), bars, width)
		ax.set_ylabel('Grand Total')
		ax.set_title('Campaign Overview')
		ax.set_xticks(map(lambda x: float(x) + (width / 2), range(len(bars))))
		ax.set_xticklabels(('Messages', 'Visits', 'Credentials'))
		self.canvas.draw()

class CampaignViewVisitsTimelineGraph(CampaignViewGraph):
	size_request = (400, 200)
	def refresh(self):
		rpc = self.parent.rpc
		cid = self.config['campaign_id']

		# reads all the visits in for right now...
		visits = list(rpc.remote_table('campaign/visits', cid))
		first_visits = map(lambda visit: datetime.datetime.strptime(visit['first_visit'], '%Y-%m-%d %H:%M:%S'), visits)
		first_visits.sort()

		ax = self.axes[0]
		ax.clear()
		ax.plot_date(first_visits, range(1, len(first_visits) + 1), '-')
		ax.xaxis.set_major_locator(dates.DayLocator())
		ax.xaxis.set_major_formatter(dates.DateFormatter('%Y-%m-%d'))
		ax.xaxis.set_minor_locator(dates.HourLocator())
		ax.autoscale_view()

		ax.fmt_xdata = dates.DateFormatter('%Y-%m-%d')
		self.figure.autofmt_xdate()
		self.canvas.draw()

class CampaignViewDashboardTab(gui_utilities.UtilityGladeGObject):
	gobject_ids = [
		'box_overview',
		'box_visits_timeline',
		'scrolledwindow_overview',
		'scrolledwindow_visits_timeline'
	]
	top_gobject = 'box'
	label_text = 'Dashboard'
	def __init__(self, *args, **kwargs):
		self.label = Gtk.Label(self.label_text)
		super(CampaignViewDashboardTab, self).__init__(*args, **kwargs)
		self.last_load_time = float('-inf')
		self.load_lifetime = utilities.timedef_to_seconds('3s')
		self.graphs = []

		overview_graph = CampaignViewOverviewGraph(self.config, self.parent)
		self.gobjects['scrolledwindow_overview'].add_with_viewport(overview_graph.canvas)
		self.graphs.append(overview_graph)
		self.gobjects['box_overview'].pack_end(overview_graph.navigation_toolbar, False, False, 0)

		visits_timeline_graph = CampaignViewVisitsTimelineGraph(self.config, self.parent)
		self.gobjects['scrolledwindow_visits_timeline'].add_with_viewport(visits_timeline_graph.canvas)
		self.graphs.append(visits_timeline_graph)
		self.gobjects['box_visits_timeline'].pack_end(visits_timeline_graph.navigation_toolbar, False, False, 0)

	def load_campaign_information(self, force = False):
		if not force and ((time.time() - self.last_load_time) < self.load_lifetime):
			return
		if not hasattr(self.parent, 'rpc'):
			self.logger.warning('skipping load_campaign_information because rpc is not initialized')
			return
		self.last_load_time = time.time()
		for graph in self.graphs:
			graph.refresh()
