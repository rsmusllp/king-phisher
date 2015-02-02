#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  king_phisher/client/dialogs/about.py
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

from king_phisher.client import gui_utilities
from king_phisher import find
from king_phisher import utilities
from king_phisher import version

from gi.repository import GdkPixbuf
from gi.repository import Gtk

__all__ = ['KingPhisherClientAboutDialog']

class KingPhisherClientAboutDialog(gui_utilities.UtilityGladeGObject):
	"""
	Display a :py:class:`Gtk.AboutDialog` with information regarding the King
	Phisher client.
	"""
	top_gobject = 'dialog'
	def __init__(self, *args, **kwargs):
		super(KingPhisherClientAboutDialog, self).__init__(*args, **kwargs)
		logo_file_path = find.find_data_file('king-phisher-icon.svg')
		if logo_file_path:
			logo_pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_size(logo_file_path, 128, 128)
			self.dialog.set_property('logo', logo_pixbuf)
		self.dialog.set_property('version', version.version)
		self.dialog.connect('activate-link', lambda _, url: utilities.open_uri(url))

	def interact(self):
		self.dialog.show_all()
		self.dialog.run()
		self.dialog.destroy()
