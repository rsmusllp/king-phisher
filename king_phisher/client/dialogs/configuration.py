#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  king_phisher/client/dialogs/configuration.py
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

from gi.repository import GObject
from gi.repository import Gtk

__all__ = ['KingPhisherClientConfigurationDialog']

class KingPhisherClientConfigurationDialog(gui_utilities.UtilityGladeGObject):
	"""
	Display the King Phisher client configuration dialog. Running this
	dialog via the :py:func:`.interact` method will cause some server
	settings to be loaded.
	"""
	gobject_ids = [
		# Server Tab
		'entry_server',
		'entry_server_username',
		'entry_sms_phone_number',
		'combobox_sms_carrier',
		# SMTP Server Tab
		'entry_smtp_server',
		'spinbutton_smtp_max_send_rate',
		'switch_smtp_ssl_enable',
		'switch_smtp_ssh_enable',
		'entry_ssh_server',
		'entry_ssh_username'
	]
	top_gobject = 'dialog'
	top_level_dependencies = [
		'SMSCarriers',
		'SMTPSendRate'
	]
	def signal_switch_smtp_ssh(self, switch, _):
		active = switch.get_property('active')
		self.gobjects['entry_ssh_server'].set_sensitive(active)
		self.gobjects['entry_ssh_username'].set_sensitive(active)

	def signal_toggle_alert_subscribe(self, cbutton):
		active = cbutton.get_property('active')
		if active:
			remote_method = 'campaign/alerts/subscribe'
		else:
			remote_method = 'campaign/alerts/unsubscribe'
		self.parent.rpc(remote_method, self.config['campaign_id'])

	def signal_toggle_reject_after_credentials(self, cbutton):
		self.parent.rpc('campaigns/set', self.config['campaign_id'], 'reject_after_credentials', cbutton.get_property('active'))

	def interact(self):
		cb_subscribed = self.gtk_builder_get('checkbutton_alert_subscribe')
		cb_reject_after_creds = self.gtk_builder_get('checkbutton_reject_after_credentials')
		entry_beef_hook = self.gtk_builder_get('entry_server_beef_hook')
		server_config = self.parent.rpc('config/get', ['beef.hook_url', 'server.require_id', 'server.secret_id'])
		entry_beef_hook.set_property('text', server_config.get('beef.hook_url', ''))
		self.config['server_config']['server.require_id'] = server_config['server.require_id']
		self.config['server_config']['server.secret_id'] = server_config['server.secret_id']
		# older versions of GObject.signal_handler_find seem to have a bug which cause a segmentation fault in python
		if GObject.pygobject_version < (3, 10):
			cb_subscribed.set_property('active', self.parent.rpc('campaign/alerts/is_subscribed', self.config['campaign_id']))
			cb_reject_after_creds.set_property('active', self.parent.rpc.remote_table_row('campaigns', self.config['campaign_id'])['reject_after_credentials'])
		else:
			with gui_utilities.gobject_signal_blocked(cb_subscribed, 'toggled'):
				cb_subscribed.set_property('active', self.parent.rpc('campaign/alerts/is_subscribed', self.config['campaign_id']))
				cb_reject_after_creds.set_property('active', self.parent.rpc.remote_table_row('campaigns', self.config['campaign_id'])['reject_after_credentials'])

		cb_reject_after_creds.set_sensitive(self.config['server_config']['server.require_id'])

		self.dialog.show_all()
		response = self.dialog.run()
		if response != Gtk.ResponseType.CANCEL:
			self.objects_save_to_config()
			self.verify_sms_settings()
			self.parent.rpc('config/set', {'beef.hook_url': entry_beef_hook.get_property('text').strip()})
		self.dialog.destroy()
		return response

	def verify_sms_settings(self):
		phone_number = gui_utilities.gobject_get_value(self.gobjects['entry_sms_phone_number'])
		phone_number_set = bool(phone_number)
		sms_carrier_set = bool(self.gobjects['combobox_sms_carrier'].get_active() > 0)
		if phone_number_set ^ sms_carrier_set:
			gui_utilities.show_dialog_warning('Missing Information', self.parent, 'Both a phone number and a valid carrier must be specified')
			if 'sms_phone_number' in self.config:
				del self.config['sms_phone_number']
			if 'sms_carrier' in self.config:
				del self.config['sms_carrier']
		elif phone_number_set and sms_carrier_set:
			phone_number = filter(lambda x: x in map(str, range(0, 10)), phone_number)
			if len(phone_number) != 10:
				gui_utilities.show_dialog_warning('Invalid Phone Number', self.parent, 'The phone number must contain exactly 10 digits')
				return
			username = self.config['server_username']
			self.parent.rpc('users/set', username, ('phone_number', 'phone_carrier'), (phone_number, self.config['sms_carrier']))
