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

import codecs
import collections
import copy
import csv
import datetime
import logging
import os
import re
import shutil
import xml.etree.ElementTree as ET
import xml.dom.minidom as minidom

from king_phisher import archive
from king_phisher import errors
from king_phisher import ipaddress
from king_phisher import serializers
from king_phisher import utilities

from boltons import iterutils
import dateutil.tz
import geojson
from smoke_zephyr.utilities import escape_single_quote
from smoke_zephyr.utilities import unescape_single_quote
from smoke_zephyr.utilities import parse_case_snake_to_camel
import xlsxwriter

__all__ = (
	'campaign_to_xml',
	'convert_value',
	'liststore_export',
	'liststore_to_csv',
	'liststore_to_xlsx_worksheet',
	'message_data_to_kpm'
)

KPM_ARCHIVE_FILES = {
	'attachment_file': 'message_attachment.bin',
	'target_file': 'target_file.csv'
}

KPM_INLINE_IMAGE_REGEXP = re.compile(r"""{{\s*inline_image\(\s*(('(?:[^'\\]|\\.)+')|("(?:[^"\\]|\\.)+"))\s*\)\s*}}""")

logger = logging.getLogger('KingPhisher.Client.export')

XLSXWorksheetOptions = collections.namedtuple('XLSXWorksheetOptions', ('column_widths', 'title'))

def message_template_to_kpm(template):
	files = []
	cursor = 0
	match = True
	while match:
		match = KPM_INLINE_IMAGE_REGEXP.search(template[cursor:])
		if not match:
			break
		file_path = unescape_single_quote(match.group(1)[1:-1])
		files.append(file_path)
		file_name = os.path.basename(file_path)
		start = cursor + match.start()
		end = cursor + match.end()
		inline_tag = "{{{{ inline_image('{0}') }}}}".format(escape_single_quote(file_name))
		template = template[:start] + inline_tag + template[end:]
		cursor = start + len(inline_tag)
	return template, files

def message_template_from_kpm(template, files):
	files = dict(zip(map(os.path.basename, files), files))
	cursor = 0
	match = True
	while match:
		match = KPM_INLINE_IMAGE_REGEXP.search(template[cursor:])
		if not match:
			break
		file_name = unescape_single_quote(match.group(1)[1:-1])
		file_path = files.get(file_name)
		start = cursor + match.start()
		end = cursor + match.end()
		if not file_path:
			cursor = end
			continue
		insert_tag = "{{{{ inline_image('{0}') }}}}".format(escape_single_quote(file_path))
		template = template[:start] + insert_tag + template[end:]
		cursor = start + len(insert_tag)
	return template

def convert_value(table_name, key, value):
	"""
	Perform any conversions necessary to neatly display the data in XML format.

	:param str table_name: The table name that the key and value pair are from.
	:param str key: The data key.
	:param value: The data value to convert.
	:return: The converted value.
	:rtype: str
	"""
	if isinstance(value, datetime.datetime):
		value = value.isoformat()
	if value is not None:
		value = str(value)
	return value

def campaign_to_xml(rpc, campaign_id, xml_file, encoding='utf-8'):
	"""
	Load all information for a particular campaign and dump it to an XML file.

	:param rpc: The connected RPC instance to load the information with.
	:type rpc: :py:class:`.KingPhisherRPCClient`
	:param campaign_id: The ID of the campaign to load the information for.
	:param str xml_file: The destination file for the XML data.
	:param str encoding: The encoding to use for strings.
	"""
	tzutc = dateutil.tz.tzutc()
	root = ET.Element('king_phisher')
	# Generate export metadata
	metadata = ET.SubElement(root, 'metadata')
	serializers.to_elementtree_subelement(
		metadata,
		'timestamp',
		datetime.datetime.utcnow().replace(tzinfo=tzutc),
		attrib={'utc': 'true'}
	)
	serializers.to_elementtree_subelement(metadata, 'version', '1.3')

	campaign = ET.SubElement(root, 'campaign')
	logger.info('gathering campaign information for export')
	page_size = 2
	try:
		campaign_info = rpc.graphql_find_file('get_campaign_export.graphql', id=campaign_id, page=page_size)['db']['campaign']
	except errors.KingPhisherGraphQLQueryError as error:
		logger.error('graphql error: ' + error.message)
		raise
	for key, value in campaign_info.items():
		if key in ('landingPages', 'messages', 'visits', 'credentials', 'deaddropDeployments', 'deaddropConnections'):
			continue
		if isinstance(value, datetime.datetime):
			value = value.replace(tzinfo=tzutc)
		serializers.to_elementtree_subelement(campaign, key, value)

	table_elements = {}
	while True:
		cursor = None  # set later if any table hasNextPage
		for table_name in ('landing_pages', 'messages', 'visits', 'credentials', 'deaddrop_deployments', 'deaddrop_connections'):
			gql_table_name = parse_case_snake_to_camel(table_name, upper_first=False)
			if campaign_info[gql_table_name]['pageInfo']['hasNextPage']:
				cursor = campaign_info[gql_table_name]['pageInfo']['endCursor']
			table = campaign_info[gql_table_name]['edges']
			if table_name not in table_elements:
				table_elements[table_name] = ET.SubElement(campaign, table_name)
			for node in table:
				table_row_element = ET.SubElement(table_elements[table_name], table_name[:-1])
				for key, value in node['node'].items():
					if isinstance(value, datetime.datetime):
						value = value.replace(tzinfo=tzutc)
					serializers.to_elementtree_subelement(table_row_element, key, value)
		if cursor is None:
			break
		campaign_info = rpc.graphql_find_file('get_campaign_export.graphql', id=campaign_id, cursor=cursor, page=page_size)['db']['campaign']
	logger.info('completed processing campaign information for export')

	document = minidom.parseString(ET.tostring(root))
	with open(xml_file, 'wb') as file_h:
		file_h.write(document.toprettyxml(indent='  ', encoding=encoding))
	logger.info('campaign export complete')

