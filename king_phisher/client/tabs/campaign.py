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
import ipaddress
import logging
import threading
import time

from king_phisher import find
from king_phisher import utilities
from king_phisher.client import export
from king_phisher.client import graphs
from king_phisher.client import gui_utilities
from king_phisher.client import widget_managers

from boltons import iterutils
from gi.repository import GdkPixbuf
from gi.repository import GLib
from gi.repository import Gtk
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

	@property
	def rpc(self):
		return self.application.rpc

	def load_campaign_information(self, force=True):
		raise NotImplementedError()

	def signal_button_clicked_refresh(self, button):
		self.load_campaign_information()

	def signal_destroy(self, gobject):
		self.is_destroyed.set()
		if isinstance(self.loader_thread, threading.Thread) and self.loader_thread.is_alive():
			self.logger.debug("waiting on thread: {0}.loader_thread (tid: 0x{1:x})".format(self.__class__.__name__, self.loader_thread.ident))
			while self.loader_thread.is_alive():
				gui_utilities.gtk_sync()
			self.logger.debug("joined thread: {0}.loader_thread (tid: 0x{1:x})".format(self.__class__.__name__, self.loader_thread.ident))

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
			'treeview_campaign'
		)
	)
	remote_table_name = ''
	"""The database table represented by this tab."""
	view_columns = ()
	"""The dictionary map of column numbers to column names starting at column 1."""
	def __init__(self, *args, **kwargs):
		super(CampaignViewGenericTableTab, self).__init__(*args, **kwargs)
		treeview = self.gobjects['treeview_campaign']
		self.treeview_manager = widget_managers.TreeViewManager(
			treeview,
			selection_mode=Gtk.SelectionMode.MULTIPLE,
			cb_delete=self._prompt_to_delete_row,
			cb_refresh=self.load_campaign_information
		)
		self.treeview_manager.set_column_titles(self.view_columns, column_offset=1)
		self.popup_menu = self.treeview_manager.get_popup_menu()
		"""The :py:class:`Gtk.Menu` object which is displayed when right-clicking in the view area."""

	def _prompt_to_delete_row(self, treeview, selection):
		if isinstance(self.loader_thread, threading.Thread) and self.loader_thread.is_alive():
			gui_utilities.show_dialog_warning('Can Not Delete Rows While Loading', self.parent)
			return
		(model, tree_paths) = selection.get_selected_rows()
		if not tree_paths:
			return
		tree_iters = map(model.get_iter, tree_paths)
		row_ids = [model.get_value(ti, 0) for ti in tree_iters]
		if len(row_ids) == 1:
			message = 'Delete This Row?'
		else:
			message = "Delete These {0:,} Rows?".format(len(row_ids))
		if not gui_utilities.show_dialog_yes_no(message, self.parent, 'This information will be lost.'):
			return
		if len(row_ids) == 1:
			self.rpc('db/table/delete', self.remote_table_name, row_ids[0])
		else:
			self.rpc('db/table/delete/multi', self.remote_table_name, row_ids)
		self.load_campaign_information()

	def format_row_data(self, row):
		"""
		This method is overridden by subclasses to format the raw row
		data returned from the server. The length of the list must equal
		the number of columns in the table. This method is called for
		each row in the remote table by the loader thread.

		:return: The formated row data.
		:rtype: list
		"""
		raise NotImplementedError()

	def format_cell_data(self, cell_data):
		"""
		This method provides formatting to the individual cell values returned
		from the :py:meth:`.format_row_data` function. Values are converted into
		a format suitable for reading.

		:param cell: The value to format.
		:return: The formatted cell value.
		:rtype: str
		"""
		if isinstance(cell_data, datetime.datetime):
			cell_data = utilities.datetime_utc_to_local(cell_data)
			return utilities.format_datetime(cell_data)
		elif cell_data is None:
			return ''
		return str(cell_data)

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
		if isinstance(self.loader_thread, threading.Thread) and self.loader_thread.is_alive():
			return
		self.loader_thread_lock.acquire()
		treeview = self.gobjects['treeview_campaign']
		store = treeview.get_model()
		if store == None:
			store_columns = [str]
			for _ in range(len(self.view_columns)):
				store_columns.append(str)
			store = Gtk.ListStore(*store_columns)
			treeview.set_model(store)
		else:
			store.clear()
		self.loader_thread = threading.Thread(target=self.loader_thread_routine, args=(store,))
		self.loader_thread.daemon = True
		self.loader_thread.start()
		self.loader_thread_lock.release()
		return

	def loader_thread_routine(self, store):
		"""
		The loading routine to be executed within a thread.

		:param store: The store object to place the new data.
		:type store: :py:class:`Gtk.ListStore`
		"""
		gui_utilities.glib_idle_add_wait(lambda: self.gobjects['treeview_campaign'].set_property('sensitive', False))
		for row in self.rpc.remote_table(self.remote_table_name, query_filter={'campaign_id': self.config['campaign_id']}):
			if self.is_destroyed.is_set():
				break
			if self.rpc is None:
				break
			row_data = self.format_row_data(row)
			if row_data is None:
				self.rpc('db/table/delete', self.remote_table_name, row.id)
				continue
			row_data = list(map(self.format_cell_data, row_data))
			row_data.insert(0, str(row.id))
			gui_utilities.glib_idle_add_wait(store.append, row_data)
		if self.is_destroyed.is_set():
			return
		gui_utilities.glib_idle_add_wait(lambda: self.gobjects['treeview_campaign'].set_property('sensitive', True))
		self.last_load_time = time.time()

	def signal_button_clicked_export(self, button):
		self.export_table_to_csv()

	def export_table_to_csv(self):
		"""Export the data represented by the view to a CSV file."""
		if not self.loader_thread_lock.acquire(False) or (isinstance(self.loader_thread, threading.Thread) and self.loader_thread.is_alive()):
			gui_utilities.show_dialog_warning('Can Not Export Rows While Loading', self.parent)
			return
		dialog = gui_utilities.FileChooser('Export Data', self.parent)
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

	def export_table_to_xlsx_worksheet(self, worksheet):
		"""Export the data represented by the view to a XLSX worksheet."""
		if not self.loader_thread_lock.acquire(False) or (isinstance(self.loader_thread, threading.Thread) and self.loader_thread.is_alive()):
			gui_utilities.show_dialog_warning('Can Not Export Rows While Loading', self.parent)
			return
		store = self.gobjects['treeview_campaign'].get_model()
		columns = dict(enumerate(('UID',) + self.view_columns))
		worksheet.set_column(0, len(columns), 30)
		export.liststore_to_xlsx_worksheet(store, worksheet, columns)
		self.loader_thread_lock.release()

