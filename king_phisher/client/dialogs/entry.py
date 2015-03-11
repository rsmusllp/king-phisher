#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  king_phisher/client/dialogs/entry.py
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

from king_phisher.client import gui_utilities

from gi.repository import Gtk

__all__ = ['KingPhisherClientTextEntryDialog']

class KingPhisherClientTextEntryDialog(gui_utilities.UtilityGladeGObject):
	"""
	Display a :py:class:`Gtk.Dialog` with a simple text entry.
	"""
	top_gobject = 'dialog'
	def __init__(self, *args, **kwargs):
		super(KingPhisherClientTextEntryDialog, self).__init__(*args, **kwargs)
		self.label = self.gtk_builder_get('label')
		self.entry = self.gtk_builder_get('entry')
		button = self.dialog.get_widget_for_response(response_id=Gtk.ResponseType.APPLY)
		button.grab_default()

	@classmethod
	def build_prompt(cls, config, parent, title, label_text, entry_text=None, entry_tooltip_text=None):
		prompt = cls(config, parent)
		prompt.dialog.set_property('title', title)
		prompt.label.set_text(label_text)
		if entry_text:
			prompt.entry.set_text(entry_text)
		if entry_tooltip_text:
			prompt.entry.set_property('tooltip-text', entry_tooltip_text)
		return prompt

	def interact(self):
		self.dialog.show_all()
		response = self.dialog.run()
		entry_text = self.entry.get_text()
		self.dialog.destroy()
		if response != Gtk.ResponseType.APPLY:
			return
		return entry_text