def campaign_credentials_to_msf_txt(rpc, campaign_id, target_file):
	"""
	Export credentials into a format that can easily be used with Metasploit's
	USERPASS_FILE option.

	:param rpc: The connected RPC instance to load the information with.
	:type rpc: :py:class:`.KingPhisherRPCClient`
	:param campaign_id: The ID of the campaign to load the information for.
	:param str target_file: The destination file for the credential data.
	"""
	with open(target_file, 'w') as file_h:
		for credential_node in _get_graphql_campaign_credentials(rpc, campaign_id):
			credential = credential_node['node']
			file_h.write("{0} {1}\n".format(credential['username'], credential['password']))

def _get_graphql_campaign_credentials(rpc, campaign_id):
	results = rpc.graphql("""\
	query getCampaignCredentials($campaign: String!) {
		db {
			campaign(id: $campaign) {
				credentials {
					edges {
						node {
							username
							password
						}
					}
				}
			}
		}
	}""", {'campaign': campaign_id})
	return results['db']['campaign']['credentials']['edges']

def campaign_visits_to_geojson(rpc, campaign_id, geojson_file):
	"""
	Export the geo location information for all the visits of a campaign into
	the `GeoJSON <http://geojson.org/>`_ format.

	:param rpc: The connected RPC instance to load the information with.
	:type rpc: :py:class:`.KingPhisherRPCClient`
	:param campaign_id: The ID of the campaign to load the information for.
	:param str geojson_file: The destination file for the GeoJSON data.
	"""
	ips_for_georesolution = {}
	ip_counter = collections.Counter()
	for visit_node in _get_graphql_campaign_visits(rpc, campaign_id):
		visit = visit_node['node']
		ip_counter.update((visit['ip'],))
		visitor_ip = ipaddress.ip_address(visit['ip'])
		if not isinstance(visitor_ip, ipaddress.IPv4Address):
			continue
		if visitor_ip.is_loopback or visitor_ip.is_private:
			continue
		if not visitor_ip in ips_for_georesolution:
			ips_for_georesolution[visitor_ip] = visit['firstSeen']
		elif ips_for_georesolution[visitor_ip] > visit['firstSeen']:
			ips_for_georesolution[visitor_ip] = visit['firstSeen']
	ips_for_georesolution = [ip for (ip, _) in sorted(ips_for_georesolution.items(), key=lambda x: x[1])]
	locations = {}
	for ip_addresses in iterutils.chunked(ips_for_georesolution, 50):
		locations.update(rpc.geoip_lookup_multi(ip_addresses))
	points = []
	for ip, location in locations.items():
		if not (location.coordinates and location.coordinates[0] and location.coordinates[1]):
			continue
		points.append(geojson.Feature(geometry=location, properties={'count': ip_counter[ip], 'ip-address': ip}))
	feature_collection = geojson.FeatureCollection(points)
	with open(geojson_file, 'w') as file_h:
		serializers.JSON.dump(feature_collection, file_h, pretty=True)

def _get_graphql_campaign_visits(rpc, campaign_id):
	results = rpc.graphql("""\
	query getCampaignVisits($campaign: String!) {
		db {
			campaign(id: $campaign) {
				visits {
					edges {
						node {
							firstSeen
							ip
						}
					}
				}
			}
		}
	}""", {'campaign': campaign_id})
	return results['db']['campaign']['visits']['edges']

