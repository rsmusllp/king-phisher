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
import os
import posixpath as webpath
import re
import urllib.parse

from king_phisher import archive
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

_ModelURLScheme = collections.namedtuple('ModelURLScheme', (
	'id',
	'name',
	'description',
	'port'
))

_KPMPaths = collections.namedtuple('KPMPaths', (
	'kpm_file',
	'destination_folder',
	'is_valid'
))

def _kpm_file_path_is_valid(file_path):
	if not file_path:
		return False
	if not os.path.isfile(file_path) and os.access(file_path, os.R_OK):
		return False
	if not archive.is_archive(file_path):
		return False
	return True

def _homogenous_label_width(labels):
	width = max(label.get_preferred_width().minimum_width for label in labels)
	for label in labels:
		label.set_property('width-request', width)

def _set_icon(image, icon_name):
	image.set_property('stock', icon_name)

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
			'button_url_ssl_issue_certificate',
			'calendar_campaign_expiration',
			'checkbutton_alert_subscribe',
			'checkbutton_expire_campaign',
			'checkbutton_reject_after_credentials',
			'combobox_campaign_type',
			'combobox_company_existing',
			'combobox_url_hostname',
			'combobox_url_path',
			'combobox_url_scheme',
			'entry_campaign_description',
			'entry_campaign_name',
			'entry_kpm_dest_folder',
			'entry_kpm_file',
			'entry_test_validation_text',
			'entry_validation_regex_mfa_token',
			'entry_validation_regex_password',
			'entry_validation_regex_username',
			'frame_campaign_expiration',
			'frame_company_existing',
			'frame_company_new',
			'image_intro_title',
			'image_url_ssl_status',
			'label_confirm_body',
			'label_confirm_title',
			'label_intro_body',
			'label_intro_title',
			'label_url_for_scheme',
			'label_url_for_hostname',
			'label_url_for_path',
			'label_url_info_authors',
			'label_url_info_created',
			'label_url_info_description',
			'label_url_info_title',
			'label_url_info_for_authors',
			'label_url_preview',
			'label_url_ssl_for_status',
			'label_url_ssl_status',
			'label_validation_regex_mfa_token',
			'label_validation_regex_password',
			'label_validation_regex_username',
			'listbox_url_info_classifiers',
			'listbox_url_info_references',
			'radiobutton_company_existing',
			'radiobutton_company_new',
			'radiobutton_company_none',
			'revealer_url_ssl_settings',
			'togglebutton_expiration_time',
		),
		top_level=(
			'ClockHourAdjustment',
			'ClockMinuteAdjustment',
			'StockExecuteImage',
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

		campaign_edges = self.application.rpc.graphql(
			'{ db { campaigns { edges { node { id name } } } } }',
		)['db']['campaigns']['edges']
		self._campaign_names = dict((edge['node']['name'], edge['node']['id']) for edge in campaign_edges)
		self._cache_hostname = {}
		self._cache_site_template = {}
		self._can_issue_certs = False
		self._ssl_status = {}

		self._expiration_time = managers.TimeSelectorButtonManager(self.application, self.gobjects['togglebutton_expiration_time'])
		self._set_comboboxes()
		self._set_defaults()
		self.application.rpc.async_graphql(
			'{ ssl { status { enabled hasLetsencrypt hasSni } } }',
			on_success=self.__async_rpc_cb_ssl_status
		)
		_homogenous_label_width((
			self.gobjects['label_url_for_scheme'],
			self.gobjects['label_url_ssl_for_status'],
			self.gobjects['label_url_info_for_authors']
		))

		if not self.config['server_config']['server.require_id']:
			self.gobjects['checkbutton_reject_after_credentials'].set_sensitive(False)
			self.gobjects['checkbutton_reject_after_credentials'].set_property('active', False)

		confirm_preamble = 'Verify all settings are correct in the previous sections'
		if campaign_id:
			# re-configuring an existing campaign
			self.gobjects['label_confirm_body'].set_text(confirm_preamble + ', then hit "Apply" to update the King Phisher campaign with the new settings.')
			self.gobjects['label_intro_body'].set_text('This assistant will walk you through reconfiguring the selected King Phisher campaign.')
			self.gobjects['label_intro_title'].set_text('Configure Campaign')
			self._set_webserver_url(self.config['mailer.webserver_url'])
		else:
			# creating a new campaign
			self.gobjects['label_confirm_body'].set_text(confirm_preamble + ', then hit "Apply" to create the new King Phisher campaign.')
			self.gobjects['label_intro_body'].set_text('This assistant will walk you through creating and configuring a new King Phisher campaign.')
			self.gobjects['label_intro_title'].set_text('New Campaign')

	def __async_rpc_cb_issue_cert_error(self, error, message=None):
		self._set_page_complete(True, page='Web Server URL')
		self.gobjects['button_url_ssl_issue_certificate'].set_sensitive(True)
		_set_icon(self.gobjects['image_url_ssl_status'], 'gtk-dialog-warning')
		label = self.gobjects['label_url_ssl_status']
		label.set_text('An error occurred while requesting a certificate for the specified hostname')
		gui_utilities.show_dialog_error(
			'Operation Error',
			self.application.get_active_window(),
			message or "Unknown error: {!r}".format(error)
		)

	def __async_rpc_cb_issue_cert_success(self, result):
		self._set_page_complete(True, page='Web Server URL')
		if not result['success']:
			return self.__async_rpc_cb_issue_cert_error(None, result['message'])
		_set_icon(self.gobjects['image_url_ssl_status'], 'gtk-yes')
		label = self.gobjects['label_url_ssl_status']
		label.set_text('A certificate for the specified hostname has been issued and loaded')

	def __async_rpc_cb_populate_url_hostname_combobox(self, hostnames):
		hostnames = sorted(hostnames)
		model = self.gobjects['combobox_url_hostname'].get_model()
		for hostname in hostnames:
			model.append((hostname,))

	def __async_rpc_cb_populate_url_info(self, hostname, path, results):
		self._cache_site_template[(hostname, path)] = results
		template = results['siteTemplate']
		if template is None:
			return
		self.gobjects['label_url_info_created'].set_text(utilities.format_datetime(utilities.datetime_utc_to_local(template['created'])))
		metadata = template['metadata']
		if metadata is None:
			return
		self.gobjects['label_url_info_title'].set_text(metadata['title'])
		self.gobjects['label_url_info_authors'].set_text('\n'.join(metadata['authors']))
		self.gobjects['label_url_info_description'].set_text(metadata['description'])
		if metadata['referenceUrls']:
			gui_utilities.gtk_listbox_populate_urls(
				self.gobjects['listbox_url_info_references'],
				metadata['referenceUrls'],
				signals={'activate-link': self.signal_label_activate_link}
			)
		gui_utilities.gtk_listbox_populate_labels(self.gobjects['listbox_url_info_classifiers'], metadata['classifiers'])

	def __async_rpc_cb_populate_url_scheme_combobox(self, addresses):
		addresses = sorted(addresses, key=lambda address: address['port'])
		combobox_url_scheme = self.gobjects['combobox_url_scheme']
		model = combobox_url_scheme.get_model()
		for address in addresses:
			if address['ssl']:
				scheme_name = 'https'
				description = '' if address['port'] == 443 else 'port: ' + str(address['port'])
			else:
				scheme_name = 'http'
				description = '' if address['port'] == 80 else 'port: ' + str(address['port'])
			# use the scheme and port to make a row UID
			model.append(_ModelURLScheme(
				id=scheme_name + '/' + str(address['port']),
				name=scheme_name,
				description=description,
				port=address['port']
			))
		if gui_utilities.gtk_list_store_search(model, 'https/443'):
			combobox_url_scheme.set_active_id('https/443')
		elif gui_utilities.gtk_list_store_search(model, 'http/80'):
			combobox_url_scheme.set_active_id('http/80')

	def __async_rpc_cb_changed_url_hostname(self, hostname, results):
		self._cache_hostname[hostname] = results
		templates = results['siteTemplates']
		combobox = self.gobjects['combobox_url_path']
		combobox.set_property('button-sensitivity', templates['total'] > 0)
		model = combobox.get_model()
		model.clear()
		for template in templates['edges']:
			template = template['node']
			path = utilities.make_webrelpath(template['path'])
			if path and not path.endswith(webpath.sep):
				path += webpath.sep
			for page in template['metadata']['pages']:
				model.append((path + utilities.make_webrelpath(page), path))
		# this is going to trigger a changed signal and the cascade effect will update the URL information and preview
		combobox.set_active_id(utilities.make_webrelpath(gui_utilities.gtk_combobox_get_entry_text(combobox)))

		sni_hostname = results['ssl']['sniHostname']
		label = self.gobjects['label_url_ssl_status']
		if sni_hostname is None:
			_set_icon(self.gobjects['image_url_ssl_status'], 'gtk-no')
			label.set_text('There is no certificate available for the specified hostname')
			if self._can_issue_certs:
				self.gobjects['button_url_ssl_issue_certificate'].set_sensitive(True)
		else:
			_set_icon(self.gobjects['image_url_ssl_status'], 'gtk-yes')
			label.set_text('A certificate for the specified hostname is available')

	def __async_rpc_cb_ssl_status(self, results):
		self._ssl_status = results['ssl']['status']
		self._can_issue_certs = all(results['ssl']['status'].values())

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

	def _get_campaign_by_name(self, name):
		campaign = self.application.rpc.graphql("""\
			query getCampaignByName($name: String!)
			{ db { campaign(name: $name) { id } } }
		""", query_vars={'name': name})['db']['campaign']
		return campaign

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
		if not _kpm_file_path_is_valid(file_path):
			return _KPMPaths(None, None, False)
		if not (dir_path and os.path.isdir(dir_path) and os.access(dir_path, os.R_OK | os.W_OK)):
			return _KPMPaths(None, None, False)
		return _KPMPaths(file_path, dir_path, True)

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

	def _get_webserver_url(self):
		return self.gobjects['label_url_preview'].get_text()

	@property
	def _server_uses_ssl(self):
		return any(address['ssl'] for address in self.config['server_config']['server.addresses'])

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
			gui_utilities.gtk_combobox_set_entry_completion(combobox)
		# setup the URL scheme combobox asynchronously
		model = Gtk.ListStore(str, str, str, int)
		combobox = self.gobjects['combobox_url_scheme']
		combobox.set_model(model)
		combobox.pack_start(renderer, True)
		combobox.add_attribute(renderer, 'text', 2)
		rpc.async_call('config/get', ('server.addresses',), on_success=self.__async_rpc_cb_populate_url_scheme_combobox, when_idle=True)
		# setup the URL hostname combobox asynchronously
		model = Gtk.ListStore(str)
		combobox = self.gobjects['combobox_url_hostname']
		combobox.set_model(model)
		gui_utilities.gtk_combobox_set_entry_completion(combobox)
		rpc.async_call('hostnames/get', on_success=self.__async_rpc_cb_populate_url_hostname_combobox, when_idle=True)
		# setup the URL path combobox model, but don't populate it until a hostname is selected
		model = Gtk.ListStore(str, str)
		combobox = self.gobjects['combobox_url_path']
		combobox.set_model(model)
		gui_utilities.gtk_combobox_set_entry_completion(combobox)

	def _set_defaults(self):
		"""
		Set any default values for widgets. Also load settings from the existing
		campaign if one was specified.
		"""
		calendar = self.gobjects['calendar_campaign_expiration']
		default_day = datetime.datetime.today() + datetime.timedelta(days=31)
		gui_utilities.gtk_calendar_set_pydate(calendar, default_day)

		if self.is_new_campaign:
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

	def _set_webserver_url(self, webserver_url):
		webserver_url = urllib.parse.urlparse(webserver_url.strip())
		if webserver_url.scheme == 'http':
			self.gobjects['combobox_url_scheme'].set_active_id('http/' + str(webserver_url.port or 80))
		elif webserver_url.scheme == 'https':
			self.gobjects['combobox_url_scheme'].set_active_id('https/' + str(webserver_url.port or 443))
		if webserver_url.hostname:
			self.gobjects['combobox_url_hostname'].get_child().set_text(webserver_url.hostname)
		if webserver_url.path:
			self.gobjects['combobox_url_path'].get_child().set_text(utilities.make_webrelpath(webserver_url.path))

	def _set_page_complete(self, complete, page=None):
		if page is None:
			page = self.assistant.get_nth_page(self.assistant.get_current_page())
		elif isinstance(page, str):
			page = self.assistant.get_nth_page(self._page_titles[page])
		elif isinstance(page, int):
			page = self.assistant.get_nth_page(page)
		self.assistant.set_page_complete(page, complete)

	def signal_assistant_apply(self, _):
		self._close_ready = False
		# have to do it this way because the next page will be selected when the apply signal is complete
		set_current_page = lambda page_name: self.assistant.set_current_page(max(0, self._page_titles[page_name] - 1))

		# get and validate the campaign name
		campaign_name = self.gobjects['entry_campaign_name'].get_text()
		campaign_name = campaign_name.strip()
		if not campaign_name:
			gui_utilities.show_dialog_error('Invalid Campaign Name', self.parent, 'A valid campaign name must be specified.')
			set_current_page('Basic Settings')
			return True
		campaign = self._get_campaign_by_name(campaign_name)
		if campaign and campaign['id'] != self.campaign_id:
			gui_utilities.show_dialog_error('Invalid Campaign Name', self.parent, 'A unique campaign name must be specified.')
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

		if self._ssl_status['hasSni']:
			combobox_url_scheme = self.gobjects['combobox_url_scheme']
			active = combobox_url_scheme.get_active()
			if active != -1:
				url_scheme = _ModelURLScheme(*combobox_url_scheme.get_model()[active])
				if url_scheme.name == 'https':
					hostname = gui_utilities.gtk_combobox_get_entry_text(self.gobjects['combobox_url_hostname'])
					if not self.application.rpc('ssl/sni_hostnames/load', hostname):
						gui_utilities.show_dialog_error('Failure', self.parent, 'Failed to load an SSL certificate for the specified hostname.')

		self.config['mailer.webserver_url'] = self._get_webserver_url()
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

	def signal_button_clicked_issue_certificate(self, button):
		button.set_sensitive(False)
		self._set_page_complete(False, page='Web Server URL')
		label = self.gobjects['label_url_ssl_status']
		label.set_text('A certificate for the specified hostname is being requested')
		hostname = gui_utilities.gtk_combobox_get_entry_text(self.gobjects['combobox_url_hostname'])
		self.application.rpc.async_call(
			'ssl/letsencrypt/issue',
			(hostname,),
			on_error=self.__async_rpc_cb_issue_cert_error,
			on_success=self.__async_rpc_cb_issue_cert_success,
			when_idle=True
		)

	def signal_calendar_prev(self, calendar):
		today = datetime.date.today()
		calendar_day = gui_utilities.gtk_calendar_get_pydate(calendar)
		if calendar_day >= today:
			return
		gui_utilities.gtk_calendar_set_pydate(calendar, today)

	def signal_checkbutton_expire_campaign_toggled(self, _):
		active = self.gobjects['checkbutton_expire_campaign'].get_property('active')
		self.gobjects['frame_campaign_expiration'].set_sensitive(active)

	@gui_utilities.delayed_signal()
	def signal_combobox_changed_set_url_information(self, _):
		for label in ('info_title', 'info_authors', 'info_created', 'info_description'):
			self.gobjects['label_url_' + label].set_text('')
		hostname = gui_utilities.gtk_combobox_get_entry_text(self.gobjects['combobox_url_hostname'])
		if not hostname:
			return
		combobox_url_path = self.gobjects['combobox_url_path']
		path = gui_utilities.gtk_combobox_get_active_cell(combobox_url_path, column=1)
		if path is None:
			model = combobox_url_path.get_model()
			text = utilities.make_webrelpath(gui_utilities.gtk_combobox_get_entry_text(combobox_url_path))
			row_iter = gui_utilities.gtk_list_store_search(model, text)
			if row_iter:
				path = model[row_iter][1]
		gui_utilities.gtk_widget_destroy_children(self.gobjects['listbox_url_info_classifiers'])
		gui_utilities.gtk_widget_destroy_children(self.gobjects['listbox_url_info_references'])
		cached_result = self._cache_site_template.get((hostname, path))
		if cached_result:
			self.__async_rpc_cb_populate_url_info(hostname, path, cached_result)
			return
		self.application.rpc.async_graphql(
			"""
			query getSiteTemplate($hostname: String, $path: String) {
			  siteTemplate(hostname: $hostname, path: $path) {
				created path metadata { title authors description referenceUrls classifiers pages }
			  }
			}
			""",
			query_vars={'hostname': hostname, 'path': path},
			on_success=self.__async_rpc_cb_populate_url_info,
			cb_args=(hostname, path),
			when_idle=True
		)

	def signal_combobox_changed_set_url_preview(self, _):
		label = self.gobjects['label_url_preview']
		label.set_text('')
		combobox_url_scheme = self.gobjects['combobox_url_scheme']
		active = combobox_url_scheme.get_active()
		if active == -1:
			return
		url_scheme = _ModelURLScheme(*combobox_url_scheme.get_model()[active])
		authority = gui_utilities.gtk_combobox_get_entry_text(self.gobjects['combobox_url_hostname'])
		path = gui_utilities.gtk_combobox_get_entry_text(self.gobjects['combobox_url_path'])
		if url_scheme and authority:
			path = utilities.make_webrelpath(path)
			if (url_scheme.name == 'http' and url_scheme.port != 80) or (url_scheme.name == 'https' and url_scheme.port != 443):
				authority += ':' + str(url_scheme.port)
			label.set_text("{}://{}/{}".format(url_scheme.name, authority, path))

	@gui_utilities.delayed_signal()
	def signal_combobox_changed_url_hostname(self, combobox):
		self.gobjects['button_url_ssl_issue_certificate'].set_sensitive(False)
		hostname = gui_utilities.gtk_combobox_get_entry_text(combobox)
		if not hostname:
			return
		cached_result = self._cache_hostname.get(hostname)
		if cached_result:
			self.__async_rpc_cb_changed_url_hostname(hostname, cached_result)
			return
		self.application.rpc.async_graphql(
			"""
			query getHostname($hostname: String) {
			  siteTemplates(hostname: $hostname) {
				total edges { node { hostname path metadata { pages } } }
			  }
			  ssl { sniHostname(hostname: $hostname) { enabled } }
			}
			""",
			query_vars={'hostname': hostname},
			on_success=self.__async_rpc_cb_changed_url_hostname,
			cb_args=(hostname,),
			when_idle=True
		)

	def signal_combobox_changed_url_scheme(self, combobox):
		active = combobox.get_active()
		if active == -1:
			return
		url_scheme = _ModelURLScheme(*combobox.get_model()[active])
		revealer = self.gobjects['revealer_url_ssl_settings']
		revealer.set_reveal_child(url_scheme.name == 'https')

	def signal_entry_changed_campaign_name(self, entry):
		campaign_name = entry.get_text().strip()
		if not campaign_name:
			entry.set_property('secondary-icon-stock', 'gtk-dialog-warning')
		if self.is_new_campaign:
			if self._campaign_names.get(campaign_name) is not None:
				entry.set_property('secondary-icon-stock', 'gtk-dialog-warning')
			else:
				entry.set_property('secondary-icon-stock', None)
		elif self.is_editing_campaign:
			other_cid = self._campaign_names.get(campaign_name)
			if other_cid is not None and other_cid != self.campaign_id:
				entry.set_property('secondary-icon-stock', 'gtk-dialog-warning')
			else:
				entry.set_property('secondary-icon-stock', None)

	def signal_entry_changed_test_validation_text(self, field):
		test_text = field.get_text()
		for field in ('username', 'password', 'mfa_token'):
			self._do_regex_validation(test_text, self.gobjects['entry_validation_regex_' + field])

	def signal_entry_changed_validation_regex(self, entry):
		self._do_regex_validation(self.gobjects['entry_test_validation_text'].get_text(), entry)

	def signal_label_activate_link(self, _, uri):
		utilities.open_uri(uri)

	def signal_kpm_select_clicked(self, _):
		dialog = extras.FileChooserDialog('Import Message Configuration', self.parent)
		dialog.quick_add_filter('King Phisher Message Files', '*.kpm')
		dialog.quick_add_filter('All Files', '*')
		response = dialog.run_quick_open()
		dialog.destroy()
		if not response:
			return False
		target_path = response['target_path']
		self.gobjects['entry_kpm_file'].set_text(target_path)
		self._set_page_complete(self._get_kpm_path().is_valid)

		if not _kpm_file_path_is_valid(target_path):
			return
		# open the KPM for reading to extract the target URL for the assistant,
		# ignore the directory to allow the user to optionally only import the URL
		kpm = archive.ArchiveFile(target_path, 'r')
		if not kpm.has_file('message_config.json'):
			self.logger.warning('the kpm archive is missing the message_config.json file')
			return
		message_config = kpm.get_json('message_config.json')
		webserver_url = message_config.get('webserver_url')
		if not webserver_url:
			return
		self._set_webserver_url(webserver_url)

	def signal_kpm_dest_folder_clicked(self, _):
		dialog = extras.FileChooserDialog('Destination Directory', self.parent)
		response = dialog.run_quick_select_directory()
		dialog.destroy()
		if not response:
			return False
		self.gobjects['entry_kpm_dest_folder'].set_text(response['target_path'])
		self._set_page_complete(self._get_kpm_path().is_valid)

	def signal_kpm_entry_clear(self, entry_widget):
		entry_widget.set_text('')
		self._set_page_complete(self._get_kpm_path().is_valid)

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

	def interact(self):
		self.assistant.show_all()
