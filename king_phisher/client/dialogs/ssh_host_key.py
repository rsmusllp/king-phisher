#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  king_phisher/client/dialogs/ssh_host_key.py
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

import base64
import binascii
import hashlib
import logging

from king_phisher.client import gui_utilities

from gi.repository import Gtk
from gi.repository import Pango
import paramiko

__all__ = ('HostKeyAcceptDialog', 'HostKeyWarnDialog')

class HostKeyPolicy(paramiko.MissingHostKeyPolicy):
	def __init__(self, application):
		self.application = application
		self.logger = logging.getLogger('KingPhisher.Client.' + self.__class__.__name__)
		super(HostKeyPolicy, self).__init__()

	def get_key_details(self, hostname, key):
		name = key.get_name().lower()
		if name.startswith('ssh-'):
			name = name[4:]
		name = name.split('-', 1)[0].upper()
		details = ''
		details += "{0} key fingerprint is SHA256:{1}.\n".format(name, base64.b64encode(hashlib.new('sha256', key.asbytes()).digest()))
		details += "{0} key fingerprint is MD5:{1}.\n".format(name, binascii.b2a_hex(hashlib.new('md5', key.asbytes()).digest()))
		return details

	def missing_host_key(self, client, hostname, key):
		config = self.application.config
		known_hosts = config.get('ssh_known_hosts', {})
		host_key_fingerprint = 'sha256:' + base64.b64encode(hashlib.new('sha256', key.asbytes()).digest())
		host_key_string = "{0} {1}".format(key.get_name(), base64.b64encode(key.asbytes()))

		key_details = self.get_key_details(hostname, key)
		if not hostname in known_hosts:
			dialog = HostKeyAcceptDialog(self.application, key_details)
			if dialog.interact() != Gtk.ResponseType.ACCEPT:
				raise RuntimeError()
			known_hosts[hostname] = host_key_string
		elif known_hosts[hostname] == host_key_string:
			self.logger.debug("accepting known ssh host key {0} {1}".format(hostname, host_key_fingerprint))
			return
		else:
			self.logger.warning("ssh host key does not match known value for {0}".format(hostname))
			dialog = HostKeyWarnDialog(self.application, key_details)
			if dialog.interact() != Gtk.ResponseType.ACCEPT:
				raise RuntimeError()
		config['ssh_known_hosts'] = known_hosts

class HostKeyDialog(gui_utilities.GladeGObject):
	"""
	"""
	gobject_ids = ('textview_key_details',)
	top_gobject = 'dialog'
	top_level_dependencies = (
		'StockApplyImage',
		'StockStopImage'
	)
	default_response = None
	def __init__(self, application, key_details):
		super(HostKeyDialog, self).__init__(application)
		self.key_details = self.gtk_builder_get('textview_key_details')
		self.key_details.modify_font(Pango.FontDescription('monospace 9'))
		self.key_details.get_buffer().set_text(key_details)
		if self.default_response is not None:
			button = self.dialog.get_widget_for_response(response_id=self.default_response)
			button.grab_default()

	def interact(self):
		self.dialog.show_all()
		response = self.dialog.run()
		self.dialog.destroy()
		return response

class HostKeyAcceptDialog(HostKeyDialog):
	default_button = Gtk.ResponseType.ACCEPT

class HostKeyWarnDialog(HostKeyDialog):
	default_button = Gtk.ResponseType.REJECT
