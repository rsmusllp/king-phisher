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
import logging
import os
import shlex
import shutil
import ssl
import socket
import sys
import uuid

from king_phisher import constants
from king_phisher import errors
from king_phisher import find
from king_phisher import ipaddress
from king_phisher import its
from king_phisher import serializers
from king_phisher import ssh_forward
from king_phisher import utilities
from king_phisher import version
from king_phisher.client import assistants
from king_phisher.client import client_rpc
from king_phisher.client import dialogs
from king_phisher.client import graphs
from king_phisher.client import gui_utilities
from king_phisher.client import plugins
from king_phisher.client import server_events
from king_phisher.client.dialogs import ssh_host_key
from king_phisher.client.windows import main
from king_phisher.client.windows import rpc_terminal
from king_phisher.constants import ConnectionErrorReason

import advancedhttpserver
from gi.repository import Gdk
from gi.repository import Gio
from gi.repository import GLib
from gi.repository import GObject
from gi.repository import Gtk
import paramiko
from smoke_zephyr.utilities import parse_server
from smoke_zephyr.utilities import parse_timespan
from smoke_zephyr.utilities import which

if its.py_v2:
	from httplib import BadStatusLine
else:
	from http.client import BadStatusLine

DISABLED = constants.DISABLED

GTK3_DEFAULT_THEME = 'Adwaita'
"""The default GTK3 Theme for style information."""

USER_DATA_PATH = 'king-phisher'
"""The default folder name for user specific data storage."""