class CampaignViewDeaddropTab(CampaignViewGenericTableTab):
	"""Display campaign information regarding dead drop connections."""
	remote_table_name = 'deaddrop_connections'
	label_text = 'Deaddrop'
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
	def format_row_data(self, connection):
		deploy_details = self.rpc.remote_table_row('deaddrop_deployments', connection.deployment_id, cache=True)
		if not deploy_details:
			return None
		row = (
			deploy_details.destination,
			connection.visit_count,
			connection.visitor_ip,
			connection.local_username,
			connection.local_hostname,
			connection.local_ip_addresses,
			connection.first_visit,
			connection.last_visit
		)
		return row

class CampaignViewCredentialsTab(CampaignViewGenericTableTab):
	"""Display campaign information regarding submitted credentials."""
	remote_table_name = 'credentials'
	label_text = 'Credentials'
	view_columns = (
		'Email Address',
		'Username',
		'Password',
		'Submitted'
	)
	def __init__(self, *args, **kwargs):
		super(CampaignViewCredentialsTab, self).__init__(*args, **kwargs)
		treeview = self.gobjects['treeview_campaign']
		pwd_column_id = self.view_columns.index('Password')
		treeview.get_column(pwd_column_id).set_property('visible', False)

	def format_row_data(self, credential):
		msg_details = self.rpc.remote_table_row('messages', credential.message_id, cache=True)
		if not msg_details:
			return None
		row = (
			msg_details.target_email,
			credential.username,
			credential.password,
			credential.submitted
		)
		return row

	def signal_button_toggled_show_passwords(self, button):
		treeview = self.gobjects['treeview_campaign']
		pwd_column_id = self.view_columns.index('Password')
		treeview.get_column(pwd_column_id).set_property('visible', button.get_property('active'))

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

		# Position: (DefaultGraphName, Size)
		dash_ports = {
			'top_left': (380, 200),
			'top_right': (380, 200),
			'bottom': None
		}
		for dash_port, details in dash_ports.items():
			graph_name = self.config['dashboard.' + dash_port]
			cls = graphs.get_graph(graph_name)
			if not cls:
				self.logger.warning('could not get graph: ' + graph_name)
				logo_file_path = find.find_data_file('king-phisher-icon.svg')
				if logo_file_path:
					image = Gtk.Image.new_from_pixbuf(GdkPixbuf.Pixbuf.new_from_file_at_size(logo_file_path, 128, 128))
					image.show()
					self.gobjects['scrolledwindow_' + dash_port].add(image)
				continue
			graph_inst = cls(self.application, details, getattr(self, self.top_gobject).get_style_context())
			self.gobjects['scrolledwindow_' + dash_port].add_with_viewport(graph_inst.canvas)
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
			if isinstance(self.loader_thread, threading.Thread) and self.loader_thread.is_alive():
				return
			self.loader_thread = threading.Thread(target=self.loader_thread_routine)
			self.loader_thread.daemon = True
			self.loader_thread.start()

	def loader_idle_routine(self):
		"""The routine which refreshes the campaign data at a regular interval."""
		if self.rpc:
			self.logger.debug('idle loader routine called')
			self.load_campaign_information()
		return True

	def loader_thread_routine(self):
		"""The loading routine to be executed within a thread."""
		if not 'campaign_id' in self.config:
			return
		if not self.rpc.remote_table_row('campaigns', self.config['campaign_id']):
			return
		info_cache = {}
		for graph in self.graphs:
			if self.is_destroyed.is_set():
				break
			info_cache.update(gui_utilities.glib_idle_add_wait(lambda g=graph: g.refresh(info_cache, self.is_destroyed)))
		self.last_load_time = time.time()

