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
import os

from king_phisher import errors
from king_phisher.client import gui_utilities

from gi.repository import GLib
from gi.repository import Gtk
from gi.repository import Pango
import paramiko
import paramiko.hostkeys

__all__ = ('HostKeyAcceptDialog', 'HostKeyWarnDialog')

class BaseHostKeyDialog(gui_utilities.GladeGObject):
	"""
	A base class for dialogs which show information about SSH host keys. It is
	assumed that the widgets defined in :py:attr:`.gobject_ids` are present
	including one button to accept the host key, and one to reject. The class's
	default response can be set using :py:attr:`.default_response`.
	"""
	gobject_ids = (
		'button_accept',
		'button_reject',
		'textview_key_details'
	)
	top_gobject = 'dialog'
	top_level_dependencies = (
		'StockApplyImage',
		'StockStopImage'
	)
	default_response = None
	"""The response that should be selected as the default for the dialog."""
	def __init__(self, application, hostname, key):
		"""
		:param application: The application to associate this popup dialog with.
		:type application: :py:class:`.KingPhisherClientApplication`
		:param str hostname: The hostname associated with the key.
		:param key: The host's SSH key.
		:type key: :py:class:`paramiko.pkey.PKey`
		"""
		super(BaseHostKeyDialog, self).__init__(application)
		self.hostname = hostname
		self.key = key
		textview = self.gobjects['textview_key_details']
		textview.modify_font(Pango.FontDescription('monospace 9'))
		textview.get_buffer().set_text(self.key_details)
		if self.default_response is not None:
			button = self.dialog.get_widget_for_response(response_id=self.default_response)
			button.grab_default()

	@property
	def key_details(self):
		key_type = self.key.get_name().lower()
		details = "Host: {0} ({1})\n".format(self.hostname, key_type)
		if key_type.startswith('ssh-'):
			key_type = key_type[4:]
		key_type = key_type.split('-', 1)[0].upper()
		details += "{0} key fingerprint is SHA256:{1}.\n".format(key_type, base64.b64encode(hashlib.new('sha256', self.key.asbytes()).digest()))
		details += "{0} key fingerprint is MD5:{1}.\n".format(key_type, binascii.b2a_hex(hashlib.new('md5', self.key.asbytes()).digest()))
		return details

	def interact(self):
		self.dialog.show_all()
		response = self.dialog.run()
		self.dialog.destroy()
		return response

class HostKeyAcceptDialog(BaseHostKeyDialog):
	"""
	A dialog that shows an SSH host key for a host that has not previously had
	one associated with it.
	"""
	default_button = Gtk.ResponseType.ACCEPT

class HostKeyWarnDialog(BaseHostKeyDialog):
	"""
	A dialog that warns about an SSH host key that does not match the one that
	was previously stored for the host.
	"""
	default_button = Gtk.ResponseType.REJECT
	def signal_checkbutton_toggled(self, button):
		self.gobjects['button_accept'].set_sensitive(button.get_property('active'))

class MissingHostKeyPolicy(paramiko.MissingHostKeyPolicy):
	"""
	A host key policy for use with paramiko that will validate SSH host keys
	correctly. If a key is new, the user will be prompted with
	:py:class:`.HostKeyAcceptDialog` dialog to accept it or if the host key does
	not match the user will be warned with :py:class:`.HostKeyWarnDialog`. The
	host keys accepted through this policy are stored in an OpenSSH compatible
	"known_hosts" file using paramiko.
	"""
	def __init__(self, application):
		"""
		:param application: The application which is using this policy.
		:type application: :py:class:`.KingPhisherClientApplication`
		"""
		self.application = application
		self.logger = logging.getLogger('KingPhisher.Client.' + self.__class__.__name__)
		super(MissingHostKeyPolicy, self).__init__()

	def missing_host_key(self, client, hostname, key):
		host_key_fingerprint = 'sha256:' + base64.b64encode(hashlib.new('sha256', key.asbytes()).digest())
		host_keys = paramiko.hostkeys.HostKeys()
		host_keys_modified = False
		known_hosts_file = self.application.config.get('ssh_known_hosts_file', os.path.join(GLib.get_user_config_dir(), 'king-phisher', 'known_hosts'))

		if os.access(known_hosts_file, os.R_OK):
			host_keys.load(known_hosts_file)

		if host_keys.lookup(hostname):
			if host_keys.check(hostname, key):
				self.logger.debug("accepting known ssh host key {0} {1} {2}".format(hostname, key.get_name(), host_key_fingerprint))
				return
			self.logger.warning("ssh host key does not match known value for {0}".format(hostname))
			dialog = HostKeyWarnDialog(self.application, hostname, key)
			if dialog.interact() != Gtk.ResponseType.ACCEPT:
				raise errors.KingPhisherAbortError('bad ssh host key for ' + hostname)
		else:
			dialog = HostKeyAcceptDialog(self.application, hostname, key)
			if dialog.interact() != Gtk.ResponseType.ACCEPT:
				raise errors.KingPhisherAbortError('unknown ssh host key for ' + hostname)
			host_keys.add(hostname, key.get_name(), key)
			host_keys_modified = True

		if host_keys_modified:
			host_keys.save(known_hosts_file)
			os.chmod(known_hosts_file, 0600)
