#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  king_phisher/client/tabs/campaign.py
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

import datetime
import logging
import threading
import time

from king_phisher import errors
from king_phisher import find
from king_phisher import ipaddress
from king_phisher import utilities
from king_phisher.client import export
from king_phisher.client import graphs
from king_phisher.client import gui_utilities
from king_phisher.client.widget import extras
from king_phisher.client.widget import managers

import advancedhttpserver
from gi.repository import GdkPixbuf
from gi.repository import GLib
from gi.repository import Gtk
import rule_engine
from smoke_zephyr.utilities import parse_timespan

UNKNOWN_LOCATION_STRING = 'N/A (Unknown)'

class CampaignViewGenericTab(gui_utilities.GladeGObject):
	"""
	This object is meant to be subclassed by all of the tabs which load and
	display information about the current campaign.
	"""
	label_text = 'Unknown'
	"""The label of the tab for display in the GUI."""
	top_gobject = 'box'
	def __init__(self, *args, **kwargs):
		super(CampaignViewGenericTab, self).__init__(*args, **kwargs)
		self.label = Gtk.Label(label=self.label_text)
		"""The :py:class:`Gtk.Label` representing this tab with text from :py:attr:`~.CampaignViewGenericTab.label_text`."""
		self.is_destroyed = threading.Event()
		getattr(self, self.top_gobject).connect('destroy', self.signal_destroy)

		self.last_load_time = float('-inf')
		"""The last time the data was loaded from the server."""
		self.refresh_frequency = parse_timespan(str(self.config.get('gui.refresh_frequency', '5m')))
		"""The lifetime in seconds to wait before refreshing the data from the server."""
		self.loader_thread = None
		"""The thread object which loads the data from the server."""
		self.loader_thread_lock = threading.Lock()
		"""The :py:class:`threading.Lock` object used for synchronization between the loader and main threads."""
		self.loader_thread_stop = threading.Event()
		"""The :py:class:`threading.Event` object used to request that the loader thread stop before completion."""
		self.application.connect('campaign-set', self.signal_kpc_campaign_set)

	def _sync_loader_thread(self):
		"""
		Synchronize the loader thread by ensuring that it is stopped. If it is
		currently running, this will use :py:attr:`~.loader_thread_stop` to
		request that the loader stops early.
		"""
		if not self.loader_thread_is_running:
			return
		# it's alive so tell it to stop, wait for it, then proceed
		self.loader_thread_stop.set()
		while self.loader_thread.is_alive():
			gui_utilities.gtk_sync()
			self.loader_thread.join(1)

	@property
	def rpc(self):
		return self.application.rpc

	@property
	def loader_thread_is_running(self):
		if self.loader_thread is None:
			return False
		return self.loader_thread.is_alive()

	def load_campaign_information(self, force=True):
		raise NotImplementedError()

	def signal_button_clicked_refresh(self, button):
		self.load_campaign_information()

	def signal_destroy(self, gobject):
		self.is_destroyed.set()
		self.loader_thread_stop.set()
		if isinstance(self.loader_thread, threading.Thread) and self.loader_thread.is_alive():
			self.logger.debug("waiting on thread: {0}.loader_thread (tid: 0x{1:x})".format(self.__class__.__name__, self.loader_thread.ident))
			while self.loader_thread.is_alive():
				gui_utilities.gtk_sync()
			self.logger.debug("joined thread: {0}.loader_thread (tid: 0x{1:x})".format(self.__class__.__name__, self.loader_thread.ident))

	def signal_kpc_campaign_set(self, *_):
		self.load_campaign_information()

