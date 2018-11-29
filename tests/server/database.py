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

import datetime
import os
import unittest

from king_phisher import find
from king_phisher import testing
from king_phisher.server.database import manager as db_manager
from king_phisher.server.database import models as db_models
from king_phisher.server.database import storage as db_storage
from king_phisher.server.database import validation as db_validation
from king_phisher.utilities import random_string

import sqlalchemy

get_tables_with_column_id = db_models.get_tables_with_column_id

class DatabaseTestBase(testing.KingPhisherTestCase):
	def _init_db(self):
		try:
			db_manager.init_database('sqlite://')
		except Exception as error:
			self.fail("failed to initialize the database (error: {0})".format(error.__class__.__name__))

class DatabaseRPCTests(testing.KingPhisherServerTestCase):
	def assertRPCPermissionDenied(self, db_method, *args, **kwargs):
		super(DatabaseRPCTests, self).assertRPCPermissionDenied('db/table/' + db_method, *args, **kwargs)

	def test_storage_data_is_private(self):
		# ensure that meta_data is kept private and that private tables can't be accessed via rpc
		self.assertTrue(db_models.StorageData.is_private)
		self.assertIsNone(self.rpc('db/table/view', 'storage_data'))
		self.assertRPCPermissionDenied('get', 'storage_data', 1)
		self.assertRPCPermissionDenied('set', 'storage_data', 1, ('namespace',), ('test',))
		self.assertRPCPermissionDenied('delete', 'storage_data', 1)

class DatabaseSchemaTests(testing.KingPhisherTestCase):
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

class DatabaseStorageTests(DatabaseTestBase):
	def test_storage_keys_must_be_strings(self):
		storage = db_storage.KeyValueStorage()
		with self.assertRaises(TypeError):
			storage[1] = 'test'

	def test_storage_missing_values_raise_keyerror(self):
		storage = db_storage.KeyValueStorage()
		with self.assertRaises(KeyError):
			storage['missing']

	def test_storage_accepts_native_types(self):
		storage = db_storage.KeyValueStorage()
		self.assertNotIsInstance(storage, dict)
		storage['data'] = {
			'key1': 1,
			'key2': 'hello world',
			'key3': True,
			'key4': datetime.datetime.utcnow()
		}
		self.assertEquals(len(storage), 1)

class DatabaseTests(DatabaseTestBase):
	def test_create_database(self):
		self._init_db()

	def test_get_meta_data(self):
		self._init_db()
		database_driver = db_manager.get_metadata('database_driver')
		self.assertEqual(database_driver, 'sqlite')

		schema_version = db_manager.get_metadata('schema_version')
		self.assertEqual(schema_version, db_models.SCHEMA_VERSION)

	def test_get_row_by_id(self):
		self._init_db()
		session = db_manager.Session()
		user = db_models.User(name='alice')
		session.add(user)
		campaign_name = random_string(10)
		campaign = db_models.Campaign(name=campaign_name, user=user)
		session.add(campaign)
		session.commit()
		self.assertIsNotNone(campaign.id)
		campaign_id = campaign.id
		del campaign

		row = db_manager.get_row_by_id(session, db_models.Campaign, campaign_id)
		self.assertEqual(row.id, campaign_id)
		self.assertEqual(row.name, campaign_name)

	def test_set_meta_data(self):
		self._init_db()
		# set a new value
		key = random_string(10)
		value = random_string(20)
		db_manager.set_metadata(key, value)
		self.assertEqual(db_manager.get_metadata(key), value)

		# update an existing value
		value = random_string(30)
		db_manager.set_metadata(key, value)
		self.assertEqual(db_manager.get_metadata(key), value)

	def test_users_dont_default_to_admin(self):
		user = db_models.User(name='alice')
		self.assertFalse(user.is_admin)

	def test_models_convert_to_dictionaries(self):
		model = db_models.User(name='alice')
		dictionary = model.to_dict()
		self.assertIsInstance(dictionary, dict)
		self.assertIn('name', dictionary)
		self.assertEqual(dictionary['name'], 'alice')

class DatabaseValidateCredentialTests(testing.KingPhisherTestCase):
	campaign = db_models.Campaign(credential_regex_username=r'a\S+')
	def test_credential_collection_members(self):
		for field in db_validation.CredentialCollection._fields:
			self.assertTrue(hasattr(db_models.Credential, field))

	def test_empty_configuration_returns_none(self):
		self.assertIsNone(db_validation.validate_credential(
			db_validation.CredentialCollection(username='alice', password='Wonderland!123', mfa_token='031337'),
			db_models.Campaign()
		))

	def test_extra_fields_are_ignored(self):
		self.assertTrue(db_validation.validate_credential(
			db_validation.CredentialCollection(username='alice', password='Wonderland!123', mfa_token=None),
			self.campaign
		))
		self.assertTrue(db_validation.validate_credential(
			db_validation.CredentialCollection(username='alice', password=None, mfa_token='031337'),
			self.campaign
		))
		self.assertTrue(db_validation.validate_credential(
			db_validation.CredentialCollection(username='alice', password='Wonderland!123', mfa_token='031337'),
			self.campaign
		))

	def test_validation_methods(self):
		cred = db_validation.CredentialCollection(username='alice', password=None, mfa_token=None)
		self.assertEqual(
			db_validation.validate_credential_fields(cred, self.campaign),
			db_validation.CredentialCollection(username=True, password=None, mfa_token=None)
		)
		self.assertTrue(db_validation.validate_credential(cred, self.campaign))

		cred = db_validation.CredentialCollection(username='calie', password=None, mfa_token=None)
		self.assertEqual(
			db_validation.validate_credential_fields(cred, self.campaign),
			db_validation.CredentialCollection(username=False, password=None, mfa_token=None)
		)
		self.assertFalse(db_validation.validate_credential(cred, self.campaign))

		cred = db_validation.CredentialCollection(username='alice', password=None, mfa_token=None)
		campaign = db_models.Campaign(credential_regex_username=r'a\S+', credential_regex_password=r'a\S+')
		self.assertEqual(
			db_validation.validate_credential_fields(cred, campaign),
			db_validation.CredentialCollection(username=True, password=False, mfa_token=None)
		)
		self.assertFalse(db_validation.validate_credential(cred, campaign))

	def test_empty_fields_fail(self):
		self.assertEqual(db_validation.validate_credential_fields(
			db_validation.CredentialCollection(username='', password=None, mfa_token=None),
			self.campaign
		), db_validation.CredentialCollection(username=False, password=None, mfa_token=None))

	def test_none_fields_fail(self):
		self.assertEqual(db_validation.validate_credential_fields(
			db_validation.CredentialCollection(username=None, password=None, mfa_token=None),
			self.campaign
		), db_validation.CredentialCollection(username=False, password=None, mfa_token=None))

	def test_bad_regexs_are_skipped(self):
		self.assertEqual(db_validation.validate_credential_fields(
			db_validation.CredentialCollection(username='alice', password=None, mfa_token=None),
			db_models.Campaign(credential_regex_username=r'\S+[')
		), db_validation.CredentialCollection(username=None, password=None, mfa_token=None))

if __name__ == '__main__':
	unittest.main()
