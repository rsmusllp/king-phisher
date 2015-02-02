#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  king_phisher/client/client.py
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

import copy
import json
import logging
import os
import random
import shlex
import shutil
import socket
import sys
import time

from king_phisher import find
from king_phisher import utilities
from king_phisher import version
from king_phisher.client import dialogs
from king_phisher.client import export
from king_phisher.client import graphs
from king_phisher.client import gui_utilities
from king_phisher.client import tools
from king_phisher.client.client_rpc import KingPhisherRPCClient
from king_phisher.client.tabs.campaign import CampaignViewTab
from king_phisher.client.tabs.mail import MailSenderTab
from king_phisher.ssh_forward import SSHTCPForwarder
from king_phisher.third_party.AdvancedHTTPServer import AdvancedHTTPServerRPCError

from gi.repository import Gdk
from gi.repository import GdkPixbuf
from gi.repository import GLib
from gi.repository import GObject
from gi.repository import Gtk
import paramiko

CONFIG_FILE_PATH = '~/.king_phisher.json'
"""The default search location for the client configuration file."""

if isinstance(Gtk.Window, utilities.Mock):
	_Gtk_Window = type('Gtk.Window', (object,), {})
	_Gtk_Window.__module__ = ''
else:
	_Gtk_Window = Gtk.Window

