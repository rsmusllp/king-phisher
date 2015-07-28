#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  king_phisher/client/dialogs/tag_editor.py
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

import functools

from king_phisher.client import gui_utilities
from king_phisher.third_party import AdvancedHTTPServer

from gi.repository import Gtk
from gi.repository import Pango

__all__ = ['TagEditorDialog']

class TagEditorDialog(gui_utilities.GladeGObject):
	"""
	Display a dialog which can be used to edit the various tags that are
	present on the remote server. This can be used to rename tags and modify
	their descriptions.
	"""
	gobject_ids = (
		'notebook',
		'button_close',
		'treeview_campaign_types',
		'treeview_company_departments',
		'treeview_industries'
	)
	top_gobject = 'dialog'
	objects_persist = False
	tag_tables = ('campaign_types', 'company_departments', 'industries')
	def __init__(self, *args, **kwargs):
		super(TagEditorDialog, self).__init__(*args, **kwargs)
		self.popup_menus = {}
		self.treeview_managers = {}
		for tag_table in self.tag_tables:
			treeview = self.gobjects['treeview_' + tag_table]
			model = Gtk.ListStore(int, str, str)
			treeview.set_model(model)
			tvm = gui_utilities.TreeViewManager(
				treeview,
				cb_delete=functools.partial(self.delete_tag, tag_table),
				cb_refresh=functools.partial(self.load_tags, tag_table)
			)
			name_renderer = Gtk.CellRendererText()
			name_renderer.connect('edited', self.signal_renderer_edited, (tag_table, 1, 'name'))
			name_renderer.set_property('editable', True)
			description_renderer = Gtk.CellRendererText()
			description_renderer.connect('edited', self.signal_renderer_edited, (tag_table, 2, 'description'))
			description_renderer.set_property('editable', True)
			description_renderer.set_property('ellipsize', Pango.EllipsizeMode.END)
			tvm.set_column_titles(
				('Name', 'Description'),
				column_offset=1,
				renderers=(name_renderer, description_renderer)
			)
			self.treeview_managers[tag_table] = tvm
			self.popup_menus[tag_table] = tvm.get_popup_menu()
		self.load_tags()

	def delete_tag(self, tag_table, treeview, selection):
		(model, tree_iter) = selection.get_selected()
		if not tree_iter:
			return
		tag_id = model.get_value(tree_iter, 0)
		if not gui_utilities.show_dialog_yes_no('Delete This Tag?', self.dialog, 'This action is irreversible.'):
			return
		self.application.rpc('db/table/delete', tag_table, tag_id)
		self.load_tags(tag_table)

	def load_tags(self, tags=None):
		if tags is None:
			tags = self.tag_tables
		elif isinstance(tags, str):
			tags = (tags,)
		for tag in tags:
			model = self.gobjects['treeview_' + tag].get_model()
			model.clear()
			for tag in self.application.rpc.remote_table(tag):
				model.append((tag.id, tag.name, tag.description))

	def interact(self):
		self.dialog.show_all()
		self.dialog.run()
		self.dialog.destroy()

	def signal_renderer_edited(self, cell, path, property_value, details):
		tag_table, store_id, property_name = details
		model = self.gobjects['treeview_' + tag_table].get_model()
		model_iter = model.get_iter(path)
		tag_id = model.get_value(model_iter, 0)

		try:
			self.application.rpc('db/table/set', tag_table, tag_id, (property_name,), (property_value,))
		except AdvancedHTTPServer.AdvancedHTTPServerRPCError:
			gui_utilities.show_dialog_error('Failed To Modify', self.dialog, 'An error occurred while modifying the information.')
		else:
			model.set_value(model_iter, store_id, property_value)
