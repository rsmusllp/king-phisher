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

from king_phisher.client import gui_utilities

__all__ = ['CampaignCreationAssistant']

class CampaignCreationAssistant(gui_utilities.GladeGObject):
	"""
	Display an assistant which walks the user through creating a campaign.
	"""
	gobject_ids = [
		'entry_campaign_name',
		'entry_campaign_description'
	]
	top_gobject = 'assistant'
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

	def signal_assistant_apply(self, _):
		self._close_ready = False
		campaign_name = self.gobjects['entry_campaign_name'].get_text()
		if not campaign_name:
			gui_utilities.show_dialog_error('Invalid Campaign Name', self.parent, 'A unique and valid campaign name must be specified.')
			self.assistant.set_current_page(self._page_titles['Basic Settings'])
			return True

		cid = self.application.rpc('campaign/new', campaign_name)
		properties = {}
		prop = self.gobjects['entry_campaign_description'].get_text()
		if prop:
			properties['description'] = prop
		self.application.rpc('db/table/set', 'campaigns', cid, properties.keys(), properties.values())
		self._close_ready = True
		return

	def signal_assistant_cancel(self, _):
		self.assistant.destroy()

	def signal_assistant_close(self, _):
		if self._close_ready:
			self.assistant.destroy()
		self._close_ready = True

	def interact(self):
		self.assistant.show_all()
