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
import os
import traceback

from king_phisher import utilities
from king_phisher.client import gui_utilities
from king_phisher.client.widget import managers
from king_phisher.client.plugins import PluginCatalogManager

from gi.repository import Gdk
from gi.repository import Gtk
from gi.repository import GLib

__all__ = ('PluginManagerWindow',)

DEFAULT_PLUGIN_PATH = os.path.join(GLib.get_user_config_dir(), 'king-phisher', 'plugins')

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
			'paned_plugins',
			'scrolledwindow_plugins',
			'stack_plugin_info',
			'treeview_plugins',
			'textview_plugin_info',
			'viewport_plugin_info',
			'statusbar'
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
		toggle_renderer_enable = Gtk.CellRendererToggle()
		toggle_renderer_enable.connect('toggled', self.signal_renderer_toggled_enable)
		toggle_renderer_install = Gtk.CellRendererToggle()
		toggle_renderer_install.connect('toggled', self.signal_renderer_toggled_install)
		tvm.set_column_titles(
			['Enabled', 'Installed', 'Type', 'Title', 'Compatible', 'Version'],
			column_offset=1,
			renderers=[
				toggle_renderer_enable,
				toggle_renderer_install,
				Gtk.CellRendererText(),
				Gtk.CellRendererText(),
				Gtk.CellRendererText(),
				Gtk.CellRendererText()
			]
		)
		tvm.column_views['Enabled'].set_cell_data_func(toggle_renderer_enable, self._toggle_cell_data_func)
		tvm.column_views['Enabled'].add_attribute(toggle_renderer_enable, 'visible', 7)
		tvm.column_views['Installed'].add_attribute(toggle_renderer_install, 'visible', 8)
		self._model = Gtk.TreeStore(str, bool, bool, str, str, str, str, bool, bool)
		self._model.set_sort_column_id(2, Gtk.SortType.ASCENDING)
		treeview.set_model(self._model)

		#GLib.idle_add(self.gobjects['statusbar'].push, (0, 'Loading....'))

		self.catalog_plugins = PluginCatalogManager('client', 'https://raw.githubusercontent.com/securestate/king-phisher-plugins/dev/catalog.json')
		self.load_plugins()

		self.popup_menu = tvm.get_popup_menu()
		self.popup_menu.append(Gtk.SeparatorMenuItem())
		menu_item = Gtk.MenuItem.new_with_label('Reload')
		menu_item.connect('activate', self.signal_popup_menu_activate_reload)
		self.popup_menu.append(menu_item)
		menu_item_reload_all = Gtk.MenuItem.new_with_label('Reload All')
		menu_item_reload_all.connect('activate', self.signal_popup_menu_activate_relaod_all)
		self.popup_menu.append(menu_item_reload_all)
		self.popup_menu.show_all()

		self.window.show()
		selection = treeview.get_selection()
		selection.unselect_all()
		paned = self.gobjects['paned_plugins']
		self._paned_offset = paned.get_allocation().height - paned.get_position()

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
		#(parent (name, bool of check box, installed, type_name column, title column, compatible, version, bool if checkbox is visible))
		for name, plugin in pm.loaded_plugins.items():
			if plugin.name in self.config['plugins.installed']:
				continue
			store.append(None, (
				plugin.name,
				plugin.name in pm.enabled_plugins,
				True,
				'Plugin',
				plugin.title,
				'Yes' if plugin.is_compatible else 'No',
				plugin.version,
				True,
				False
			))
		for catalogs in self.catalog_plugins.catalog_ids():
			catalog = store.append(None, (catalogs, True, None, 'Catalog', catalogs, None, None, False, False))
			for repos in self.catalog_plugins.get_repos(catalogs):
				repo = store.append(catalog, (repos.id, True, None, 'Repository', repos.title, None, None, False, False))
				plugin_collections = self.catalog_plugins.get_collection(catalogs, repos.id)
				client_plugins = list(plugin_collections)
				client_plugins.sort()
				for plugins in client_plugins:
					installed = False
					enabled = False
					if plugin_collections[plugins]['name'] in self.config['plugins.installed']:
						if repos.id == self.config['plugins.installed'][plugin_collections[plugins]['name']][1]:
							installed = True
							enabled = True if plugin_collections[plugins]['name'] in self.config['plugins.enabled'] else False
					store.append(repo, (
						plugin_collections[plugins]['name'],
						enabled,
						installed,
						'Plugin',
						plugin_collections[plugins]['title'],
						'Unknown',
						'N/A',
						True,
						True
					))
		for name in self._module_errors.keys():
			store.append((
				name,
				False,
				"{0} (Load Failed)".format(name)
			))
		#GLib.idle_add(self.gobjects['statusbar'].pop, 0)
		#GLib.idle_add(self.gobjects['statusbar'].push, (0, 'Finished loading'))

	def signal_popup_menu_activate_relaod_all(self, _):
		self.load_plugins()

	def signal_treeview_row_activated(self, treeview, path, column):
		self._set_plugin_info(self._model[path])

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

		compatibility_details = list(klass.compatibility)
		compatibility_details.insert(0, ('Type', 'Value', 'Met'))
		row = 0
		for row, req in enumerate(compatibility_details):
			grid.insert_row(row)
			label = Gtk.Label(req[0])
			label.set_property('halign', Gtk.Align.START)
			grid.attach(label, 0, row, 1, 1)
			label = Gtk.Label(req[1])
			label.set_property('halign', Gtk.Align.START)
			grid.attach(label, 1, row, 1, 1)
			label = Gtk.Label(('Yes' if req[2] else 'No') if row else req[2])
			label.set_property('halign', Gtk.Align.END)
			grid.attach(label, 2, row, 1, 1)
		if not row:
			popover.destroy()
			return
		popover.show_all()

	def signal_expander_activate(self, expander):
		paned = self.gobjects['paned_plugins']
		if expander.get_property('expanded'):  # collapsing
			paned.set_position(paned.get_allocation().height + self._paned_offset)

	def signal_paned_button_press_event(self, paned, event):
		return not self.gobjects['expander_plugin_info'].get_property('expanded')

	def signal_popup_menu_activate_reload(self, _):
		treeview = self.gobjects['treeview_plugins']
		pm = self.application.plugin_manager
		selected_plugin = None
		selection = treeview.get_selection()
		if selection.count_selected_rows():
			(model, tree_paths) = selection.get_selected_rows()
			selected_plugin = model[tree_paths[0]][0]

		for tree_iter in gui_utilities.gtk_treeview_selection_iterate(treeview):
			name = self._model[tree_iter][0]  # pylint: disable=unsubscriptable-object
			enabled = name in pm.enabled_plugins
			pm.unload(name)
			try:
				klass = pm.load(name, reload_module=True)
			except Exception as error:
				self._on_plugin_load_error(name, error)
				if name == selected_plugin:
					self._set_plugin_info(name)
				self._model[tree_iter][2] = "{0} (Reload Failed)".format(name)  # pylint: disable=unsubscriptable-object
				continue
			if name in self._module_errors:
				del self._module_errors[name]
			self._model[tree_iter][2] = klass.title  # pylint: disable=unsubscriptable-object
			if name == selected_plugin:
				self._set_plugin_info(name)
			if enabled:
				pm.enable(name)

	def signal_renderer_toggled_enable(self, _, path):
		pm = self.application.plugin_manager
		if self._model[path][3] != 'Plugin':
			return
		plugin_model = self._model[path]
		name = self._model[path][0]  # pylint: disable=unsubscriptable-object
		if name not in pm.loaded_plugins:
			return
		if name in self.config['plugins.installed']:
			installed_plugin_info = self.config['plugins.installed'][name]
			model_repo, model_cat = self._get_plugin_model_parents(self._model[path])
			if model_repo[0] != installed_plugin_info[1] or model_cat[0] != installed_plugin_info[0]:
				return
		if name in self._module_errors:
			gui_utilities.show_dialog_error('Can Not Enable Plugin', self.window, 'Can not enable a plugin which failed to load.')
			return
		if self._model[path][1]:  # pylint: disable=unsubscriptable-object
			self._disable_plugin(plugin_model)
		else:
			if not pm.loaded_plugins[name].is_compatible:
				gui_utilities.show_dialog_error('Incompatible Plugin', self.window, 'This plugin is not compatible.')
				return
			if not pm.enable(name):
				return
			self._model[path][1] = True # pylint: disable=unsubscriptable-object
			self.config['plugins.enabled'].append(name)

	def signal_renderer_toggled_install(self, _, path):
		plugin_model = self._model[path]
		repo_model, catalog_model = self._get_plugin_model_parents(plugin_model)
		plugin_collection = self.catalog_plugins.get_collection(catalog_model[0], repo_model[0])
		if plugin_model[2]:
			if plugin_model[1]:
				response = gui_utilities.show_dialog_yes_no(
					'Plugin is enabled',
					self.window,
					"This will disable the plugin, do you wish to continue?"
				)
				if not response:
					return
				self._disable_plugin(plugin_model)
			self.application.plugin_manager.unload(plugin_model[0])
			self._uninstall_plugin(plugin_collection, plugin_model)
			self.logger.info("uninstalled plugin {}".format(plugin_model[0]))
		else:
			if plugin_model[0] in self.config['plugins.installed']:
				installed_plugin_info = self.config['plugins.installed'][plugin_model[0]]
				if installed_plugin_info != [catalog_model[0], repo_model[0]]:
					response = gui_utilities.show_dialog_yes_no(
						'Plugin installed from another source',
						self.window,
						"A plugin with this name is already installed from Catalog: {} Repo: {}\nDo you want to replace it with this one?".format(installed_plugin_info[0], installed_plugin_info[1])
					)
					if not response:
						return
					if not self._remove_matching_plugin(plugin_model[0], installed_plugin_info):
						self.logger.warning('failed to uninstall plugin {}'.format(plugin_model[0]))
						return
			self.catalog_plugins.install_plugin(catalog_model[0], repo_model[0], plugin_model[0], DEFAULT_PLUGIN_PATH)
			self.config['plugins.installed'][plugin_model[0]] = [catalog_model[0], repo_model[0]]
			plugin_model[2] = True
			self.logger.info("installed plugin {} from catalog {}, repository {}".format(plugin_model[0], catalog_model[0], repo_model[0]))
		self.application.plugin_manager.load_all(on_error=self._on_plugin_load_error)

	def _disable_plugin(self, plugin_model):
		self.application.plugin_manager.disable(plugin_model[0])
		self.config['plugins.enabled'].remove(plugin_model[0])
		plugin_model[1] = False

	def _remove_matching_plugin(self, plugin_name, installed_plugin_info):
		for catalog_model in self._model:
			if catalog_model[0] != installed_plugin_info[0]:
				continue
			for repo_model in catalog_model.iterchildren():
				if repo_model[0] != installed_plugin_info[1]:
					continue
				for plugin_model in repo_model.iterchildren():
					if plugin_model[0] != plugin_name:
						continue
					if plugin_model[1]:
						self._disable_plugin(plugin_model)
					self._uninstall_plugin(self.catalog_plugins.get_collection(installed_plugin_info[0], installed_plugin_info[1]), plugin_model)
					return True

	def _get_plugin_model_parents(self, plugin_model):
		return plugin_model.parent, plugin_model.parent.parent

	def _uninstall_plugin(self, plugin_collection, plugin_model):
		for files in plugin_collection[plugin_model[0]]['files']:
			file_name = files[0]
			if os.path.isfile(os.path.join(DEFAULT_PLUGIN_PATH, file_name)):
				os.remove(os.path.join(DEFAULT_PLUGIN_PATH, file_name))
		del self.config['plugins.installed'][plugin_model[0]]
		plugin_model[2] = False

	def _set_plugin_info(self, model_instance):
		stack = self.gobjects['stack_plugin_info']
		textview = self.gobjects['textview_plugin_info']
		buf = textview.get_buffer()
		buf.delete(buf.get_start_iter(), buf.get_end_iter())
		name = model_instance[0]
		if model_instance[3] != 'Plugin':
			stack.set_visible_child(textview)
			self._set_non_plugin_info(model_instance)
			return
		if name in self._module_errors:
			stack.set_visible_child(textview)
			self._set_plugin_info_error(name)
		else:
			stack.set_visible_child(self.gobjects['grid_plugin_info'])
			self._set_plugin_info_details(model_instance)

	def _set_non_plugin_info(self, model_instance):
		textview = self.gobjects['textview_plugin_info']
		buf = textview.get_buffer()
		text = ''
		if model_instance[3] == 'Catalog':
			instance_information = self.catalog_plugins.catalogs[model_instance[0]]
		else:
			instance_information = self.catalog_plugins.get_repo(model_instance.parent[0], model_instance[0])

		if 'title' in dir(instance_information):
			text += "Repository: {}\n".format(instance_information.title if instance_information.title else instance_information.id)
		else:
			text += "Catalog: {}\n".format(instance_information.id)

		if 'maintainers' in dir(instance_information):
			if instance_information.maintainers:
				text += 'maintainer: ' + '\nmaintainer: '.join(instance_information.maintainers) + '\n'

		if 'description' in dir(instance_information):
			if instance_information.description:
				text += instance_information.description + '\n'

		buf.insert(buf.get_end_iter(), "{0}\n".format(text), -1)

	def _set_plugin_info_details(self, plugin_model):
		name = plugin_model[0]
		pm = self.application.plugin_manager
		self._last_plugin_selected = name
		if name in pm.loaded_plugins:
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
			self.gobjects['label_plugin_info_description'].set_text(klass.description)
		else:
			repo_model, catalog_model = self._get_plugin_model_parents(plugin_model)
			for repo in self.catalog_plugins.get_repos(catalog_model[0]):
				if repo.id != repo_model[0]:
					continue
				plugin = repo.collections['plugins/client'][plugin_model[0]]
				self.gobjects['label_plugin_info_title'].set_text(plugin['title'])
				self.gobjects['label_plugin_info_compatible'].set_text('Fix ME Please') #fix me
				self.gobjects['label_plugin_info_version'].set_text(plugin['version'])
				self.gobjects['label_plugin_info_authors'].set_text('\n'.join(plugin['authors']))
				label_homepage = self.gobjects['label_plugin_info_homepage']
				if plugin['homepage'] is None:
					label_homepage.set_property('visible', False)
				else:
					label_homepage.set_markup("<a href=\"{0}\">Homepage</a>".format(plugin['homepage']))
					label_homepage.set_property('tooltip-text', plugin['homepage'])
					label_homepage.set_property('visible', True)
				self.gobjects['label_plugin_info_description'].set_text(plugin['description'])

	def _set_plugin_info_error(self, model_instance):
		name = model_instance[0]
		textview = self.gobjects['textview_plugin_info']
		buf = textview.get_buffer()
		exc, formatted_exc = self._module_errors[name]
		buf.insert(buf.get_end_iter(), "{0!r}\n\n".format(exc), -1)
		buf.insert(buf.get_end_iter(), ''.join(formatted_exc), -1)