class CampaignViewGenericTableTab(CampaignViewGenericTab):
	"""
	This object is meant to be subclassed by tabs which will display
	campaign information of different types from specific database
	tables. The data in this object is refreshed when multiple events
	occur and it uses an internal timer to represent the last time the
	data was refreshed.
	"""
	dependencies = gui_utilities.GladeDependencies(
		children=(
			'button_refresh',
			'entry_filter',
			'revealer_filter',
			'treeview_campaign'
		)
	)
	node_query = None
	"""
	The GraphQL query used to load a particular node from the remote table.
	This query is provided with a single parameter of the node's id.
	"""
	table_name = ''
	"""The database table represented by this tab."""
	table_query = None
	"""
	The GraphQL query used to load the desired information from the remote
	table. This query is provided with the following three parameters:
	campaign, count and cursor.
	"""
	view_columns = ()
	"""The dictionary map of column numbers to column names starting at column 1."""
	xlsx_worksheet_options = None
	def __init__(self, *args, **kwargs):
		super(CampaignViewGenericTableTab, self).__init__(*args, **kwargs)
		treeview = self.gobjects['treeview_campaign']
		self.treeview_manager = managers.TreeViewManager(
			treeview,
			selection_mode=Gtk.SelectionMode.MULTIPLE,
			cb_delete=self._prompt_to_delete_row,
			cb_refresh=self.load_campaign_information
		)
		self.treeview_manager.set_column_titles(self.view_columns, column_offset=1)
		self.popup_menu = self.treeview_manager.get_popup_menu()
		"""The :py:class:`Gtk.Menu` object which is displayed when right-clicking in the view area."""
		treeview = self.gobjects['treeview_campaign']
		store_columns = [str] * (len(self.view_columns) + 1)

		self._rule = None
		self._rule_context = rule_engine.Context(
			type_resolver=rule_engine.type_resolver_from_dict(
				dict((column.lower().replace(' ', '_'), rule_engine.DataType.STRING) for column in self.view_columns)
			)
		)

		self._tv_model = Gtk.ListStore(*store_columns)
		self._tv_model_filter = self._tv_model.filter_new()
		self._tv_model_filter.set_visible_func(self._tv_filter)
		treeview.set_model(self._tv_model_filter)
		self.application.connect('server-connected', self.signal_kp_server_connected)

		filter_revealer = self.gobjects['revealer_filter']
		menu_item = Gtk.CheckMenuItem.new_with_label('Show Filter')
		menu_item.set_active(filter_revealer.get_reveal_child())
		menu_item.connect('activate', lambda widget: filter_revealer.set_reveal_child(widget.get_active()))
		menu_item.show()
		self.popup_menu.append(menu_item)

	def signal_entry_changed_filter(self, entry):
		text = entry.get_text()
		self._rule = None
		if text:
			try:
				self._rule = rule_engine.Rule(text, context=self._rule_context)
			except rule_engine.EngineError:
				entry.set_property('secondary-icon-stock', 'gtk-dialog-warning')
				return
		entry.set_property('secondary-icon-stock', None)
		self._tv_model_filter.refilter()

	def signal_kp_server_connected(self, _):
		event_id = 'db-' + self.table_name.replace('_', '-')
		server_events = self.application.server_events
		if not server_events:
			return
		server_events.subscribe(event_id, ('deleted', 'inserted', 'updated'), ('id', 'campaign_id'))
		server_events.connect(event_id, self.signal_server_event_db)

	def signal_server_event_db(self, _, event_type, rows):
		get_node = lambda id: self.rpc.graphql(self.node_query, {'id': str(id)})['db']['node']
		for row in rows:
			if str(row.campaign_id) != self.config['campaign_id']:
				continue
			for case in utilities.switch(event_type):
				if case('inserted'):
					row_data = self.format_node_data(get_node(row.id))
					row_data = list(map(self.format_cell_data, row_data))
					row_data.insert(0, str(row.id))
					gui_utilities.glib_idle_add_wait(self._tv_model.append, row_data)
				ti = gui_utilities.gtk_list_store_search(self._tv_model, str(row.id))
				if ti is None:
					self.logger.warning("received server db event: {0} for non-existent row {1}:{2}".format(event_type, self.table_name, str(row.id)))
					break
				if case('deleted'):
					self._tv_model.remove(ti)
					break
				if case('updated'):
					row_data = self.format_node_data(get_node(row.id))
					for idx, cell_data in enumerate(row_data, 1):
						self._tv_model[ti][idx] = self.format_cell_data(cell_data)
					break

	def _export_lock(self):
		show_dialog_warning = lambda: gui_utilities.show_dialog_warning('Export Failed', self.parent, 'Can not export data while loading.')
		if not self.loader_thread_lock.acquire(False):
			show_dialog_warning()
			return False
		if isinstance(self.loader_thread, threading.Thread) and self.loader_thread.is_alive():
			self.loader_thread_lock.release()
			show_dialog_warning()
			return False
		return True

	def _prompt_to_delete_row(self, treeview, _):
		if isinstance(self.loader_thread, threading.Thread) and self.loader_thread.is_alive():
			gui_utilities.show_dialog_warning('Can Not Delete Rows While Loading', self.parent)
			return
		row_ids = [self._tv_model.get_value(ti, 0) for ti in gui_utilities.gtk_treeview_selection_iterate(treeview)]
		if len(row_ids) == 0:
			return
		elif len(row_ids) == 1:
			message = 'Delete This Row?'
		else:
			message = "Delete These {0:,} Rows?".format(len(row_ids))
		if not gui_utilities.show_dialog_yes_no(message, self.parent, 'This information will be lost.'):
			return
		self.application.emit(self.table_name[:-1] + '-delete', row_ids)

	def _tv_filter(self, model, tree_iter, _):
		if self._rule is None:
			return True
		model_row = model[tree_iter]
		row = dict((key.lower().replace(' ', '_'), model_row[idx]) for idx, key in enumerate(self.view_columns, 1))
		try:
			return self._rule.matches(row)
		except rule_engine.EngineError:
			return True

	def format_node_data(self, node):
		"""
		This method is overridden by subclasses to format the raw node
		data returned from the server. The length of the list must equal
		the number of columns in the table. This method is called for
		each node in the remote table by the loader thread.

		:param dict node: The node from a GraphQL query representing data for this table.
		:return: The formatted row data.
		:rtype: list
		"""
		raise NotImplementedError()

	def format_cell_data(self, cell_data, encoding='utf-8'):
		"""
		This method provides formatting to the individual cell values returned
		from the :py:meth:`.format_row_data` function. Values are converted into
		a format suitable for reading.

		:param cell: The value to format.
		:param str encoding: The encoding to use to coerce the return value into a unicode string.
		:return: The formatted cell value.
		:rtype: str
		"""
		if isinstance(cell_data, datetime.datetime):
			cell_data = utilities.datetime_utc_to_local(cell_data)
			return utilities.format_datetime(cell_data, encoding=encoding)

		if cell_data is None:
			cell_data = ''
		elif isinstance(cell_data, int):
			cell_data = str(cell_data)

		# ensure that the return value is a unicode string
		if isinstance(cell_data, bytes):
			cell_data = cell_data.decode(encoding)
		return cell_data

	def load_campaign_information(self, force=True):
		"""
		Load the necessary campaign information from the remote server.
		Unless *force* is True, the
		:py:attr:`~.CampaignViewGenericTab.last_load_time` is compared
		with the :py:attr:`~.CampaignViewGenericTab.refresh_frequency` to
		check if the information is stale. If the local data is not stale,
		this function will return without updating the table.

		:param bool force: Ignore the load life time and force loading the remote data.
		"""
		if not force and ((time.time() - self.last_load_time) < self.refresh_frequency):
			return
		with self.loader_thread_lock:
			self._sync_loader_thread()
			self.loader_thread_stop.clear()
			self._tv_model.clear()
			self.loader_thread = utilities.Thread(target=self.loader_thread_routine, args=(self._tv_model,))
			self.loader_thread.daemon = True
			self.loader_thread.start()
		return

	def loader_thread_routine(self, store):
		"""
		The loading routine to be executed within a thread.

		:param store: The store object to place the new data.
		:type store: :py:class:`Gtk.ListStore`
		"""
		gui_utilities.glib_idle_add_wait(lambda: self.gobjects['treeview_campaign'].set_property('sensitive', False))
		campaign_id = self.config['campaign_id']
		count = 500
		page_info = {'endCursor': None, 'hasNextPage': True}
		while page_info['hasNextPage']:
			if self.rpc is None:
				break
			try:
				results = self.rpc.graphql(self.table_query, {'campaign': campaign_id, 'count': count, 'cursor': page_info['endCursor']})
			except errors.KingPhisherGraphQLQueryError as error:
				self.logger.error('graphql error: ' + error.message)
				raise
			if self.loader_thread_stop.is_set():
				break
			if self.is_destroyed.is_set():
				break
			for edge in results['db']['campaign'][self.table_name]['edges']:
				node = edge['node']
				row_data = self.format_node_data(node)
				row_data = list(map(self.format_cell_data, row_data))
				row_data.insert(0, str(node['id']))
				gui_utilities.glib_idle_add_wait(store.append, row_data)
			page_info = results['db']['campaign'][self.table_name]['pageInfo']
		if self.is_destroyed.is_set():
			return
		gui_utilities.glib_idle_add_wait(lambda: self.gobjects['treeview_campaign'].set_property('sensitive', True))
		self.last_load_time = time.time()

	def signal_button_clicked_export(self, button):
		self.export_table_to_csv()

	def export_table_to_csv(self):
		"""Export the data represented by the view to a CSV file."""
		if not self._export_lock():
			return
		dialog = extras.FileChooserDialog('Export Data', self.parent)
		file_name = self.config['campaign_name'] + '.csv'
		response = dialog.run_quick_save(file_name)
		dialog.destroy()
		if not response:
			self.loader_thread_lock.release()
			return
		destination_file = response['target_path']
		store = self.gobjects['treeview_campaign'].get_model()
		columns = dict(enumerate(('UID',) + self.view_columns))
		export.liststore_to_csv(store, destination_file, columns)
		self.loader_thread_lock.release()

	def export_table_to_xlsx_worksheet(self, worksheet, title_format):
		"""
		Export the data represented by the view to an XLSX worksheet.

		:param worksheet: The destination sheet for the store's data.
		:type worksheet: :py:class:`xlsxwriter.worksheet.Worksheet`
		:param title_format: The formatting to use for the title row.
		:type title_format: :py:class:`xlsxwriter.format.Format`
		"""
		if not self._export_lock():
			return
		store = self.gobjects['treeview_campaign'].get_model()
		columns = dict(enumerate(('UID',) + self.view_columns))
		export.liststore_to_xlsx_worksheet(store, worksheet, columns, title_format, xlsx_options=self.xlsx_worksheet_options)
		self.loader_thread_lock.release()

