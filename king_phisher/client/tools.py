#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  king_phisher/client/tools.py
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

import json
import logging
import os
import select
import signal

from king_phisher import find
from king_phisher import utilities
from king_phisher import version
from king_phisher.client import client_rpc
from king_phisher.client import dialogs
from king_phisher.client import gui_utilities

from gi.repository import GLib
from gi.repository import Gtk

try:
	from gi.repository import Vte
except ImportError:
	has_vte = False
	"""Whether the :py:mod:`gi.repository.Vte` module is available."""
else:
	has_vte = True

class KingPhisherClientRPCTerminal(object):
	"""
	A terminal using VTE that allows raw RPC methods to be called from
	within the King Phisher client. This is primarily useful for
	unofficial and advanced features or debugging and development.
	"""
	def __init__(self, config, parent, application):
		"""
		:param dict config: The King Phisher client configuration.
		:param parent: The parent window for this object.
		:type parent: :py:class:`Gtk.Window`
		:param application: The application instance to which this window belongs.
		:type application: :py:class:`.KingPhisherClientApplication`
		"""
		assert isinstance(application, Gtk.Application)
		self.config = config
		self.parent = parent
		self.application = application
		self.logger = logging.getLogger('KingPhisher.Client.' + self.__class__.__name__)
		if not has_vte:
			gui_utilities.show_dialog_error('RPC Terminal Is Unavailable', parent, 'VTE is not installed')
			return

		self.window = Gtk.ApplicationWindow(application=application)
		self.window.set_property('title', 'King Phisher RPC')
		self.window.set_transient_for(parent)
		self.window.set_destroy_with_parent(True)
		self.window.connect('destroy', self.signal_window_destroy)
		self.terminal = Vte.Terminal()
		self.terminal.set_property('rewrap-on-resize', True)
		self.terminal.set_scroll_on_keystroke(True)
		vbox = Gtk.VBox()
		self.window.add(vbox)
		vbox.pack_end(self.terminal, True, True, 0)

		action_group = Gtk.ActionGroup("rpc_terminal_window_actions")
		self._add_menu_actions(action_group)
		uimanager = self._create_ui_manager()
		uimanager.insert_action_group(action_group)
		menubar = uimanager.get_widget("/MenuBar")
		vbox.pack_start(menubar, False, False, 0)

		rpc = self.parent.rpc
		config = {}
		config['campaign_id'] = self.config['campaign_id']
		config['campaign_name'] = self.config['campaign_name']
		config['rpc_data'] = {
			'address': (rpc.host, rpc.port),
			'use_ssl': rpc.use_ssl,
			'username': rpc.username,
			'uri_base': rpc.uri_base,
			'hmac_key': rpc.hmac_key,
		}

		module_path = os.path.dirname(client_rpc.__file__) + ((os.path.sep + '..') * client_rpc.__name__.count('.'))
		module_path = os.path.normpath(module_path)

		python_command = [
			"import {0}".format(client_rpc.__name__),
			"{0}.vte_child_routine('{1}')".format(client_rpc.__name__, json.dumps(config))
		]
		python_command = '; '.join(python_command)

		if hasattr(self.terminal, 'pty_new_sync'):
			# Vte._version >= 2.91
			vte_pty = self.terminal.pty_new_sync(Vte.PtyFlags.DEFAULT)
			self.terminal.set_pty(vte_pty)
			self.terminal.connect('child-exited', lambda vt, status: self.window.destroy())
		else:
			# Vte._version <= 2.90
			vte_pty = self.termina.pty_new(Vte.PtyFlags.DEFAULT)
			self.terminal.set_pty_object(vte_pty)
			self.terminal.connect('child-exited', lambda vt: self.window.destroy())

		child_pid, _, _, _ = GLib.spawn_async(
			working_directory=os.getcwd(),
			argv=[utilities.which('python'), '-c', python_command],
			envp=['PYTHONPATH=' + module_path],
			flags=(GLib.SpawnFlags.SEARCH_PATH | GLib.SpawnFlags.DO_NOT_REAP_CHILD),
			child_setup=self._child_setup,
			user_data=vte_pty
		)

		self.logger.info("vte spawned child process with pid: {0}".format(child_pid))
		self.child_pid = child_pid
		self.terminal.watch_child(child_pid)
		GLib.spawn_close_pid(child_pid)
		self.window.show_all()

		# automatically enter the password
		vte_pty_fd = vte_pty.get_fd()
		if len(select.select([vte_pty_fd], [], [], 1)[0]):
			os.write(vte_pty_fd, rpc.password + '\n')
		return

	def _add_menu_actions(self, action_group):
		# Edit Menu Actions
		action_editmenu = Gtk.Action("EditMenu", "Edit", None, None)
		action_group.add_action(action_editmenu)

		action_copy = Gtk.Action("EditCopy", "Copy", "Copy", None)
		action_copy.connect("activate", lambda x: self.terminal.copy_clipboard())
		action_group.add_action_with_accel(action_copy, "<control><shift>C")

		action_paste = Gtk.Action("EditPaste", "Paste", "Paste", None)
		action_paste.connect("activate", lambda x: self.terminal.paste_clipboard())
		action_group.add_action_with_accel(action_paste, "<control><shift>V")

		# Help Menu Actions
		action = Gtk.Action('HelpMenu', 'Help', None, None)
		action_group.add_action(action)

		action = Gtk.Action('HelpAbout', 'About', 'About', None)
		action.connect('activate', lambda x: dialogs.AboutDialog(self.config, self.window).interact())
		action_group.add_action(action)

		rpc_api_docs_url = "http://king-phisher.readthedocs.org/en/{0}/rpc_api.html".format('latest' if version.version_label in ('alpha', 'beta') else 'stable')
		action = Gtk.Action('HelpApiDocs', 'API Documentation', 'API Documentation', None)
		action.connect('activate', lambda x: utilities.open_uri(rpc_api_docs_url))
		action_group.add_action(action)

		action = Gtk.Action('HelpWiki', 'Wiki', 'Wiki', None)
		action.connect('activate', lambda x: utilities.open_uri('https://github.com/securestate/king-phisher/wiki'))
		action_group.add_action(action)

	def _child_setup(self, vte_pty):
		vte_pty.child_setup()

	def _create_ui_manager(self):
		uimanager = Gtk.UIManager()
		with open(find.find_data_file('ui_info/rpc_terminal_window.xml')) as ui_info_file:
			ui_data = ui_info_file.read()
		uimanager.add_ui_from_string(ui_data)
		accelgroup = uimanager.get_accel_group()
		self.window.add_accel_group(accelgroup)
		return uimanager

	def signal_window_destroy(self, window):
		if os.path.exists("/proc/{0}".format(self.child_pid)):
			self.logger.debug("sending sigkill to child process: {0}".format(self.child_pid))
			os.kill(self.child_pid, signal.SIGKILL)
