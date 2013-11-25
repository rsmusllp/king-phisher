#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  king_phisher/server/rpcmixin.py
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

import contextlib

from king_phisher.server import database

VIEW_ROW_COUNT = 25
DATABASE_TABLES = database.DATABASE_TABLES

class KingPhisherRequestHandlerRPCMixin(object):
	def install_handlers(self):
		super(KingPhisherRequestHandlerRPCMixin, self).install_handlers()
		self.rpc_handler_map['/ping'] = self.rpc_ping

		self.rpc_handler_map['/campaign/message/new'] = self.rpc_campaign_message_new
		self.rpc_handler_map['/campaign/new'] = self.rpc_campaign_new

		self.rpc_handler_map['/campaign/delete'] = self.rpc_campaign_delete

		for table_name in DATABASE_TABLES.keys():
			self.rpc_handler_map['/' + table_name + '/delete'] = self.rpc_database_delete_row_by_id
			self.rpc_handler_map['/' + table_name + '/get'] = self.rpc_database_get_row_by_id
			self.rpc_handler_map['/' + table_name + '/view'] = self.rpc_database_get_rows

		# Tables with a campaign_id field
		for table_name in ['messages', 'visits', 'credentials', 'deaddrop_deployments', 'deaddrop_connections']:
			self.rpc_handler_map['/campaign/' + table_name + '/view'] = self.rpc_database_get_rows

		# Tables with a message_id field
		for table_name in ['visits', 'credentials']:
			self.rpc_handler_map['/message/' + table_name + '/view'] = self.rpc_database_get_rows

	@contextlib.contextmanager
	def get_cursor(self):
		self.database_lock.acquire()
		cursor = self.database.cursor()
		yield cursor
		self.database.commit()
		self.database_lock.release()

	def rpc_ping(self):
		return True

	def rpc_campaign_new(self, name):
		with self.get_cursor() as cursor:
			cursor.execute('INSERT INTO campaigns (name, creator) VALUES (?, ?)', (name, self.basic_auth_user))
			cursor.execute('SELECT id FROM campaigns WHERE name = ?', (name,))
			campaign_id = cursor.fetchone()[0]
		return campaign_id

	def rpc_campaign_message_new(self, campaign_id, email_id, email_target):
		with self.get_cursor() as cursor:
			cursor.execute('INSERT INTO messages (id, campaign_id, target_email) VALUES (?, ?, ?)', (email_id, campaign_id, email_target))
		return

	def rpc_campaign_delete(self, campaign_id):
		tables = ['deaddrop_connections', 'deaddrop_deployments', 'credentials', 'visits', 'messages']
		with self.get_cursor() as cursor:
			for table in tables:
				sql_query = "DELETE FROM {0} WHERE campaign_id = ?".format(table)
				cursor.execute(sql_query, (campaign_id,))
			cursor.execute("DELETE FROM campaigns WHERE id = ?", (campaign_id,))
		return

	def rpc_database_get_rows(self, *args):
		args = list(args)
		offset = (args.pop() * VIEW_ROW_COUNT)

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
