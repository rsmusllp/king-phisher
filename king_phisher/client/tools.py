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

import code
import getpass
import json
import logging
import os
import select
import signal
import sys

from king_phisher import find
from king_phisher import utilities
from king_phisher.client import gui_utilities
from king_phisher.client.rpcclient import KingPhisherRPCClient
from king_phisher.third_party.AdvancedHTTPServer import AdvancedHTTPServerRPCError

from gi.repository import Gtk
from gi.repository import GLib

try:
	from gi.repository import Vte
except ImportError:
	has_vte = False
else:
	has_vte = True

class KingPhisherClientRPCTerminal(object):
	def __init__(self, config, parent):
		self.config = config
		self.parent = parent
		self.logger = logging.getLogger('KingPhisher.Client.' + self.__class__.__name__)
		if not has_vte:
			gui_utilities.show_dialog_error('RPC terminal is unavailable', parent, 'VTE is not installed')
			return
		self.window = Gtk.Window()
		self.window.set_property('title', 'King Phisher RPC')
		self.window.set_transient_for(parent)
		self.window.set_destroy_with_parent(True)
		self.window.connect('destroy', self.signal_window_destroy)
		self.terminal = Vte.Terminal()
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
		config['ssh_server'] = self.config['ssh_server']
		config['ssh_username'] = self.config['ssh_username']
		config['rpc_data'] = {
			'address': (rpc.host, rpc.port),
			'use_ssl': rpc.use_ssl,
			'username': rpc.username,
			'uri_base': rpc.uri_base,
			'hmac_key': rpc.hmac_key,
		}
		config = json.dumps(config)
		argv = []
		argv.append(utilities.which('python'))
		argv.append('-c')
		argv.append("import {0}; {0}.{1}.child_routine('{2}')".format(self.__module__, self.__class__.__name__, config))
		_, child_pid = self.terminal.fork_command_full(Vte.PtyFlags.DEFAULT, os.getcwd(), argv, None, GLib.SpawnFlags.DEFAULT, None, None)
		self.logger.info("vte spawned child process with pid: {0}".format(child_pid))
		self.child_pid = child_pid
		self.terminal.connect('child-exited', lambda vt: self.window.destroy())
		self.window.show_all()

		# Automatically enter the password
		vte_pty = self.terminal.get_pty_object()
		vte_pty_fd = vte_pty.get_fd()
		if len(select.select([vte_pty_fd], [], [], 0.5)[0]):
			os.write(vte_pty_fd, rpc.password + '\n')
		return

	@staticmethod
	def child_routine(config):
		config = json.loads(config)
		try:
			import readline
			import rlcompleter
		except ImportError:
			pass
		else:
			readline.parse_and_bind('tab: complete')
		plugins_directory = find.find_data_directory('plugins')
		if plugins_directory:
			sys.path.append(plugins_directory)

		rpc = KingPhisherRPCClient(**config['rpc_data'])
		logged_in = False
		for _ in range(0, 3):
			rpc.password = getpass.getpass("{0}@{1}'s password: ".format(config['ssh_username'], config['ssh_server'].split(':', 1)[0]))
			try:
				logged_in = rpc('ping')
			except AdvancedHTTPServerRPCError:
				print('Permission denied, please try again.')
				continue
			else:
				break
		if not logged_in:
			return

		banner = "Python {0} on {1}".format(sys.version, sys.platform)
		print(banner)
		information = "Campaign Name: '{0}'  ID: {1}".format(config['campaign_name'], config['campaign_id'])
		print(information)
		console_vars = {
			'CAMPAIGN_NAME': config['campaign_name'],
			'CAMPAIGN_ID': config['campaign_id'],
			'os': os,
			'rpc': rpc
		}
		export_to_builtins = ['CAMPAIGN_NAME', 'CAMPAIGN_ID', 'rpc']
		console = code.InteractiveConsole(console_vars)
		for var in export_to_builtins:
			console.push("__builtins__['{0}'] = {0}".format(var))
		console.interact('The \'rpc\' object holds the connected KingPhisherRPCClient instance')
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
			os.kill(self.child_pid, signal.SIGKILL)
