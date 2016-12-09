#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  tests/server/database.py
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

import unittest

from king_phisher import testing
from king_phisher.server.database import manager as db_manager
from king_phisher.server.database import models as db_models
from king_phisher.utilities import random_string

import sqlalchemy

get_tables_with_column_id = db_models.get_tables_with_column_id

class ServerDatabaseTests(testing.KingPhisherTestCase):
	def _init_db(self):
		try:
			db_manager.init_database('sqlite://')
		except Exception as error:
			self.fail("failed to initialize the database (error: {0})".format(error.__class__.__name__))

	def test_create_database(self):
		self._init_db()

	def test_get_meta_data(self):
		self._init_db()
		database_driver = db_manager.get_meta_data('database_driver')
		self.assertEqual(database_driver, 'sqlite')

		schema_version = db_manager.get_meta_data('schema_version')
		self.assertEqual(schema_version, db_models.SCHEMA_VERSION)

	def test_get_row_by_id(self):
		self._init_db()
		session = db_manager.Session()
		user = db_models.User(id='alice')
		session.add(user)
		campaign_name = random_string(10)
		campaign = db_models.Campaign(name=campaign_name, user_id=user.id)
		session.add(campaign)
		session.commit()
		self.assertIsNotNone(campaign.id)
		campaign_id = campaign.id
		del campaign

		row = db_manager.get_row_by_id(session, db_models.Campaign, campaign_id)
		self.assertEqual(row.id, campaign_id)
		self.assertEqual(row.name, campaign_name)

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
			'meta_data',
			'storage_data',
			'users',
			'visits'
		])
		self.assertSetEqual(get_tables_with_column_id('id'), tables)

	def test_public_table_column_types(self):
		# this test is to ensure that the data types of public tables are
		# suitable for serialization, i.e. not binary
		for table_name, table in db_models.database_table_objects.items():
			if table.is_private:
				continue
			for column in table.__table__.columns:
				self.assertIsInstance(
					column.type,
					(sqlalchemy.Boolean, sqlalchemy.DateTime, sqlalchemy.Integer, sqlalchemy.String),
					msg="{0}.{1} is not an acceptable data type for a public table".format(table_name, column.name)
				)

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

	def test_set_meta_data(self):
		try:
			db_manager.init_database('sqlite://')
		except Exception as error:
			self.fail("failed to initialize the database (error: {0})".format(error.__class__.__name__))

		# set a new value
		key = random_string(10)
		value = random_string(20)
		db_manager.set_meta_data(key, value)
		self.assertEqual(db_manager.get_meta_data(key), value)

		# update an existing value
		value = random_string(30)
		db_manager.set_meta_data(key, value)
		self.assertEqual(db_manager.get_meta_data(key), value)

class ServerDatabaseRPCTests(testing.KingPhisherServerTestCase):
	def assertRPCPermissionDenied(self, db_method, *args, **kwargs):
		super(ServerDatabaseRPCTests, self).assertRPCPermissionDenied('db/table/' + db_method, *args, **kwargs)

	def test_meta_data_is_private(self):
		# ensure that meta_data is kept private and that private tables can't be accessed via rpc
		self.assertTrue(db_models.MetaData.is_private)
		self.assertIsNone(self.rpc('db/table/view', 'meta_data'))
		self.assertRPCPermissionDenied('get', 'meta_data', 'schema_version')
		self.assertRPCPermissionDenied('set', 'meta_data', 'schema_version', ('value', 'value_type'), ('test', 'str'))
		self.assertRPCPermissionDenied('insert', 'meta_data', ('id', 'value', 'value_type'), ('test', 'test', 'str'))
		self.assertRPCPermissionDenied('delete', 'meta_data', 'schema_version')

if __name__ == '__main__':
	unittest.main()
