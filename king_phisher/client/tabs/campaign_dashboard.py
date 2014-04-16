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
	from matplotlib import pyplot
	from matplotlib.figure import Figure
	from matplotlib.backends.backend_gtk3agg import FigureCanvasGTK3Agg as FigureCanvas

class CampaignViewDashboardTab(gui_utilities.UtilityGladeGObject):
	top_gobject = 'box'
	label_text = 'Dashboard'
	def __init__(self, *args, **kwargs):
		self.label = Gtk.Label(self.label_text)
		super(CampaignViewDashboardTab, self).__init__(*args, **kwargs)
		self.last_load_time = float('-inf')
		self.load_lifetime = utilities.timedef_to_seconds('3s')
		self.box.show_all()

		self.figure, ax = pyplot.subplots()
		self.canvas = FigureCanvas(self.figure)
		self.canvas.show()
		self.box.pack_start(self.canvas, True, True, 0)

	def load_campaign_information(self, force = False):
		if not force and ((time.time() - self.last_load_time) < self.load_lifetime):
			return
		self.last_load_time = time.time()
		rpc = self.parent.rpc
		cid = self.config['campaign_id']
		bars = []
		bars.append(rpc('campaign/messages/count', cid))
		bars.append(rpc('campaign/visits/count', cid))
		bars.append(rpc('campaign/credentials/count', cid))

		width = 0.25
		ax = self.figure.get_axes()[0]
		ax.clear()
		ax.bar(range(len(bars)), bars, width)
		ax.set_ylabel('Grand Total')
		ax.set_title('Campaign Overview')
		ax.set_xticks(map(lambda x: float(x) + (width / 2), range(len(bars))))
		ax.set_xticklabels(('Messages', 'Visits', 'Credentials'))

		self.canvas.draw()
