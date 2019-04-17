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

import collections
import datetime
import ipaddress
import os
import re
import urllib

from king_phisher import utilities
from king_phisher.client import gui_utilities
from king_phisher.client.widget import extras
from king_phisher.client.widget import resources
from king_phisher.client.widget import managers

from gi.repository import Gtk
import advancedhttpserver

__all__ = ('CampaignAssistant',)

_ModelNamedRow = collections.namedtuple('ModelNamedRow', (
	'hostname',
	'page',
	'url',
	'classifiers',
	'authors',
	'description',
	'created'
))

_KPMPaths = collections.namedtuple('KPMPaths', (
	'kpm_file',
	'destination_folder',
	'is_valid'
))

class CampaignAssistant(gui_utilities.GladeGObject):
	"""
	Display an assistant which walks the user through creating a new campaign or
	configuring an existing campaign. If no *campaign_id* is specified a new
	campaign will be created.
	"""
	dependencies = gui_utilities.GladeDependencies(
		children=(
			resources.CompanyEditorGrid(
				gui_utilities.GladeProxyDestination(
					'add',
					widget='alignment_company'
				)
			),
			'button_select_kpm_dest_folder',
			'button_select_kpm_file',
			'calendar_campaign_expiration',
			'checkbutton_alert_subscribe',
			'checkbutton_expire_campaign',
			'checkbutton_reject_after_credentials',
			'combobox_campaign_type',
			'combobox_company_existing',
			'entry_campaign_description',
			'entry_campaign_name',
			'entry_hostname_filter',
			'entry_kpm_dest_folder',
			'entry_kpm_file',
			'entry_test_validation_text',
			'entry_validation_regex_mfa_token',
			'entry_validation_regex_password',
			'entry_validation_regex_username',
			'expander_url_info',
			'frame_campaign_expiration',
			'frame_company_existing',
			'frame_company_new',
			'image_intro_title',
			'label_confirm_body',
			'label_confirm_title',
			'label_intro_body',
			'label_intro_title',
			'label_url_info_authors',
			'label_url_info_created',
			'label_url_info_description',
			'label_url_info_for_classifiers',
			'label_url_info_url',
			'label_validation_regex_mfa_token',
			'label_validation_regex_password',
			'label_validation_regex_username',
			'listbox_url_info_classifiers',
			'paned_url_info',
			'radiobutton_company_existing',
			'radiobutton_company_new',
			'radiobutton_company_none',
			'togglebutton_expiration_time',
			'treeselection_url_selector',
			'treeview_url_selector',
		),
		top_level=(
			'ClockHourAdjustment',
			'ClockMinuteAdjustment'
		)
	)
	top_gobject = 'assistant'
	objects_persist = False
	def __init__(self, application, campaign_id=None):
		"""
		:param application: The application instance which this object belongs to.
		:type application: :py:class:`~king_phisher.client.application.KingPhisherClientApplication`
		:param campaign_id: The ID of the campaign to edit.
		"""
		super(CampaignAssistant, self).__init__(application)
		self.campaign_id = campaign_id
		self._close_ready = True
		self._page_titles = {}
		for page_n in range(self.assistant.get_n_pages()):
			page = self.assistant.get_nth_page(page_n)
			page_title = self.assistant.get_page_title(page)
			if page_title:
				self._page_titles[page_title] = page_n

		self._expiration_time = managers.TimeSelectorButtonManager(self.application, self.gobjects['togglebutton_expiration_time'])
		self._set_comboboxes()
		self._set_defaults()

		if not self.config['server_config']['server.require_id']:
			self.gobjects['checkbutton_reject_after_credentials'].set_sensitive(False)
			self.gobjects['checkbutton_reject_after_credentials'].set_property('active', False)

		confirm_preamble = 'Verify all settings are correct in the previous sections'
		if campaign_id:
			# re-configuring an existing campaign
			self.gobjects['label_confirm_body'].set_text(confirm_preamble + ', then hit "Apply" to update the King Phisher campaign with the new settings.')
			self.gobjects['label_intro_body'].set_text('This assistant will walk you through reconfiguring the selected King Phisher campaign.')
			self.gobjects['label_intro_title'].set_text('Configure Campaign')
		else:
			# creating a new campaign
			self.gobjects['label_confirm_body'].set_text(confirm_preamble + ', then hit "Apply" to create the new King Phisher campaign.')
			self.gobjects['label_intro_body'].set_text('This assistant will walk you through creating and configuring a new King Phisher campaign.')
			self.gobjects['label_intro_title'].set_text('New Campaign')

		self._url_thread = None
		domain_completion = Gtk.EntryCompletion()
		self._hostname_list_store = Gtk.ListStore(str)
		domain_completion.set_model(self._hostname_list_store)
		domain_completion.set_text_column(0)
		self.gobjects['entry_hostname_filter'].set_completion(domain_completion)

		tvm = managers.TreeViewManager(self.gobjects['treeview_url_selector'])
		tvm.set_column_titles(
			['Hostname', 'Landing Page', 'URL'],
			renderers=[
				Gtk.CellRendererText(),
				Gtk.CellRendererText(),
				Gtk.CellRendererText()
			]
		)
		self._url_model = Gtk.ListStore(str, str, str, object, object, str, str)
		self._url_model.set_sort_column_id(0, Gtk.SortType.ASCENDING)
		self.gobjects['treeview_url_selector'].set_model(self._url_model)
		self._url_information = {
			'created': None,
			'data': None
		}
		self._load_url_treeview_tsafe(refresh=True)
		paned = self.gobjects['paned_url_info']
		self._paned_offset = paned.get_allocation().height - paned.get_position()

	@property
	def campaign_name(self):
		"""
		The string value of the configured campaign name. This may be set even
		when the campaign was not created, which would be the case if the user
		closed the window.
		"""
		return self.gobjects['entry_campaign_name'].get_text()

	@property
	def is_editing_campaign(self):
		return self.campaign_id is not None

	@property
	def is_new_campaign(self):
		return self.campaign_id is None

	def _update_completion_status(self):
		self.assistant.set_page_complete(self.assistant.get_nth_page(self.assistant.get_current_page()), self._get_kpm_path().is_valid)

	@property
	def _url_thread_is_ready(self):
		return self._url_thread is None or not self._url_thread.is_alive()

	@property
	def _server_uses_ssl(self):
		return any(address['ssl'] for address in self.config['server_config']['server.addresses'])

	def signal_kpm_select_clicked(self, _):
		dialog = extras.FileChooserDialog('Import Message Configuration', self.parent)
		dialog.quick_add_filter('King Phisher Message Files', '*.kpm')
		dialog.quick_add_filter('All Files', '*')
		response = dialog.run_quick_open()
		dialog.destroy()
		if not response:
			return False
		self.gobjects['entry_kpm_file'].set_text(response['target_path'])
		self._update_completion_status()

	def signal_kpm_dest_folder_clicked(self, _):
		dialog = extras.FileChooserDialog('Destination Directory', self.parent)
		response = dialog.run_quick_select_directory()
		dialog.destroy()
		if not response:
			return False
		self.gobjects['entry_kpm_dest_folder'].set_text(response['target_path'])
		self._update_completion_status()

	def signal_kpm_entry_clear(self, entry_widget):
		entry_widget.set_text('')
		self._update_completion_status()

	def _set_comboboxes(self):
		"""Set up all the comboboxes and load the data for their models."""
		renderer = resources.renderer_text_desc
		rpc = self.application.rpc
		for tag_name, tag_table in (('campaign_type', 'campaign_types'), ('company_existing', 'companies'), ('company_industry', 'industries')):
			combobox = self.gobjects['combobox_' + tag_name]
			model = combobox.get_model()
			if model is None:
				combobox.pack_start(renderer, True)
				combobox.add_attribute(renderer, 'text', 2)
			combobox.set_model(rpc.get_tag_model(tag_table, model=model))

	def _load_url_treeview_tsafe(self, hostname=None, refresh=False):
		if refresh or not self._url_information['created']:
			self._url_information['data'] = self.application.rpc.graphql_find_file('get_site_templates.graphql')
			self._url_information['created'] = datetime.datetime.utcnow()
		url_information = self._url_information['data']
		if not url_information:
			return

		rows = []
		domains = []
		for edge in url_information['siteTemplates']['edges']:
			template = edge['node']
			for page in template['metadata']['pages']:
				if hostname and template['hostname'] and not template['hostname'].startswith(hostname):
					continue
				page = page.strip('/')
				resource = '/' + '/'.join((template.get('path', '').strip('/'), page)).lstrip('/')
				domains.append(template['hostname'])
				rows.append(_ModelNamedRow(
					hostname=template['hostname'],
					page=page,
					url=self._build_url(template['hostname'], resource, 'http'),
					classifiers=template['metadata']['classifiers'],
					authors=template['metadata']['authors'],
					description=template['metadata']['description'].strip('\n'),
					created=utilities.format_datetime(utilities.datetime_utc_to_local(template['created']))
				))

				if self._server_uses_ssl:
					rows.append(_ModelNamedRow(
						hostname=template['hostname'],
						page=page,
						url=self._build_url(template['hostname'], resource, 'https'),
						classifiers=template['metadata']['classifiers'],
						authors=template['metadata']['authors'],
						description=template['metadata']['description'].strip('\n'),
						created=utilities.format_datetime(utilities.datetime_utc_to_local(template['created']))
					))

		gui_utilities.glib_idle_add_once(self.gobjects['treeselection_url_selector'].unselect_all)
		gui_utilities.glib_idle_add_store_extend(self._url_model, rows, clear=True)
		# make domain list unique in case multiple pages are advertised for the domains
		domains = [[domain] for domain in set(domains)]
		gui_utilities.glib_idle_add_store_extend(self._hostname_list_store, domains, clear=True)

	def _build_url(self, hostname, page, scheme):
		if not hostname:
			for address in self.config['server_config']['server.addresses']:
				ip = ipaddress.ip_address(address['host'])
				if not ip.is_unspecified and (ip.is_global or ip.is_private):
					hostname = address['host']
					break
			else:
				hostname = 'localhost'
		return urllib.parse.urljoin(scheme + '://' + hostname, page)

	def signal_url_entry_change(self, gtk_entry):
		gtk_entry_text = gtk_entry.get_text()
		if not self._url_information['created'] or datetime.datetime.utcnow() - self._url_information['created'] > datetime.timedelta(minutes=5):
			self._load_url_treeview_tsafe(hostname=gtk_entry_text, refresh=True)
		else:
			self._load_url_treeview_tsafe(hostname=gtk_entry_text, refresh=False)

	def _set_defaults(self):
		"""
		Set any default values for widgets. Also load settings from the existing
		campaign if one was specified.
		"""
		calendar = self.gobjects['calendar_campaign_expiration']
		default_day = datetime.datetime.today() + datetime.timedelta(days=31)
		gui_utilities.gtk_calendar_set_pydate(calendar, default_day)

		if self.campaign_id is None:
			return
		campaign = self.application.get_graphql_campaign()

		# set entries
		self.gobjects['entry_campaign_name'].set_text(campaign['name'])
		self.gobjects['entry_validation_regex_username'].set_text(campaign['credentialRegexUsername'] or '')
		self.gobjects['entry_validation_regex_password'].set_text(campaign['credentialRegexPassword'] or '')
		self.gobjects['entry_validation_regex_mfa_token'].set_text(campaign['credentialRegexMfaToken'] or '')

		if campaign['description'] is not None:
			self.gobjects['entry_campaign_description'].set_text(campaign['description'])
		if campaign['campaignType'] is not None:
			combobox = self.gobjects['combobox_campaign_type']
			model = combobox.get_model()
			model_iter = gui_utilities.gtk_list_store_search(model, campaign['campaignType']['id'], column=0)
			if model_iter is not None:
				combobox.set_active_iter(model_iter)

		self.gobjects['checkbutton_alert_subscribe'].set_property('active', self.application.rpc('campaign/alerts/is_subscribed', self.campaign_id))
		self.gobjects['checkbutton_reject_after_credentials'].set_property('active', bool(campaign['maxCredentials']))

		if campaign['company'] is not None:
			self.gobjects['radiobutton_company_existing'].set_active(True)
			combobox = self.gobjects['combobox_company_existing']
			model = combobox.get_model()
			model_iter = gui_utilities.gtk_list_store_search(model, campaign['company']['id'], column=0)
			if model_iter is not None:
				combobox.set_active_iter(model_iter)

		if campaign['expiration'] is not None:
			expiration = utilities.datetime_utc_to_local(campaign['expiration'])
			self.gobjects['checkbutton_expire_campaign'].set_active(True)
			self._expiration_time.time = expiration.time()
			gui_utilities.gtk_calendar_set_pydate(self.gobjects['calendar_campaign_expiration'], expiration.date())

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

	def _get_company_existing_id(self):
		combobox_company = self.gobjects['combobox_company_existing']
		model = combobox_company.get_model()
		model_iter = combobox_company.get_active_iter()
		if model is None or model_iter is None:
			return
		return model.get_value(model_iter, 0)

	def _get_company_new_id(self):
		name = self.gobjects['entry_company_name'].get_text()
		name = name.strip()
		# check if this company name already exists in the model
		model = self.gobjects['combobox_company_existing'].get_model()
		model_iter = gui_utilities.gtk_list_store_search(model, name, column=1)
		if model_iter is not None:
			return model.get_value(model_iter, 0)
		# check if this company name already exists remotely
		remote_company = self._get_graphql_company(name)
		if remote_company:
			return remote_company['id']

		company_id = self.application.rpc(
			'db/table/insert',
			'companies',
			('name', 'description', 'industry_id', 'url_main', 'url_email', 'url_remote_access'),
			(
				name,
				self.get_entry_value('company_description'),
				self._get_tag_from_combobox(self.gobjects['combobox_company_industry'], 'industries'),
				self.get_entry_value('company_url_main'),
				self.get_entry_value('company_url_email'),
				self.get_entry_value('company_url_remote_access')
			)
		)
		self.gobjects['radiobutton_company_existing'].set_active(True)
		return company_id

	def _get_graphql_company(self, company_name):
		results = self.application.rpc.graphql("""\
		query getCompany($name: String!) {
			db {
				company(name: $name) {
					id
				}
			}
		}""", {'name': company_name})
		return results['db']['company']

	def _get_kpm_path(self):
		file_path = self.gobjects['entry_kpm_file'].get_text()
		dir_path = self.gobjects['entry_kpm_dest_folder'].get_text()
		if not dir_path and not file_path:
			return _KPMPaths(None, None, True)
		if not (file_path and os.path.isfile(file_path) and os.access(file_path, os.R_OK)):
			return _KPMPaths(None, None, False)
		if not (dir_path and os.path.isdir(dir_path) and os.access(dir_path, os.R_OK | os.W_OK)):
			return _KPMPaths(None, None, False)
		return _KPMPaths(file_path, dir_path, True)

	def _set_info_url_details(self, model_row):
		named_row = _ModelNamedRow(*model_row)
		self.gobjects['label_url_info_url'].set_text(named_row.url or '')
		self.gobjects['label_url_info_authors'].set_text('\n'.join(named_row.authors))
		self.gobjects['label_url_info_created'].set_text(named_row.created or '')
		self.gobjects['label_url_info_description'].set_text(named_row.description or '')

		if named_row.classifiers:
			self.gobjects['label_url_info_for_classifiers'].set_property('visible', True)
			gui_utilities.gtk_listbox_populate_labels(
				self.gobjects['listbox_url_info_classifiers'],
				named_row.classifiers
			)
		else:
			self.gobjects['label_url_info_for_classifiers'].set_property('visible', False)

	def _do_regex_validation(self, test_text, entry):
		try:
			regex = re.compile(entry.get_text())
		except re.error:
			entry.set_property('secondary-icon-stock', 'gtk-dialog-warning')
			return
		result = True
		if regex.pattern and test_text:
			result = regex.match(test_text) is not None
		entry.set_property('secondary-icon-stock', 'gtk-yes' if result else 'gtk-no')

	def signal_assistant_apply(self, _):
		self._close_ready = False
		# have to do it this way because the next page will be selected when the apply signal is complete
		set_current_page = lambda page_name: self.assistant.set_current_page(max(0, self._page_titles[page_name] - 1))

		# get and validate the campaign name
		campaign_name = self.gobjects['entry_campaign_name'].get_text()
		campaign_name = campaign_name.strip()
		if not campaign_name:
			gui_utilities.show_dialog_error('Invalid Campaign Name', self.parent, 'A unique and valid campaign name must be specified.')
			set_current_page('Basic Settings')
			return True

		properties = {}
		# validate the credential validation regular expressions
		for field in ('username', 'password', 'mfa_token'):
			regex = self.gobjects['entry_validation_regex_' + field].get_text()
			if regex:
				try:
					re.compile(regex)
				except re.error:
					label = self.gobjects['label_validation_regex_' + field].get_text()
					gui_utilities.show_dialog_error('Invalid Regex', self.parent, "The '{0}' regular expression is invalid.".format(label))
					return True
			else:
				regex = None  # keep empty strings out of the database
			properties['credential_regex_' + field] = regex

		# validate the company
		company_id = None
		if self.gobjects['radiobutton_company_existing'].get_active():
			company_id = self._get_company_existing_id()
			if company_id is None:
				gui_utilities.show_dialog_error('Invalid Company', self.parent, 'A valid existing company must be specified.')
				set_current_page('Company')
				return True
		elif self.gobjects['radiobutton_company_new'].get_active():
			company_id = self._get_company_new_id()
			if company_id is None:
				gui_utilities.show_dialog_error('Invalid Company', self.parent, 'The new company settings are invalid.')
				set_current_page('Company')
				return True

		# get and validate the campaign expiration
		expiration = None
		if self.gobjects['checkbutton_expire_campaign'].get_property('active'):
			expiration = datetime.datetime.combine(
				gui_utilities.gtk_calendar_get_pydate(self.gobjects['calendar_campaign_expiration']),
				self._expiration_time.time
			)
			expiration = utilities.datetime_local_to_utc(expiration)
			if self.is_new_campaign and expiration <= datetime.datetime.now():
				gui_utilities.show_dialog_error('Invalid Campaign Expiration', self.parent, 'The expiration date is set in the past.')
				set_current_page('Expiration')
				return True

		# point of no return
		campaign_description = self.get_entry_value('campaign_description')
		if self.campaign_id:
			properties['name'] = self.campaign_name
			properties['description'] = campaign_description
			cid = self.campaign_id
		else:
			try:
				cid = self.application.rpc('campaign/new', campaign_name, description=campaign_description)
				properties['name'] = campaign_name
			except advancedhttpserver.RPCError as error:
				if not error.is_remote_exception:
					raise error
				if not error.remote_exception['name'] == 'exceptions.ValueError':
					raise error
				error_message = error.remote_exception.get('message', 'an unknown error occurred').capitalize() + '.'
				gui_utilities.show_dialog_error('Failed To Create Campaign', self.parent, error_message)
				set_current_page('Basic Settings')
				return True
			self.application.emit('campaign-created', cid)

		properties['campaign_type_id'] = self._get_tag_from_combobox(self.gobjects['combobox_campaign_type'], 'campaign_types')
		properties['company_id'] = company_id
		properties['expiration'] = expiration
		properties['max_credentials'] = (1 if self.gobjects['checkbutton_reject_after_credentials'].get_property('active') else None)
		self.application.rpc('db/table/set', 'campaigns', cid, tuple(properties.keys()), tuple(properties.values()))

		should_subscribe = self.gobjects['checkbutton_alert_subscribe'].get_property('active')
		if should_subscribe != self.application.rpc('campaign/alerts/is_subscribed', cid):
			if should_subscribe:
				self.application.rpc('campaign/alerts/subscribe', cid)
			else:
				self.application.rpc('campaign/alerts/unsubscribe', cid)

		self.application.emit('campaign-changed', cid)

		old_cid = self.config.get('campaign_id')
		self.config['campaign_id'] = cid
		self.config['campaign_name'] = properties['name']

		_kpm_pathing = self._get_kpm_path()
		if all(_kpm_pathing):
			if not self.application.main_tabs['mailer'].emit('message-data-import', _kpm_pathing.kpm_file, _kpm_pathing.destination_folder):
				gui_utilities.show_dialog_info('Failure', self.parent, 'Failed to import the message configuration.')
			else:
				gui_utilities.show_dialog_info('Success', self.parent, 'Successfully imported the message configuration.')

		url_model, url_iter = self.gobjects['treeselection_url_selector'].get_selected()
		if url_iter:
			selected_row = []
			for column_n in range(0, url_model.get_n_columns()):
				selected_row.append(url_model.get_value(url_iter, column_n))
			selected_row = _ModelNamedRow(*selected_row)
			self.config['mailer.webserver_url'] = selected_row.url

		self.application.emit('campaign-set', old_cid, cid)
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
		if page_title == 'Company':
			combobox = self.gobjects['combobox_company_existing']
			model = combobox.get_model()
			company_name = self.get_entry_value('company_name')
			if company_name:
				model_iter = gui_utilities.gtk_list_store_search(model, company_name, column=1)
				if model_iter is not None:
					combobox.set_active_iter(model_iter)
					self.gobjects['radiobutton_company_existing'].set_active(True)

	def signal_calendar_prev(self, calendar):
		today = datetime.date.today()
		calendar_day = gui_utilities.gtk_calendar_get_pydate(calendar)
		if calendar_day >= today:
			return
		gui_utilities.gtk_calendar_set_pydate(calendar, today)

	def signal_checkbutton_expire_campaign_toggled(self, _):
		active = self.gobjects['checkbutton_expire_campaign'].get_property('active')
		self.gobjects['frame_campaign_expiration'].set_sensitive(active)

	def signal_entry_changed_test_validation_text(self, field):
		test_text = field.get_text()
		for field in ('username', 'password', 'mfa_token'):
			self._do_regex_validation(test_text, self.gobjects['entry_validation_regex_' + field])

	def signal_entry_changed_validation_regex(self, entry):
		self._do_regex_validation(self.gobjects['entry_test_validation_text'].get_text(), entry)

	def signal_expander_activate(self, expander):
		paned = self.gobjects['paned_url_info']
		if expander.get_property('expanded'):  # collapsing
			paned.set_position(paned.get_allocation().height + self._paned_offset)

	def signal_paned_button_press_event(self, paned, event):
		return not self.gobjects['expander_url_info'].get_property('expanded')

	def signal_radiobutton_toggled(self, radiobutton):
		if not radiobutton.get_active():
			return
		if radiobutton == self.gobjects['radiobutton_company_existing']:
			self.gobjects['frame_company_existing'].set_sensitive(True)
			self.gobjects['frame_company_new'].set_sensitive(False)
		elif radiobutton == self.gobjects['radiobutton_company_new']:
			self.gobjects['frame_company_existing'].set_sensitive(False)
			self.gobjects['frame_company_new'].set_sensitive(True)
		elif radiobutton == self.gobjects['radiobutton_company_none']:
			self.gobjects['frame_company_existing'].set_sensitive(False)
			self.gobjects['frame_company_new'].set_sensitive(False)

	def signal_treeview_row_activated(self, treeview, path, column):
		model_row = self._url_model[path]
		self._set_info_url_details(model_row)

	def interact(self):
		self.assistant.show_all()