class KingPhisherClient(_Gtk_Window):
	"""
	This is the top level King Phisher client object. It contains the
	custom GObject signals, keeps all the GUI references, and manages
	the RPC client object. This is also the parent window for most
	GTK objects.

	:GObject Signals: :ref:`gobject-signals-kingphisher-client-label`
	"""
	__gsignals__ = {
		'campaign-set': (GObject.SIGNAL_RUN_FIRST, None, (str,)),
		'exit': (GObject.SIGNAL_RUN_LAST, None, ()),
		'exit-confirm': (GObject.SIGNAL_RUN_LAST, None, ()),
		'server-connected': (GObject.SIGNAL_RUN_FIRST, None, ())
	}
	def __init__(self, config_file=None):
		"""
		:param str config_file: The path to the configuration file to load.
		"""
		super(KingPhisherClient, self).__init__()
		self.logger = logging.getLogger('KingPhisher.Client')
		# print version information for debugging purposes
		self.logger.debug("gi.repository GLib version: {0}".format('.'.join(map(str, GLib.glib_version))))
		self.logger.debug("gi.repository GObject version: {0}".format('.'.join(map(str, GObject.pygobject_version))))
		self.logger.debug("gi.repository Gtk version: {0}.{1}.{2}".format(Gtk.get_major_version(), Gtk.get_minor_version(), Gtk.get_micro_version()))
		if tools.has_vte:
			self.logger.debug("gi.repository VTE version: {0}".format(tools.Vte._version))
		if graphs.has_matplotlib:
			self.logger.debug("matplotlib version: {0}".format(graphs.matplotlib.__version__))
		self.config_file = (config_file or CONFIG_FILE_PATH)
		"""The file containing the King Phisher client configuration."""
		self.ssh_forwarder = None
		"""The :py:class:`.SSHTCPForwarder` instance used for tunneling traffic."""
		self.config = None
		"""The main King Phisher client configuration."""
		try:
			self.load_config(load_defaults=True)
		except Exception:
			self.logger.critical('failed to load the client configuration')
			raise
		self.set_property('title', 'King Phisher')
		vbox = Gtk.Box()
		vbox.set_property('orientation', Gtk.Orientation.VERTICAL)
		vbox.show()
		self.add(vbox)
		default_icon_file = find.find_data_file('king-phisher-icon.svg')
		if default_icon_file:
			icon_pixbuf = GdkPixbuf.Pixbuf.new_from_file(default_icon_file)
			self.set_default_icon(icon_pixbuf)

		action_group = Gtk.ActionGroup(name="client_window_actions")
		self._add_menu_actions(action_group)
		uimanager = self._create_ui_manager()
		self._add_menu_optional_actions(action_group, uimanager)
		self.add_accel_group(uimanager.get_accel_group())
		uimanager.insert_action_group(action_group)
		self.uimanager = uimanager
		menubar = uimanager.get_widget("/MenuBar")
		vbox.pack_start(menubar, False, False, 0)

		# create notebook and tabs
		self.notebook = Gtk.Notebook()
		"""The primary :py:class:`Gtk.Notebook` that holds the top level taps of the client GUI."""
		self.notebook.connect('switch-page', self.signal_notebook_switch_page)
		self.notebook.set_scrollable(True)
		vbox.pack_start(self.notebook, True, True, 0)

		self.tabs = {}
		current_page = self.notebook.get_current_page()
		self.last_page_id = current_page

		mailer_tab = MailSenderTab(self.config, self)
		self.tabs['mailer'] = mailer_tab
		self.notebook.insert_page(mailer_tab.box, mailer_tab.label, current_page + 1)
		self.notebook.set_current_page(current_page + 1)

		campaign_tab = CampaignViewTab(self.config, self)
		campaign_tab.box.show()
		self.tabs['campaign'] = campaign_tab
		self.notebook.insert_page(campaign_tab.box, campaign_tab.label, current_page + 2)

		self.set_size_request(800, 600)
		self.connect('delete-event', self.signal_delete_event)
		self.notebook.show()
		self.show()
		self.rpc = None # needs to be initialized last
		"""The :py:class:`.KingPhisherRPCClient` instance."""

		login_dialog = dialogs.KingPhisherClientLoginDialog(self.config, self)
		login_dialog.dialog.connect('response', self.signal_login_dialog_response, login_dialog)
		login_dialog.dialog.show()

	def _add_menu_actions(self, action_group):
		# File Menu Actions
		action = Gtk.Action(name='FileMenu', label='File', tooltip=None, stock_id=None)
		action_group.add_action(action)

		action = Gtk.Action(name='FileOpenCampaign', label='_Open Campaign', tooltip='Open a Campaign', stock_id=Gtk.STOCK_NEW)
		action.connect('activate', lambda x: self.show_campaign_selection())
		action_group.add_action_with_accel(action, '<control>O')

		action = Gtk.Action(name='FileImportMenu', label='Import', tooltip=None, stock_id=None)
		action_group.add_action(action)

		action = Gtk.Action(name='FileImportMessageConfiguration', label='Message Configuration', tooltip='Message Configuration', stock_id=None)
		action.connect('activate', lambda x: self.tabs['mailer'].import_message_data())
		action_group.add_action(action)

		action = Gtk.Action(name='FileExportMenu', label='Export', tooltip=None, stock_id=None)
		action_group.add_action(action)

		action = Gtk.Action(name='FileExportCampaignXML', label='Campaign XML', tooltip='Campaign XML', stock_id=None)
		action.connect('activate', lambda x: self.export_campaign_xml())
		action_group.add_action(action)

		action = Gtk.Action(name='FileExportMessageConfiguration', label='Message Configuration', tooltip='Message Configuration', stock_id=None)
		action.connect('activate', lambda x: self.tabs['mailer'].export_message_data())
		action_group.add_action(action)

		action = Gtk.Action(name='FileQuit', label=None, tooltip=None, stock_id=Gtk.STOCK_QUIT)
		action.connect('activate', lambda x: self.emit('exit-confirm'))
		action_group.add_action_with_accel(action, '<control>Q')

		# Edit Menu Actions
		action = Gtk.Action(name='EditMenu', label='Edit', tooltip=None, stock_id=None)
		action_group.add_action(action)

		action = Gtk.Action(name='EditPreferences', label='Preferences', tooltip='Edit Preferences', stock_id=Gtk.STOCK_EDIT)
		action.connect('activate', lambda x: self.edit_preferences())
		action_group.add_action(action)

		action = Gtk.Action(name='EditDeleteCampaign', label='Delete Campaign', tooltip='Delete Campaign', stock_id=None)
		action.connect('activate', lambda x: self.delete_campaign())
		action_group.add_action(action)

		action = Gtk.Action(name='EditStopService', label='Stop Service', tooltip='Stop The Remote King-Phisher Service', stock_id=None)
		action.connect('activate', lambda x: self.stop_remote_service())
		action_group.add_action(action)

		# Tools Menu Action
		action = Gtk.Action(name='ToolsMenu', label='Tools', tooltip=None, stock_id=None)
		action_group.add_action(action)

		action = Gtk.Action(name='ToolsRPCTerminal', label='RPC Terminal', tooltip='RPC Terminal', stock_id=None)
		action.connect('activate', lambda x: tools.KingPhisherClientRPCTerminal(self.config, self))
		action_group.add_action(action)

		# Help Menu Actions
		action = Gtk.Action(name='HelpMenu', label='Help', tooltip=None, stock_id=None)
		action_group.add_action(action)

		action = Gtk.Action(name='HelpAbout', label='About', tooltip='About', stock_id=None)
		action.connect('activate', lambda x: self.show_about_dialog())
		action_group.add_action(action)

		action = Gtk.Action(name='HelpWiki', label='Wiki', tooltip='Wiki', stock_id=None)
		action.connect('activate', lambda x: utilities.open_uri('https://github.com/securestate/king-phisher/wiki'))
		action_group.add_action(action)

	def _add_menu_optional_actions(self, action_group, uimanager):
		if graphs.has_matplotlib:
			action = Gtk.Action(name='ToolsGraphMenu', label='Create Graph', tooltip=None, stock_id=None)
			action_group.add_action(action)

			for graph_name in graphs.get_graphs():
				action_name = 'ToolsGraph' + graph_name
				action = Gtk.Action(name=action_name, label=graph_name, tooltip=graph_name, stock_id=None)
				action.connect('activate', lambda _: self.show_campaign_graph(graph_name))
				action_group.add_action(action)

			merge_id = uimanager.new_merge_id()
			uimanager.add_ui(merge_id, '/MenuBar/ToolsMenu', 'ToolsGraphMenu', 'ToolsGraphMenu', Gtk.UIManagerItemType.MENU, False)
			for graph_name in graphs.get_graphs():
				action_name = 'ToolsGraph' + graph_name
				uimanager.add_ui(merge_id, '/MenuBar/ToolsMenu/ToolsGraphMenu', action_name, action_name, Gtk.UIManagerItemType.MENUITEM, False)

		if sys.platform.startswith('linux'):
			action = Gtk.Action(name='ToolsSFTPClient', label='SFTP Client', tooltip='SFTP Client', stock_id=None)
			action.connect('activate', lambda x: self.start_sftp_client())
			action_group.add_action(action)
			merge_id = uimanager.new_merge_id()
			uimanager.add_ui(merge_id, '/MenuBar/ToolsMenu', 'ToolsSFTPClient', 'ToolsSFTPClient', Gtk.UIManagerItemType.MENUITEM, False)

	def _create_ui_manager(self):
		uimanager = Gtk.UIManager()
		with open(find.find_data_file('ui_info/client_window.xml')) as ui_info_file:
			ui_data = ui_info_file.read()
		uimanager.add_ui_from_string(ui_data)
		return uimanager

	def signal_notebook_switch_page(self, notebook, current_page, index):
		#previous_page = notebook.get_nth_page(self.last_page_id)
		self.last_page_id = index
		mailer_tab = self.tabs.get('mailer')
		campaign_tab = self.tabs.get('campaign')

		notebook = None
		if mailer_tab and current_page == mailer_tab.box:
			notebook = mailer_tab.notebook
		elif campaign_tab and current_page == campaign_tab.box:
			notebook = campaign_tab.notebook

		if notebook:
			index = notebook.get_current_page()
			notebook.emit('switch-page', notebook.get_nth_page(index), index)

	def signal_delete_event(self, x, y):
		self.emit('exit-confirm')
		return True

	def do_campaign_set(self, campaign_id):
		self.rpc.cache_clear()
		self.logger.info("campaign set to {0} (id: {1})".format(self.config['campaign_name'], self.config['campaign_id']))

	def do_exit(self):
		self.hide()
		gui_utilities.gtk_widget_destroy_children(self)
		gui_utilities.gtk_sync()
		self.server_disconnect()
		self.save_config()
		self.destroy()
		Gtk.main_quit()
		return

	def do_exit_confirm(self):
		self.emit('exit')

	def do_server_connected(self):
		self.load_server_config()
		campaign_id = self.config.get('campaign_id')
		if campaign_id == None:
			if not self.show_campaign_selection():
				self.logger.debug('no campaign selected, disconnecting and exiting')
				self.emit('exit')
				return True
		campaign_info = self.rpc.remote_table_row('campaigns', self.config['campaign_id'], cache=True)
		if campaign_info == None:
			if not self.show_campaign_selection():
				self.logger.debug('no campaign selected, disconnecting and exiting')
				self.emit('exit')
				return True
			campaign_info = self.rpc.remote_table_row('campaigns', self.config['campaign_id'], cache=True, refresh=True)
		self.config['campaign_name'] = campaign_info['name']
		self.emit('campaign-set', self.config['campaign_id'])
		return

	def client_quit(self):
		"""
		Unconditionally quit the client and perform any necessary clean up
		operations. The exit-confirm signal will not be sent so there will not
		be any opportunities for the client to cancel the operation.
		"""
		self.emit('exit')

	def signal_login_dialog_response(self, dialog, response, glade_dialog):
		server_version_info = None
		title_ssh_error = 'Failed To Connect To The SSH Service'
		title_rpc_error = 'Failed To Connect To The King Phisher RPC Service'

		if response == Gtk.ResponseType.CANCEL or response == Gtk.ResponseType.DELETE_EVENT:
			dialog.destroy()
			self.emit('exit')
			return True
		glade_dialog.objects_save_to_config()
		server = utilities.server_parse(self.config['server'], 22)
		username = self.config['server_username']
		password = self.config['server_password']
		server_remote_port = self.config['server_remote_port']
		local_port = random.randint(2000, 6000)
		connection_failed = True
		try:
			self.ssh_forwarder = SSHTCPForwarder(server, username, password, local_port, ('127.0.0.1', server_remote_port), preferred_private_key=self.config['ssh_preferred_key'])
			self.ssh_forwarder.start()
			time.sleep(0.5)
			self.logger.info('started ssh port forwarding')
		except paramiko.AuthenticationException:
			self.logger.warning('failed to authenticate to the remote ssh server')
			gui_utilities.show_dialog_error(title_ssh_error, self, 'The server responded that the credentials are invalid')
		except socket.error as error:
			error_number, error_message = error.args
			if error_number == 111:
				gui_utilities.show_dialog_error(title_ssh_error, self, 'The server refused the connection')
			else:
				gui_utilities.show_dialog_error(title_ssh_error, self, "Socket error #{0} ({1})".format((error_number or 'NOT-SET'), error_message))
		except Exception:
			self.logger.warning('failed to connect to the remote ssh server')
			gui_utilities.show_dialog_error(title_ssh_error, self)
		else:
			connection_failed = False
		finally:
			if connection_failed:
				self.server_disconnect()
				return

		self.rpc = KingPhisherRPCClient(('localhost', local_port), username=username, password=password, use_ssl=self.config.get('server_use_ssl'))
		if self.config.get('rpc.serializer'):
			try:
				self.rpc.set_serializer(self.config['rpc.serializer'])
			except ValueError as error:
				self.logger.error("failed to set the rpc serializer, error: '{0}'".format(error.message))

		connection_failed = True
		try:
			assert(self.rpc('client/initialize'))
			server_version_info = self.rpc('version')
			assert(server_version_info != None)
		except AdvancedHTTPServerRPCError as err:
			if err.status == 401:
				self.logger.warning('failed to authenticate to the remote king phisher service')
				gui_utilities.show_dialog_error(title_rpc_error, self, 'The server responded that the credentials are invalid')
			else:
				self.logger.warning('failed to connect to the remote rpc server with http status: ' + str(err.status))
				gui_utilities.show_dialog_error(title_rpc_error, self, 'The server responded with HTTP status: ' + str(err.status))
		except:
			self.logger.warning('failed to connect to the remote rpc service')
			gui_utilities.show_dialog_error(title_rpc_error, self, 'Ensure that the King Phisher Server is currently running')
		else:
			connection_failed = False
		finally:
			if connection_failed:
				self.server_disconnect()
				return

		server_rpc_api_version = server_version_info.get('rpc_api_version', -1)
		self.logger.info("successfully connected to the king phisher server (version: {0} rpc api version: {1})".format(server_version_info['version'], server_rpc_api_version))
		self.server_local_port = local_port
		if server_rpc_api_version != version.rpc_api_version:
			if version.rpc_api_version < server_rpc_api_version:
				secondary_text = 'The local client is not up to date with the server version.'
			else:
				secondary_text = 'The remote server is not up to date with the client version.'
			secondary_text += '\nPlease ensure that both the client and server are fully up to date.'
			gui_utilities.show_dialog_error('The RPC API Versions Are Incompatible', self, secondary_text)
			self.server_disconnect()
			return
		dialog.destroy()
		self.emit('server-connected')
		return

	def server_disconnect(self):
		"""Clean up the SSH TCP connections and disconnect from the server."""
		if self.ssh_forwarder:
			self.ssh_forwarder.stop()
			self.ssh_forwarder = None
			self.logger.info('stopped ssh port forwarding')
		return

	def load_config(self, load_defaults=False):
		"""
		Load the client configuration from disk and set the
		:py:attr:`~.KingPhisherClient.config` attribute.

		:param bool load_defaults: Load missing options from the template configuration file.
		"""
		self.logger.info('loading the config from disk')
		config_file = os.path.expanduser(self.config_file)
		client_template = find.find_data_file('client_config.json')
		if not os.path.isfile(config_file):
			shutil.copy(client_template, config_file)
		with open(config_file, 'r') as tmp_file:
			self.config = json.load(tmp_file)
		if load_defaults:
			with open(client_template, 'r') as tmp_file:
				client_template = json.load(tmp_file)
			for key, value in client_template.items():
				if not key in self.config:
					self.config[key] = value

	def load_server_config(self):
		"""Load the necessary values from the server's configuration."""
		self.config['server_config'] = self.rpc('config/get', ['server.require_id', 'server.secret_id', 'server.tracking_image'])
		return

	def save_config(self):
		"""Write the client configuration to disk."""
		self.logger.info('writing the client configuration to disk')
		config = copy.copy(self.config)
		for key in self.config.keys():
			if 'password' in key or key == 'server_config':
				del config[key]
		config_file = os.path.expanduser(self.config_file)
		config_file_h = open(config_file, 'wb')
		json.dump(config, config_file_h, sort_keys=True, indent=4)

	def delete_campaign(self):
		"""
		Delete the campaign on the server. A confirmation dialog will be
		displayed before the operation is performed. If the campaign is
		deleted and a new campaign is not selected with
		:py:meth:`.show_campaign_selection`, the client will quit.
		"""
		if not gui_utilities.show_dialog_yes_no('Delete This Campaign?', self, 'This action is irreversible, all campaign data will be lost.'):
			return
		self.rpc('campaign/delete', self.config['campaign_id'])
		if not self.show_campaign_selection():
			gui_utilities.show_dialog_error('A Campaign Must Be Selected', self, 'Now exiting')
			self.client_quit()

	def edit_preferences(self):
		"""
		Display a
		:py:class:`.dialogs.configuration.KingPhisherClientConfigurationDialog`
		instance and saves the configuration to disk if cancel is not selected.
		"""
		dialog = dialogs.KingPhisherClientConfigurationDialog(self.config, self)
		if dialog.interact() != Gtk.ResponseType.CANCEL:
			self.save_config()

	def export_campaign_xml(self):
		"""Export the current campaign to an XML data file."""
		dialog = gui_utilities.UtilityFileChooser('Export Campaign XML Data', self)
		file_name = self.config['campaign_name'] + '.xml'
		response = dialog.run_quick_save(file_name)
		dialog.destroy()
		if not response:
			return
		destination_file = response['target_path']
		export.campaign_to_xml(self.rpc, self.config['campaign_id'], destination_file)

	def show_about_dialog(self):
		"""
		Display the about dialog showing details about the programs version,
		license etc.
		"""
		about_dialog = dialogs.KingPhisherClientAboutDialog(self.config, self)
		about_dialog.interact()

	def show_campaign_graph(self, graph_name):
		"""
		Create a new :py:class:`.CampaignGraph` instance and make it into
		a window. *graph_name* must be the name of a valid, exported
		graph provider.

		:param str graph_name: The name of the graph to make a window of.
		"""
		Klass = graphs.get_graph(graph_name)
		graph_inst = Klass(self.config, self)
		graph_inst.load_graph()
		window = graph_inst.make_window()
		window.show_all()

	def show_campaign_selection(self):
		"""
		Display the campaign selection dialog in a new
		:py:class:`.KingPhisherClientCampaignSelectionDialog` instance.

		:return: The status of the dialog.
		:rtype: bool
		"""
		dialog = dialogs.KingPhisherClientCampaignSelectionDialog(self.config, self)
		return dialog.interact() == Gtk.ResponseType.APPLY

	def start_sftp_client(self):
		"""
		Start the client's preferred sftp client application.
		"""
		if not self.config['sftp_client']:
			gui_utilities.show_dialog_warning('Invalid SFTP Configuration', self, 'An SFTP client is not configured')
			return False
		command = str(self.config['sftp_client'])
		sftp_bin = shlex.split(command)[0]
		if not utilities.which(sftp_bin):
			self.logger.warning('could not locate the sftp binary: ' + sftp_bin)
			gui_utilities.show_dialog_warning('Invalid SFTP Configuration', self, "Could not find the SFTP binary '{0}'".format(sftp_bin))
			return False
		try:
			command = command.format(username=self.config['server_username'], server=self.config['server'])
		except KeyError:
			pass
		self.logger.debug("starting sftp client command: {0}".format(command))
		utilities.start_process(command, wait=False)
		return

	def stop_remote_service(self):
		"""
		Stop the remote King Phisher server. This will request that the
		server stop processing new requests and exit. This will display
		a confirmation dialog before performing the operation. If the
		remote service is stopped, the client will quit.
		"""
		if not gui_utilities.show_dialog_yes_no('Stop The Remote King Phisher Service?', self, 'This will stop the remote King Phisher service and\nnew incoming requests will not be processed.'):
			return
		self.rpc('shutdown')
		self.logger.info('the remote king phisher service has been stopped')
		gui_utilities.show_dialog_error('The Remote Service Has Been Stopped', self, 'Now exiting')
		self.client_quit()
		return