class CampaignViewDeaddropTab(CampaignViewGenericTableTab):
	"""Display campaign information regarding dead drop connections."""
	table_name = 'deaddrop_connections'
	label_text = 'Deaddrop'
	node_query = """\
	query getDeaddropConnection($id: String!) {
		db {
			node: deaddropConnection(id: $id) {
				id
				deaddropDeployment { destination }
				count
				ip
				localUsername
				localHostname
				localIpAddresses
				firstSeen
				lastSeen
			}
		}
	}
	"""
	table_query = """\
	query getDeaddropConnections($campaign: String!, $count: Int!, $cursor: String) {
		db {
			campaign(id: $campaign) {
				deaddrop_connections: deaddropConnections(first: $count, after: $cursor) {
					total
					edges {
						node {
							id
							deaddropDeployment {
								id
								destination
							}
							count
							ip
							localUsername
							localHostname
							localIpAddresses
							firstSeen
							lastSeen
						}
					}
					pageInfo {
						endCursor
						hasNextPage
					}
				}
			}
		}
	}
	"""
	view_columns = (
		'Destination',
		'Visit Count',
		'IP Address',
		'Username',
		'Hostname',
		'Local IP Addresses',
		'First Hit',
		'Last Hit'
	)
	def format_node_data(self, connection):
		deaddrop_destination = connection['deaddropDeployment']['destination']
		if not deaddrop_destination:
			return None
		row = (
			deaddrop_destination,
			connection['count'],
			connection['ip'],
			connection['localUsername'],
			connection['localHostname'],
			connection['localIpAddresses'],
			connection['firstSeen'],
			connection['lastSeen']
		)
		return row

