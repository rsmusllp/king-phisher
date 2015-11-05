#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  king_phisher/client/application.py
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
import ipaddress
import logging
import os
import shlex
import shutil
import ssl
import socket
import sys
import uuid

from king_phisher import find
from king_phisher import json_ex
from king_phisher import utilities
from king_phisher import version
from king_phisher.client import assistants
from king_phisher.client import client_rpc
from king_phisher.client import dialogs
from king_phisher.client import graphs
from king_phisher.client import gui_utilities
from king_phisher.client.windows import main
from king_phisher.client.windows import rpc_terminal
from king_phisher.constants import ConnectionErrorReason
from king_phisher.ssh_forward import SSHTCPForwarder
from king_phisher.third_party.AdvancedHTTPServer import AdvancedHTTPServerRPCError

from gi.repository import Gdk
from gi.repository import Gio
from gi.repository import GLib
from gi.repository import GObject
from gi.repository import Gtk
import paramiko
from smoke_zephyr.utilities import parse_server
from smoke_zephyr.utilities import which

CONFIG_FILE_PATH = os.path.join(GLib.get_user_config_dir(), 'king-phisher', 'config.json')
"""The default search location for the client configuration file."""
GTK3_DEFAULT_THEME = 'Adwaita'
"""The default GTK3 Theme for style information."""

if isinstance(Gtk.Application, utilities.Mock):
	_Gtk_Application = type('Gtk.Application', (object,), {})
	_Gtk_Application.__module__ = ''
else:
	_Gtk_Application = Gtk.Application

