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

import functools

from king_phisher.client import gui_utilities
from king_phisher.client.dialogs import about
from king_phisher.client.widget import extras
from king_phisher.client.widget import managers

from gi.repository import Gdk
from gi.repository import Gtk

__all__ = ('LoginDialog', 'SMTPLoginDialog', 'SSHLoginDialog')

class LoginDialogBase(gui_utilities.GladeGObject):
	"""
	This object is basic login dialog object that can be inherited from and
	customized.
	"""
	dependencies = gui_utilities.GladeDependencies(
		children=(
			'button_connect',
			'entry_server',
			'entry_username',
			'entry_password',
			'label_main'
		),
		name='LoginDialogBase'
	)
	label = None
	top_gobject = 'dialog'
	def __init__(self, *args, **kwargs):
		super(LoginDialogBase, self).__init__(*args, **kwargs)
		if self.label is not None:
			self.gobjects['label_main'].set_text(self.label)

	def interact(self):
		self.dialog.show_all()
		response = self.dialog.run()
		if response != Gtk.ResponseType.CANCEL:
			self.objects_save_to_config()
		self.dialog.destroy()
		return response

	def signal_entry_activate(self, entry):
		self.gobjects['button_connect'].emit('clicked')

class LoginDialog(LoginDialogBase):
	"""
	This object is the main King Phisher login dialog, it is used to
	prompt for connection information for the King Phisher server.

	It allows the user to specify the host and port to connect to and
	credentials for authentication.
	"""
	dependencies = gui_utilities.GladeDependencies(
		children=(
			'button_connect',
			'entry_server',
			'entry_server_username',
			'entry_server_password',
			'entry_server_one_time_password',
			'label_main',
			'label_server_one_time_password',
			'revealer_server_one_time_password',
			'spinbutton_server_remote_port',
			'switch_server_use_ssl'
		),
		top_level=('PortAdjustment',)
	)
	def __init__(self, *args, **kwargs):
		super(LoginDialog, self).__init__(*args, **kwargs)
		self.popup_menu = managers.MenuManager()
		self.popup_menu.append('About', lambda x: about.AboutDialog(self.application).interact())
		self.popup_menu.append('Import Configuration', self.signal_menuitem_activate_import_config)

	def signal_button_pressed(self, _, event):
		if not (event.type == Gdk.EventType.BUTTON_PRESS and event.button == Gdk.BUTTON_SECONDARY):
			return
		self.popup_menu.menu.popup(None, None, functools.partial(gui_utilities.gtk_menu_position, event), None, event.button, event.time)
		return True

	def signal_menuitem_activate_import_config(self, _):
		dialog = extras.FileChooserDialog('Import Configuration File', self.dialog)
		response = dialog.run_quick_open()
		dialog.destroy()
		if response is None:
			return
		config_path = response['target_path']
		try:
			self.application.merge_config(config_path, strict=False)
		except Exception:
			self.logger.warning('failed to merge configuration file: ' + config_path, exc_info=True)
			gui_utilities.show_dialog_error('Invalid Configuration File', self.dialog, 'Could not import the configuration file.')
		else:
			self.objects_load_from_config()

	def signal_switch_ssl(self, switch, _):
		if switch.get_property('active'):
			self.gobjects['spinbutton_server_remote_port'].set_value(443)
		else:
			self.gobjects['spinbutton_server_remote_port'].set_value(80)

class SMTPLoginDialog(LoginDialogBase):
	"""
	This object is the King Phisher SMTP login dialog, it is used to prompt for
	connection information to an SMTP server.

	It allows the user to specify the host and port to connect to and
	credentials for authentication.
	"""
	config_prefix = 'smtp_'
	label = 'SMTP Login'

class SSHLoginDialog(LoginDialogBase):
	"""
	This object is the King Phisher SSH login dialog, it is used to prompt for
	connection information to an SSH server.

	It allows the user to specify the host and port to connect to and
	credentials for authentication.
	"""
	config_prefix = 'ssh_'
	label = 'SSH Login'
