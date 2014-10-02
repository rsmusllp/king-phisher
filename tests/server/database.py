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

from king_phisher.server.database import manager as db_manager
from king_phisher.server.database import models as db_models
from king_phisher.utilities import random_string

get_tables_with_column_id = db_models.get_tables_with_column_id

class ServerDatabaseTests(unittest.TestCase):
	def test_create_database(self):
		try:
			db_manager.init_database('sqlite://')
		except Exception as error:
			self.fail("failed to initialize the database (error: {0})".format(error.__class__.__name__))

	def test_get_meta_data(self):
		try:
			db_manager.init_database('sqlite://')
		except Exception as error:
			self.fail("failed to initialize the database (error: {0})".format(error.__class__.__name__))

		database_driver = db_manager.get_meta_data('database_driver')
		self.assertEqual(database_driver, 'sqlite')

		schema_version = db_manager.get_meta_data('schema_version')
		self.assertEqual(schema_version, db_models.SCHEMA_VERSION)

	def test_get_tables_id(self):
		tables = set([
			'alert_subscriptions',
			'campaigns',
			'credentials',
			'deaddrop_connections',
			'deaddrop_deployments',
			'landing_pages',
			'messages',
			'meta_data',
			'users',
			'visits'
		])
		tables_with_id = get_tables_with_column_id('id')
		self.assertSetEqual(set(get_tables_with_column_id('id')), tables)

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
		self.assertSetEqual(set(get_tables_with_column_id('campaign_id')), tables)

	def test_get_tables_message_id(self):
		tables = set([
			'credentials',
			'visits'
		])
		self.assertSetEqual(set(get_tables_with_column_id('message_id')), tables)

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

if __name__ == '__main__':
	unittest.main()
