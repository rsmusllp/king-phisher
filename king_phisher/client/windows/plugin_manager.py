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

import collections
import copy
import datetime
import errno
import functools
import os
import sys
import traceback

from king_phisher import utilities
from king_phisher.catalog import Catalog
from king_phisher.client import plugins
from king_phisher.client import gui_utilities
from king_phisher.client.widget import managers
from king_phisher.client.windows import html

from gi.repository import Gdk
from gi.repository import Gtk
import requests.exceptions
import smoke_zephyr.requirements
import smoke_zephyr.utilities

__all__ = ('PluginManagerWindow',)

_ROW_TYPE_PLUGIN = 'plugin'
_ROW_TYPE_REPOSITORY = 'repository'
_ROW_TYPE_CATALOG = 'catalog'
_LOCAL_REPOSITORY_ID = 'local'
_LOCAL_REPOSITORY_TITLE = '[Locally Installed]'

_ModelNamedRow = collections.namedtuple('ModelNamedRow', (
	'id',
	'installed',
	'enabled',
	'title',
	'compatibility',
	'version',
	'visible_enabled',
	'visible_installed',
	'sensitive_installed',
	'type'
))

class _ModelNode(object):
	__slots__ = ('children', 'row')
	def __init__(self, *args, **kwargs):
		self.row = _ModelNamedRow(*args, **kwargs)
		self.children = collections.deque()

class PluginDocumentationWindow(html.HTMLWindow):
	"""
	A window for displaying plugin documentation from their respective README.md
	files. If the documentation file can not be found a
	:py:exc:`.FileNotFoundError` exception will be raised on initialization. The
	contents of the README.md file is then rendered as markdown data and
	displayed using an :py:class:`~king_phisher.client.windows.html.HTMLWindow`.
	The plugin must be loaded into the
	:py:attr:`~king_phisher.client.application.KingPhisherClientApplication.plugin_manager`
	but does not have to be enabled for documentation to be displayed.
	"""
	template = 'plugin-documentation.html'
	"""The Jinja2 HTML template to load for hosting the rendered markdown documentation."""
	def __init__(self, application, plugin_id):
		"""
		:param application: The parent application for this object.
		:type application: :py:class:`Gtk.Application`
		:param str plugin_id: The identifier of this plugin.
		"""
		super(PluginDocumentationWindow, self).__init__(application)
		plugin_path = self.application.plugin_manager.get_plugin_path(plugin_id)
		if plugin_path is None:
			raise FileNotFoundError(errno.ENOENT, "could not find the data path for plugin '{0}'".format(plugin_id))
		md_file = os.path.join(plugin_path, 'README.md')
		if md_file is None or not os.path.isfile(md_file):
			self.window.destroy()
			raise FileNotFoundError(errno.ENOENT, "plugin '{0}' has no documentation".format(plugin_id), md_file)
		self._md_file = md_file
		self._plugin = self.application.plugin_manager[plugin_id]
		self.refresh()
		self.webview.connect('key-press-event', self.signal_key_press_event)
		self.webview.connect('open-remote-uri', self.signal_webview_open_remote_uri)
		self.window.set_title('Plugin Documentation')

	def refresh(self):
		"""
		Refresh the contents of the documentation. This will reload both the
		markdown content from README.md as well as the HTML template file.
		"""
		self.webview.load_markdown_file(self._md_file, template=self.template, template_vars={'plugin': self._plugin})

	def signal_webview_open_remote_uri(self, webview, uri, decision):
		utilities.open_uri(uri)

	def signal_key_press_event(self, webview, event):
		if event.type != Gdk.EventType.KEY_PRESS:
			return
		keyval = event.get_keyval()[1]
		if keyval == Gdk.KEY_F5:
			self.refresh()