class KingPhisherClientApplication(_Gtk_Application):
	"""
	This is the top level King Phisher client object. It contains the
	custom GObject signals, keeps all the GUI references, and manages
	the RPC client object. This is also the parent window for most
	GTK objects.

	:GObject Signals: :ref:`gobject-signals-application-label`
	"""
	__gsignals__ = {
		'campaign-changed': (GObject.SIGNAL_RUN_FIRST, None, (str,)),
		'campaign-set': (GObject.SIGNAL_RUN_FIRST, None, (str,)),
		'exit': (GObject.SIGNAL_RUN_LAST, None, ()),
		'exit-confirm': (GObject.SIGNAL_RUN_LAST, None, ()),
		'reload-css-style': (GObject.SIGNAL_RUN_FIRST, None, ()),
		'rpc-cache-clear': (GObject.SIGNAL_RUN_FIRST, None, ()),
		'server-connected': (GObject.SIGNAL_RUN_LAST, None, ())
	}
	def __init__(self, config_file=None):
		super(KingPhisherClientApplication, self).__init__()
		self.logger = logging.getLogger('KingPhisher.Client.Application')
		# log version information for debugging purposes
		self.logger.debug("gi.repository GLib version: {0}".format('.'.join(map(str, GLib.glib_version))))
		self.logger.debug("gi.repository GObject version: {0}".format('.'.join(map(str, GObject.pygobject_version))))
		self.logger.debug("gi.repository Gtk version: {0}.{1}.{2}".format(Gtk.get_major_version(), Gtk.get_minor_version(), Gtk.get_micro_version()))
		if rpc_terminal.has_vte:
			self.logger.debug("gi.repository VTE version: {0}".format(rpc_terminal.Vte._version))
		if graphs.has_matplotlib:
			self.logger.debug("matplotlib version: {0}".format(graphs.matplotlib.__version__))
		self.set_property('application-id', 'org.king-phisher.client')
		self.set_property('register-session', True)
		self.config_file = CONFIG_FILE_PATH
		"""The file containing the King Phisher client configuration."""
		if not os.path.isfile(self.config_file):
			self._create_config()
		self.config = None
		"""The primary King Phisher client configuration."""
		self.main_window = None
		"""The primary top-level :py:class:`~.MainAppWindow` instance."""
		self.rpc = None
		"""The :py:class:`~.KingPhisherRPCClient` instance for the application."""
		self._ssh_forwarder = None
		"""The SSH forwarder responsible for tunneling RPC communications."""
		self.style_provider = None
		try:
			self.load_config(load_defaults=True)
		except IOError:
			self.logger.critical('failed to load the client configuration')
			raise

		self.connect('window-added', self.signal_window_added)
		self.actions = {}
		self._create_actions()

	def _create_actions(self):
		action = Gio.SimpleAction.new('emit-application-signal', GLib.VariantType.new('s'))
		action.connect('activate', self.action_emit_application_signal)
		accelerators = (
			('<Control><Shift>F1', 'rpc-cache-clear'),
			('<Control><Shift>F12', 'reload-css-style')
		)
		for key, signal_name in accelerators:
			if Gtk.check_version(3, 14, 0):
				self.add_accelerator(key, 'win.emit-application-signal', GLib.Variant.new_string(signal_name))
			else:
				self.set_accels_for_action("win.emit-application-signal('{0}')".format(signal_name), (key,))
		self.actions['emit-application-signal'] = action
		self.add_action(action)

	def _create_ssh_forwarder(self, server, username, password):
		"""
		Create and set the
		:py:attr:`~.KingPhisherClientApplication._ssh_forwarder` attribute.

		:param tuple server: The server information as a host and port tuple.
		:param str username: The username to authenticate to the SSH server with.
		:param str password: The password to authenticate to the SSH server with.
		:rtype: int
		:return: The local port that is forwarded to the remote server or None if the connection failed.
		"""
		active_window = self.get_active_window()
		title_ssh_error = 'Failed To Connect To The SSH Service'
		server_remote_port = self.config['server_remote_port']

		try:
			self._ssh_forwarder = SSHTCPForwarder(server, username, password, ('127.0.0.1', server_remote_port), preferred_private_key=self.config['ssh_preferred_key'])
			self._ssh_forwarder.start()
		except paramiko.AuthenticationException:
			self.logger.warning('failed to authenticate to the remote ssh server')
			gui_utilities.show_dialog_error(title_ssh_error, active_window, 'The server responded that the credentials are invalid.')
		except socket.error as error:
			gui_utilities.show_dialog_exc_socket_error(error, active_window, title=title_ssh_error)
		except Exception as error:
			self.logger.warning('failed to connect to the remote ssh server', exc_info=True)
			gui_utilities.show_dialog_error(title_ssh_error, active_window, "An {0}.{1} error occurred.".format(error.__class__.__module__, error.__class__.__name__))
		else:
			self.logger.info("started ssh port forwarding to the remote king phisher server ({0})".format(str(self._ssh_forwarder)))
			return self._ssh_forwarder.local_server
		self.server_disconnect()
		return

	def _create_config(self):
		config_dir = os.path.dirname(self.config_file)
		if not os.path.isdir(config_dir):
			self.logger.debug('creating the user configuration directory')
			os.makedirs(config_dir)
		# move the pre 1.0.0 config file if it exists
		old_path = os.path.expanduser('~/.king_phisher.json')
		if os.path.isfile(old_path) and os.access(old_path, os.R_OK):
			self.logger.debug('moving the old config file to the new location')
			os.rename(old_path, self.config_file)
		else:
			client_template = find.find_data_file('client_config.json')
			shutil.copy(client_template, self.config_file)

	def campaign_configure(self):
		assistant = assistants.CampaignAssistant(self, campaign_id=self.config['campaign_id'])
		assistant.assistant.set_transient_for(self.get_active_window())
		assistant.assistant.set_modal(True)

		# do this to keep a reference to prevent garbage collection
		attr_name = '_tmpref_campaign_assistant'
		setattr(self, attr_name, assistant)
		assistant.assistant.connect('destroy', lambda widget: delattr(self, attr_name))

		assistant.interact()

	def campaign_delete(self):
		"""
		Delete the campaign on the server. A confirmation dialog will be
		displayed before the operation is performed. If the campaign is
		deleted and a new campaign is not selected with
		:py:meth:`.show_campaign_selection`, the client will quit.
		"""
		if not gui_utilities.show_dialog_yes_no('Delete This Campaign?', self.get_active_window(), 'This action is irreversible, all campaign data will be lost.'):
			return
		self.rpc('db/table/delete', 'campaigns', self.config['campaign_id'])
		if not self.show_campaign_selection():
			gui_utilities.show_dialog_error('Now Exiting', self.get_active_window(), 'A campaign must be selected.')
			self.quit()

	def campaign_rename(self):
		"""
		Show a dialog prompting the user to for the a new name to assign to the
		currently selected campaign.
		"""
		campaign = self.rpc.remote_table_row('campaigns', self.config['campaign_id'])
		prompt = dialogs.TextEntryDialog.build_prompt(self, 'Rename Campaign', 'Enter the new campaign name:', campaign.name)
		response = prompt.interact()
		if response == None or response == campaign.name:
			return
		self.rpc('db/table/set', 'campaigns', self.config['campaign_id'], 'name', response)
		gui_utilities.show_dialog_info('Campaign Name Updated', self.get_active_window(), 'The campaign name was successfully changed.')

	def exception_hook(self, exc_type, exc_value, exc_traceback):
		if isinstance(exc_value, KeyboardInterrupt):
			self.logger.warning('received a KeyboardInterrupt exception')
			return
		exc_info = (exc_type, exc_value, exc_traceback)
		error_uid = str(uuid.uuid4())
		self.logger.error("error uid: {0} an unhandled exception was thrown".format(error_uid), exc_info=exc_info)
		dialogs.ExceptionDialog(self, exc_info=exc_info, error_uid=error_uid).interact()

	def quit(self, optional=False):
		"""
		Quit the client and perform any necessary clean up operations. If
		*optional* is False then the exit-confirm signal will not be sent and
		there will not be any opportunities for the client to cancel the
		operation.

		:param bool optional: Whether the quit is request is optional or not.
		"""
		self.emit('exit-confirm' if optional else 'exit')

	def action_emit_application_signal(self, _, signal_name):
		signal_name = signal_name.get_string()
		self.logger.debug('action emit-application-signal invoked for ' + signal_name)
		self.emit(signal_name)

	def do_activate(self):
		Gtk.Application.do_activate(self)
		sys.excepthook = self.exception_hook

		# reset theme settings to defaults so we have a standard baseline
		settings = Gtk.Settings.get_default()
		if settings.get_property('gtk-theme-name') != GTK3_DEFAULT_THEME:
			self.logger.debug('resetting the gtk-theme-name property to it\'s default value')
			settings.set_property('gtk-theme-name', GTK3_DEFAULT_THEME)
		if settings.get_property('gtk-icon-theme-name') != GTK3_DEFAULT_THEME:
			self.logger.debug('resetting the gtk-icon-theme-name property to it\'s default value')
			settings.set_property('gtk-icon-theme-name', GTK3_DEFAULT_THEME)

		# load a custom css file if one is available
		css_file = self.theme_file
		if css_file:
			self.style_provider = self.load_style_css(css_file)
		else:
			self.logger.debug('no custom css file was found')

		# create and show the main window
		self.main_window = main.MainAppWindow(self.config, self)
		self.main_window.set_position(Gtk.WindowPosition.CENTER)
		self.main_window.show()

	def do_campaign_changed(self, campaign_id):
		pass

	def do_campaign_set(self, campaign_id):
		self.logger.info("campaign set to {0} (id: {1})".format(self.config['campaign_name'], self.config['campaign_id']))
		self.emit('rpc-cache-clear')

	def do_exit(self):
		self.main_window.hide()
		gui_utilities.gtk_widget_destroy_children(self.main_window)
		gui_utilities.gtk_sync()
		self.server_disconnect()
		self.main_window.destroy()
		return

	def do_exit_confirm(self):
		self.emit('exit')

	def do_reload_css_style(self):
		if self.style_provider:
			Gtk.StyleContext.remove_provider_for_screen(
				Gdk.Screen.get_default(),
				self.style_provider
			)
			self.style_provider = None
		css_file = self.theme_file
		if css_file:
			self.style_provider = self.load_style_css(css_file)

	def do_rpc_cache_clear(self):
		if self.rpc:
			self.rpc.cache_clear()

	def do_server_connected(self):
		self.load_server_config()
		campaign_id = self.config.get('campaign_id')
		if campaign_id is None:
			if not self.show_campaign_selection():
				self.logger.debug('no campaign selected, disconnecting and exiting')
				self.emit('exit')
				return True
		campaign_info = self.rpc.remote_table_row('campaigns', self.config['campaign_id'], cache=True)
		if campaign_info is None:
			if not self.show_campaign_selection():
				self.logger.debug('no campaign selected, disconnecting and exiting')
				self.emit('exit')
				return True
			campaign_info = self.rpc.remote_table_row('campaigns', self.config['campaign_id'], cache=True, refresh=True)
		self.config['campaign_name'] = campaign_info.name
		self.emit('campaign-set', self.config['campaign_id'])
		return

	def do_shutdown(self):
		Gtk.Application.do_shutdown(self)
		sys.excepthook = sys.__excepthook__
		self.save_config()

	@property
	def theme_file(self):
		return find.find_data_file(os.path.join('style', 'theme.css'))

	def load_config(self, load_defaults=False):
		"""
		Load the client configuration from disk and set the
		:py:attr:`~.KingPhisherClientApplication.config` attribute.

		:param bool load_defaults: Load missing options from the template configuration file.
		"""
		self.logger.info('loading the config from disk')
		client_template = find.find_data_file('client_config.json')
		config_file = os.path.expanduser(self.config_file)
		with open(config_file, 'r') as tmp_file:
			self.config = json_ex.load(tmp_file)
		if load_defaults:
			with open(client_template, 'r') as tmp_file:
				client_template = json_ex.load(tmp_file)
			for key, value in client_template.items():
				if not key in self.config:
					self.config[key] = value

	def load_server_config(self):
		"""Load the necessary values from the server's configuration."""
		self.config['server_config'] = self.rpc('config/get', ['server.require_id', 'server.secret_id', 'server.tracking_image', 'server.web_root'])
		return

	def load_style_css(self, css_file):
		self.logger.debug('loading style from css file: ' + css_file)
		css_file = Gio.File.new_for_path(css_file)
		style_provider = Gtk.CssProvider()
		style_provider.connect('parsing-error', self.signal_css_provider_parsing_error)
		try:
			style_provider.load_from_file(css_file)
		except GLib.Error:  # pylint: disable=catching-non-exception
			self.logger.error('there was an error parsing the css file, it will not be applied as a style provider')
			return None
		Gtk.StyleContext.add_provider_for_screen(
			Gdk.Screen.get_default(),
			style_provider,
			Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
		)
		return style_provider

	def save_config(self):
		"""Write the client configuration to disk."""
		self.logger.info('writing the client configuration to disk')
		config = copy.copy(self.config)
		for key in self.config.keys():
			if 'password' in key or key == 'server_config':
				del config[key]
		with open(os.path.expanduser(self.config_file), 'w') as config_file_h:
			json_ex.dump(config, config_file_h)

	def server_connect(self, username, password, otp=None):
		# pylint: disable=too-many-locals
		server_version_info = None
		title_rpc_error = 'Failed To Connect To The King Phisher RPC Service'
		active_window = self.get_active_window()

		server = parse_server(self.config['server'], 22)
		if server[0] == 'localhost' or (utilities.is_valid_ip_address(server[0]) and ipaddress.ip_address(server[0]).is_loopback):
			local_server = ('localhost', self.config['server_remote_port'])
			self.logger.info("connecting to local king phisher instance")
		else:
			local_server = self._create_ssh_forwarder(server, username, password)
		if not local_server:
			return False, ConnectionErrorReason.ERROR_PORT_FORWARD

		rpc = client_rpc.KingPhisherRPCClient(local_server, use_ssl=self.config.get('server_use_ssl'))
		if self.config.get('rpc.serializer'):
			try:
				rpc.set_serializer(self.config['rpc.serializer'])
			except ValueError as error:
				self.logger.error("failed to set the rpc serializer, error: '{0}'".format(error.message))

		connection_failed = True
		try:
			server_version_info = rpc('version')
			assert server_version_info is not None
		except AdvancedHTTPServerRPCError as error:
			self.logger.warning('failed to connect to the remote rpc service with http status: ' + str(error.status))
			gui_utilities.show_dialog_error(title_rpc_error, active_window, "The server responded with HTTP status: {0}.".format(str(error.status)))
		except socket.error as error:
			gui_utilities.show_dialog_exc_socket_error(error, active_window)
		except ssl.CertificateError as error:
			self.logger.warning('failed to connect to the remote rpc service with a https certificate error: ' + error.message)
			gui_utilities.show_dialog_error(title_rpc_error, active_window, 'The server presented an invalid SSL certificate.')
		except Exception:
			self.logger.warning('failed to connect to the remote rpc service', exc_info=True)
			gui_utilities.show_dialog_error(title_rpc_error, active_window, 'Ensure that the King Phisher Server is currently running.')
		else:
			connection_failed = False

		if connection_failed:
			self.server_disconnect()
			return False, ConnectionErrorReason.ERROR_CONNECTION

		server_rpc_api_version = server_version_info.get('rpc_api_version', -1)
		if isinstance(server_rpc_api_version, int):
			# compatibility with pre-0.2.0 version
			server_rpc_api_version = (server_rpc_api_version, 0)
		self.logger.info("successfully connected to the king phisher server (version: {0} rpc api version: {1}.{2})".format(server_version_info['version'], server_rpc_api_version[0], server_rpc_api_version[1]))

		error_text = None
		if server_rpc_api_version[0] < version.rpc_api_version.major or (server_rpc_api_version[0] == version.rpc_api_version.major and server_rpc_api_version[1] < version.rpc_api_version.minor):
			error_text = 'The server is running an old and incompatible version.'
			error_text += '\nPlease update the remote server installation.'
		elif server_rpc_api_version[0] > version.rpc_api_version.major:
			error_text = 'The client is running an old and incompatible version.'
			error_text += '\nPlease update the local client installation.'
		if error_text:
			gui_utilities.show_dialog_error('The RPC API Versions Are Incompatible', active_window, error_text)
			self.server_disconnect()
			return False, ConnectionErrorReason.ERROR_INCOMPATIBLE_VERSIONS

		login_result, login_reason = rpc.login(username, password, otp)
		if not login_result:
			self.logger.warning('failed to authenticate to the remote king phisher service, reason: ' + login_reason)
			self.server_disconnect()
			return False, login_reason

		self.rpc = rpc
		self.emit('server-connected')
		return True, ConnectionErrorReason.SUCCESS

	def server_disconnect(self):
		"""Clean up the SSH TCP connections and disconnect from the server."""
		if self.rpc is not None:
			try:
				self.rpc('logout')
			except AdvancedHTTPServerRPCError as error:
				self.logger.warning('failed to logout, rpc error: ' + error.message)
			self.rpc = None
		if self._ssh_forwarder:
			self._ssh_forwarder.stop()
			self._ssh_forwarder = None
			self.logger.info('stopped ssh port forwarding')
		return

	def show_campaign_graph(self, graph_name):
		"""
		Create a new :py:class:`.CampaignGraph` instance and make it into
		a window. *graph_name* must be the name of a valid, exported
		graph provider.

		:param str graph_name: The name of the graph to make a window of.
		"""
		cls = graphs.get_graph(graph_name)
		graph_inst = cls(self)
		graph_inst.load_graph()
		window = graph_inst.make_window()
		window.show()

	def show_campaign_selection(self):
		"""
		Display the campaign selection dialog in a new
		:py:class:`.CampaignSelectionDialog` instance.

		:return: Whether or not a campaign was selected.
		:rtype: bool
		"""
		dialog = dialogs.CampaignSelectionDialog(self)
		return dialog.interact() == Gtk.ResponseType.APPLY

	def show_preferences(self):
		"""
		Display a
		:py:class:`.dialogs.configuration.ConfigurationDialog`
		instance and saves the configuration to disk if cancel is not selected.
		"""
		dialog = dialogs.ConfigurationDialog(self)
		if dialog.interact() != Gtk.ResponseType.CANCEL:
			self.save_config()

	def signal_css_provider_parsing_error(self, css_provider, css_section, gerror):
		file_path = css_section.get_file()
		if file_path:
			file_path = file_path.get_path()
		else:
			file_path = '[ unknown file ]'
		self.logger.error("css parser error ({0}) in {1}:{2}".format(gerror.message, file_path, css_section.get_start_line()))
		return

	def signal_window_added(self, _, window):
		for action in self.actions.values():
			window.add_action(action)

	def start_sftp_client(self):
		"""
		Start the client's preferred sftp client application in a new process.
		"""
		if not self.config['sftp_client']:
			gui_utilities.show_dialog_error('Invalid SFTP Configuration', self.get_active_window(), 'An SFTP client is not configured.\nOne can be configured in the Client Preferences.')
			return False
		command = str(self.config['sftp_client'])
		sftp_bin = shlex.split(command)[0]
		if not which(sftp_bin):
			self.logger.error('could not locate the sftp binary: ' + sftp_bin)
			gui_utilities.show_dialog_error('Invalid SFTP Configuration', self.get_active_window(), "Could not find the SFTP binary '{0}'".format(sftp_bin))
			return False
		try:
			command = command.format(
				server=self.config['server'],
				username=self.config['server_username'],
				web_root=self.config['server_config']['server.web_root']
			)
		except KeyError as error:
			self.logger.error("key error while parsing the sftp command for token: {0}".format(error.args[0]))
			gui_utilities.show_dialog_error('Invalid SFTP Configuration', self.get_active_window(), "Invalid token '{0}' in the SFTP command.".format(error.args[0]))
			return False
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
		if not gui_utilities.show_dialog_yes_no('Stop The Remote King Phisher Service?', self.get_active_window(), 'This will stop the remote King Phisher service and\nnew incoming requests will not be processed.'):
			return
		self.rpc('shutdown')
		self.logger.info('the remote king phisher service has been stopped')
		gui_utilities.show_dialog_error('Now Exiting', self.get_active_window(), 'The remote service has been stopped.')
		self.quit()
		return
