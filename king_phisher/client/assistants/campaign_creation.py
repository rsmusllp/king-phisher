#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  king_phisher/client/assistants/campaign_creation.py
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

import datetime

from king_phisher import utilities
from king_phisher.client import gui_utilities
from king_phisher.third_party import AdvancedHTTPServer

from gi.repository import Gtk

__all__ = ['CampaignCreationAssistant']

class CampaignCreationAssistant(gui_utilities.GladeGObject):
	"""
	Display an assistant which walks the user through creating and configuring a
	new campaign.
	"""
	gobject_ids = (
		'calendar_campaign_expiration',
		'checkbutton_alert_subscribe',
		'checkbutton_expire_campaign',
		'checkbutton_reject_after_credentials',
		'combobox_campaign_type',
		'entry_campaign_name',
		'entry_campaign_description',
		'frame_campaign_expiration',
		'spinbutton_campaign_expiration_hour',
		'spinbutton_campaign_expiration_minute'
	)
	top_gobject = 'assistant'
	top_level_dependencies = ('ClockHourAdjustment', 'ClockMinuteAdjustment')
	objects_persist = False
	def __init__(self, *args, **kwargs):
		super(CampaignCreationAssistant, self).__init__(*args, **kwargs)
		self._close_ready = True
		self._page_titles = {}
		for page_n in range(self.assistant.get_n_pages()):
			page = self.assistant.get_nth_page(page_n)
			page_title = self.assistant.get_page_title(page)
			if page_title:
				self._page_titles[page_title] = page_n
		self.gobjects['combobox_campaign_type'].set_model(Gtk.ListStore(str, int))
		if not self.config['server_config']['server.require_id']:
			self.gobjects['checkbutton_reject_after_credentials'].set_sensitive(False)
			self.gobjects['checkbutton_reject_after_credentials'].set_property('active', False)

	@property
	def campaign_name(self):
		"""
		The string value of the configured campaign name. This may be set even
		when the campaign was not created, which would be the case if the user
		closed the window.
		"""
		return self.gobjects['entry_campaign_name'].get_text()

	def _get_campaign_type_id(self):
		combobox_campaign_type = self.gobjects['combobox_campaign_type']
		model = combobox_campaign_type.get_model()
		if model is None:
			return
		model_iter = combobox_campaign_type.get_active_iter()
		if model_iter is None:
			campaign_type = combobox_campaign_type.get_child().get_text()
			if not campaign_type:
				return
			model_iter = gui_utilities.gtk_list_store_search(model, campaign_type)
			if model_iter is None:
				return self.application.rpc('db/table/insert', 'campaign_types', 'name', campaign_type)
		return model.get_value(model_iter, 1)

	def signal_assistant_apply(self, _):
		self._close_ready = False
		# have to do it this way because the next page will be selected when the apply signal is complete
		set_current_page = lambda page_name: self.assistant.set_current_page(max(0, self._page_titles[page_name] - 1))

		# get and validate the campaign name
		campaign_name = self.gobjects['entry_campaign_name'].get_text()
		if not campaign_name:
			gui_utilities.show_dialog_error('Invalid Campaign Name', self.parent, 'A unique and valid campaign name must be specified.')
			set_current_page('Basic Settings')
			return True

		# get and validate the campaign expiration
		expiration = None
		if self.gobjects['checkbutton_expire_campaign'].get_property('active'):
			expiration = datetime.datetime.combine(
				gui_utilities.gtk_calendar_get_pydate(self.gobjects['calendar_campaign_expiration']),
				datetime.time(
					int(self.gobjects['spinbutton_campaign_expiration_hour'].get_value()),
					int(self.gobjects['spinbutton_campaign_expiration_minute'].get_value())
				)
			)
			expiration = utilities.datetime_local_to_utc(expiration)
			if expiration <= datetime.datetime.now():
				gui_utilities.show_dialog_error('Invalid Campaign Expiration', self.parent, 'The expiration date is set in the past.')
				set_current_page('Expiration')
				return True

		# create the campaign, point of no return
		try:
			cid = self.application.rpc('campaign/new', campaign_name, description=self.gobjects['entry_campaign_description'].get_text())
		except AdvancedHTTPServer.AdvancedHTTPServerRPCError as error:
			if not error.is_remote_exception:
				raise error
			if not error.remote_exception['name'] == 'exceptions.ValueError':
				raise error
			error_message = error.remote_exception.get('message', 'an unknown error occurred').capitalize() + '.'
			gui_utilities.show_dialog_error('Failed To Create Campaign', self.parent, error_message)
			set_current_page('Basic Settings')
			return True

		properties = {}
		properties['campaign_type_id'] = self._get_campaign_type_id()
		properties['expiration'] = expiration
		properties['reject_after_credentials'] = self.gobjects['checkbutton_reject_after_credentials'].get_property('active')
		self.application.rpc('db/table/set', 'campaigns', cid, properties.keys(), properties.values())

		if self.gobjects['checkbutton_alert_subscribe'].get_property('active'):
			self.application.rpc('campaign/alerts/subscribe', cid)

		self._close_ready = True
		return

	def signal_assistant_cancel(self, assistant):
		assistant.destroy()

	def signal_assistant_close(self, assistant):
		if self._close_ready:
			assistant.destroy()
		self._close_ready = True

	def signal_assistant_prepare(self, _, page):
		page_title = self.assistant.get_page_title(page)
		if page_title == 'Basic Settings':
			combobox = self.gobjects['combobox_campaign_type']
			model = combobox.get_model()
			model.clear()
			for campaign_type in self.application.rpc.remote_table('campaign_types'):
				model.append((campaign_type.name, campaign_type.id))
		elif page_title == 'Expiration':
			calendar = self.gobjects['calendar_campaign_expiration']
			default_day = datetime.datetime.today() + datetime.timedelta(days=31)
			gui_utilities.gtk_calendar_set_pydate(calendar, default_day)

	def signal_calendar_prev(self, calendar):
		today = datetime.date.today()
		calendar_day = gui_utilities.gtk_calendar_get_pydate(calendar)
		if calendar_day >= today:
			return
		gui_utilities.gtk_calendar_set_pydate(calendar, today)

	def signal_checkbutton_expire_campaign_toggled(self, _):
		active = self.gobjects['checkbutton_expire_campaign'].get_property('active')
		self.gobjects['frame_campaign_expiration'].set_sensitive(active)

	def interact(self):
		self.assistant.show_all()
