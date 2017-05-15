#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  king_phisher/client/windows/campaign_import.py
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
import logging
import threading
import xml.etree.ElementTree as ET

from king_phisher import serializers
from king_phisher.client import gui_utilities
from king_phisher.client.widget import extras
from king_phisher.errors import KingPhisherInputValidationError

import advancedhttpserver
from gi.repository import GLib

__all__ = ('ImportCampaignWindow',)

class ImportThread(threading.Thread):
	def __init__(self, *args, **kwargs):
		super(ImportThread, self).__init__(*args, **kwargs)
		self.stop_flag = threading.Event()
		self.stop_flag.clear()

	def stop(self):
		self.stop_flag.set()

	def stopped(self):
		return self.stop_flag.is_set()

class ImportCampaignWindow(gui_utilities.GladeGObject):
	"""
	Display a dialog which allows a new campaign to be created or an
	existing campaign to be opened.
	"""
	dependencies = gui_utilities.GladeDependencies(
		children=(
			'progressbar',
			'textview',
			'entry_campaign',
			'entry_file',
			'button_import',
			'button_select',
			'spinner'
		),
		top_level=('ImportCampaignWindow',)
	)
	top_gobject = 'window'
	def __init__(self, *args, **kwargs):
		super(ImportCampaignWindow, self).__init__(*args, **kwargs)
		self.logger = logging.getLogger('KingPhisher.Client.ImportCampaignWindow')
		self.rpc = self.application.rpc
		self.button_import_campaign = self.gobjects['button_import']
		self.button_import_campaign.set_sensitive(False)
		self.button_select = self.gobjects['button_select']
		self.entry_campaign_name = self.gobjects['entry_campaign']
		self.entry_path = self.gobjects['entry_file']
		self.import_progress = self.gobjects['progressbar']
		self.spinner = self.gobjects['spinner']
		self.text_buffer = self.gobjects['textview'].get_buffer()

		# place holders for once an xml file is loaded
		self.campaign_info = None
		self.db_campaigns = None
		self.thread_import_campaign = None
		self.window.show_all()

	def _set_text_view(self, string_to_set):
		GLib.idle_add(self.text_buffer.set_text, string_to_set + '\n')

	def __update_text_view(self, string_to_add):
		end_iter = self.text_buffer.get_end_iter()
		self.text_buffer.insert(end_iter, string_to_add + '\n')

	def _update_text_view(self, string_to_add, idle=False):
		if idle:
			GLib.idle_add(self.__update_text_view, string_to_add)
		else:
			self.__update_text_view(string_to_add)

	def _update_id(self, element, id_fields, old_id, new_id):
		"""
		Iterates through the element and replaces the specified old ID with the
		new ID in the requested ID fields.

		:param element: Element to iterate over where the old id values can be found.
		:type element: :py:class:`xml.etree.ElementTree.Element`
		:param list id_fields: The list of fields to look for old_id.
		:param old_id: The old id value that has been changed
		:param new_id: The new id value to set.
		"""
		for nods in element.iter():
			if nods.tag in id_fields and nods.text == old_id:
				nods.text = new_id
				# if new_id is none set type to null
				if new_id is None:
					nods.attrib['type'] = 'null'

	def _get_keys_values(self, element):
		keys = []
		rows = []
		for subelements in element:
			values = []
			for node in subelements:
				keys.append(node.tag) if node.tag not in keys else None
				value = serializers.from_elementtree_element(node)
				if isinstance(value, (datetime.datetime, datetime.date, datetime.time)):
					value = value.replace(tzinfo=None)  # remove the UTC timezone info
				values.append(value)
			rows.append(tuple(values))
		return keys, rows

	def signal_entry_change(self, _):
		"""
		When there is a change in the campaign entry field it will check to see
		if the name is already in use. If it is not in use it will change the
		sensitivity of the :py:attr:`.button_import_campaign` to allow the user
		to start the import process.
		"""
		if not self.campaign_info:
			return
		if not self._check_campaign_name(self.entry_campaign_name.get_text()):
			self.button_import_campaign.set_sensitive(False)
			return
		self.button_import_campaign.set_sensitive(True)
		return

	def signal_multi_open_xml_file(self, _):
		if not self.button_select.get_property('sensitive'):
			return
		self.select_xml_campaign()

	def signal_window_delete_event(self, _, event):
		"""
		Checks to make sure the import campaign thread is closed before
		closing the window.
		"""
		if not self.campaign_info:
			return False
		if not self.thread_import_campaign:
			return False
		if not self.thread_import_campaign.is_alive():
			return False
		response = gui_utilities.show_dialog_yes_no(
			'Cancel Importing?',
			self.window,
			'Do you want to cancel importing the campaign?'
		)
		if not response:
			return True

		self.thread_import_campaign.stop()
		self.thread_import_campaign.join()
		self._import_cleanup(remove_campaign=True)

	def failed_import_action(self):
		response = gui_utilities.show_dialog_yes_no(
			'Failed to import campaign',
			self.window,
			'Import failed, do you want to cancel and delete this campaign?'
		)
		return response

	def remove_import_campaign(self):
		"""
		Used to delete the imported campaign on failure or early exit of the
		import window, if the user selects to have it removed.
		"""
		campaign_id = self.campaign_info.find('id').text
		campaign_name = self.campaign_info.find('name').text
		campaign_check = self.rpc('db/table/get', 'campaigns', campaign_id)
		if not campaign_check:
			return
		if campaign_name == campaign_check['name']:
			self.rpc('db/table/delete', 'campaigns', campaign_id)
			self.logger.info("deleted campaign {}".format(campaign_id))

	def signal_import_button(self, _):
		"""
		This will check to see if the campaign information is present. If
		campaign information is present it will launch an py:class:`ImportThread`
		to import the campaign in the background, freeing up the GUI for the
		user to conduct other functions.
		"""
		if not self.campaign_info:
			self._update_text_view('No campaign information to import')
			self.button_import_campaign.set_sensitive(False)
			return
		self.thread_import_campaign = ImportThread(target=self._import_campaign)
		self.thread_import_campaign.start()

	def select_xml_campaign(self):
		"""
		Prompts the user with a file dialog window to select the King Phisher
		Campaign XML file to import. Validates the file to make sure it is a
		Campaign exported from King Phisher and is the correct version to import.
		"""
		dialog = extras.FileChooserDialog('Import Campaign from XML', self.window)
		dialog.quick_add_filter('King Phisher XML Campaign', '*.xml')
		dialog.quick_add_filter('All Files', '*')
		response = dialog.run_quick_open()
		dialog.destroy()
		if not response:
			return
		target_file = response['target_path']
		self.entry_path.set_text(target_file)

		try:
			campaign_xml = ET.parse(target_file)
		except ET.ParseError as error:
			self.logger.error("cannot import campaign: {0} is not a valid XML file".format(target_file), error)
			gui_utilities.show_dialog_error(
				'Improper Format',
				self.window,
				'{} is not a valid XML file'.format(target_file)
			)
			return

		root = campaign_xml.getroot()
		if root.tag != 'king_phisher':
			self.logger.error("not a King Phisher XML campaign file: {}".format(target_file))
			gui_utilities.show_dialog_error(
				'Improper Format',
				self.window,
				'{} is not a valid King Phisher XML campaign file'.format(target_file)
			)
			return

		meta_data = root.find('metadata')
		if meta_data.find('version').text < '1.3':
			self.logger.error("cannot import version less then 1.3, file version is {}".format(meta_data.find('version').text))
			gui_utilities.show_dialog_error(
				'Invalid Version',
				self.window,
				'cannot import XML campaign data less then version 1.3'
			)
			return

		self.campaign_info = root.find('campaign')
		if not self.campaign_info:
			gui_utilities.show_dialog_error(
				'No Campaign Data',
				self.window,
				'No campaign data to import'.format(target_file)
			)
			return

		self.db_campaigns = self.rpc.graphql("{ db { campaigns { edges { node { id, name } } } } }")['db']['campaigns']['edges']
		self.entry_campaign_name.set_text(self.campaign_info.find('name').text)
		self.thread_import_campaign = None
		if not self._check_campaign_name(self.campaign_info.find('name').text, verbose=True):
			self.button_import_campaign.set_sensitive(False)
			return
		self.button_import_campaign.set_sensitive(True)

	def _check_campaign_name(self, campaign_name, verbose=False):
		"""
		Will check to see if the provided campaign name is safe to use.

		:param str campaign_name: campaign name to check
		:param bool verbose: If true will update output to text buffer.
		:return: True if campaign name can be used
		:rtype: bool
		"""
		if not self.campaign_info or not self.db_campaigns:
			return False

		if next((nodes for nodes in self.db_campaigns if nodes['node']['name'] == campaign_name), None):
			if verbose:
				self._update_text_view("Campaign name {} is already in use by another campaign.".format(campaign_name), idle=True)
			return False

		if verbose:
			self._update_text_view("Campaign Name {} is not in use, ready to import".format(campaign_name), idle=True)
		return True

	def preprep_xml_data(self):
		"""
		This function provides the actions required to see if required IDs are
		already in the database. If they are not it will clear them out and set
		subelement.attrib['type'] to null. If the element is required it will
		set it to a default value. This will normalize the data and ready it for
		import into the database.
		"""
		self._set_text_view('Normalizing Campaign Data')
		self.campaign_info.find('name').text = self.entry_campaign_name.get_text()

		campaign_type_check = self.rpc('db/table/get', 'campaign_types', self.campaign_info.find('campaign_type_id').text)
		if not campaign_type_check:
			temp_string = 'Campaign type not found, removing'
			self.logger.info(temp_string.lower())
			self._update_text_view(temp_string, idle=True)
			reset_node = self.campaign_info.find('campaign_type_id')
			reset_node.clear()
			reset_node.attrib['type'] = 'null'

		if self.campaign_info.find('user_id').text != self.config['server_username']:
			temp_string = 'Setting the campaign owner to the current user'
			self.logger.info(temp_string.lower())
			self._update_text_view(temp_string, idle=True)
			self.campaign_info.find('user_id').text = self.config['server_username']

		company_id_check = self.rpc('db/table/get', 'companies', int(self.campaign_info.find('company_id').text))
		if not company_id_check:
			temp_string = 'Company id not found, removing'
			self.logger.info(temp_string.lower())
			self._update_text_view(temp_string, idle=True)
			reset_node = self.campaign_info.find('company_id')
			reset_node.clear()
			reset_node.attrib['type'] = 'null'

		for message in self.campaign_info.find('messages').getiterator():
			if message.tag != 'company_department_id':
				continue
			if not message.text:
				continue
			self.logger.info("checking company_department_id {}".format(message.text))
			company_department_id_check = self.rpc('db/table/get', 'company_departments', message.text)
			if not company_department_id_check:
				temp_string = "Company department id {} not found, removing it from campaign".format(message.text)
				self.logger.info(temp_string.lower())
				self._update_text_view(temp_string, idle=True)
				self._update_id(self.campaign_info, ['company_department_id'], message.text, None)

	def _import_cleanup(self, remove_campaign=False):
		if remove_campaign:
			self.remove_import_campaign()
		GLib.idle_add(self.button_import_campaign.set_sensitive, False)
		GLib.idle_add(self.button_select.set_sensitive, True)
		GLib.idle_add(self.spinner.stop)
		self.campaign_info = None

	def _import_campaign(self):
		"""
		Used by the import thread to import the campaign into the database.
		Through this process after every major action, the thread will check
		to see if it has been requested to stop.
		"""
		self.logger.debug("import campaign running in tid: 0x{0:x}".format(threading.current_thread().ident))
		if not self.campaign_info:
			return
		# prevent user from changing campaign info during import
		start_time = datetime.datetime.now()
		GLib.idle_add(self.button_import_campaign.set_sensitive, False)
		GLib.idle_add(self.button_select.set_sensitive, False)
		GLib.idle_add(self.spinner.start)

		batch_size = 100
		if self.thread_import_campaign.stopped():
			return
		self.preprep_xml_data()

		self.campaign_info.find('id').text = self.rpc(
			'campaign/new',
			self.campaign_info.find('name').text,
			self.campaign_info.find('description').text
		)
		self.logger.info("created new campaign id: {}".format(self.campaign_info.find('id').text))

		nodes_completed = 0
		node_count = float(len(self.campaign_info.findall('.//*')))
		if self.thread_import_campaign.stopped():
			return
		for nods in self.campaign_info.getiterator():
			if nods.tag == 'campaign_id':
				nods.text = self.campaign_info.find('id').text
		self._update_text_view("Campaign created, ID set to {}".format(self.campaign_info.find('id').text), idle=True)

		keys = []
		values = []
		if self.thread_import_campaign.stopped():
			return
		for elements in self.campaign_info:
			if elements.tag in ('id', 'landing_pages', 'messages', 'visits', 'credentials', 'deaddrop_deployments', 'deaddrop_connections'):
				continue
			keys.append(elements.tag)
			values.append(elements.text)

		self.rpc('db/table/set', 'campaigns', int(self.campaign_info.find('id').text), tuple(keys), tuple(values))
		nodes_completed += float(len(values) + 1)
		percentage_completed = nodes_completed / node_count
		GLib.idle_add(self.import_progress.set_fraction, percentage_completed)
		if self.thread_import_campaign.stopped():
			return

		for tables in ('landing_pages', 'messages', 'visits', 'credentials', 'deaddrop_deployments', 'deaddrop_connections'):
			inserted_ids = []
			if self.thread_import_campaign.stopped():
				return
			self._update_text_view("Serializing table {} data for import".format(tables), idle=True)
			keys, rows = self._get_keys_values(self.campaign_info.find(tables))
			self._update_text_view("Working on table {} adding {} rows".format(tables, len(rows)), idle=True)
			if self.thread_import_campaign.stopped():
				return

			# make table rows easy to manage for updating new ids returned
			table_rows = []
			for row in rows:
				row = dict(zip(keys, row))
				table_rows.append(row)

			while rows and not self.thread_import_campaign.stopped():
				try:
					inserted_ids = inserted_ids + self.rpc('/db/table/insert/multi', tables, keys, rows[:batch_size], deconflict_ids=True)
				except advancedhttpserver.RPCError:
					response = gui_utilities.glib_idle_add_wait(self.failed_import_action)
					self._import_cleanup(remove_campaign=response)
					failed_string = 'Failed to import campaign, all partial campaign data ' + ('has been removed' if response else 'was left in place')
					self.logger.warning(failed_string.lower())
					self._update_text_view(failed_string, idle=True)
					return

				rows = rows[batch_size:]
				nodes_completed += float(batch_size * len(keys))
				percentage_completed = nodes_completed / node_count
				GLib.idle_add(self.import_progress.set_fraction, percentage_completed)

			if self.thread_import_campaign.stopped():
				return

			# update id fields to maintain relationships
			self._update_text_view("Updating dependencies for table: {}".format(tables), idle=True)
			for id_ in inserted_ids:
				if id_ != table_rows[inserted_ids.index(id_)]['id']:
					self._update_id(
						self.campaign_info, ['id', "{}_id".format(tables[:-1])],
						table_rows[inserted_ids.index(id_)]['id'], id_
					)

		GLib.idle_add(self.import_progress.set_fraction, 1.0)
		self._import_cleanup()
		done_string = "Done importing campaign. Importing the campaign took {}".format(datetime.datetime.now() - start_time)
		self._update_text_view(done_string, idle=True)
		self.logger.info(done_string.lower())