class CampaignViewCredentialsTab(CampaignViewGenericTableTab):
	"""Display campaign information regarding submitted credentials."""
	table_name = 'credentials'
	label_text = 'Credentials'
	node_query = """\
	query getCredential($id: String!) {
		db {
			node: credential(id: $id) {
				id
				submitted
				message { targetEmail }
				username
				password
				mfaToken
				regexValidated
			}
		}
	}
	"""
	table_query = """\
	query getCredentials($campaign: String!, $count: Int!, $cursor: String) {
		db {
			campaign(id: $campaign) {
				credentials(first: $count, after: $cursor) {
					total
					edges {
						node {
							id
							message { targetEmail }
							submitted
							username
							password
							mfaToken
							regexValidated
						}
					}
					pageInfo {
						endCursor
						hasNextPage
					}
				}
			}
		}
	}
	"""
	secret_columns = ('Password', 'MFA Token')
	view_columns = (
		'Email Address',
		'Submitted',
		'Validation',
		'Username',
	) + secret_columns
	xlsx_worksheet_options = export.XLSXWorksheetOptions(
		column_widths=(20, 30, 25, 30, 30, 30, 20),
		title=label_text
	)
	def __init__(self, *args, **kwargs):
		super(CampaignViewCredentialsTab, self).__init__(*args, **kwargs)
		treeview = self.gobjects['treeview_campaign']
		for column_name in self.secret_columns:
			treeview.get_column(self.view_columns.index(column_name)).set_property('visible', False)

	def format_node_data(self, node):
		regex_validated = ''
		if node['regexValidated'] is not None:
			regex_validated = 'Pass' if node['regexValidated'] else 'Fail'
		row = (
			node['message']['targetEmail'],
			node['submitted'],
			regex_validated,
			node['username'],
			node['password'],
			node['mfaToken']
		)
		return row

	def signal_button_toggled_show_secrets(self, button):
		treeview = self.gobjects['treeview_campaign']
		visible = button.get_property('active')
		for column_name in self.secret_columns:
			treeview.get_column(self.view_columns.index(column_name)).set_property('visible', visible)