def message_data_from_kpm(target_file, dest_dir, encoding='utf-8'):
	"""
	Retrieve the stored details describing a message from a previously exported
	file.

	:param str target_file: The file to load as a message archive.
	:param str dest_dir: The directory to extract data and attachment files to.
	:param str encoding: The encoding to use for strings.
	:return: The restored details from the message config.
	:rtype: dict
	"""
	if not archive.is_archive(target_file):
		logger.warning('the file is not recognized as a valid archive')
		raise errors.KingPhisherInputValidationError('file is not in the correct format')
	kpm = archive.ArchiveFile(target_file, 'r')

	attachment_member_names = [n for n in kpm.file_names if n.startswith('attachments' + os.path.sep)]
	attachments = []

	if not kpm.has_file('message_config.json'):
		logger.warning('the kpm archive is missing the message_config.json file')
		raise errors.KingPhisherInputValidationError('data is missing from the message archive')
	message_config = kpm.get_data('message_config.json')
	message_config = message_config.decode(encoding)
	message_config = serializers.JSON.loads(message_config)

	if attachment_member_names:
		attachment_dir = os.path.join(dest_dir, 'attachments')
		if not os.path.isdir(attachment_dir):
			os.mkdir(attachment_dir)
		for file_name in attachment_member_names:
			arcfile_h = kpm.get_file(file_name)
			file_path = os.path.join(attachment_dir, os.path.basename(file_name))
			with open(file_path, 'wb') as file_h:
				shutil.copyfileobj(arcfile_h, file_h)
			attachments.append(file_path)
		logger.debug("extracted {0} attachment file{1} from the archive".format(len(attachments), 's' if len(attachments) > 1 else ''))

	for config_name, file_name in KPM_ARCHIVE_FILES.items():
		if not file_name in kpm.file_names:
			if config_name in message_config:
				logger.warning("the kpm archive is missing the {0} file".format(file_name))
				raise errors.KingPhisherInputValidationError('data is missing from the message archive')
			continue
		if not message_config.get(config_name):
			logger.warning("the kpm message configuration is missing the {0} setting".format(config_name))
			raise errors.KingPhisherInputValidationError('data is missing from the message archive')
		arcfile_h = kpm.get_file(file_name)
		file_path = os.path.join(dest_dir, os.path.basename(message_config[config_name]))
		with open(file_path, 'wb') as file_h:
			shutil.copyfileobj(arcfile_h, file_h)
		message_config[config_name] = file_path

	if 'message_content.html' in kpm.file_names:
		if 'html_file' not in message_config:
			logger.warning('the kpm message configuration is missing the html_file setting')
			raise errors.KingPhisherInputValidationError('data is missing from the message archive')
		arcfile_h = kpm.get_file('message_content.html')
		file_path = os.path.join(dest_dir, os.path.basename(message_config['html_file']))
		with open(file_path, 'wb') as file_h:
			file_h.write(message_template_from_kpm(arcfile_h.read().decode(encoding), attachments).encode(encoding))
		message_config['html_file'] = file_path
	elif 'html_file' in message_config:
		logger.warning('the kpm archive is missing the message_content.html file')
		raise errors.KingPhisherInputValidationError('data is missing from the message archive')
	kpm.close()
	return message_config

def message_data_to_kpm(message_config, target_file, encoding='utf-8'):
	"""
	Save details describing a message to the target file.

	:param dict message_config: The message details from the client configuration.
	:param str target_file: The file to write the data to.
	:param str encoding: The encoding to use for strings.
	"""
	message_config = copy.copy(message_config)
	kpm = archive.ArchiveFile(target_file, 'w')

	for config_name, file_name in KPM_ARCHIVE_FILES.items():
		if os.access(message_config.get(config_name, ''), os.R_OK):
			kpm.add_file(file_name, message_config[config_name])
			message_config[config_name] = os.path.basename(message_config[config_name])
			continue
		if len(message_config.get(config_name, '')):
			logger.info("the specified {0} '{1}' is not readable, the setting will be removed".format(config_name, message_config[config_name]))
		if config_name in message_config:
			del message_config[config_name]

	if os.access(message_config.get('html_file', ''), os.R_OK):
		with codecs.open(message_config['html_file'], 'r', encoding=encoding) as file_h:
			template = file_h.read()
		message_config['html_file'] = os.path.basename(message_config['html_file'])
		template, attachments = message_template_to_kpm(template)
		logger.debug("identified {0} attachment file{1} to be archived".format(len(attachments), 's' if len(attachments) > 1 else ''))
		kpm.add_data('message_content.html', template)
		for attachment in attachments:
			if os.access(attachment, os.R_OK):
				kpm.add_file(os.path.join('attachments', os.path.basename(attachment)), attachment)
	else:
		if len(message_config.get('html_file', '')):
			logger.info("the specified html_file '{0}' is not readable, the setting will be removed".format(message_config['html_file']))
		if 'html_file' in message_config:
			del message_config['html_file']

	kpm.add_data('message_config.json', serializers.JSON.dumps(message_config, pretty=True))
	kpm.close()
	return

