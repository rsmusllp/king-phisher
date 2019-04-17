#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  king_phisher/client/dialogs/company_editor.py
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
from king_phisher.client.widget import resources

from gi.repository import Gtk

__all__ = ('CompanyEditorDialog',)

class CompanyEditorDialog(gui_utilities.GladeGObject):
	"""
	Display a dialog which can be used to edit the various fields associated
	with a company object.
	"""
	dependencies = gui_utilities.GladeDependencies(
		children=(
			resources.CompanyEditorGrid(
				gui_utilities.GladeProxyDestination(
					'pack_start',
					widget='box_company',
					kwargs=dict(expand=True, fill=True, padding=0)
				)
			),
			'combobox_company_existing'
		)
	)
	top_gobject = 'dialog'
	objects_persist = False
	def __init__(self, *args, **kwargs):
		super(CompanyEditorDialog, self).__init__(*args, **kwargs)
		self._company_info_changed = False
		self._last_company_id = None
		self._set_comboboxes()
		self.gobjects['combobox_company_industry'].connect('changed', self.signal_editable_changed)
		self.gobjects['entry_company_industry'].connect('changed', self.signal_editable_changed)
		self.gobjects['entry_company_name'].connect('changed', self.signal_editable_changed)
		self.gobjects['entry_company_description'].connect('changed', self.signal_editable_changed)
		self.gobjects['entry_company_url_main'].connect('changed', self.signal_editable_changed)
		self.gobjects['entry_company_url_email'].connect('changed', self.signal_editable_changed)
		self.gobjects['entry_company_url_remote_access'].connect('changed', self.signal_editable_changed)

		campaign = self.application.rpc.graphql_find_file('get_campaign.graphql', id=self.config['campaign_id'])['db']['campaign']
		if campaign['company'] is not None:
			combobox = self.gobjects['combobox_company_existing']
			combobox.set_active_iter(gui_utilities.gtk_list_store_search(combobox.get_model(), str(campaign['company']['id'])))
			self._get_company_info(campaign['company']['id'])

	def _set_comboboxes(self):
		"""Set up all the comboboxes and load the data for their models."""
		renderer = resources.renderer_text_desc
		rpc = self.application.rpc
		for tag_name, tag_table in (('company_existing', 'companies'), ('company_industry', 'industries')):
			combobox = self.gobjects['combobox_' + tag_name]
			model = combobox.get_model()
			if model is None:
				combobox.pack_start(renderer, True)
				combobox.add_attribute(renderer, 'text', 2)
			combobox.set_model(rpc.get_tag_model(tag_table, model=model))

	def _get_company_info(self, company_id):
		company = self.application.rpc.graphql("""\
		query getCompany($id: String!) {
			db {
				company(id: $id) {
					id
					description
					name
					industryId
					urlMain
					urlEmail
					urlRemoteAccess
				}
			}
		}""", {'id': company_id})['db']['company']
		combobox = self.gobjects['combobox_company_industry']
		if company['industryId'] is None:
			combobox.set_active_iter(None)
			combobox.get_child().set_text('')
		else:
			combobox.set_active_iter(gui_utilities.gtk_list_store_search(combobox.get_model(), str(company['industryId'])))
		self.gobjects['entry_company_name'].set_text(company['name'])
		self.gobjects['entry_company_description'].set_text(company['description'] or '')
		self.gobjects['entry_company_url_main'].set_text(company['urlMain'] or '')
		self.gobjects['entry_company_url_email'].set_text(company['urlEmail'] or '')
		self.gobjects['entry_company_url_remote_access'].set_text(company['urlRemoteAccess'] or '')

	def _get_tag_from_combobox(self, combobox, db_table):
		model = combobox.get_model()
		model_iter = combobox.get_active_iter()
		if model_iter is not None:
			return model.get_value(model_iter, 0)
		campaign_type = combobox.get_child().get_text().strip()
		if not campaign_type:
			return
		model_iter = gui_utilities.gtk_list_store_search(model, campaign_type, column=1)
		if model_iter is None:
			return self.application.rpc('db/table/insert', db_table, 'name', campaign_type)
		return model.get_value(model_iter, 0)

	def _set_company_info(self, company_id):
		company_name = self.get_entry_value('company_name')
		company_description = self.get_entry_value('company_description')
		self.application.rpc.remote_table_row_set('companies', company_id, {
			'name': company_name,
			'description': company_description,
			'industry_id': self._get_tag_from_combobox(self.gobjects['combobox_company_industry'], 'industries'),
			'url_main': self.get_entry_value('company_url_main'),
			'url_email': self.get_entry_value('company_url_email'),
			'url_remote_access': self.get_entry_value('company_url_remote_access')
		})
		model = self.gobjects['combobox_company_existing'].get_model()
		model_iter = gui_utilities.gtk_list_store_search(model, company_id)
		model[model_iter][1] = company_name
		model[model_iter][2] = company_description

	def _should_set_company_info(self):
		if self._last_company_id is None:
			return False
		if not self._company_info_changed:
			return False
		return gui_utilities.show_dialog_yes_no('Update Company Info?', self.parent, 'Do you want to save the changes to the company information?')

	def interact(self):
		self.dialog.show_all()
		response = self.dialog.run()
		if response == Gtk.ResponseType.APPLY and self._should_set_company_info():
			self._set_company_info(self._last_company_id)
		self.dialog.destroy()

	def signal_combobox_company_changed(self, _):
		if self._should_set_company_info():
			self._set_company_info(self._last_company_id)

		combobox = self.gobjects['combobox_company_existing']
		model = combobox.get_model()
		company_id = model.get_value(combobox.get_active_iter(), 0)
		self._last_company_id = company_id
		self._get_company_info(company_id)
		self._company_info_changed = False

	def signal_editable_changed(self, _):
		if self._last_company_id is None:
			return
		self._company_info_changed = True
