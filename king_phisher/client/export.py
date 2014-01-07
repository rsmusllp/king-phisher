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
#  * Neither the name of the  nor the names of its
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

import csv
import datetime
import xml.etree.ElementTree as ET

def campaign_to_xml(rpc, campaign_id, xml_file):
	root = ET.Element('kingphisher')
	# generate export metadata
	metadata = ET.SubElement(root, 'metadata')
	timestamp = ET.SubElement(metadata, 'timestamp')
	timestamp.text = datetime.datetime.now().isoformat()
	version = ET.SubElement(metadata, 'version')
	version.text = '1.0'

	campaign = ET.SubElement(root, 'campaign')
	campaign_info = rpc.remote_table_row('campaigns', campaign_id)
	for key, value in campaign_info.items():
		ET.SubElement(campaign, key).text = str(value).encode('utf-8')

	# Tables with a campaign_id field
	for table_name in ['messages', 'visits', 'credentials', 'deaddrop_deployments', 'deaddrop_connections']:
		table_element = ET.SubElement(campaign, table_name)
		for table_row in rpc.remote_table('campaign/' + table_name, campaign_id):
			table_row_element = ET.SubElement(table_element, table_name[:-1])
			for key, value in table_row.items():
				ET.SubElement(table_row_element, key).text = str(value).encode('utf-8')

	element_tree = ET.ElementTree(root)
	element_tree.write(xml_file, encoding = 'utf-8', xml_declaration = True)

def treeview_liststore_to_csv(treeview, target_file):
	target_file_h = open(target_file, 'wb')
	writer = csv.writer(target_file_h, quoting = csv.QUOTE_ALL)
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