if its.mocked:
	_Gtk_Application = type('Gtk.Application', (object,), {'__module__': ''})
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
	# pylint: disable=too-many-public-methods
	__gsignals__ = {
		'campaign-changed': (GObject.SIGNAL_RUN_FIRST, None, (str,)),
		'campaign-created': (GObject.SIGNAL_RUN_FIRST, None, (str,)),
		'campaign-delete': (GObject.SIGNAL_ACTION | GObject.SIGNAL_RUN_LAST, None, (str,)),
		'campaign-set': (GObject.SIGNAL_RUN_FIRST, None, (str, str)),
		'config-load': (GObject.SIGNAL_ACTION | GObject.SIGNAL_RUN_LAST, None, (bool,)),
		'config-save': (GObject.SIGNAL_ACTION | GObject.SIGNAL_RUN_LAST, None, ()),
		'credential-delete': (GObject.SIGNAL_ACTION | GObject.SIGNAL_RUN_LAST, None, (object,)),
		'exit': (GObject.SIGNAL_ACTION | GObject.SIGNAL_RUN_LAST, None, ()),
		'exit-confirm': (GObject.SIGNAL_ACTION | GObject.SIGNAL_RUN_LAST, None, ()),
		'message-delete': (GObject.SIGNAL_ACTION | GObject.SIGNAL_RUN_LAST, None, (object,)),
		'message-sent': (GObject.SIGNAL_RUN_FIRST, None, (str, str)),
		'reload-css-style': (GObject.SIGNAL_ACTION | GObject.SIGNAL_RUN_LAST, None, ()),
		'rpc-cache-clear': (GObject.SIGNAL_ACTION | GObject.SIGNAL_RUN_LAST, None, ()),
		'server-connected': (GObject.SIGNAL_RUN_FIRST, None, ()),
		'server-disconnected': (GObject.SIGNAL_RUN_FIRST, None, ()),
		'sftp-client-start': (GObject.SIGNAL_ACTION | GObject.SIGNAL_RUN_LAST, None, ()),
		'visit-delete': (GObject.SIGNAL_ACTION | GObject.SIGNAL_RUN_LAST, None, (object,)),
		'unhandled-exception': (GObject.SIGNAL_RUN_FIRST, None, (object, object))
	}
	def __init__(self, config_file=None, use_plugins=True, use_style=True):
		super(KingPhisherClientApplication, self).__init__()
		if use_style:
			gtk_version = (Gtk.get_major_version(), Gtk.get_minor_version())
			if gtk_version > (3, 18):
				self._theme_file = 'theme.v2.css'
			else:
				self._theme_file = 'theme.v1.css'
		else:
			self._theme_file = DISABLED
		self.user_data_path = os.path.join(GLib.get_user_config_dir(), USER_DATA_PATH)
		self.logger = logging.getLogger('KingPhisher.Client.Application')
		# log version information for debugging purposes
		self.logger.debug("gi.repository GLib version: {0}".format('.'.join(map(str, GLib.glib_version))))
		self.logger.debug("gi.repository GObject version: {0}".format('.'.join(map(str, GObject.pygobject_version))))
		self.logger.debug("gi.repository Gtk version: {0}.{1}.{2}".format(Gtk.get_major_version(), Gtk.get_minor_version(), Gtk.get_micro_version()))
		if rpc_terminal.has_vte:
			self.logger.debug("gi.repository VTE version: {0}".format(rpc_terminal.Vte._version))
		if graphs.has_matplotlib:
			self.logger.debug("matplotlib version: {0}".format(graphs.matplotlib.__version__))
		# do not negotiate a single instance application
		# https://developer.gnome.org/gio/unstable/GApplication.html#G-APPLICATION-NON-UNIQUE:CAPS
		self.set_flags(Gio.ApplicationFlags.NON_UNIQUE)
		self.set_property('application-id', 'org.king-phisher.client')
		self.set_property('register-session', True)
		self.config_file = config_file or os.path.join(self.user_data_path, 'config.json')
		"""The file containing the King Phisher client configuration."""
		if not os.path.isfile(self.config_file):
			self._create_config()
		self.config = None
		"""The primary King Phisher client configuration."""
		self.main_window = None
		"""The primary top-level :py:class:`~.MainAppWindow` instance."""
		self.references = []
		"""A list to store references to arbitrary objects in for avoiding garbage collection."""
		self.rpc = None
		"""The :py:class:`~.KingPhisherRPCClient` instance for the application."""
		self._rpc_ping_event = None
		# this will be populated when the RPC object is authenticated to ping
		# the server periodically and keep the session alive
		self.server_events = None
		"""The :py:class:`~.ServerEventSubscriber` instance for the application to receive server events."""
		self._ssh_forwarder = None
		"""The SSH forwarder responsible for tunneling RPC communications."""
		self.style_provider = None
		try:
			self.emit('config-load', True)
		except IOError:
			self.logger.critical('failed to load the client configuration')
			raise

		self.connect('window-added', self.signal_window_added)
		self.actions = {}
		self._create_actions()

		if not use_plugins:
			self.logger.info('disabling all plugins')
			self.config['plugins.enabled'] = []
		self.plugin_manager = plugins.ClientPluginManager(
			[os.path.join(self.user_data_path, 'plugins'), find.data_directory('plugins')],
			self
		)
		if use_plugins:
			self.plugin_manager.load_all()

	def _create_actions(self):
		action = Gio.SimpleAction.new('emit-application-signal', GLib.VariantType.new('s'))
		action.connect('activate', self.action_emit_application_signal)
		accelerators = (
			('<Control><Shift>F1', 'rpc-cache-clear'),
			('<Control><Shift>F2', 'config-save'),
			('<Control><Shift>F12', 'reload-css-style')
		)
		for key, signal_name in accelerators:
			if Gtk.check_version(3, 14, 0):
				self.add_accelerator(key, 'win.emit-application-signal', GLib.Variant.new_string(signal_name))
			else:
				self.set_accels_for_action("win.emit-application-signal('{0}')".format(signal_name), (key,))
		self.actions['emit-application-signal'] = action
		self.add_action(action)

	def _create_ssh_forwarder(self, server, username, password, window=None):
		"""
		Create and set the
		:py:attr:`~.KingPhisherClientApplication._ssh_forwarder` attribute.

		:param tuple server: The server information as a host and port tuple.
		:param str username: The username to authenticate to the SSH server with.
		:param str password: The password to authenticate to the SSH server with.
		:param window: The GTK window to use as the parent for error dialogs.
		:type window: :py:class:`Gtk.Window`
		:rtype: int
		:return: The local port that is forwarded to the remote server or None if the connection failed.
		"""
		window = window or self.get_active_window()
		title_ssh_error = 'Failed To Connect To The SSH Service'
		server_remote_port = self.config['server_remote_port']

		try:
			self._ssh_forwarder = ssh_forward.SSHTCPForwarder(
				server,
				username,
				password,
				('127.0.0.1', server_remote_port),
				private_key=self.config.get('ssh_preferred_key'),
				missing_host_key_policy=ssh_host_key.MissingHostKeyPolicy(self)
			)
			self._ssh_forwarder.start()
		except ssh_forward.KingPhisherSSHKeyError as error:
			gui_utilities.show_dialog_error('SSH Key Configuration Error', window, error.message)
		except errors.KingPhisherAbortError as error:
			self.logger.info("ssh connection aborted ({0})".format(error.message))
		except paramiko.PasswordRequiredException:
			gui_utilities.show_dialog_error(title_ssh_error, window, 'The specified SSH key requires a password.')
		except paramiko.AuthenticationException:
			self.logger.warning('failed to authenticate to the remote ssh server')
			gui_utilities.show_dialog_error(title_ssh_error, window, 'The server responded that the credentials are invalid.')
		except paramiko.SSHException as error:
			self.logger.warning("failed with ssh exception '{0}'".format(error.args[0]))
		except socket.error as error:
			gui_utilities.show_dialog_exc_socket_error(error, window, title=title_ssh_error)
		except Exception as error:
			self.logger.warning('failed to connect to the remote ssh server', exc_info=True)
			gui_utilities.show_dialog_error(title_ssh_error, window, "An {0}.{1} error occurred.".format(error.__class__.__module__, error.__class__.__name__))
		else:
			return self._ssh_forwarder.local_server
		self.emit('server-disconnected')
		return

	def _create_config(self):
		config_dir = os.path.dirname(self.config_file)
		if not os.path.isdir(config_dir):
			self.logger.debug('creating the user configuration directory')
			os.makedirs(config_dir)
		client_template = find.data_file('client_config.json')
		shutil.copy(client_template, self.config_file)

	def add_reference(self, ref_object):
		"""
		Add *ref_object* to the :py:attr:`.references` so the object won't be
		garbage collected. The object must either be a
		:py:class:`.GladeGObject` or :py:class:`Gtk.Widget` instance so a
		cleanup function can be attached to a ``destroy`` signal to remove the
		reference automatically.

		:param ref_object: The object to store a reference to.
		:type ref_object: :py:class:`.GladeGObject`, :py:class:`Gtk.Widget`
		"""
		utilities.assert_arg_type(ref_object, (gui_utilities.GladeGObject, Gtk.Widget))
		self.references.append(ref_object)
		if isinstance(ref_object, gui_utilities.GladeGObject):
			widget = getattr(ref_object, ref_object.top_gobject)
		else:
			widget = ref_object
		widget.connect('destroy', self.signal_multi_destroy_remove_reference, ref_object)

	def campaign_configure(self):
		assistant = assistants.CampaignAssistant(self, campaign_id=self.config['campaign_id'])
		assistant.assistant.set_transient_for(self.get_active_window())
		assistant.assistant.set_modal(True)
		self.add_reference(assistant)
		assistant.interact()

	def do_campaign_delete(self, campaign_id):
		"""
		Delete the campaign on the server. A confirmation dialog will be
		displayed before the operation is performed. If the campaign is deleted
		and a new campaign is not selected with
		:py:meth:`.show_campaign_selection`, the client will quit.
		"""
		self.rpc('db/table/delete', 'campaigns', campaign_id)
		if campaign_id == self.config['campaign_id'] and not self.show_campaign_selection():
			gui_utilities.show_dialog_error('Now Exiting', self.get_active_window(), 'A campaign must be selected.')
			self.quit()

	def do_credential_delete(self, row_ids):
		if len(row_ids) == 1:
			self.rpc('db/table/delete', 'credentials', row_ids[0])
		else:
			self.rpc('db/table/delete/multi', 'credentials', row_ids)

	def do_message_delete(self, row_ids):
		if len(row_ids) == 1:
			self.rpc('db/table/delete', 'messages', row_ids[0])
		else:
			self.rpc('db/table/delete/multi', 'messages', row_ids)

	def do_visit_delete(self, row_ids):
		if len(row_ids) == 1:
			self.rpc('db/table/delete', 'visits', row_ids[0])
		else:
			self.rpc('db/table/delete/multi', 'visits', row_ids)

	def get_graphql_campaign(self, campaign_id=None):
		"""
		Retrieve the GraphQL representation of the specified campaign. If
		*campaign_id* is not specified, then the data for the current campaign
		is retrieved.

		:param str campaign_id: The ID for the campaign whose information should be retrieved.
		:return: The campaign's GraphQL representation.
		:rtype: dict
		"""
		campaign_id = campaign_id or self.config['campaign_id']
		campaign = self.rpc.graphql_find_file('get_campaign.graphql', id=campaign_id)
		return campaign['db']['campaign']

	def exception_hook(self, exc_type, exc_value, exc_traceback):
		if isinstance(exc_value, KeyboardInterrupt):
			self.logger.warning('received a KeyboardInterrupt exception')
			return
		exc_info = (exc_type, exc_value, exc_traceback)
		error_uid = uuid.uuid4()
		self.logger.error("error uid: {0} an unhandled exception was thrown".format(str(error_uid)), exc_info=exc_info)
		self.emit('unhandled-exception', exc_info, error_uid)

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
		settings.set_property('gtk-application-prefer-dark-theme', False)

		# load a custom css theme file if one is available
		theme_file = self.theme_file
		if theme_file:
			self.style_provider = self.load_style_css(theme_file)
		elif theme_file is DISABLED:
			self.logger.debug('no css theme file will be loaded (styling has been disabled)')
		else:
			self.logger.debug('no css theme file will be loaded (file not found)')

		# create and show the main window
		self.main_window = main.MainAppWindow(self.config, self)
		self.main_tabs = self.main_window.tabs

		enabled_plugins = sorted(set(self.config['plugins.enabled']))
		for name in enabled_plugins:
			try:
				self.plugin_manager.load(name)
				self.plugin_manager.enable(name)
			except Exception:
				enabled_plugins.remove(name)
				self.config['plugins.enabled'].remove(name)
				self.logger.info("plugin '{0}' has been disabled".format(name))
				gui_utilities.show_dialog_error(
					'Failed To Enable Plugin',
					self.main_window,
					"Plugin '{0}' could not be enabled.".format(name)
				)
		self.config['plugins.enabled'] = enabled_plugins

	def do_campaign_set(self, *_):
		self.logger.info("campaign set to {0} (id: {1})".format(self.config['campaign_name'], self.config['campaign_id']))
		self.emit('rpc-cache-clear')

	def do_config_save(self):
		self.logger.info('writing the client configuration to disk')
		config = copy.copy(self.config)
		for key in self.config.keys():
			if 'password' in key or key == 'server_config':
				del config[key]
		self.logger.info('writing the config to: ' + self.config_file)
		with open(self.config_file, 'w') as config_file_h:
			serializers.JSON.dump(config, config_file_h, pretty=True)

	def do_exit(self):
		self.plugin_manager.shutdown()
		self.main_window.hide()
		gui_utilities.gtk_widget_destroy_children(self.main_window)
		gui_utilities.gtk_sync()
		self.emit('server-disconnected')
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
		theme_file = self.theme_file
		if theme_file:
			self.style_provider = self.load_style_css(theme_file)

	def do_rpc_cache_clear(self):
		if not self.rpc:
			return
		self.rpc.cache_clear()
		self.logger.debug('the rpc cache has been cleared')

	def do_server_connected(self):
		self.load_server_config()
		campaign_id = self.config.get('campaign_id')
		campaign = self.get_graphql_campaign() if campaign_id else None
		if not campaign:
			if not self.show_campaign_selection():
				self.logger.debug('no campaign selected, disconnecting and exiting')
				self.emit('exit')
				return True
			campaign = self.get_graphql_campaign()
		self.config['campaign_name'] = campaign['name']
		self.emit('campaign-set', None, self.config['campaign_id'])
		return

	def do_shutdown(self):
		Gtk.Application.do_shutdown(self)
		sys.excepthook = sys.__excepthook__
		self.emit('config-save')

	def do_unhandled_exception(self, exc_info, error_uid):
		dialogs.ExceptionDialog.interact_on_idle(self, exc_info=exc_info, error_uid=error_uid)

	@property
	def theme_file(self):
		if not self._theme_file:
			return DISABLED
		return find.data_file(os.path.join('style', self._theme_file))

	def do_config_load(self, load_defaults):
		"""
		Load the client configuration from disk and set the
		:py:attr:`~.KingPhisherClientApplication.config` attribute.

		:param bool load_defaults: Load missing options from the template configuration file.
		"""
		self.logger.info('loading the config from disk')
		client_template = find.data_file('client_config.json')
		self.logger.info('loading the config from: ' + self.config_file)
		with open(self.config_file, 'r') as tmp_file:
			self.config = serializers.JSON.load(tmp_file)
		if load_defaults:
			with open(client_template, 'r') as tmp_file:
				client_template = serializers.JSON.load(tmp_file)
			for key, value in client_template.items():
				if not key in self.config:
					self.config[key] = value

	def merge_config(self, config_file, strict=True):
		"""
		Merge the configuration information from the specified configuration
		file. Only keys which exist in the currently loaded configuration are
		copied over while non-existent keys are skipped. The contents of the new
		configuration overwrites the existing.

		:param bool strict: Do not try remove trailing commas from the JSON data.
		:param str config_file: The path to the configuration file to merge.
		"""
		with open(config_file, 'r') as tmp_file:
			config = serializers.JSON.load(tmp_file, strict=strict)
		if not isinstance(config, dict):
			self.logger.error("can not merge configuration file: {0} (invalid format)".format(config_file))
			return
		self.logger.debug('merging configuration information from source file: ' + config_file)
		for key, value in config.items():
			if not key in self.config:
				self.logger.warning("skipped merging non-existent configuration key {0}".format(key))
				continue
			self.config[key] = value
		return

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

	def server_connect(self, username, password, otp=None, window=None):
		"""
		Initialize the connection to the King Phisher server.

		:param str username: The username to authenticate with.
		:param str password: The password to authenticate with.
		:param str otp: The optional one-time password to authenticate with.
		:param window: The GTK window to use as the parent for error dialogs.
		:type window: :py:class:`Gtk.Window`
		:rtype: tuple
		"""
		# pylint: disable=too-many-locals
		server_version_info = None
		title_rpc_error = 'Failed To Connect To The King Phisher RPC Service'
		window = window or self.get_active_window()

		server = parse_server(self.config['server'], 22)
		if ipaddress.is_loopback(server[0]):
			local_server = ('localhost', self.config['server_remote_port'])
			self.logger.info("connecting to local king phisher instance")
		else:
			local_server = self._create_ssh_forwarder(server, username, password, window=window)
		if not local_server:
			return False, ConnectionErrorReason.ERROR_PORT_FORWARD

		rpc = client_rpc.KingPhisherRPCClient(local_server, use_ssl=self.config.get('server_use_ssl'))
		if self.config.get('rpc.serializer'):
			try:
				rpc.set_serializer(self.config['rpc.serializer'])
			except ValueError as error:
				self.logger.error("failed to set the rpc serializer, error: '{0}'".format(error.message))

		generic_message = 'Can not contact the RPC HTTP service, ensure that the '
		generic_message += "King Phisher Server is currently running on port {0}.".format(int(self.config['server_remote_port']))
		connection_failed = True
		try:
			server_version_info = rpc('version')
			if server_version_info is None:
				raise RuntimeError('no version information was retrieved from the server')
		except advancedhttpserver.RPCError as error:
			self.logger.warning('failed to connect to the remote rpc service due to http status: ' + str(error.status))
			gui_utilities.show_dialog_error(title_rpc_error, window, "The server responded with HTTP status: {0}.".format(str(error.status)))
		except BadStatusLine as error:
			self.logger.warning('failed to connect to the remote rpc service due to http bad status line: ' + error.line)
			gui_utilities.show_dialog_error(title_rpc_error, window, generic_message)
		except socket.error as error:
			self.logger.debug('failed to connect to the remote rpc service due to a socket error', exc_info=True)
			gui_utilities.show_dialog_exc_socket_error(error, window)
		except ssl.CertificateError as error:
			self.logger.warning('failed to connect to the remote rpc service with a https certificate error: ' + error.message)
			gui_utilities.show_dialog_error(title_rpc_error, window, 'The server presented an invalid SSL certificate.')
		except Exception:
			self.logger.warning('failed to connect to the remote rpc service', exc_info=True)
			gui_utilities.show_dialog_error(title_rpc_error, window, generic_message)
		else:
			connection_failed = False

		if connection_failed:
			self.emit('server-disconnected')
			return False, ConnectionErrorReason.ERROR_CONNECTION

		server_rpc_api_version = server_version_info.get('rpc_api_version', -1)
		if isinstance(server_rpc_api_version, int):
			# compatibility with pre-0.2.0 version
			server_rpc_api_version = (server_rpc_api_version, 0)
		self.logger.info(
			"successfully connected to the king phisher server (version: {0} rpc api version: {1}.{2})".format(
				server_version_info['version'],
				server_rpc_api_version[0],
				server_rpc_api_version[1]
			)
		)

		error_text = None
		if server_rpc_api_version[0] < version.rpc_api_version.major or (server_rpc_api_version[0] == version.rpc_api_version.major and server_rpc_api_version[1] < version.rpc_api_version.minor):
			error_text = 'The server is running an old and incompatible version.'
			error_text += '\nPlease update the remote server installation.'
		elif server_rpc_api_version[0] > version.rpc_api_version.major:
			error_text = 'The client is running an old and incompatible version.'
			error_text += '\nPlease update the local client installation.'
		if error_text:
			gui_utilities.show_dialog_error('The RPC API Versions Are Incompatible', window, error_text)
			self.emit('server-disconnected')
			return False, ConnectionErrorReason.ERROR_INCOMPATIBLE_VERSIONS

		login_result, login_reason = rpc.login(username, password, otp)
		if not login_result:
			self.logger.warning('failed to authenticate to the remote king phisher service, reason: ' + login_reason)
			self.emit('server-disconnected')
			return False, login_reason
		rpc.username = username
		self.logger.debug('successfully authenticated to the remote king phisher service')
		self._rpc_ping_event = GLib.timeout_add_seconds(parse_timespan('5m'), rpc.ping)

		self.rpc = rpc
		event_subscriber = server_events.ServerEventSubscriber(rpc)
		if not event_subscriber.is_connected:
			self.logger.error('failed to connect the server event socket')
			event_subscriber.reconnect = False
			event_subscriber.shutdown()
			return False, ConnectionErrorReason.ERROR_UNKNOWN
		self.server_events = event_subscriber
		self.emit('server-connected')
		return True, ConnectionErrorReason.SUCCESS

	def do_server_disconnected(self):
		"""
		Clean up the connections to the server and disconnect. This logs out
		of the RPC, closes the server event socket, and stops the SSH
		forwarder.
		"""
		if self.rpc is not None:
			if self.server_events is not None:
				self.server_events.reconnect = False
			GLib.source_remove(self._rpc_ping_event)
			try:
				self.rpc('logout')
			except advancedhttpserver.RPCError as error:
				self.logger.warning('failed to logout, rpc error: ' + error.message)
			else:
				if self.server_events is not None:
					self.server_events.shutdown()
					self.server_events = None
			self.rpc = None

		if self._ssh_forwarder:
			self._ssh_forwarder.stop()
			self._ssh_forwarder = None
		return

	def show_campaign_graph(self, graph_name):
		"""
		Create a new :py:class:`.CampaignGraph` instance and make it into
		a window. *graph_name* must be the name of a valid, exported
		graph provider.

		:param str graph_name: The name of the graph to make a window of.
		"""
		cls = graphs.get_graph(graph_name)
		graph_inst = cls(self, style_context=self.style_context)
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
			self.emit('config-save')

	def signal_css_provider_parsing_error(self, css_provider, css_section, gerror):
		file_path = css_section.get_file()
		if file_path:
			file_path = file_path.get_path()
		else:
			file_path = '[ unknown file ]'
		self.logger.error("css parser error ({0}) in {1}:{2}".format(gerror.message, file_path, css_section.get_start_line() + 1))
		return

	def signal_multi_destroy_remove_reference(self, widget, ref_object):
		self.references.remove(ref_object)

	def signal_window_added(self, _, window):
		for action in self.actions.values():
			window.add_action(action)

	def do_sftp_client_start(self):
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
		active_window = self.get_active_window()
		if not gui_utilities.show_dialog_yes_no('Stop The Remote King Phisher Service?', active_window, 'This will stop the remote King Phisher service and\nnew incoming requests will not be processed.'):
			return
		self.rpc('shutdown')
		self.logger.info('the remote king phisher service has been stopped')
		gui_utilities.show_dialog_error('Now Exiting', active_window, 'The remote service has been stopped.')
		self.quit()
		return

	@property
	def style_context(self):
		window = self.get_active_window() or self.main_window
		if window is None:
			return None
		return window.get_style_context()