class CampaignViewDashboardTab(CampaignViewGenericTab):
	"""Display campaign information on a graphical dash board."""
	dependencies = gui_utilities.GladeDependencies(
		children=(
			'box_top_left',
			'box_top_right',
			'box_bottom',
			'scrolledwindow_top_left',
			'scrolledwindow_top_right',
			'scrolledwindow_bottom'
		)
	)
	label_text = 'Dashboard'
	"""The tabs label for display in the GUI."""
	def __init__(self, *args, **kwargs):
		super(CampaignViewDashboardTab, self).__init__(*args, **kwargs)
		self.graphs = []
		"""The :py:class:`.CampaignGraph` classes represented on the dash board."""

		dash_ports = {
			# dashboard position, (width, height)
			'top_left': (380, 200),
			'top_right': (380, 200),
			'bottom': (760, 200)
		}
		for dash_port, details in dash_ports.items():
			graph_name = self.config['dashboard.' + dash_port]
			cls = graphs.get_graph(graph_name)
			if not cls:
				self.logger.warning('could not get graph: ' + graph_name)
				logo_file_path = find.data_file('king-phisher-icon.svg')
				if logo_file_path:
					image = Gtk.Image.new_from_pixbuf(GdkPixbuf.Pixbuf.new_from_file_at_size(logo_file_path, 128, 128))
					image.show()
					self.gobjects['scrolledwindow_' + dash_port].add(image)
				continue
			graph_inst = cls(self.application, details, getattr(self, self.top_gobject).get_style_context())
			self.gobjects['scrolledwindow_' + dash_port].add(graph_inst.canvas)
			self.gobjects['box_' + dash_port].pack_end(graph_inst.navigation_toolbar, False, False, 0)
			self.graphs.append(graph_inst)
		self.logger.debug("dashboard refresh frequency set to {0} seconds".format(self.refresh_frequency))
		GLib.timeout_add_seconds(self.refresh_frequency, self.loader_idle_routine)

	def load_campaign_information(self, force=True):
		"""
		Load the necessary campaign information from the remote server.
		Unless *force* is True, the :py:attr:`~.last_load_time` is compared with
		the :py:attr:`~.refresh_frequency` to check if the information is stale.
		If the local data is not stale, this function will return without
		updating the table.

		:param bool force: Ignore the load life time and force loading the remote data.
		"""
		if not force and ((time.time() - self.last_load_time) < self.refresh_frequency):
			return
		if not self.application.rpc:
			self.logger.warning('skipping load_campaign_information because rpc is not initialized')
			return
		with self.loader_thread_lock:
			self._sync_loader_thread()
			self.loader_thread_stop.clear()
			self.loader_thread = utilities.Thread(target=self.loader_thread_routine)
			self.loader_thread.daemon = True
			self.loader_thread.start()

	def loader_idle_routine(self):
		"""The routine which refreshes the campaign data at a regular interval."""
		if self.rpc and not self.loader_thread_is_running:
			self.logger.debug('idle loader routine called')
			self.load_campaign_information()
		return True

	def loader_thread_routine(self):
		"""The loading routine to be executed within a thread."""
		if not 'campaign_id' in self.config:
			return
		try:
			campaign = self.application.get_graphql_campaign()
		except (ConnectionError, advancedhttpserver.RPCConnectionError):
			return
		if campaign is None:
			return
		info_cache = {}
		for graph in self.graphs:
			if self.loader_thread_stop.is_set():
				break
			if self.is_destroyed.is_set():
				break
			info_cache.update(gui_utilities.glib_idle_add_wait(lambda g=graph: g.refresh(info_cache, self.loader_thread_stop)))
		else:
			self.last_load_time = time.time()

