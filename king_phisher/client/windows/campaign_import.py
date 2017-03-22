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

from king_phisher import utilities
from king_phisher import serializers
from king_phisher.client import gui_utilities
from king_phisher.client.widget import extras
from king_phisher.errors import KingPhisherInputValidationError

import advancedhttpserver
from gi.repository import Gtk
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
		return self.stop_flag.isSet()

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
		self.select_button = self.gobjects['button_select']
		self.entry_campaign_name = self.gobjects['entry_campaign']
		self.entry_path = self.gobjects['entry_file']
		self.import_progress = self.gobjects['progressbar']
		self.spinner = self.gobjects['spinner']
		self.text_buffer = self.gobjects['textview'].get_buffer()

		# place holders for once an xml file is loaded
		self.campaign_info = None
		self.db_campaigns = None
		self.thread_import_campaign = None

	def _set_text_view(self, string_to_set):
		self.text_buffer.set_text(string_to_set + "\n")

	def _update_text_view(self, string_to_add):
		end_iter = self.text_buffer.get_end_iter()
		self.text_buffer.insert(end_iter, string_to_add + "\n")

	def _update_id(self, element, id_fields, old_id, new_id):
		"""
		Iterates through the element and replaces the specified old ID to the new ID in the requested ID fields.

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
				if node.attrib['type'] in ('datetime', 'date', 'time'):
					values.append(serializers.from_elementtree_element(node).replace(tzinfo=None))
				else:
					values.append(serializers.from_elementtree_element(node))
			rows.append(tuple(values))
		return keys, rows

	def interact(self):
		self.window.set_position(Gtk.WindowPosition.CENTER_ON_PARENT)
		self.window.show_all()

	def entry_change(self, _):
		"""
		When there is a change in the campaign entry field it will check to see if the name is already in use.
		If it is not in use it will change the Sensitivity of the Import Campaign Button to allow the user to
		start the import process.
		"""
		if not self.campaign_info:
			return
		if not self._check_campaign_name(self.entry_campaign_name.get_text()):
			self.button_import_campaign.set_sensitive(False)
			return
		self.button_import_campaign.set_sensitive(True)
		return

	def open_xml_file(self, _):
		if not self.select_button.get_property('sensitive'):
			return
		self.select_xml_campaign()

	def close_import_campaign(self, _):
		"""
		Checks to make sure the import campaign thread is closed before closing.
		"""
		if not self.campaign_info:
			return
		if not self.thread_import_campaign:
			return
		if not self.thread_import_campaign.isAlive():
			return
		response = gui_utilities.show_dialog(
			Gtk.MessageType.QUESTION,
			'Do you want to cancel importing the campaign?',
			self.window,
			message_buttons=Gtk.ButtonsType.YES_NO
		)
		if not response:
			return

		self.thread_import_campaign.stop()
		self.thread_import_campaign.join()
		self.remove_import_campaign()

	def failed_import_action(self):
		response = gui_utilities.show_dialog(
			Gtk.MessageType.QUESTION,
			'Import Failed, do you want to delete this campaign?',
			self.window,
			message_buttons=Gtk.ButtonsType.YES_NO
		)
		return response

	def remove_import_campaign(self):
		"""
		Used to delete the imported campaign on failure or early exit of the import window, if the user
		selects to have it removed.
		"""
		campaign_id = self.campaign_info.find('id').text
		campaign_name = self.campaign_info.find('name').text
		campaign_check = self.rpc('db/table/get', 'campaigns', campaign_id)
		if not campaign_check:
			return
		if campaign_name == campaign_check['name']:
			self.rpc('db/table/delete', 'campaigns', campaign_id)
			self.logger.info('Deleted Campaign {}'.format(campaign_id))

	def import_button(self, _):
		"""
		Function called when the user starts the import campaign process, It will create a new thread,
		to have the campaign run in the background freeing up the GUI for the user to conduct other functions.
		"""
		if not self.campaign_info:
			GLib.idle_add(self._update_text_view, 'No campaign information to import')
			self.button_import_campaign.set_sensitive(False)
			return
		self.thread_import_campaign = ImportThread(target=self.import_campaign)
		self.thread_import_campaign.start()

	def select_xml_campaign(self):
		"""
		Prompts the user with a file dialog window to select the King Phisher Campaign XML file to import.
		Validates the file to make sure it is a Campaign exported from King Phisher and is the correct version to import.
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
			self.logger.error('cannot import campaign: {0} is not a valid XML file'.format(target_file), error)
			raise KingPhisherInputValidationError('{0} is not a valid xml file'.format(target_file))

		root = campaign_xml.getroot()
		if root.tag != 'king_phisher':
			raise KingPhisherInputValidationError('File not a King Phisher Campaign XML Export File')
		meta_data = root.find('metadata')
		if meta_data.find('version').text < '1.3':
			raise KingPhisherInputValidationError('Can only import XML Campaign data version 1.3 or higher')
		self.campaign_info = root.find('campaign')
		if not self.campaign_info:
			raise KingPhisherInputValidationError('XML File does not contain any campaign information')

		self.db_campaigns = self.rpc.graphql("{ db { campaigns { edges { node { id, name } } } } }")['db']['campaigns']['edges']
		self.entry_campaign_name.set_text(self.campaign_info.find('name').text)
		self.thread_import_campaign = None
		if not self._check_campaign_name(self.campaign_info.find('name').text, verbose=True):
			self.button_import_campaign.set_sensitive(False)
			return
		self.button_import_campaign.set_sensitive(True)

	def _check_campaign_name(self, campaign_name, verbose=False):
		"""
		Used to check to see the user has provided a campaign name that is not already in use.
		If verbose is used it will display information in detailed output text buffer.

		:param str campaign_name: campaign name to check
		:param bool verbose:
		:return: True if campaign name can be used
		:rtype: bool
		"""
		if not self.campaign_info or not self.db_campaigns:
			return False

		if next((nodes for nodes in self.db_campaigns if nodes['node']['name'] == campaign_name), None):
			if verbose:
				GLib.idle_add(
					self._update_text_view,
					'Campaign name {} is already in use by another campaign.'.format(campaign_name)
				)
			return False

		if verbose:
			GLib.idle_add(self._update_text_view, 'Campaign Name {} is not in use, ready to import'.format(campaign_name))
		return True

	def prepep_xml_data(self):
		"""
		This function provides the actions required to see if depended IDs are already in the database.
		If they are not it will clear them out and set subelement.attrib['type'] to null.
		If the element is required it will set it to a default value.
		This will normalize the data and ready it for import into the database.
		"""
		GLib.idle_add(
			self._set_text_view,
			'{}: Normalizing Campaign Data'.format(utilities.format_datetime(datetime.datetime.now()))
		)
		self.campaign_info.find('name').text = self.entry_campaign_name.get_text()

		campaign_type_check = self.rpc('db/table/get', 'campaign_types', self.campaign_info.find('campaign_type_id').text)
		if not campaign_type_check:
			temp_string = 'Campaign type not found, removing'
			self.logger.info(temp_string)
			GLib.idle_add(self._set_text_view, temp_string)
			reset_node = self.campaign_info.find('campaign_type_id')
			reset_node.clear()
			reset_node.attrib['type'] = 'null'

		user_id_check = self.rpc('db/table/get', 'users', self.campaign_info.find('user_id').text)
		if not user_id_check:
			temp_string = 'User {0} not found, setting created by to current user'.format(self.campaign_info.find('user_id').text)
			self.logger.info(temp_string)
			GLib.idle_add(self._set_text_view, temp_string)
			self.campaign_info.find('user_id').text = self.config['server_username']

		company_id_check = self.rpc('db/table/get', 'companies', int(self.campaign_info.find('company_id').text))
		if not company_id_check:
			temp_string = 'Company id not found, removing'
			self.logger.info(temp_string)
			GLib.idle_add(self._set_text_view, temp_string)
			reset_node = self.campaign_info.find('company_id')
			reset_node.clear()
			reset_node.attrib['type'] = 'null'

		for message in self.campaign_info.find('messages').getiterator():
			if message.tag != 'company_department_id':
				continue
			if not message.text:
				continue
			self.logger.info('checking company_department_id {}'.format(message.text))
			company_department_id_check = self.rpc('db/table/get', 'company_departments', message.text)
			if not company_department_id_check:
				temp_string = 'Company department id not found, removing it from campaign'
				self.logger.info(temp_string)
				GLib.idle_add(self._set_text_view, temp_string)
				self._update_id(self.campaign_info, ['company_department_id'], message.text, None)

	def import_campaign(self):
		"""
		Used by the import thread to import the campaign into the database.
		Through this process after every major process, the thread will check to see if it has been stopped.
		"""
		if not self.campaign_info:
			return
		# prevent user from changing campaign info during import
		start_time = datetime.datetime.now()
		GLib.idle_add(self.button_import_campaign.set_sensitive, False)
		GLib.idle_add(self.select_button.set_sensitive, False)
		GLib.idle_add(self.spinner.start)

		batch_size = 100
		if self.thread_import_campaign.stopped():
			return
		self.prepep_xml_data()

		self.campaign_info.find('id').text = self.rpc(
			'campaign/new',
			self.campaign_info.find('name').text,
			self.campaign_info.find('description').text
		)
		self.logger.info('created new campaign id: {}'.format(self.campaign_info.find('id').text))

		nodes_completed = 0
		node_count = float(len(self.campaign_info.findall('.//*')))
		if self.thread_import_campaign.stopped():
			return
		for nods in self.campaign_info.getiterator():
			if nods.tag == 'campaign_id':
				nods.text = self.campaign_info.find('id').text
		GLib.idle_add(self._update_text_view, 'Campaign created, ID set to {}'.format(self.campaign_info.find('id').text))

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
			GLib.idle_add(self._update_text_view, 'Serializing table {} data for import'.format(tables))
			keys, rows = self._get_keys_values(self.campaign_info.find(tables))
			GLib.idle_add(self._update_text_view, 'Working on table {} adding {} rows'.format(tables, len(rows)))
			if self.thread_import_campaign.stopped():
				return

			# make table rows easy to manage for updating new ids returned
			table_rows = []
			for row in rows:
				row = dict(zip(keys, row))
				table_rows.append(row)

			while len(rows) > 0:
				if self.thread_import_campaign.stopped():
					return
				try:
					inserted_ids = inserted_ids + self.rpc('/db/table/insert/multi', tables, keys, rows[:batch_size], deconflict_ids=True)
				except advancedhttpserver.RPCError:
					response = gui_utilities.glib_idle_add_wait(self.failed_import_action)
					if response:
						self.remove_import_campaign()
						GLib.idle_add(self.button_import_campaign.set_sensitive, False)
						GLib.idle_add(self.select_button.set_sensitive, True)
						GLib.idle_add(self.spinner.stop)
						return

				rows = rows[batch_size:]
				nodes_completed += float(batch_size * len(keys))
				percentage_completed = nodes_completed / node_count
				GLib.idle_add(self.import_progress.set_fraction, percentage_completed)
				if self.thread_import_campaign.stopped():
					return

			# update id fields to maintain relationships
			GLib.idle_add(self._update_text_view, 'Updating dependencies for table: {}'.format(tables))
			for id_ in inserted_ids:
				if id_ != table_rows[inserted_ids.index(id_)]['id']:
					self._update_id(
						self.campaign_info, ['id', '{}_id'.format(tables[:-1])],
						table_rows[inserted_ids.index(id_)]['id'], id_
					)

		GLib.idle_add(self.import_progress.set_fraction, 1.0)
		GLib.idle_add(self.button_import_campaign.set_sensitive, False)
		self.campaign_info = None
		GLib.idle_add(self.entry_campaign_name.set_text, '')
		GLib.idle_add(self.entry_path.set_text, '')
		GLib.idle_add(self.select_button.set_sensitive, True)
		GLib.idle_add(self.spinner.stop)
		done_string = 'Done importing campaign it took {}'.format(datetime.datetime.now() - start_time)
		GLib.idle_add(self._update_text_view, done_string)
		self.logger.info(done_string)
