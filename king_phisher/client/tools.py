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

import logging
import os
import signal

from king_phisher import json_ex
from king_phisher import utilities
from king_phisher import version
from king_phisher.client import client_rpc
from king_phisher.client import dialogs
from king_phisher.client import gui_utilities

from gi.repository import GLib
from gi.repository import Gtk
from smoke_zephyr.utilities import which

try:
	from gi.repository import Vte
except ImportError:
	has_vte = False
	"""Whether the :py:mod:`Vte` module is available or not."""
else:
	has_vte = True

class RPCTerminalWindow(gui_utilities.GladeGObject):
	gobject_ids = (
		'box_main',
		'menu_edit',
		'menu_help'
	)
	top_gobject = 'window'
	top_level_dependencies = (
		'StockDialogQuestionImage',
		'StockHelpImage'
	)
	def __init__(self, terminal, *args, **kwargs):
		super(RPCTerminalWindow, self).__init__(*args, **kwargs)
		self.terminal = terminal
		self.child_pid = None
		self.gobjects['box_main'].pack_end(self.terminal, True, True, 0)
		if hasattr(self.terminal.props, 'rewrap_on_resize'):
			self.terminal.set_property('rewrap-on-resize', True)
		self.terminal.set_scroll_on_keystroke(True)

	def signal_menuitem_edit_copy(self, menuitem):
		self.terminal.copy_clipboard()

	def signal_menuitem_edit_paste(self, menuitem):
		self.terminal.paste_clipboard()

	def signal_menuitem_help_about(self, menuitem):
		dialogs.AboutDialog(self.application).interact()

	def signal_menuitem_help_api_docs(self, menuitem):
		rpc_api_docs_url = "http://king-phisher.readthedocs.org/en/{0}/server_api/rpc_api.html".format('latest' if version.version_label in ('alpha', 'beta') else 'stable')
		utilities.open_uri(rpc_api_docs_url)

	def signal_menuitem_help_wiki(self, menuitem):
		utilities.open_uri('https://github.com/securestate/king-phisher/wiki')

	def signal_window_destroy(self, window):
		if self.child_pid == None:
			self.logger.error('signal_window_destory was called but the child pid is None')
			return
		if os.path.exists("/proc/{0}".format(self.child_pid)):
			self.logger.debug("sending sigkill to child process: {0}".format(self.child_pid))
			os.kill(self.child_pid, signal.SIGKILL)

class KingPhisherClientRPCTerminal(object):
	"""
	A terminal using VTE that allows raw RPC methods to be called from
	within the King Phisher client. This is primarily useful for
	unofficial and advanced features or debugging and development.
	"""
	def __init__(self, application):
		"""
		:param application: The application instance to which this window belongs.
		:type application: :py:class:`.KingPhisherClientApplication`
		"""
		assert isinstance(application, Gtk.Application)
		self.application = application
		self.logger = logging.getLogger('KingPhisher.Client.' + self.__class__.__name__)
		if not has_vte:
			gui_utilities.show_dialog_error('RPC Terminal Is Unavailable', self.application.get_active_window(), 'VTE is not installed')
			return
		config = application.config

		self.terminal = Vte.Terminal()
		self.rpc_window = RPCTerminalWindow(self.terminal, self.application)

		rpc = self.application.rpc
		config = {
			'campaign_id': config['campaign_id'],
			'campaign_name': config['campaign_name'],
			'rpc_data': {
				'address': (rpc.host, rpc.port),
				'use_ssl': rpc.use_ssl,
				'username': rpc.username,
				'uri_base': rpc.uri_base,
				'headers': rpc.headers,
				'hmac_key': rpc.hmac_key
			}
		}

		module_path = os.path.dirname(client_rpc.__file__) + ((os.path.sep + '..') * client_rpc.__name__.count('.'))
		module_path = os.path.normpath(module_path)

		python_command = [
			"import {0}".format(client_rpc.__name__),
			"{0}.vte_child_routine('{1}')".format(client_rpc.__name__, json_ex.dumps(config, pretty=False))
		]
		python_command = '; '.join(python_command)

		if hasattr(self.terminal, 'pty_new_sync'):
			# Vte._version >= 2.91
			vte_pty = self.terminal.pty_new_sync(Vte.PtyFlags.DEFAULT)
			self.terminal.set_pty(vte_pty)
			self.terminal.connect('child-exited', lambda vt, status: self.rpc_window.window.destroy())
		else:
			# Vte._version <= 2.90
			vte_pty = self.terminal.pty_new(Vte.PtyFlags.DEFAULT)
			self.terminal.set_pty_object(vte_pty)
			self.terminal.connect('child-exited', lambda vt: self.rpc_window.window.destroy())

		child_pid, _, _, _ = GLib.spawn_async(
			working_directory=os.getcwd(),
			argv=[which('python'), '-c', python_command],
			envp=['PYTHONPATH=' + module_path],
			flags=(GLib.SpawnFlags.SEARCH_PATH | GLib.SpawnFlags.DO_NOT_REAP_CHILD),
			child_setup=self._child_setup,
			user_data=vte_pty
		)

		self.logger.info("vte spawned child process with pid: {0}".format(child_pid))
		self.child_pid = child_pid
		self.terminal.watch_child(child_pid)
		GLib.spawn_close_pid(child_pid)
		self.rpc_window.window.show_all()
		self.rpc_window.child_pid = child_pid
		return

	def _child_setup(self, vte_pty):
		vte_pty.child_setup()
