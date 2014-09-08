#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  king_phisher/client/export.py
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

import copy
import csv
import datetime
import json
import os
import shutil
import tarfile
import xml.etree.ElementTree as ET

try:
	import cStringIO as StringIO
except ImportError:
	import StringIO

__all__ = ['campaign_to_xml', 'convert_value', 'message_data_to_kpm', 'treeview_liststore_to_csv']

TABLE_VALUE_CONVERSIONS = {
	'campaigns/created': lambda ts: datetime.datetime.strptime(ts, '%Y-%m-%d %H:%M:%S').isoformat(),
	'campaigns/reject_after_credentials': bool,
	'messages/opened': lambda value: (None if value == None else value),
	'messages/trained': bool
}

def convert_value(table_name, key, value):
	"""
	Perform any conversions necessary to neatly display the data in XML
	format.

	:param str table_name: The table name that the key and value pair are from.
	:param str key: The data key.
	:param value: The data value to convert.
	:return: The converted value.
	:rtype: str
	"""
	conversion_key = table_name + '/' + key
	if conversion_key in TABLE_VALUE_CONVERSIONS:
		value = TABLE_VALUE_CONVERSIONS[conversion_key](value)
	if value != None:
		value = str(value).encode('utf-8')
	return value

def campaign_to_xml(rpc, campaign_id, xml_file):
	"""
	Load all information for a particular campaign and dump it to an XML
	file.

	:param rpc: The connected RPC instance to load the information with.
	:type rpc: :py:class:`.KingPhisherRPCClient`
	:param campaign_id: The ID of the campaign to load the information for.
	:param str xml_file: The destination file for the XML data.
	"""
	root = ET.Element('kingphisher')
	# Generate export metadata
	metadata = ET.SubElement(root, 'metadata')
	timestamp = ET.SubElement(metadata, 'timestamp')
	timestamp.text = datetime.datetime.now().isoformat()
	version = ET.SubElement(metadata, 'version')
	version.text = '1.1'

	campaign = ET.SubElement(root, 'campaign')
	campaign_info = rpc.remote_table_row('campaigns', campaign_id)
	for key, value in campaign_info.items():
		ET.SubElement(campaign, key).text = convert_value('campaigns', key, value)

	# Tables with a campaign_id field
	for table_name in ['landing_pages', 'messages', 'visits', 'credentials', 'deaddrop_deployments', 'deaddrop_connections']:
		table_element = ET.SubElement(campaign, table_name)
		for table_row in rpc.remote_table('campaign/' + table_name, campaign_id):
			table_row_element = ET.SubElement(table_element, table_name[:-1])
			for key, value in table_row.items():
				ET.SubElement(table_row_element, key).text = convert_value(table_name, key, value)

	element_tree = ET.ElementTree(root)
	element_tree.write(xml_file, encoding='utf-8', xml_declaration=True)

def message_data_from_kpm(target_file, dest_dir):
	"""
	Retrieve the stored details describing a message from a previously exported
	file.

	:param str target_file: The file to load as a message archive.
	:param str dest_dir: The directory to extract data and attachment files to.
	:return: The restored details from the message config.
	:rtype: dict
	"""
	tar_h = tarfile.open(target_file)
	member_names = tar_h.getnames()
	tar_get_file = lambda name: tar_h.extractfile(tar_h.getmember(name))

	message_config = tar_get_file('message_config.json').read()
	message_config = json.loads(message_config)

	if 'message_content.html' in member_names:
		msg_content = tar_get_file('message_content.html')
		with open(os.path.join(dest_dir, message_config['html_file']), 'wb') as file_h:
			shutil.copyfileobj(msg_content, file_h)

	return message_config

def message_data_to_kpm(message_config, attachments, target_file):
	"""
	Save details describing a message to the target file.

	:param dict message_config: The message details from the :py:attr:`~.KingPhisherClient.config`.
	:param list attachments: A list of attachments for the message to be inserted into the archive.
	:param str target_file: The file to write the data to.
	"""
	message_config = copy.copy(message_config)
	epoch = datetime.datetime.utcfromtimestamp(0)
	mtime = (datetime.datetime.utcnow() - epoch).total_seconds()
	tar_h = tarfile.open(target_file, 'w:bz2')

	if os.path.isfile(message_config.get('html_file', '')):
		tar_h.add(message_config['html_file'], arcname='message_content.html')
		message_config['html_file'] = os.path.basename(message_config['html_file'])
	elif 'html_file' in message_config:
		del message_config['html_file']

	if os.path.isfile(message_config.get('target_file', '')):
		tar_h.add(message_config['target_file'], arcname='target_file.csv')
		message_config['target_file'] = os.path.basename(message_config['target_file'])
	elif 'target_file' in message_config:
		del message_config['target_file']

	msg_strio = StringIO.StringIO()
	msg_strio.write(json.dumps(message_config, sort_keys=True, indent=4))
	tarinfo_h = tarfile.TarInfo(name='message_config.json')
	tarinfo_h.mtime = mtime
	tarinfo_h.size = msg_strio.tell()
	msg_strio.seek(os.SEEK_SET)
	tar_h.addfile(tarinfo=tarinfo_h, fileobj=msg_strio)

	tar_h.close()
	return

def treeview_liststore_to_csv(treeview, target_file):
	"""
	Convert a treeview object to a CSV file. The CSV column names are loaded
	from the treeview.

	:param treeview: The treeview to load the information from.
	:type treeview: :py:class:`Gtk.TreeView`
	:param str target_file: The destination file for the CSV data.
	:return: The number of rows that were written.
	:rtype: int
	"""
	target_file_h = open(target_file, 'wb')
	writer = csv.writer(target_file_h, quoting=csv.QUOTE_ALL)
	column_names = map(lambda x: x.get_property('title'), treeview.get_columns())
	column_names.insert(0, 'UID')
	column_count = len(column_names)
	writer.writerow(column_names)
	store = treeview.get_model()
	store_iter = store.get_iter_first()
	rows_written = 0
	while store_iter:
		values = map(lambda x: store.get_value(store_iter, x), range(column_count))
		writer.writerow(values)
		rows_written += 1
		store_iter = store.iter_next(store_iter)
	target_file_h.close()
	return rows_written
