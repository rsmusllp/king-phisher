#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  king_phisher/client/dialogs/login.py
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

from king_phisher.client import gui_utilities
from king_phisher.client.dialogs import about

from gi.repository import Gdk
from gi.repository import Gtk

__all__ = ['LoginDialog', 'SSHLoginDialog']

class BaseLoginDialog(gui_utilities.GladeGObject):
	"""
	This object is basic login dialog object that can be inherited from and
	customized.
	"""
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

class LoginDialog(BaseLoginDialog):
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
		'entry_server_password',
		'spinbutton_server_remote_port',
		'switch_server_use_ssl'
	]
	top_level_dependencies = [
		'PortAdjustment'
	]
	def __init__(self, *args, **kwargs):
		super(LoginDialog, self).__init__(*args, **kwargs)
		self.popup_menu = Gtk.Menu.new()
		menu_item = Gtk.MenuItem.new_with_label('About')
		menu_item.connect('activate', lambda x: about.AboutDialog(self.config, self.dialog).interact())
		self.popup_menu.append(menu_item)
		self.popup_menu.show_all()

	def signal_switch_ssl(self, switch, _):
		if switch.get_property('active'):
			self.gobjects['spinbutton_server_remote_port'].set_value(443)
		else:
			self.gobjects['spinbutton_server_remote_port'].set_value(80)

	def signal_button_pressed(self, widget, event):
		if not (event.type == Gdk.EventType.BUTTON_PRESS and event.button == 3):
			return
		self.popup_menu.popup(None, None, gui_utilities.gtk_menu_position, event, event.button, event.time)
		return True

class SSHLoginDialog(BaseLoginDialog):
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
