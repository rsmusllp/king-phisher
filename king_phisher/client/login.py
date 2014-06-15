#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  king_phisher/client/login.py
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

from king_phisher.client.gui_utilities import UtilityGladeGObject

from gi.repository import Gtk

class KingPhisherClientLoginDialog(UtilityGladeGObject):
	"""
	This object is the main King Phisher login dialog, it is used to
	prompt for connection information for the King Phisher server.

	It allows the user to specify the host and port to connect to and
	credentials for authentication.
	"""
	gobject_ids = [
		'button_connect',
		'entry_server',
		'entry_server_username',
		'entry_server_password'
	]
	top_gobject = 'dialog'
	def interact(self):
		self.dialog.show_all()
		response = self.dialog.run()
		if response != Gtk.ResponseType.CANCEL:
			self.objects_save_to_config()
		self.dialog.destroy()
		return response

	def signal_entry_activate(self, entry):
		self.gobjects['button_connect'].emit('clicked')

class KingPhisherClientSSHLoginDialog(KingPhisherClientLoginDialog):
	"""
	This object is the King Phisher SSH login dialog, it is used to
	prompt for connection information to an SSH server.

	It allows the user to specify the host and port to connect to and
	credentials for authentication.
	"""
	gobject_ids = [
		'button_connect',
		'entry_ssh_server',
		'entry_ssh_username',
		'entry_ssh_password'
	]
