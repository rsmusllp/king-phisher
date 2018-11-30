#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  tests/server/database/models.py
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

import os
import unittest

from king_phisher import find
from king_phisher import testing
from king_phisher.server.database import models as db_models

import sqlalchemy

get_tables_with_column_id = db_models.get_tables_with_column_id

class DatabaseModelRPCTests(testing.KingPhisherServerTestCase):
	def assertRPCPermissionDenied(self, db_method, *args, **kwargs):
		super(DatabaseModelRPCTests, self).assertRPCPermissionDenied('db/table/' + db_method, *args, **kwargs)

	def test_storage_data_is_private(self):
		# ensure that meta_data is kept private and that private tables can't be accessed via rpc
		self.assertTrue(db_models.StorageData.is_private)
		self.assertIsNone(self.rpc('db/table/view', 'storage_data'))
		self.assertRPCPermissionDenied('get', 'storage_data', 1)
		self.assertRPCPermissionDenied('set', 'storage_data', 1, ('namespace',), ('test',))
		self.assertRPCPermissionDenied('delete', 'storage_data', 1)

class DatabaseModelSchemaTests(testing.KingPhisherTestCase):
	def test_get_tables_id(self):
		tables = set([
			'alert_subscriptions',
			'authenticated_sessions',
			'campaign_types',
			'campaigns',
			'company_departments',
			'companies',
			'credentials',
			'deaddrop_connections',
			'deaddrop_deployments',
			'industries',
			'landing_pages',
			'messages',
			'storage_data',
			'users',
			'visits'
		])
		self.assertSetEqual(get_tables_with_column_id('id'), tables)

	def test_public_table_column_types(self):
		# this test is to ensure that the data types of public tables are
		# suitable for serialization, i.e. not binary
		for metatable in db_models.database_tables.values():
			if metatable.model.is_private:
				continue
			for column in metatable.model.__table__.columns:
				self.assertIsInstance(
					column.type,
					(sqlalchemy.Boolean, sqlalchemy.DateTime, sqlalchemy.Integer, sqlalchemy.String),
					msg="{0}.{1} is not an acceptable data type for a public table".format(metatable.name, column.name)
				)

	def test_public_tables_str_id_has_default_func(self):
		# this test is to ensure that public tables that use strings as their
		# id column have a default function to generate them
		for metatable in db_models.database_tables.values():
			if metatable.model.is_private:
				continue
			id_column = getattr(metatable.model, 'id', None)
			if id_column is None:
				continue
			for column in id_column.property.columns:
				if not isinstance(column.type, sqlalchemy.String):
					continue
				self.assertIsNotNone(column.default, msg="{0}.id must have a default function defined".format(metatable.name))

	def test_table_names(self):
		for table_name in db_models.database_tables.keys():
			self.assertRegex(table_name, '^' + db_models.DATABASE_TABLE_REGEX + '$')

	def test_get_tables_campaign_id(self):
		tables = set([
			'alert_subscriptions',
			'credentials',
			'deaddrop_connections',
			'deaddrop_deployments',
			'landing_pages',
			'messages',
			'visits'
		])
		self.assertSetEqual(get_tables_with_column_id('campaign_id'), tables)

	def test_get_tables_message_id(self):
		tables = set([
			'credentials',
			'visits'
		])
		self.assertSetEqual(get_tables_with_column_id('message_id'), tables)

	def test_schema_file_names(self):
		alembic_directory = find.data_directory('alembic')
		versions = os.listdir(os.path.join(alembic_directory, 'versions'))
		for schema_file in versions:
			if not schema_file.endswith('.py'):
				continue
			self.assertRegex(schema_file, r'[a-f0-9]{10,16}_schema_v\d+\.py', schema_file)

	def test_users_dont_default_to_admin(self):
		user = db_models.User(name='alice')
		self.assertFalse(user.is_admin)

if __name__ == '__main__':
	unittest.main()