def _split_columns(columns):
	if isinstance(columns, collections.OrderedDict):
		column_names = (columns[c] for c in columns.keys())
		store_columns = columns.keys()
	else:
		column_names = (columns[c] for c in sorted(columns.keys()))
		store_columns = sorted(columns.keys())
	return tuple(column_names), tuple(store_columns)

def liststore_export(store, columns, cb_write, cb_write_args, row_offset=0, write_columns=True):
	"""
	A function to facilitate writing values from a list store to an arbitrary
	callback for exporting to different formats. The callback will be called
	with the row number, the column values and the additional arguments
	specified in *\\*cb_write_args*.

	.. code-block:: python

	  cb_write(row, column_values, *cb_write_args).

	:param store: The store to export the information from.
	:type store: :py:class:`Gtk.ListStore`
	:param dict columns: A dictionary mapping store column ids to the value names.
	:param function cb_write: The callback function to be called for each row of data.
	:param tuple cb_write_args: Additional arguments to pass to *cb_write*.
	:param int row_offset: A modifier value to add to the row numbers passed to *cb_write*.
	:param bool write_columns: Write the column names to the export.
	:return: The number of rows that were written.
	:rtype: int
	"""
	column_names, store_columns = _split_columns(columns)
	if write_columns:
		cb_write(0, column_names, *cb_write_args)

	store_iter = store.get_iter_first()
	rows_written = 0
	while store_iter:
		cb_write(rows_written + 1 + row_offset, (store.get_value(store_iter, c) for c in store_columns), *cb_write_args)
		rows_written += 1
		store_iter = store.iter_next(store_iter)
	return rows_written

def _csv_write(row, columns, writer):
	writer.writerow(tuple(columns))

def liststore_to_csv(store, target_file, columns):
	"""
	Write the contents of a :py:class:`Gtk.ListStore` to a csv file.

	:param store: The store to export the information from.
	:type store: :py:class:`Gtk.ListStore`
	:param str target_file: The destination file for the CSV data.
	:param dict columns: A dictionary mapping store column ids to the value names.
	:return: The number of rows that were written.
	:rtype: int
	"""
	target_file_h = open(target_file, 'w')
	writer = csv.writer(target_file_h, quoting=csv.QUOTE_ALL)
	rows = liststore_export(store, columns, _csv_write, (writer,))
	target_file_h.close()
	return rows

def _xlsx_write(row, columns, worksheet, row_format=None):
	for column, text in enumerate(columns):
		worksheet.write(row, column, text, row_format)

def liststore_to_xlsx_worksheet(store, worksheet, columns, title_format, xlsx_options=None):
	"""
	Write the contents of a :py:class:`Gtk.ListStore` to an XLSX workseet.

	:param store: The store to export the information from.
	:type store: :py:class:`Gtk.ListStore`
	:param worksheet: The destination sheet for the store's data.
	:type worksheet: :py:class:`xlsxwriter.worksheet.Worksheet`
	:param dict columns: A dictionary mapping store column ids to the value names.
	:param xlsx_options: A collection of additional options for formatting the Excel Worksheet.
	:type xlsx_options: :py:class:`.XLSXWorksheetOptions`
	:return: The number of rows that were written.
	:rtype: int
	"""
	utilities.assert_arg_type(worksheet, xlsxwriter.worksheet.Worksheet, 2)
	utilities.assert_arg_type(columns, dict, 3)
	utilities.assert_arg_type(title_format, xlsxwriter.format.Format, 4)
	utilities.assert_arg_type(xlsx_options, (type(None), XLSXWorksheetOptions), 5)

	if xlsx_options is None:
		worksheet.set_column(0, len(columns), 30)
	else:
		for column, width in enumerate(xlsx_options.column_widths):
			worksheet.set_column(column, column, width)

	column_names, _ = _split_columns(columns)
	if xlsx_options is None:
		start_row = 0
	else:
		start_row = 2
		worksheet.merge_range(0, 0, 0, len(column_names) - 1, xlsx_options.title, title_format)
	row_count = liststore_export(store, columns, _xlsx_write, (worksheet,), row_offset=start_row, write_columns=False)

	if not row_count:
		column_ = 0
		for column_name in column_names:
			worksheet.write(start_row, column_, column_name)
			column_ += 1
		return row_count

	options = {
		'columns': list({'header': column_name} for column_name in column_names),
		'style': 'Table Style Medium 1'
	}
	worksheet.add_table(start_row, 0, row_count + start_row, len(column_names) - 1, options=options)
	worksheet.freeze_panes(1 + start_row, 0)
	return row_count