class PluginManagerWindow(gui_utilities.GladeGObject):
	"""
	The window which allows the user to selectively enable and disable plugins
	for the client application. This also handles configuration changes, so the
	enabled plugins will persist across application runs.
	"""
	dependencies = gui_utilities.GladeDependencies(
		children=(
			'expander_info',
			'grid_catalog_repo_info',
			'grid_plugin_info',
			'label_catalog_repo_info_description',
			'label_catalog_repo_info_for_description',
			'label_catalog_repo_info_for_maintainers',
			'label_catalog_repo_info_homepage',
			'label_catalog_repo_info_maintainers',
			'label_catalog_repo_info_title',
			'label_plugin_info_authors',
			'label_plugin_info_compatible',
			'label_plugin_info_description',
			'label_plugin_info_for_classifiers',
			'label_plugin_info_for_compatible',
			'label_plugin_info_for_references',
			'label_plugin_info_homepage',
			'label_plugin_info_title',
			'label_plugin_info_version',
			'listbox_plugin_info_classifiers',
			'listbox_plugin_info_references',
			'menubutton_plugin_info',
			'paned_plugins',
			'scrolledwindow_plugins',
			'stack_info',
			'treeview_plugins',
			'textview_plugin_info',
			'viewport_info',
			'statusbar'
		)
	)
	top_gobject = 'window'

	def __init__(self, *args, **kwargs):
		super(PluginManagerWindow, self).__init__(*args, **kwargs)
		self.catalog_plugins = plugins.ClientCatalogManager(self.application.user_data_path)
		self.plugin_path = os.path.join(self.application.user_data_path, 'plugins')
		self.status_bar = self.gobjects['statusbar']
		self._installed_plugins_treeview_tracker = None
		"""
		This is used to track and make sure all plugins make it into the
		treeview. It is set each time catalogs are loaded or refreshed. Once the
		loading operation is complete, plugins that remain were not loaded due
		their data (repo or id) missing from the catalog, likely due to it
		having been removed.
		"""
		self._worker_thread = None
		self._worker_thread_start(self._load_catalogs_tsafe)
		self.__load_errors = {}
		self.__installing_plugin = None

		tvm = managers.TreeViewManager(self.gobjects['treeview_plugins'])
		toggle_renderer_enable = Gtk.CellRendererToggle()
		toggle_renderer_enable.connect('toggled', self.signal_renderer_toggled_enable)
		toggle_renderer_install = Gtk.CellRendererToggle()
		toggle_renderer_install.connect('toggled', self.signal_renderer_toggled_install)
		tvm.set_column_titles(
			('Installed', 'Enabled', 'Title', 'Compatible', 'Version'),
			column_offset=1,
			renderers=(
				toggle_renderer_install,
				toggle_renderer_enable,
				Gtk.CellRendererText(),
				Gtk.CellRendererText(),
				Gtk.CellRendererText()
			)
		)
		tvm.column_views['Enabled'].set_cell_data_func(toggle_renderer_enable, self._toggle_enabled_cell_data_func)
		tvm.column_views['Enabled'].add_attribute(toggle_renderer_enable, 'sensitive', 1)
		tvm.column_views['Enabled'].add_attribute(toggle_renderer_enable, 'visible', 6)
		tvm.column_views['Installed'].set_cell_data_func(toggle_renderer_install, self._toggle_install_cell_data_func)
		tvm.column_views['Installed'].add_attribute(toggle_renderer_install, 'visible', 7)
		tvm.column_views['Installed'].add_attribute(toggle_renderer_install, 'sensitive', 8)
		self._model = Gtk.TreeStore(str, bool, bool, str, str, str, bool, bool, bool, str)
		self._model.set_sort_column_id(3, Gtk.SortType.ASCENDING)
		self.gobjects['treeview_plugins'].set_model(self._model)

		self._tv_popup_menu = managers.MenuManager(tvm.get_popup_menu())
		self._tv_popup_menu.append_item(Gtk.SeparatorMenuItem())
		self._tv_popup_menu.append('Reload', self.signal_popup_menu_activate_reload)
		self._tv_popup_menu.append('Reload All', self.signal_popup_menu_activate_reload_all)
		self._tv_popup_menu.append_item(Gtk.SeparatorMenuItem())
		self._tv_popup_menu.append('Show Documentation', self.signal_popup_menu_activate_show_documentation)
		self._tv_popup_menu.append('Update', self.signal_popup_menu_activate_update)

		self._info_popup_menu = managers.MenuManager()
		self._info_popup_menu.append('Reload', self.signal_popup_menu_activate_reload)
		self._info_popup_menu.append_item(Gtk.SeparatorMenuItem())
		self._info_popup_menu.append('Show Documentation', self.signal_popup_menu_activate_show_documentation)
		self._info_popup_menu.append('Update', self.signal_popup_menu_activate_update)
		self.gobjects['menubutton_plugin_info'].set_popup(self._info_popup_menu.menu)

		self._update_status_bar('Loading...')
		self.window.show()
		paned = self.gobjects['paned_plugins']
		self._paned_offset = paned.get_allocation().height - paned.get_position()

	def __store_add_node(self, node, parent=None):
		"""
		Add a :py:class:`._ModelNode` to :py:attr:`._model`, recursively adding
		child :py:class:`._ModelNode` or :py:class:`._ModelNamedRow` instances as
		necessary. This is *not* tsafe.

		:param node: The node to add to the TreeView model.
		:type node: :py:class:`._ModelNode`
		:param parent: An optional parent for the node, used for recursion.
		"""
		row = self._model.append(parent, node.row)
		for child in node.children:
			if isinstance(child, _ModelNode):
				self.__store_add_node(child, parent=row)
			elif isinstance(child, _ModelNamedRow):
				self._model.append(row, child)
			else:
				raise TypeError('unsupported node child type')

	def _add_catalog_to_tree_tsafe(self, catalog):
		"""
		Create a :py:class:`._ModelNode` instance to representing the catalog, its
		data and add it to the TreeView model.

		:param catalog: The catalog to add to the TreeView.
		:type catalog: :py:class:`.Catalog`
		"""
		catalog_node = _ModelNode(
			id=catalog.id,
			installed=None,
			enabled=True,
			title=catalog.id,
			compatibility=None,
			version=None,
			visible_enabled=False,
			visible_installed=False,
			sensitive_installed=False,
			type=_ROW_TYPE_CATALOG
		)
		for repo in catalog.repositories.values():
			repo_node = _ModelNode(
				id=repo.id,
				installed=None,
				enabled=True,
				title=repo.title,
				compatibility=None,
				version=None,
				visible_enabled=False,
				visible_installed=False,
				sensitive_installed=False,
				type=_ROW_TYPE_REPOSITORY
			)
			catalog_node.children.append(repo_node)

			plugin_collection = self.catalog_plugins.get_collection(catalog.id, repo.id)
			for plugin_info in plugin_collection.values():
				installed = False
				enabled = False
				plugin_name = plugin_info['name']
				install_src = self.config['plugins.installed'].get(plugin_name)
				if install_src and repo.id == install_src['repo_id'] and catalog.id == install_src['catalog_id']:
					installed = True
					# plugin was added to treeview so it is removed from the temporary tracking dict
					self._installed_plugins_treeview_tracker.pop(plugin_name)
					enabled = plugin_name in self.config['plugins.enabled']
				repo_node.children.append(_ModelNamedRow(
					id=plugin_name,
					installed=installed,
					enabled=enabled,
					title=plugin_info['title'],
					compatibility='Yes' if self.catalog_plugins.is_compatible(catalog.id, repo.id, plugin_name) else 'No',
					version=plugin_info['version'],
					visible_enabled=True,
					visible_installed=True,
					sensitive_installed=True,
					type=_ROW_TYPE_PLUGIN
				))
		gui_utilities.glib_idle_add_once(self.__store_add_node, catalog_node)

	def _get_plugin_model_parents(self, plugin_model_row):
		return _ModelNamedRow(*plugin_model_row.parent), _ModelNamedRow(*plugin_model_row.parent.parent)

	def _on_plugin_load_error_tsafe(self, name, error):
		# WARNING: this may not be called from the GUI thread
		self.__load_errors[name] = (error, traceback.format_exception(*sys.exc_info(), limit=5))

	def _plugin_disable(self, model_row):
		named_row = _ModelNamedRow(*model_row)
		self.application.plugin_manager.disable(named_row.id)
		self.config['plugins.enabled'].remove(named_row.id)
		self._set_model_item(model_row.path, enabled=False, sensitive_installed=True)

	def _plugin_enable(self, model_row):
		named_row = _ModelNamedRow(*model_row)
		pm = self.application.plugin_manager
		if not pm.loaded_plugins[named_row.id].is_compatible:
			gui_utilities.show_dialog_error('Incompatible Plugin', self.window, 'This plugin is not compatible.')
			return
		if not pm.enable(named_row.id):
			return
		self._set_model_item(model_row.path, enabled=True, sensitive_installed=False)
		self.config['plugins.enabled'].append(named_row.id)

	def _plugin_install(self, model_row):
		if not self._worker_thread_is_ready:
			# check it here to fail fast, then self._worker_thread_start checks it again later
			self._show_dialog_busy()
			return
		named_row = _ModelNamedRow(*model_row)
		repo_model, catalog_model = self._get_plugin_model_parents(model_row)
		if named_row.id in self.config['plugins.installed']:
			plugin_src = self.config['plugins.installed'].get(named_row.id)
			if plugin_src != {'catalog_id': catalog_model.id, 'repo_id': repo_model.id, 'plugin_id': named_row.id}:
				window_question = 'A plugin with this name is already installed from another\nrepository. Do you want to replace it with this one?'
				if not gui_utilities.show_dialog_yes_no('Plugin Already Installed', self.window, window_question):
					return
				if not self._remove_matching_plugin(named_row, plugin_src):
					self.logger.warning("failed to uninstall plugin {0}".format(named_row.id))
					return
		self._worker_thread_start(self._plugin_install_tsafe, catalog_model, repo_model, model_row, named_row)

	def _plugin_install_tsafe(self, catalog_model, repo_model, model_row, named_row):
		self.__installing_plugin = named_row.id
		self.logger.debug("installing plugin '{0}'".format(named_row.id))
		self._update_status_bar_tsafe("Installing plugin {}...".format(named_row.title))
		_show_dialog_error_tsafe = functools.partial(gui_utilities.glib_idle_add_once, gui_utilities.show_dialog_error, 'Failed To Install', self.window)
		try:
			self.catalog_plugins.install_plugin(catalog_model.id, repo_model.id, named_row.id, self.plugin_path)
		except requests.exceptions.ConnectionError:
			self.logger.warning("failed to download plugin {}".format(named_row.id))
			_show_dialog_error_tsafe("Failed to download {} plugin, check your internet connection.".format(named_row.id))
			self._update_status_bar_tsafe("Installing plugin {} failed.".format(named_row.title))
			self.__installing_plugin = None
			return
		except Exception:
			self.logger.warning("failed to install plugin {}".format(named_row.id), exc_info=True)
			_show_dialog_error_tsafe("Failed to install {} plugin.".format(named_row.id))
			self._update_status_bar_tsafe("Installing plugin {} failed.".format(named_row.title))
			self.__installing_plugin = None
			return

		self.config['plugins.installed'][named_row.id] = {'catalog_id': catalog_model.id, 'repo_id': repo_model.id, 'plugin_id': named_row.id}
		self.logger.info("installed plugin '{}' from catalog:{}, repository:{}".format(named_row.id, catalog_model.id, repo_model.id))
		plugin = self._reload_plugin_tsafe(model_row, named_row)
		if self.config['plugins.pip.install_dependencies']:
			try:
				packages = smoke_zephyr.requirements.check_requirements(tuple(plugin.req_packages.keys()))
			except ValueError:
				self.logger.warning("requirements check failed for plugin '{}', can not automatically install requirements".format(named_row.id))
				packages = None
			if packages:
				self.logger.debug("installing missing or incompatible packages from PyPi for plugin '{0}'".format(named_row.id))
				self._update_status_bar_tsafe(
					"Installing {:,} dependenc{} for plugin {} from PyPi.".format(len(packages), 'y' if len(packages) == 1 else 'ies', named_row.title)
				)
				if self.application.plugin_manager.library_path:
					pip_results = self.application.plugin_manager.install_packages(packages)
				else:
					self.logger.warning('no library path to install plugin dependencies')
					_show_dialog_error_tsafe(
						"Failed to run pip to install package(s) for plugin {}.".format(named_row.id)
					)
					# set pip results to none to safely complete and cleanly release installing lock.
					pip_results = None
				if pip_results is None:
					self.logger.warning('pip install failed')
					_show_dialog_error_tsafe(
						"Failed to run pip to install package(s) for plugin {}.".format(named_row.id)
					)
				elif pip_results.status:
					self.logger.warning('pip install failed, exit status: ' + str(pip_results.status))
					_show_dialog_error_tsafe(
						"Failed to install pip package(s) for plugin {}.".format(named_row.id)
					)
				else:
					plugin = self._reload_plugin_tsafe(model_row, named_row)
		self.__installing_plugin = None
		gui_utilities.glib_idle_add_once(self.__plugin_install_post, catalog_model, repo_model, model_row, named_row)

	def __plugin_install_post(self, catalog_model, repo_model, model_row, named_row):
		# handles GUI related updates after data has been fetched from the internet
		if model_row.path is not None:
			version = self.catalog_plugins.get_collection(catalog_model.id, repo_model.id)[named_row.id]['version']
			self._set_model_item(model_row.path, installed=True, version=version)
			if self._selected_model_row.path == model_row.path:
				self._popup_menu_refresh(model_row)
		self._update_status_bar("Finished installing plugin {}.".format(named_row.title))

	def _plugin_uninstall(self, model_row):
		named_row = _ModelNamedRow(*model_row)
		if not self.application.plugin_manager.uninstall(named_row.id):
			return False
		del self.config['plugins.installed'][named_row.id]
		if model_row.parent and model_row.parent[_ModelNamedRow._fields.index('id')] == _LOCAL_REPOSITORY_ID:
			del self._model[model_row.path]
		else:
			self._set_model_item(model_row.path, installed=False)
		self.logger.info("successfully uninstalled plugin {0}".format(named_row.id))
		self._update_status_bar("Finished uninstalling plugin {}.".format(named_row.title))
		return True

	def _popup_menu_refresh(self, model_row):
		named_row = _ModelNamedRow(*model_row)
		sensitive = named_row.type == _ROW_TYPE_PLUGIN and named_row.installed
		self._info_popup_menu['Show Documentation'].set_property('sensitive', sensitive)
		self._tv_popup_menu['Show Documentation'].set_property('sensitive', sensitive)
		sensitive = named_row.type == _ROW_TYPE_PLUGIN and named_row.installed and named_row.sensitive_installed
		self._info_popup_menu['Update'].set_property('sensitive', sensitive)
		self._tv_popup_menu['Update'].set_property('sensitive', sensitive)

	def _reload(self):
		model_row = self._selected_model_row
		named_row = _ModelNamedRow(*model_row)
		if named_row.type == _ROW_TYPE_CATALOG:
			self._worker_thread_start(self._reload_catalog_tsafe, model_row, named_row)
		elif named_row.type == _ROW_TYPE_REPOSITORY:
			# this just reloads the entire parent catalog, individual repositories
			# can not be reloaded at this time
			parent_model_row = model_row.parent
			parent_named_row = _ModelNamedRow(*parent_model_row)
			if parent_named_row.type != _ROW_TYPE_CATALOG:
				self.logger.warning('repository treeview row\'s parent is not a catalog')
				return
			self._worker_thread_start(self._reload_catalog_tsafe, parent_model_row, parent_named_row)
		elif named_row.type == _ROW_TYPE_PLUGIN:
			if not named_row.installed:
				return
			self._worker_thread_start(self._reload_plugin_tsafe, model_row, named_row)
		else:
			self.logger.warning('reload selected for an unsupported row type')

	def _reload_catalog_tsafe(self, model_row, named_row):
		self._update_status_bar_tsafe('Reloading catalog...')
		self._model.remove(model_row.iter)
		if named_row.id == _LOCAL_REPOSITORY_ID:
			self._load_catalog_local_tsafe()
		else:
			catalog_url = self.catalog_plugins.get_cache().get_catalog_by_id(named_row.id)['url']
			if catalog_url:
				self._load_catalog_from_url_tsafe(catalog_url)
		self._update_status_bar_tsafe('Reloading catalog... completed.')

	def _reload_plugin_tsafe(self, model_row, named_row, enabled=None):
		self._update_status_bar_tsafe('Reloading plugin...')
		pm = self.application.plugin_manager
		if enabled is None:
			enabled = named_row.id in pm.enabled_plugins
		pm.unload(named_row.id)
		try:
			klass = pm.load(named_row.id, reload_module=True)
		except Exception as error:
			self._on_plugin_load_error_tsafe(named_row.id, error)
			klass = None
		else:
			if enabled:
				pm.enable(named_row.id)
			self.__load_errors.pop(named_row.id, None)
		gui_utilities.glib_idle_add_once(self.__reload_plugin_post, model_row, named_row, klass)
		return klass

	def __reload_plugin_post(self, model_row, named_row, klass=None):
		if model_row.path is not None:
			if named_row.id == self._selected_named_row.id:
				self._set_info(model_row)
			if klass is None:
				self._set_model_item(model_row.path, title="{0} (Reload Failed)".format(named_row.id))
			else:
				self._set_model_item(
					model_row.path,
					title=klass.title,
					compatibility='Yes' if klass.is_compatible else 'No',
					version=klass.version
				)
		self._update_status_bar('Reloading plugin... completed.')

	def _remove_matching_plugin(self, named_row, plugin_src):
		repo_model = None
		for catalog_model in self._model:
			catalog_id = _ModelNamedRow(*catalog_model).id
			if plugin_src and catalog_id == plugin_src['catalog_id']:
				repo_model = next((rm for rm in catalog_model.iterchildren() if _ModelNamedRow(*rm).id == plugin_src['repo_id']), None)
				break
			elif plugin_src is None and catalog_id == _LOCAL_REPOSITORY_ID:
				# local installation acts as a pseudo-repository
				repo_model = catalog_model
				break
		if not repo_model:
			return False
		for plugin_model_row in repo_model.iterchildren():
			named_model = _ModelNamedRow(*plugin_model_row)
			if named_model.id != named_row.id:
				continue
			if named_model.enabled:
				self._plugin_disable(plugin_model_row)
			self._plugin_uninstall(plugin_model_row)
			return True
		return False

	@property
	def _selected_model_row(self):
		treeview = self.gobjects['treeview_plugins']
		selection = treeview.get_selection()
		if not selection.count_selected_rows():
			return None
		(model, tree_paths) = selection.get_selected_rows()
		return model[tree_paths[0]]

	@property
	def _selected_named_row(self):
		model_row = self._selected_model_row
		return _ModelNamedRow(*model_row) if model_row else None

	def _set_model_item(self, model_path, **kwargs):
		model_row = self._model[model_path]
		for key, value in kwargs.items():
			model_row[_ModelNamedRow._fields.index(key)] = value

	def _set_info(self, model_instance):
		named_model = _ModelNamedRow(*model_instance)
		stack = self.gobjects['stack_info']
		textview = self.gobjects['textview_plugin_info']
		buf = textview.get_buffer()
		buf.delete(buf.get_start_iter(), buf.get_end_iter())
		model_id = named_model.id
		if named_model.type == _ROW_TYPE_PLUGIN:
			if model_id in self.__load_errors:
				stack.set_visible_child(textview)
				self._set_info_plugin_error(model_instance)
			else:
				stack.set_visible_child(self.gobjects['grid_plugin_info'])
				self._set_info_plugin(model_instance)
		else:
			self._set_info_nonplugin(model_instance)

	def _set_info_nonplugin(self, model_instance):
		stack = self.gobjects['stack_info']
		stack.set_visible_child(self.gobjects['grid_catalog_repo_info'])
		named_model = _ModelNamedRow(*model_instance)
		obj_catalog = None

		# hide catalog repo labels
		self.gobjects['label_catalog_repo_info_maintainers'].set_property('visible', False)
		self.gobjects['label_catalog_repo_info_for_maintainers'].set_property('visible', False)
		self.gobjects['label_catalog_repo_info_description'].set_property('visible', False)
		self.gobjects['label_catalog_repo_info_for_description'].set_property('visible', False)
		self.gobjects['label_catalog_repo_info_homepage'].set_property('visible', False)

		self.gobjects['label_catalog_repo_info_title'].set_text(named_model.title)
		if not named_model.id:
			return
		if named_model.type == _ROW_TYPE_CATALOG:
			obj = self.catalog_plugins.catalogs.get(named_model.id, None)
			if not obj:
				return
		else:
			obj_catalog = self.catalog_plugins.catalogs.get(_ModelNamedRow(*model_instance.parent).id, None)
			if not obj_catalog:
				return
			obj = self.catalog_plugins.catalogs[_ModelNamedRow(*model_instance.parent).id].repositories[named_model.id]

		maintainers = getattr(obj, 'maintainers', getattr(obj_catalog, 'maintainers', None))
		if maintainers:
			self.gobjects['label_catalog_repo_info_maintainers'].set_text('\n'.join(maintainers))
			self.gobjects['label_catalog_repo_info_maintainers'].set_property('visible', True)
			self.gobjects['label_catalog_repo_info_for_maintainers'].set_property('visible', True)
		if getattr(obj, 'description', None):
			self.gobjects['label_catalog_repo_info_description'].set_text(obj.description)
			self.gobjects['label_catalog_repo_info_description'].set_property('visible', True)
			self.gobjects['label_catalog_repo_info_for_description'].set_property('visible', True)
		if getattr(obj, 'homepage', None) or getattr(obj, 'url', None):
			url = getattr(obj, 'homepage', getattr(obj, 'url', None))
			self.gobjects['label_catalog_repo_info_homepage'].set_markup("<a href=\"{0}\">Homepage</a>".format(url.replace('"', '&quot;')))
			self.gobjects['label_catalog_repo_info_homepage'].set_property('tooltip-text', url)
			self.gobjects['label_catalog_repo_info_homepage'].set_property('visible', True)

	def _set_info_plugin(self, plugin_model):
		named_model = _ModelNamedRow(*plugin_model)
		pm = self.application.plugin_manager
		self._last_plugin_selected = plugin_model
		if named_model.id in pm.loaded_plugins:
			plugin = pm.loaded_plugins[named_model.id].metadata
			is_compatible = plugin['is_compatible']
		else:
			repo_model, catalog_model = self._get_plugin_model_parents(plugin_model)
			plugin = self.catalog_plugins.get_collection(catalog_model.id, repo_model.id)[named_model.id]
			is_compatible = self.catalog_plugins.is_compatible(catalog_model.id, repo_model.id, named_model.id)

		self.gobjects['label_plugin_info_title'].set_text(plugin['title'])
		self.gobjects['label_plugin_info_compatible'].set_text('Yes' if is_compatible else 'No')
		self.gobjects['label_plugin_info_version'].set_text(plugin['version'])
		self.gobjects['label_plugin_info_authors'].set_text('\n'.join(plugin['authors']))
		self.gobjects['label_plugin_info_description'].set_text(plugin['description'])
		self._set_info_plugin_homepage_url(plugin['homepage'])
		self._set_info_plugin_reference_urls(plugin.get('reference_urls', []))
		classifiers = plugin.get('classifiers', [])
		if classifiers:
			self.gobjects['label_plugin_info_for_classifiers'].set_property('visible', True)
			listbox = self.gobjects['listbox_plugin_info_classifiers']
			listbox.set_property('visible', True)
			gui_utilities.gtk_listbox_populate_labels(listbox, classifiers)
		else:
			self.gobjects['label_plugin_info_for_classifiers'].set_property('visible', False)

	def _set_info_plugin_error(self, model_instance):
		id_ = _ModelNamedRow(*model_instance).id
		textview = self.gobjects['textview_plugin_info']
		buf = textview.get_buffer()
		exc, formatted_exc = self.__load_errors[id_]
		buf.insert(buf.get_end_iter(), "{0!r}\n\n".format(exc), -1)
		buf.insert(buf.get_end_iter(), ''.join(formatted_exc), -1)

	def _set_info_plugin_homepage_url(self, url=None):
		label_homepage = self.gobjects['label_plugin_info_homepage']
		if url is None:
			label_homepage.set_property('visible', False)
			return
		label_homepage.set_markup("<a href=\"{0}\">Homepage</a>".format(url.replace('"', '&quot;')))
		label_homepage.set_property('tooltip-text', url)
		label_homepage.set_property('visible', True)

	def _set_info_plugin_reference_urls(self, reference_urls):
		label = self.gobjects['label_plugin_info_for_references']
		listbox = self.gobjects['listbox_plugin_info_references']
		gui_utilities.gtk_widget_destroy_children(listbox)
		if not reference_urls:
			label.set_property('visible', False)
			listbox.set_property('visible', False)
			return
		label.set_property('visible', True)
		listbox.set_property('visible', True)
		gui_utilities.gtk_listbox_populate_urls(listbox, reference_urls, signals={'activate-link': self.signal_label_activate_link})

	def _show_dialog_busy(self):
		gui_utilities.show_dialog_warning('Currently Busy', self.window, 'An operation is already running.')

	def _show_dialog_error_tsafe(self, title, message):
		gui_utilities.glib_idle_add_once(gui_utilities.show_dialog_error, title, self.window, message)

	def _toggle_enabled_cell_data_func(self, column, cell, model, tree_iter, _):
		if model.get_value(tree_iter, 0) in self.__load_errors:
			cell.set_property('inconsistent', True)
		else:
			cell.set_property('inconsistent', False)

	def _toggle_install_cell_data_func(self, column, cell, model, tree_iter, _):
		cell.set_property('inconsistent', model.get_value(tree_iter, 0) == self.__installing_plugin)

	def _update_status_bar(self, string_to_set):
		self.status_bar.pop(0)
		self.status_bar.push(0, string_to_set)

	def _update_status_bar_tsafe(self, string_to_set):
		gui_utilities.glib_idle_add_once(self._update_status_bar, string_to_set)

	def _worker_thread_start(self, target, *args, **kwargs):
		"""
		Start a worker thread. This must only be called from the main GUI thread
		and *target* must be a tsafe method.
		"""
		if not self._worker_thread_is_ready:
			self._show_dialog_busy()
			self.logger.debug('plugin manager worker thread is alive, can not start a new one')
			return False
		self._worker_thread = utilities.Thread(target=target, args=args, kwargs=kwargs)
		self._worker_thread.start()
		return True

	@property
	def _worker_thread_is_ready(self):
		return self._worker_thread is None or not self._worker_thread.is_alive()

	#
	# Catalog Loading Methods
	#
	# Each of these functions loads the catalog and handles add it to the
	# TreeView as necessary.
	#
	def _load_catalogs_tsafe(self, refresh=False):
		self._installed_plugins_treeview_tracker = copy.deepcopy(self.config['plugins.installed'])
		for plugin in list(self._installed_plugins_treeview_tracker.keys()):
			# Remove plugins already found to be locally installed.
			if not self._installed_plugins_treeview_tracker[plugin]:
				self._installed_plugins_treeview_tracker.pop(plugin)
		if refresh:
			gui_utilities.glib_idle_add_once(self._model.clear)
		expiration = datetime.timedelta(seconds=smoke_zephyr.utilities.parse_timespan(self.config.get('cache.age', '4h')))
		self._update_status_bar_tsafe('Loading, catalogs...')
		self._load_catalog_local_tsafe()
		catalog_cache = self.catalog_plugins.get_cache()
		now = datetime.datetime.utcnow()
		for catalog_url in self.config['catalogs']:
			catalog_cache_dict = catalog_cache.get_catalog_by_url(catalog_url)
			if not refresh and catalog_cache_dict and catalog_cache_dict['created'] + expiration > now:
				catalog = self._load_catalog_from_cache_tsafe(catalog_cache_dict)
				if catalog is not None:
					continue
				catalog_cache_dict = None
			self.logger.debug("downloading catalog: {}".format(catalog_url))
			self._update_status_bar_tsafe("Loading, downloading catalog: {}".format(catalog_url))
			catalog = self._load_catalog_from_url_tsafe(catalog_url)
			if catalog is None and catalog_cache_dict is not None:
				self.logger.warning('failing over to loading the catalog from the cache')
				self._load_catalog_from_cache_tsafe(catalog_cache_dict)
		if self._installed_plugins_treeview_tracker:
			self._load_missing_plugins_tsafe()
		self._update_status_bar_tsafe('Loading completed')
		self._installed_plugins_treeview_tracker = None

	def _load_missing_plugins_tsafe(self):
		local_model_row = None
		for plugin in self._installed_plugins_treeview_tracker.keys():
			self.logger.warning("plugin {} was not found in any loaded catalog or repo, moving to locally installed".format(plugin))
			self.config['plugins.installed'][plugin] = None
			self._installed_plugins_treeview_tracker[plugin] = None
		for model_row in self._model:
			if _ModelNamedRow(*model_row).id == _LOCAL_REPOSITORY_ID:
				gui_utilities.glib_idle_add_wait(self._model.remove, model_row.iter)
				break
		else:
			raise RuntimeError('failed to find the local plugin repository')
		self._load_catalog_local_tsafe()

	def _load_catalog_from_cache_tsafe(self, catalog_cache_dict):
		catalog = None
		try:
			catalog = Catalog(catalog_cache_dict['value'])
		except (KeyError, TypeError) as error:
			self.logger.warning("{0} error when trying to add catalog dict to manager".format(error.__class__.__name))
		else:
			self.catalog_plugins.add_catalog(catalog, catalog_url=catalog_cache_dict['url'], cache=False)
			self._add_catalog_to_tree_tsafe(catalog)
		return catalog

	def _load_catalog_from_url_tsafe(self, catalog_url):
		catalog = None
		try:
			catalog = Catalog.from_url(catalog_url)
		except requests.exceptions.ConnectionError:
			self.logger.warning("connection error trying to download catalog url: {}".format(catalog_url))
			self._show_dialog_error_tsafe('Catalog Loading Error', 'Failed to download catalog, check your internet connection.')
		except Exception:
			self.logger.warning('failed to add catalog by url: ' + catalog_url, exc_info=True)
			self._show_dialog_error_tsafe('Catalog Loading Error', 'Failed to add catalog')
		else:
			self.catalog_plugins.add_catalog(catalog, catalog_url=catalog_url, cache=True)
			self._add_catalog_to_tree_tsafe(catalog)
		return catalog

	def _load_catalog_local_tsafe(self):
		"""
		Load the plugins which are available into the treeview to make them
		visible to the user.
		"""
		self.logger.debug('loading the local catalog')
		pm = self.application.plugin_manager
		self.__load_errors = {}
		pm.load_all(on_error=self._on_plugin_load_error_tsafe)
		node = _ModelNode(
			id=_LOCAL_REPOSITORY_ID,
			installed=None,
			enabled=True,
			title=_LOCAL_REPOSITORY_TITLE,
			compatibility=None,
			version=None,
			visible_enabled=False,
			visible_installed=False,
			sensitive_installed=False,
			type=_ROW_TYPE_CATALOG
		)

		for name, plugin in pm.loaded_plugins.items():
			if self.config['plugins.installed'].get(name):
				continue
			self.config['plugins.installed'][name] = None
			node.children.append(_ModelNamedRow(
				id=plugin.name,
				installed=True,
				enabled=plugin.name in pm.enabled_plugins,
				title=plugin.title,
				compatibility='Yes' if plugin.is_compatible else 'No',
				version=plugin.version,
				visible_enabled=True,
				visible_installed=True,
				sensitive_installed=False,
				type=_ROW_TYPE_PLUGIN
			))
		for name in self.__load_errors.keys():
			node.children.append(_ModelNamedRow(
				id=name,
				installed=True,
				enabled=False,
				title="{0} (Load Failed)".format(name),
				compatibility='No',
				version='Unknown',
				visible_enabled=True,
				visible_installed=True,
				sensitive_installed=False,
				type=_ROW_TYPE_PLUGIN
			))
		gui_utilities.glib_idle_add_wait(self.__store_add_node, node)

	#
	# Signal Handlers
	#
	def signal_eventbox_button_press(self, widget, event):
		if not (event.type == Gdk.EventType.BUTTON_PRESS and event.button == Gdk.BUTTON_PRIMARY):
			return
		if not self._last_plugin_selected:
			return
		named_plugin = _ModelNamedRow(*self._last_plugin_selected)
		plugin_id = named_plugin.id
		if plugin_id is None:
			return
		if plugin_id in self.application.plugin_manager:
			klass = self.application.plugin_manager[plugin_id]
			compatibility_details = list(klass.compatibility)
		else:
			repo_model, catalog_model = self._get_plugin_model_parents(self._last_plugin_selected)
			compatibility_details = list(self.catalog_plugins.compatibility(catalog_model.id, repo_model.id, named_plugin.id))

		popover = Gtk.Popover()
		popover.set_relative_to(self.gobjects['label_plugin_info_for_compatible'])
		grid = Gtk.Grid()
		popover.add(grid)
		grid.insert_column(0)
		grid.insert_column(0)
		grid.insert_column(0)
		grid.set_column_spacing(3)

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

	def signal_label_activate_link(self, _, uri):
		utilities.open_uri(uri)

	def signal_paned_button_press_event(self, paned, event):
		return not self.gobjects['expander_info'].get_property('expanded')

	def signal_popup_menu_activate_reload(self, _):
		self._reload()

	def signal_popup_menu_activate_reload_all(self, _):
		self._worker_thread_start(self._load_catalogs_tsafe, refresh=True)

	def signal_popup_menu_activate_show_documentation(self, _):
		named_row = self._selected_named_row
		if named_row is None or named_row.type != _ROW_TYPE_PLUGIN:
			return
		if not named_row.installed:
			gui_utilities.show_dialog_warning('No Documentation', self.window, 'This plugin has no documentation.')
			return
		try:
			PluginDocumentationWindow(self.application, named_row.id)
		except FileNotFoundError as error:
			self.logger.warning(error.strerror)
			gui_utilities.show_dialog_warning('No Documentation', self.window, error.strerror.capitalize() + '.')

	def signal_popup_menu_activate_update(self, _):
		model_row = self._selected_model_row
		named_row = None if model_row is None else _ModelNamedRow(*model_row)
		if named_row is None:
			return
		if not (named_row.type == _ROW_TYPE_PLUGIN and named_row.installed and named_row.sensitive_installed):
			return
		if not self._plugin_uninstall(model_row):
			gui_utilities.show_dialog_error('Update Failed', self.window, 'Failed to uninstall the existing plugin data.')
			return
		self._plugin_install(model_row)

	def signal_renderer_toggled_enable(self, _, path):
		model_row = self._model[path]
		named_row = _ModelNamedRow(*model_row)
		if named_row.type != _ROW_TYPE_PLUGIN:
			return
		if named_row.id not in self.application.plugin_manager.loaded_plugins:
			return

		if named_row.id in self.__load_errors:
			gui_utilities.show_dialog_error('Can Not Enable Plugin', self.window, 'Can not enable a plugin which failed to load.')
			return
		if named_row.enabled:
			self._plugin_disable(model_row)
		else:
			self._plugin_enable(model_row)

	def signal_renderer_toggled_install(self, _, path):
		model_row = self._model[path]
		named_row = _ModelNamedRow(*model_row)
		if named_row.type == _ROW_TYPE_PLUGIN and named_row.installed:
			if named_row.enabled:
				self._plugin_disable(model_row)
			self._plugin_uninstall(model_row)
		else:
			self._plugin_install(model_row)

	def signal_treeview_row_activated(self, treeview, path, column):
		model_row = self._model[path]
		self._set_info(model_row)
		self._popup_menu_refresh(model_row)