class CampaignViewVisitsTab(CampaignViewGenericTableTab):
	"""Display campaign information regarding incoming visitors."""
	remote_table_name = 'visits'
	label_text = 'Visits'
	view_columns = (
		'Email Address',
		'IP Address',
		'Visit Count',
		'Visitor User Agent',
		'Visitor Location',
		'First Visit',
		'Last Visit'
	)
	def __init__(self, *args, **kwargs):
		super(CampaignViewVisitsTab, self).__init__(*args, **kwargs)
		self._ips_for_georesolution = {}

	def format_row_data(self, visit):
		msg_details = self.rpc.remote_table_row('messages', visit.message_id, cache=True)
		if not msg_details:
			return None
		visitor_ip = ipaddress.ip_address(visit.visitor_ip)
		geo_location = UNKNOWN_LOCATION_STRING
		if visitor_ip.is_loopback:
			geo_location = 'N/A (Loopback)'
		elif visitor_ip.is_private:
			geo_location = 'N/A (Private)'
		elif isinstance(visitor_ip, ipaddress.IPv6Address):
			geo_location = 'N/A (IPv6 Address)'
		else:
			if not visitor_ip in self._ips_for_georesolution:
				self._ips_for_georesolution[visitor_ip] = visit.first_visit
			elif self._ips_for_georesolution[visitor_ip] > visit.first_visit:
				self._ips_for_georesolution[visitor_ip] = visit.first_visit
		row = (
			msg_details.target_email,
			str(visitor_ip),
			visit.visit_count,
			visit.visitor_details,
			geo_location,
			visit.first_visit,
			visit.last_visit
		)
		return row

	def loader_thread_routine(self, store):
		self._ips_for_georesolution = {}
		super(CampaignViewVisitsTab, self).loader_thread_routine(store)
		ips_for_geores = [ip for (ip, _) in sorted(self._ips_for_georesolution.items(), key=lambda x: x[1])]
		locations = {}
		for ip_addresses in iterutils.chunked(ips_for_geores, 50):
			locations.update(self.rpc.geoip_lookup_multi(ip_addresses))
		for row in store:
			if row[2] in locations:
				row[5] = str(locations[row[2]])

class CampaignViewMessagesTab(CampaignViewGenericTableTab):
	"""Display campaign information regarding sent messages."""
	remote_table_name = 'messages'
	label_text = 'Messages'
	view_columns = (
		'Email Address',
		'Sent',
		'Trained',
		'Department',
		'Opened',
		'Opener IP Address',
		'Opener User Agent'
	)
	def format_row_data(self, message):
		department = message.company_department
		if department:
			department = department.name
		row = (
			message.target_email,
			message.sent,
			('Yes' if message.trained else ''),
			department,
			message.opened,
			message.opener_ip,
			message.opener_user_agent
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
		self.application.connect('campaign-set', self.signal_kpc_campaign_set)

	def signal_kpc_campaign_set(self, kpc, cid):
		for tab in self.tabs.values():
			if hasattr(tab, 'load_campaign_information'):
				tab.load_campaign_information()

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
