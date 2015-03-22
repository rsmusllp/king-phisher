#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  king_phisher/client/dialogs/page_clone.py
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
from king_phisher.client import web_cloner

from gi.repository import Gtk

__all__ = ['ClonePageDialog']

class ClonePageDialog(gui_utilities.UtilityGladeGObject):
	"""
	Display a dialog for cloning a web page. The logic of the cloning operation
	is provided by the :py:mod:`.web_cloner` module.
	"""
	top_gobject = 'dialog'
	def __init__(self, *args, **kwargs):
		super(ClonePageDialog, self).__init__(*args, **kwargs)
		self.resources = Gtk.ListStore(str, str)
		treeview = self.gtk_builder_get('treeview_resources')
		treeview.set_model(self.resources)
		gui_utilities.gtk_treeview_set_column_names(treeview, ('MIME Type', 'Resource Path'))

	def set_status(self, status_text, spinner_active=False):
		status_label = self.gtk_builder_get('label_status')
		status_label.set_text("Status: {0}".format(status_text))
		status_spinner = self.gtk_builder_get('spinner_status')
		status_spinner.set_property('active', spinner_active)

	def interact(self):
		self.dialog.show_all()
		self.set_status('Waiting')
		while self.dialog.run() == Gtk.ResponseType.APPLY:
			self.set_status('Cloning', spinner_active=True)
			target_url = self.gtk_builder_get('entry_target').get_text()
			if not target_url:
				gui_utilities.show_dialog_error('Missing Information', self.dialog, 'Please set the target URL.')
				self.set_status('Missing Information')
				continue
			dest_dir = self.gtk_builder_get('entry_directory').get_text()
			if not dest_dir:
				gui_utilities.show_dialog_error('Missing Information', self.dialog, 'Please set the destination directory.')
				self.set_status('Missing Information')
				continue
			cloner = web_cloner.WebPageCloner(target_url, dest_dir)
			if not cloner.wait():
				gui_utilities.show_dialog_error('Operation Failed', self.dialog, 'The web page clone operation failed.')
				self.set_status('Failed')
				continue
			for resource, mime_type in cloner.cloned_resources.items():
				if gui_utilities.search_list_store(self.resources, resource, column=1):
					continue
				self.resources.append([mime_type, resource])
			cloner.webview.destroy()
			gui_utilities.gtk_sync()
			self.set_status('Done')
		self.dialog.destroy()

	def signal_entry_dir(self, widget):
		dialog = gui_utilities.UtilityFileChooser('Destination Directory', self.dialog)
		response = dialog.run_quick_select_directory()
		dialog.destroy()
		if response:
			widget.set_text(response['target_path'])
