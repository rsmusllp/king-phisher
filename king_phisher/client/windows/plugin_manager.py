#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  king_phisher/client/windows/plugin_manager.py
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

import sys
import textwrap
import traceback

from king_phisher import utilities
from king_phisher.client import gui_utilities
from king_phisher.client.widget import managers

from gi.repository import Gdk
from gi.repository import Gtk

__all__ = ('PluginManagerWindow',)

class PluginManagerWindow(gui_utilities.GladeGObject):
	"""
	The window which allows the user to selectively enable and disable plugins
	for the client application. This also handles configuration changes, so the
	enabled plugins will persist across application runs.
	"""
	dependencies = gui_utilities.GladeDependencies(
		children=(
			'expander_plugin_info',
			'grid_plugin_info',
			'label_plugin_info_authors',
			'label_plugin_info_for_compatible',
			'label_plugin_info_compatible',
			'label_plugin_info_description',
			'label_plugin_info_homepage',
			'label_plugin_info_title',
			'label_plugin_info_version',
			'scrolledwindow_plugins',
			'stack_plugin_info',
			'treeview_plugins',
			'textview_plugin_info',
			'viewport_plugin_info'
		)
	)
	top_gobject = 'window'
	def __init__(self, *args, **kwargs):
		super(PluginManagerWindow, self).__init__(*args, **kwargs)
		treeview = self.gobjects['treeview_plugins']
		self._last_plugin_selected = None
		self._module_errors = {}
		tvm = managers.TreeViewManager(
			treeview,
			cb_refresh=self.load_plugins
		)
		toggle_renderer = Gtk.CellRendererToggle()
		toggle_renderer.connect('toggled', self.signal_renderer_toggled)
		tvm.set_column_titles(
			('Enabled', 'Plugin'),
			column_offset=1,
			renderers=(toggle_renderer, Gtk.CellRendererText())
		)
		tvm.column_views['Enabled'].set_cell_data_func(toggle_renderer, self._toggle_cell_data_func)
		self._model = Gtk.ListStore(str, bool, str)
		self._model.set_sort_column_id(2, Gtk.SortType.DESCENDING)
		treeview.set_model(self._model)
		self.load_plugins()

		self.popup_menu = tvm.get_popup_menu()
		self.popup_menu.append(Gtk.SeparatorMenuItem())
		menu_item = Gtk.MenuItem.new_with_label('Reload')
		menu_item.connect('activate', self.signal_popup_menu_activate_reload)
		self.popup_menu.append(menu_item)
		self.popup_menu.show_all()

		self.window.show()
		selection = treeview.get_selection()
		selection.unselect_all()

	def _on_plugin_load_error(self, name, error):
		self._module_errors[name] = (error, traceback.format_exception(*sys.exc_info(), limit=5))

	def _toggle_cell_data_func(self, column, cell, model, tree_iter, _):
		if model.get_value(tree_iter, 0) in self._module_errors:
			cell.set_property('inconsistent', True)
		else:
			cell.set_property('inconsistent', False)

	def load_plugins(self):
		"""
		Load the plugins which are available into the treeview to make them
		visible to the user.
		"""
		store = self._model
		store.clear()
		pm = self.application.plugin_manager
		self._module_errors = {}
		pm.load_all(on_error=self._on_plugin_load_error)
		for name, plugin in pm.loaded_plugins.items():
			store.append((
				plugin.name,
				plugin.name in pm.enabled_plugins,
				plugin.title
			))
		for name in self._module_errors.keys():
			store.append((
				name,
				False,
				"{0} (Load Failed)".format(name)
			))

	def signal_label_activate_link(self, _, uri):
		utilities.open_uri(uri)

	def signal_eventbox_button_press(self, widget, event):
		if not (event.type == Gdk.EventType.BUTTON_PRESS and event.button == Gdk.BUTTON_PRIMARY):
			return
		name = self._last_plugin_selected
		if name is None:
			return
		klass = self.application.plugin_manager[name]
		popover = Gtk.Popover()
		popover.set_relative_to(self.gobjects['label_plugin_info_for_compatible'])
		grid = Gtk.Grid()
		popover.add(grid)
		grid.insert_column(0)
		grid.insert_column(0)
		grid.insert_column(0)
		grid.set_column_spacing(3)
		row = 0
		for req in klass.compatibility:
			grid.insert_row(row)
			label = Gtk.Label(req[0])
			label.set_property('halign', Gtk.Align.START)
			grid.attach(label, 0, row, 1, 1)
			label = Gtk.Label(req[1])
			label.set_property('halign', Gtk.Align.START)
			grid.attach(label, 1, row, 1, 1)
			label = Gtk.Label('Yes' if req[2] else 'No')
			label.set_property('halign', Gtk.Align.END)
			grid.attach(label, 2, row, 1, 1)
			row += 1
		if not row:
			popover.destroy()
			return
		popover.show_all()

	def signal_popup_menu_activate_reload(self, _):
		treeview = self.gobjects['treeview_plugins']
		pm = self.application.plugin_manager
		selected_plugin = None
		selection = treeview.get_selection()
		if selection.count_selected_rows():
			(model, tree_paths) = selection.get_selected_rows()
			selected_plugin = model[tree_paths[0]][0]

		for tree_iter in gui_utilities.gtk_treeview_selection_iterate(treeview):
			name = self._model[tree_iter][0]
			enabled = name in pm.enabled_plugins
			pm.unload(name)
			try:
				klass = pm.load(name, reload_module=True)
			except Exception as error:
				self._on_plugin_load_error(name, error)
				if name == selected_plugin:
					self._set_plugin_info(name)
				self._model[tree_iter][2] = "{0} (Reload Failed)".format(name)
				continue
			if name in self._module_errors:
				del self._module_errors[name]
				self._model[tree_iter][2] = klass.title
			if name == selected_plugin:
				self._set_plugin_info(name)
			if enabled:
				pm.enable(name)

	def signal_renderer_toggled(self, _, path):
		pm = self.application.plugin_manager
		name = self._model[path][0]
		if name in self._module_errors:
			gui_utilities.show_dialog_error('Can Not Enable Plugin', self.window, 'Can not enable a plugin which failed to load.')
			return
		if self._model[path][1]:
			pm.disable(name)
			self._model[path][1] = False
			self.config['plugins.enabled'].remove(name)
		else:
			if not pm.loaded_plugins[name].is_compatible:
				gui_utilities.show_dialog_error('Incompatible Plugin', self.window, 'This plugin is not compatible.')
				return
			if not pm.enable(name):
				return
			self._model[path][1] = True
			self.config['plugins.enabled'].append(name)

	def signal_treeview_row_activated(self, treeview, path, column):
		name = self._model[path][0]
		self._set_plugin_info(name)

	def _set_plugin_info(self, name):
		stack = self.gobjects['stack_plugin_info']
		textview = self.gobjects['textview_plugin_info']
		buf = textview.get_buffer()
		buf.delete(buf.get_start_iter(), buf.get_end_iter())
		if name in self._module_errors:
			stack.set_visible_child(textview)
			self._set_plugin_info_error(name)
		else:
			stack.set_visible_child(self.gobjects['grid_plugin_info'])
			self._set_plugin_info_details(name)

	def _set_plugin_info_details(self, name):
		pm = self.application.plugin_manager
		self._last_plugin_selected = name
		klass = pm.loaded_plugins[name]
		self.gobjects['label_plugin_info_title'].set_text(klass.title)
		self.gobjects['label_plugin_info_compatible'].set_text('Yes' if klass.is_compatible else 'No')
		self.gobjects['label_plugin_info_version'].set_text(klass.version)
		self.gobjects['label_plugin_info_authors'].set_text('\n'.join(klass.authors))
		label_homepage = self.gobjects['label_plugin_info_homepage']
		if klass.homepage is None:
			label_homepage.set_property('visible', False)
		else:
			label_homepage.set_markup("<a href=\"{0}\">Homepage</a>".format(klass.homepage))
			label_homepage.set_property('tooltip-text', klass.homepage)
			label_homepage.set_property('visible', True)
		description = klass.description
		if description[0] == '\n':
			description = description[1:]
		description = textwrap.dedent(description)
		description = description.split('\n\n')
		description = [chunk.replace('\n', ' ').strip() for chunk in description]
		description = '\n\n'.join(description)
		self.gobjects['label_plugin_info_description'].set_text(description)

	def _set_plugin_info_error(self, name):
		textview = self.gobjects['textview_plugin_info']
		exc, formatted_exc = self._module_errors[name]
		buf = textview.get_buffer()
		buf.insert_markup(buf.get_end_iter(), "<b>{0}</b>\n\n".format(repr(exc)), -1)
		buf.insert(buf.get_end_iter(), ''.join(formatted_exc), -1)