class CampaignViewVisitsTab(CampaignViewGenericTableTab):
	"""Display campaign information regarding incoming visitors."""
	table_name = 'visits'
	label_text = 'Visits'
	node_query = """\
	query getVisit($id: String!) {
		db {
			node: visit(id: $id) {
				id
				message { targetEmail }
				ip
				count
				userAgent
				ipGeoloc { city }
				firstSeen
				lastSeen
			}
		}
	}
	"""
	table_query = """\
	query getVisits($campaign: String!, $count: Int!, $cursor: String) {
		db {
			campaign(id: $campaign) {
				visits(first: $count, after: $cursor) {
					total
					edges {
						node {
							id
							message { targetEmail }
							ip
							count
							userAgent
							ipGeoloc { city }
							firstSeen
							lastSeen
						}
					}
					pageInfo {
						endCursor
						hasNextPage
					}
				}
			}
		}
	}
	"""
	view_columns = (
		'Email Address',
		'IP Address',
		'Visit Count',
		'Visitor User Agent',
		'Visitor Location',
		'First Visit',
		'Last Visit'
	)
	xlsx_worksheet_options = export.XLSXWorksheetOptions(
		column_widths=(30, 30, 25, 15, 90, 30, 25, 25),
		title=label_text
	)
	def format_node_data(self, node):
		geo_location = UNKNOWN_LOCATION_STRING
		visitor_ip = node['ip']
		if visitor_ip is None:
			visitor_ip = ''
		else:
			visitor_ip = ipaddress.ip_address(visitor_ip)
			if visitor_ip.is_loopback:
				geo_location = 'N/A (Loopback)'
			elif visitor_ip.is_private:
				geo_location = 'N/A (Private)'
			elif isinstance(visitor_ip, ipaddress.IPv6Address):
				geo_location = 'N/A (IPv6 Address)'
			elif node['ipGeoloc']:
				geo_location = node['ipGeoloc']['city']
		row = (
			node['message']['targetEmail'],
			str(visitor_ip),
			node['count'],
			node['userAgent'],
			geo_location,
			node['firstSeen'],
			node['lastSeen']
		)
		return row

