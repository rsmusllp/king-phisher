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
#  * Neither the name of the  nor the names of its
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

import os
import time

from gi.repository import Gtk
from gi.repository import GLib
from gi.repository import Vte

from king_phisher.client import rpcclient
from king_phisher.client import utilities

class KingPhisherClientRPCTerminal(object):
	def __init__(self, config, client):
		self.window = Gtk.Window()
		self.window.set_property('title', 'King Phisher RPC')
		#self.window.set_size_request(800, 600)
		self.box = Gtk.VBox()
		self.window.add(self.box)
		self.terminal = Vte.Terminal()
		self.terminal.set_scroll_on_keystroke(True)
		self.box.pack_start(self.terminal, True, True, 0)

		rpc_args = [utilities.which('python'), rpcclient.__file__]
		rpc_args.extend(['-u', config['server_username']])
		rpc_args.extend(['-p', config['server_password']])
		rpc_args.append("localhost:{0}".format(client.server_local_port))
		self.terminal.fork_command_full(Vte.PtyFlags.DEFAULT, os.getcwd(), rpc_args, [], GLib.SpawnFlags.DO_NOT_REAP_CHILD, None, None)
		self.terminal.connect('child-exited', lambda x: self.window.destroy())

		self.window.show_all()
