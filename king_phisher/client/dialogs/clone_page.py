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

import os

from king_phisher.client import gui_utilities
from king_phisher.client import web_cloner

from gi.repository import Gtk

__all__ = ['ClonePageDialog']

class ClonePageDialog(gui_utilities.GladeGObject):
	"""
	Display a dialog for cloning a web page. The logic of the cloning operation
	is provided by the :py:mod:`.web_cloner` module.
	"""
	gobject_ids = [
		'button_cancel',
		'entry_clone_directory',
		'label_status',
		'spinner_status',
		'treeview_resources'
	]
	top_gobject = 'dialog'
	def __init__(self, *args, **kwargs):
		super(ClonePageDialog, self).__init__(*args, **kwargs)
		self.resources = Gtk.ListStore(str, str, int)
		treeview = self.gobjects['treeview_resources']
		treeview.set_model(self.resources)
		self.treeview_manager = gui_utilities.TreeViewManager(treeview)
		self.treeview_manager.set_column_titles(('Resource Path', 'MIME Type', 'Size'), renderers=(Gtk.CellRendererText(), Gtk.CellRendererText(), gui_utilities.CellRenderTextBytes()))
		self.popup_menu = self.treeview_manager.get_popup_menu()

		self.button_cancel = self.gobjects['button_cancel']
		self.entry_directory = self.gobjects['entry_clone_directory']
		# managed separately to be kept out of the config
		self.entry_target = self.gtk_builder_get('entry_target')
		self.label_status = self.gobjects['label_status']
		self.spinner_status = self.gobjects['spinner_status']

	def set_status(self, status_text, spinner_active=False):
		self.label_status.set_text("Status: {0}".format(status_text))
		self.spinner_status.set_property('visible', spinner_active)
		self.spinner_status.set_property('active', spinner_active)

	def interact(self):
		self.dialog.show_all()
		self.set_status('Waiting')
		if not web_cloner.has_webkit2:
			gui_utilities.show_dialog_error('WebKit2GTK+ Is Unavailable', self.dialog, 'The WebKit2GTK+ package is not available.')
			self.dialog.destroy()
			return
		while self.dialog.run() == Gtk.ResponseType.APPLY:
			target_url = self.entry_target.get_text()
			if not target_url:
				gui_utilities.show_dialog_error('Missing Information', self.dialog, 'Please set the target URL.')
				self.set_status('Missing Information')
				continue
			dest_dir = self.entry_directory.get_text()
			if not dest_dir:
				gui_utilities.show_dialog_error('Missing Information', self.dialog, 'Please set the destination directory.')
				self.set_status('Missing Information')
				continue
			if not os.access(dest_dir, os.W_OK):
				gui_utilities.show_dialog_error('Invalid Directory', self.dialog, 'Can not write to the specified directory.')
				self.set_status('Invalid Directory')
				continue
			self.objects_save_to_config()

			self.set_status('Cloning', spinner_active=True)
			cloner = web_cloner.WebPageCloner(target_url, dest_dir)
			signal_id = self.button_cancel.connect('clicked', lambda _: cloner.stop_cloning())
			original_label = self.button_cancel.get_label()
			self.button_cancel.set_label('Cancel')
			cloner.wait()
			self.button_cancel.set_label(original_label)
			self.button_cancel.disconnect(signal_id)

			if cloner.load_failed:
				self.set_status('Failed')
				gui_utilities.show_dialog_error('Operation Failed', self.dialog, 'The web page clone operation failed.')
				continue
			for resource in cloner.cloned_resources.values():
				if gui_utilities.gtk_list_store_search(self.resources, resource.resource, column=0):
					continue
				self.resources.append([resource.resource, resource.mime_type or 'N/A', resource.size])
			self.set_status('Done')
			gui_utilities.gtk_sync()
		if len(self.resources) and gui_utilities.show_dialog_yes_no('Transfer Cloned Pages', self.dialog, 'Would you like to start the SFTP client\nto upload the cloned pages?'):
			self.application.start_sftp_client()
		self.dialog.destroy()

	def signal_multi_set_directory(self, _):
		dialog = gui_utilities.FileChooser('Destination Directory', self.dialog)
		response = dialog.run_quick_select_directory()
		dialog.destroy()
		if response:
			self.entry_directory.set_text(response['target_path'])