class CampaignViewMessagesTab(CampaignViewGenericTableTab):
	"""Display campaign information regarding sent messages."""
	table_name = 'messages'
	label_text = 'Messages'
	node_query = """\
	query getMessage($id: String!) {
		db {
			node: message(id: $id) {
				id
				targetEmail
				sent
				trained
				companyDepartment { name }
				opened
				openerIp
				openerUserAgent
			}
		}
	}
	"""
	table_query = """\
	query getMessages($campaign: String!, $count: Int!, $cursor: String) {
		db {
			campaign(id: $campaign) {
				messages(first: $count, after: $cursor) {
					total
					edges {
						node {
							id
							targetEmail
							sent
							trained
							companyDepartment { name }
							opened
							openerIp
							openerUserAgent
						}
					}
					pageInfo {
						endCursor
						hasNextPage
					}
				}
			}
		}
	}
	"""
	view_columns = (
		'Email Address',
		'Sent',
		'Trained',
		'Department',
		'Opened',
		'Opener IP Address',
		'Opener User Agent'
	)
	xlsx_worksheet_options = export.XLSXWorksheetOptions(
		column_widths=(30, 30, 30, 15, 20, 20, 25, 90),
		title=label_text
	)
	def format_node_data(self, node):
		department = node['companyDepartment']
		if department:
			department = department['name']
		row = (
			node['targetEmail'],
			node['sent'],
			('Yes' if node['trained'] else ''),
			department,
			node['opened'],
			node['openerIp'],
			node['openerUserAgent']
		)
		return row

class CampaignViewTab(object):
	"""
	The King Phisher client top-level 'View Campaign' tab. This object
	manages the sub-tabs which display all the information regarding
	the current campaign.
	"""
	def __init__(self, parent, application):
		"""
		:param parent: The parent window for this object.
		:type parent: :py:class:`Gtk.Window`
		:param application: The main client application instance.
		:type application: :py:class:`Gtk.Application`
		"""
		self.parent = parent
		self.application = application
		self.config = application.config
		self.logger = logging.getLogger('KingPhisher.Client.' + self.__class__.__name__)
		self.box = Gtk.Box()
		self.box.set_property('orientation', Gtk.Orientation.VERTICAL)
		self.box.show()
		self.label = Gtk.Label(label='View Campaign')
		"""The :py:class:`Gtk.Label` representing this tabs name."""

		self.notebook = Gtk.Notebook()
		""" The :py:class:`Gtk.Notebook` for holding sub-tabs."""
		self.notebook.connect('switch-page', self.signal_notebook_switch_page)
		self.notebook.set_scrollable(True)
		self.box.pack_start(self.notebook, True, True, 0)

		self.tabs = utilities.FreezableDict()
		"""A dict object holding the sub tabs managed by this object."""
		current_page = self.notebook.get_current_page()
		self.last_page_id = current_page

		if graphs.has_matplotlib:
			self.logger.info('matplotlib is installed, dashboard will be available')
			dashboard_tab = CampaignViewDashboardTab(application)
			self.tabs['dashboard'] = dashboard_tab
			self.notebook.append_page(dashboard_tab.box, dashboard_tab.label)
		else:
			self.logger.warning('matplotlib is not installed, dashboard will not be available')

		messages_tab = CampaignViewMessagesTab(application)
		self.tabs['messages'] = messages_tab
		self.notebook.append_page(messages_tab.box, messages_tab.label)

		visits_tab = CampaignViewVisitsTab(application)
		self.tabs['visits'] = visits_tab
		self.notebook.append_page(visits_tab.box, visits_tab.label)

		credentials_tab = CampaignViewCredentialsTab(application)
		self.tabs['credentials'] = credentials_tab
		self.notebook.append_page(credentials_tab.box, credentials_tab.label)

		if self.config.get('gui.show_deaddrop', False):
			deaddrop_connections_tab = CampaignViewDeaddropTab(application)
			self.tabs['deaddrop_connections'] = deaddrop_connections_tab
			self.notebook.append_page(deaddrop_connections_tab.box, deaddrop_connections_tab.label)

		self.tabs.freeze()
		for tab in self.tabs.values():
			tab.box.show()
		self.notebook.show()

	def signal_notebook_switch_page(self, notebook, current_page, index):
		if not hasattr(self.parent, 'rpc'):
			return
		#previous_page = notebook.get_nth_page(self.last_page_id)
		self.last_page_id = index

		for tab in self.tabs.values():
			if current_page != tab.box:
				continue
			if hasattr(tab, 'load_campaign_information'):
				tab.load_campaign_information(force=False)
