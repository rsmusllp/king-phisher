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

import ipaddress
import logging
import random
import shlex
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

from gi.repository import GdkPixbuf
from gi.repository import GObject
from gi.repository import Gtk
import paramiko

if isinstance(Gtk.ApplicationWindow, utilities.Mock):
	_Gtk_ApplicationWindow = type('Gtk.ApplicationWindow', (object,), {})
	_Gtk_ApplicationWindow.__module__ = ''
else:
	_Gtk_ApplicationWindow = Gtk.ApplicationWindow

class KingPhisherClient(_Gtk_ApplicationWindow):
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
	def __init__(self, config, application):
		"""
		:param dict config: The main King Phisher client configuration.
		:param application: The application instance to which this window belongs.
		:type application: :py:class:`.KingPhisherClientApplication`
		"""
		assert isinstance(application, Gtk.Application)
		super(KingPhisherClient, self).__init__(application=application)
		self.application = application
		self.logger = logging.getLogger('KingPhisher.Client.MainWindow')
		self.config = config
		"""The main King Phisher client configuration."""
		self._ssh_forwarder = None
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

		mailer_tab = MailSenderTab(self.config, self, self.application)
		self.tabs['mailer'] = mailer_tab
		self.notebook.insert_page(mailer_tab.box, mailer_tab.label, current_page + 1)
		self.notebook.set_current_page(current_page + 1)

		campaign_tab = CampaignViewTab(self.config, self, self.application)
		campaign_tab.box.show()
		self.tabs['campaign'] = campaign_tab
		self.notebook.insert_page(campaign_tab.box, campaign_tab.label, current_page + 2)

		self.set_size_request(800, 600)
		self.connect('delete-event', self.signal_delete_event)
		self.notebook.show()
		self.show()
		self.rpc = None # needs to be initialized last
		"""The :py:class:`.KingPhisherRPCClient` instance."""

		login_dialog = dialogs.LoginDialog(self.config, self)
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

		action = Gtk.Action(name='EditRenameCampaign', label='Rename Campaign', tooltip='Rename Campaign', stock_id=None)
		action.connect('activate', lambda x: self.rename_campaign())
		action_group.add_action(action)

		action = Gtk.Action(name='EditStopService', label='Stop Service', tooltip='Stop The Remote King-Phisher Service', stock_id=None)
		action.connect('activate', lambda x: self.stop_remote_service())
		action_group.add_action(action)

		# Tools Menu Action
		action = Gtk.Action(name='ToolsMenu', label='Tools', tooltip=None, stock_id=None)
		action_group.add_action(action)

		action = Gtk.Action(name='ToolsRPCTerminal', label='RPC Terminal', tooltip='RPC Terminal', stock_id=None)
		action.connect('activate', lambda x: tools.KingPhisherClientRPCTerminal(self.config, self, self.get_property('application')))
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
				graph = graphs.get_graph(graph_name)
				action = Gtk.Action(name=action_name, label=graph.name_human, tooltip=graph.name_human, stock_id=None)
				action.connect('activate', self.signal_activate_popup_menu_create_graph, graph_name)
				action_group.add_action(action)

			merge_id = uimanager.new_merge_id()
			uimanager.add_ui(merge_id, '/MenuBar/ToolsMenu', 'ToolsGraphMenu', 'ToolsGraphMenu', Gtk.UIManagerItemType.MENU, False)
			for graph_name in sorted(graphs.get_graphs(), key=lambda gn: graphs.get_graph(gn).name_human):
				action_name = 'ToolsGraph' + graph_name
				uimanager.add_ui(merge_id, '/MenuBar/ToolsMenu/ToolsGraphMenu', action_name, action_name, Gtk.UIManagerItemType.MENUITEM, False)

		if sys.platform.startswith('linux'):
			action = Gtk.Action(name='ToolsSFTPClient', label='SFTP Client', tooltip='SFTP Client', stock_id=None)
			action.connect('activate', lambda x: self.start_sftp_client())
			action_group.add_action(action)
			merge_id = uimanager.new_merge_id()
			uimanager.add_ui(merge_id, '/MenuBar/ToolsMenu', 'ToolsSFTPClient', 'ToolsSFTPClient', Gtk.UIManagerItemType.MENUITEM, False)

	def _create_ssh_forwarder(self, server, username, password):
		"""
		Create and set the :py:attr:`~.KingPhisherClient._ssh_forwarder`
		attribute.

		:param tuple server: The server information as a host and port tuple.
		:param str username: The username to authenticate to the SSH server with.
		:param str password: The password to authenticate to the SSH server with.
		:rtype: int
		:return: The local port that is forwarded to the remote server or None if the connection failed.
		"""
		title_ssh_error = 'Failed To Connect To The SSH Service'
		server_remote_port = self.config['server_remote_port']
		local_port = random.randint(2000, 6000)

		try:
			self._ssh_forwarder = SSHTCPForwarder(server, username, password, local_port, ('127.0.0.1', server_remote_port), preferred_private_key=self.config['ssh_preferred_key'])
			self._ssh_forwarder.start()
			time.sleep(0.5)
			self.logger.info('started ssh port forwarding')
		except paramiko.AuthenticationException:
			self.logger.warning('failed to authenticate to the remote ssh server')
			gui_utilities.show_dialog_error(title_ssh_error, self, 'The server responded that the credentials are invalid.')
		except socket.timeout:
			gui_utilities.show_dialog_error(title_ssh_error, self, 'The connection to the server timed out.')
		except socket.error as error:
			error_number, error_message = error.args
			if error_number == 111:
				gui_utilities.show_dialog_error(title_ssh_error, self, 'The server refused the connection.')
			else:
				gui_utilities.show_dialog_error(title_ssh_error, self, "Socket error #{0} ({1}).".format((error_number or 'N/A'), error_message))
		except Exception:
			self.logger.warning('failed to connect to the remote ssh server')
			gui_utilities.show_dialog_error(title_ssh_error, self, 'An unknown error occurred.')
		else:
			return local_port
		self.server_disconnect()
		return

	def _create_ui_manager(self):
		uimanager = Gtk.UIManager()
		with open(find.find_data_file('ui_info/client_window.xml')) as ui_info_file:
			ui_data = ui_info_file.read()
		uimanager.add_ui_from_string(ui_data)
		return uimanager

	def signal_activate_popup_menu_create_graph(self, _, graph_name):
		return self.show_campaign_graph(graph_name)

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
		self.destroy()
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
		self.config['campaign_name'] = campaign_info.name
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
		title_rpc_error = 'Failed To Connect To The King Phisher RPC Service'

		if response == Gtk.ResponseType.CANCEL or response == Gtk.ResponseType.DELETE_EVENT:
			dialog.destroy()
			self.emit('exit')
			return True
		glade_dialog.objects_save_to_config()
		server = utilities.server_parse(self.config['server'], 22)
		username = self.config['server_username']
		password = self.config['server_password']
		if server[0] == 'localhost' or (utilities.is_valid_ip_address(server[0]) and ipaddress.ip_address(server[0]).is_loopback):
			local_port = self.config['server_remote_port']
			self.logger.info("connecting to local king-phisher instance")
		else:
			local_port = self._create_ssh_forwarder(server, username, password)
		if not local_port:
			return

		self.rpc = KingPhisherRPCClient(('localhost', local_port), username=username, password=password, use_ssl=self.config.get('server_use_ssl'))
		if self.config.get('rpc.serializer'):
			try:
				self.rpc.set_serializer(self.config['rpc.serializer'])
			except ValueError as error:
				self.logger.error("failed to set the rpc serializer, error: '{0}'".format(error.message))

		connection_failed = True
		try:
			assert self.rpc('client/initialize')
			server_version_info = self.rpc('version')
			assert server_version_info != None
		except AdvancedHTTPServerRPCError as err:
			if err.status == 401:
				self.logger.warning('failed to authenticate to the remote king phisher service')
				gui_utilities.show_dialog_error(title_rpc_error, self, 'The server responded that the credentials are invalid.')
			else:
				self.logger.warning('failed to connect to the remote rpc server with http status: ' + str(err.status))
				gui_utilities.show_dialog_error(title_rpc_error, self, 'The server responded with HTTP status: ' + str(err.status))
		except Exception:
			self.logger.warning('failed to connect to the remote rpc service')
			gui_utilities.show_dialog_error(title_rpc_error, self, 'Ensure that the King Phisher Server is currently running.')
		else:
			connection_failed = False
		finally:
			if connection_failed:
				self.rpc = None
				self.server_disconnect()
				return

		server_rpc_api_version = server_version_info.get('rpc_api_version', -1)
		if isinstance(server_rpc_api_version, int):
			# compatibility with pre-0.2.0 version
			server_rpc_api_version = (server_rpc_api_version, 0)
		self.logger.info("successfully connected to the king phisher server (version: {0} rpc api version: {1}.{2})".format(server_version_info['version'], server_rpc_api_version[0], server_rpc_api_version[1]))
		self.server_local_port = local_port

		secondary_text = None
		if server_rpc_api_version[0] < version.rpc_api_version.major or (server_rpc_api_version[0] == version.rpc_api_version.major and server_rpc_api_version[1] < version.rpc_api_version.minor):
			secondary_text = 'The remote server is not up to date with the client version.'
		elif server_rpc_api_version[0] > version.rpc_api_version.major:
			secondary_text = 'The local client is not up to date with the server version.'
		if secondary_text:
			secondary_text += '\nPlease ensure that both the client and server are fully up to date.'
			gui_utilities.show_dialog_error('The RPC API Versions Are Incompatible', self, secondary_text)
			self.server_disconnect()
			return
		dialog.destroy()
		self.emit('server-connected')
		return

	def server_disconnect(self):
		"""Clean up the SSH TCP connections and disconnect from the server."""
		if self._ssh_forwarder:
			self._ssh_forwarder.stop()
			self._ssh_forwarder = None
			self.logger.info('stopped ssh port forwarding')
		return

	def load_server_config(self):
		"""Load the necessary values from the server's configuration."""
		self.config['server_config'] = self.rpc('config/get', ['server.require_id', 'server.secret_id', 'server.tracking_image'])
		return

	def rename_campaign(self):
		campaign = self.rpc.remote_table_row('campaigns', self.config['campaign_id'])
		prompt = dialogs.TextEntryDialog.build_prompt(self.config, self, 'Rename Campaign', 'Enter the new campaign name:', campaign.name)
		response = prompt.interact()
		if response == None or response == campaign.name:
			return
		self.rpc('campaigns/set', self.config['campaign_id'], ('name',), (response,))
		gui_utilities.show_dialog_info('Campaign Name Updated', self, 'The campaign name was successfully changed')

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
			gui_utilities.show_dialog_error('Now Exiting', self, 'A campaign must be selected.')
			self.client_quit()

	def edit_preferences(self):
		"""
		Display a
		:py:class:`.dialogs.configuration.ConfigurationDialog`
		instance and saves the configuration to disk if cancel is not selected.
		"""
		dialog = dialogs.ConfigurationDialog(self.config, self)
		if dialog.interact() != Gtk.ResponseType.CANCEL:
			app = self.get_property('application')
			app.save_config()

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
		about_dialog = dialogs.AboutDialog(self.config, self)
		about_dialog.interact()

	def show_campaign_graph(self, graph_name):
		"""
		Create a new :py:class:`.CampaignGraph` instance and make it into
		a window. *graph_name* must be the name of a valid, exported
		graph provider.

		:param str graph_name: The name of the graph to make a window of.
		"""
		cls = graphs.get_graph(graph_name)
		graph_inst = cls(self.config, self)
		graph_inst.load_graph()
		window = graph_inst.make_window()
		window.show()

	def show_campaign_selection(self):
		"""
		Display the campaign selection dialog in a new
		:py:class:`.CampaignSelectionDialog` instance.

		:return: The status of the dialog.
		:rtype: bool
		"""
		dialog = dialogs.CampaignSelectionDialog(self.config, self)
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
		gui_utilities.show_dialog_error('Now Exiting', self, 'The remote service has been stopped.')
		self.client_quit()
		return
