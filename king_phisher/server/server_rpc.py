#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  king_phisher/server/server_rpc.py
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

import contextlib
import threading

from king_phisher import version
from king_phisher.server import database

VIEW_ROW_COUNT = 25
DATABASE_TABLES = database.DATABASE_TABLES

class KingPhisherRequestHandlerRPC(object):
	def install_handlers(self):
		super(KingPhisherRequestHandlerRPC, self).install_handlers()
		self.rpc_handler_map['/ping'] = self.rpc_ping
		self.rpc_handler_map['/shutdown'] = self.rpc_shutdown
		self.rpc_handler_map['/version'] = self.rpc_version

		self.rpc_handler_map['/client/initialize'] = self.rpc_client_initialize
		self.rpc_handler_map['/config/get'] = self.rpc_config_get
		self.rpc_handler_map['/config/set'] = self.rpc_config_set

		self.rpc_handler_map['/campaign/alerts/is_subscribed'] = self.rpc_campaign_alerts_is_subscribed
		self.rpc_handler_map['/campaign/alerts/subscribe'] = self.rpc_campaign_alerts_subscribe
		self.rpc_handler_map['/campaign/alerts/unsubscribe'] = self.rpc_campaign_alerts_unsubscribe
		self.rpc_handler_map['/campaign/landing_page/new'] = self.rpc_campaign_landing_page_new
		self.rpc_handler_map['/campaign/message/new'] = self.rpc_campaign_message_new
		self.rpc_handler_map['/campaign/new'] = self.rpc_campaign_new
		self.rpc_handler_map['/campaign/delete'] = self.rpc_campaign_delete

		for table_name in DATABASE_TABLES.keys():
			self.rpc_handler_map['/' + table_name + '/count'] = self.rpc_database_count_rows
			self.rpc_handler_map['/' + table_name + '/delete'] = self.rpc_database_delete_row_by_id
			self.rpc_handler_map['/' + table_name + '/get'] = self.rpc_database_get_row_by_id
			self.rpc_handler_map['/' + table_name + '/insert'] = self.rpc_database_insert_row
			self.rpc_handler_map['/' + table_name + '/set'] = self.rpc_database_set_row_value
			self.rpc_handler_map['/' + table_name + '/view'] = self.rpc_database_get_rows

		# Tables with a campaign_id field
		for table_name in database.get_tables_with_column_id('campaign_id'):
			self.rpc_handler_map['/campaign/' + table_name + '/count'] = self.rpc_database_count_rows
			self.rpc_handler_map['/campaign/' + table_name + '/view'] = self.rpc_database_get_rows

		# Tables with a message_id field
		for table_name in database.get_tables_with_column_id('message_id'):
			self.rpc_handler_map['/message/' + table_name + '/count'] = self.rpc_database_count_rows
			self.rpc_handler_map['/message/' + table_name + '/view'] = self.rpc_database_get_rows

	@contextlib.contextmanager
	def get_cursor(self):
		with self.database.get_cursor() as cursor:
			yield cursor

	def query_count(self, query, values):
		with self.get_cursor() as cursor:
			cursor.execute(query, values)
			count = cursor.fetchone()[0]
		return count

	def rpc_ping(self):
		return True

	def rpc_client_initialize(self):
		username = self.basic_auth_user
		if not username:
			return True
		with self.get_cursor() as cursor:
			cursor.execute('INSERT OR IGNORE INTO users (id) VALUES (?)', (username,))
		return True

	def rpc_shutdown(self):
		shutdown_thread = threading.Thread(target = self.server.shutdown)
		shutdown_thread.start()
		return

	def rpc_version(self):
		return {'version':version.version, 'version_info':version.version_info._asdict()}

	def rpc_config_get(self, option_name):
		if isinstance(option_name, (list, tuple)):
			option_names = option_name
			option_values = {}
			for option_name in option_names:
				if self.config.has_option(option_name):
					option_values[option_name] = self.config.get(option_name)
			return option_values
		elif self.config.has_option(option_name):
			return self.config.get(option_name)
		return

	def rpc_config_set(self, options):
		for option_name, option_value in options.items():
			self.config.set(option_name, option_value)
		return

	def rpc_campaign_new(self, name):
		with self.get_cursor() as cursor:
			cursor.execute('INSERT INTO campaigns (name, creator) VALUES (?, ?)', (name, self.basic_auth_user))
			cursor.execute('SELECT id FROM campaigns WHERE name = ?', (name,))
			campaign_id = cursor.fetchone()[0]
		return campaign_id

	def rpc_campaign_alerts_is_subscribed(self, campaign_id):
		username = self.basic_auth_user
		with self.get_cursor() as cursor:
			if self.query_count('SELECT COUNT(id) FROM alert_subscriptions WHERE user_id = ? AND campaign_id = ?', (username, campaign_id)):
				return True
		return False

	def rpc_campaign_alerts_subscribe(self, campaign_id):
		username = self.basic_auth_user
		with self.get_cursor() as cursor:
			if self.query_count('SELECT COUNT(id) FROM alert_subscriptions WHERE user_id = ? AND campaign_id = ?', (username, campaign_id)):
				return
			cursor.execute('INSERT INTO alert_subscriptions (user_id, campaign_id) VALUES (?, ?)', (username, campaign_id))
		return

	def rpc_campaign_alerts_unsubscribe(self, campaign_id):
		username = self.basic_auth_user
		with self.get_cursor() as cursor:
			cursor.execute('DELETE FROM alert_subscriptions WHERE user_id = ? AND campaign_id = ?', (username, campaign_id))

	def rpc_campaign_landing_page_new(self, campaign_id, hostname, page):
		page = page.lstrip('/')
		if self.query_count('SELECT COUNT(id) FROM landing_pages WHERE campaign_id = ? AND hostname = ? AND page = ?', (campaign_id, hostname, page)):
			return
		with self.get_cursor() as cursor:
			cursor.execute('INSERT INTO landing_pages (campaign_id, hostname, page) VALUES (?, ?, ?)', (campaign_id, hostname, page))
		return

	def rpc_campaign_message_new(self, campaign_id, email_id, email_target):
		with self.get_cursor() as cursor:
			cursor.execute('INSERT INTO messages (id, campaign_id, target_email) VALUES (?, ?, ?)', (email_id, campaign_id, email_target))
		return

	def rpc_campaign_delete(self, campaign_id):
		tables = database.get_tables_with_column_id('campaign_id')
		with self.get_cursor() as cursor:
			for table in tables:
				sql_query = "DELETE FROM {0} WHERE campaign_id = ?".format(table)
				cursor.execute(sql_query, (campaign_id,))
			cursor.execute("DELETE FROM campaigns WHERE id = ?", (campaign_id,))
		return

	def rpc_database_count_rows(self, *args):
		args = list(args)
		table = self.path.split('/')[-2]
		fields = self.path.split('/')[1:-2]
		assert(len(fields) == len(args))
		sql_query = 'SELECT COUNT(id) FROM ' + table
		if len(fields):
			sql_query += ' WHERE ' + ' AND '.join(map(lambda f: f + '_id = ?', fields))
		return self.query_count(sql_query, args)

	def rpc_database_get_rows(self, *args):
		args = list(args)
		if len(args):
			offset = (args.pop() * VIEW_ROW_COUNT)
		else:
			offset = 0

		table = self.path.split('/')[-2]
		fields = self.path.split('/')[1:-2]
		assert(len(fields) == len(args))
		columns = DATABASE_TABLES[table]
		rows = []
		sql_query = 'SELECT ' + ', '.join(columns) + ' FROM ' + table
		if len(fields):
			sql_query += ' WHERE ' + ' AND '.join(map(lambda f: f + '_id = ?', fields))
		sql_query += ' LIMIT ' + str(VIEW_ROW_COUNT) + ' OFFSET ?'
		args.append(offset)
		with self.get_cursor() as cursor:
			for row in cursor.execute(sql_query, args):
				rows.append(row)
		if not len(rows):
			return None
		return {'columns': columns, 'rows': rows}

	def rpc_database_delete_row_by_id(self, row_id):
		table = self.path.split('/')[-2]
		with self.get_cursor() as cursor:
			cursor.execute('DELETE FROM ' + table + ' WHERE id = ?', (row_id,))
		return

	def rpc_database_get_row_by_id(self, row_id):
		table = self.path.split('/')[-2]
		columns = DATABASE_TABLES[table]
		with self.get_cursor() as cursor:
			cursor.execute('SELECT ' + ', '.join(columns) + ' FROM ' + table + ' WHERE id = ?', (row_id,))
			row = cursor.fetchone()
			if row:
				row = dict(zip(columns, row))
		return row

	def rpc_database_insert_row(self, keys, values):
		table = self.path.split('/')[-2]
		if not isinstance(keys, (list, tuple)):
			keys = (keys,)
		if not isinstance(values, (list, tuple)):
			values = (values,)
		assert(len(keys) == len(values))
		for key, value in zip(keys, values):
			assert(key in DATABASE_TABLES[table])
		with self.get_cursor() as cursor:
			cursor.execute('INSERT INTO ' + table + ' (' + ', '.join(keys) + ') VALUES (' + ', '.join('?' * len(values)) + ')', values)
		return

	def rpc_database_set_row_value(self, row_id, keys, values):
		table = self.path.split('/')[-2]
		if not isinstance(keys, (list, tuple)):
			keys = (keys,)
		if not isinstance(values, (list, tuple)):
			values = (values,)
		assert(len(keys) == len(values))
		with self.get_cursor() as cursor:
			for key, value in zip(keys, values):
				assert(key in DATABASE_TABLES[table])
				cursor.execute('UPDATE ' + table + ' SET ' + key + ' = ? WHERE id = ?', (value, row_id))
