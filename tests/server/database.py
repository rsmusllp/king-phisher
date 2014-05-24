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

from king_phisher.server.database import *
from tests.testing import random_string

class ServerDatabaseTests(unittest.TestCase):
	def test_create_database(self):
		try:
			self.assertIsInstance(create_database(':memory:'), KingPhisherDatabase)
		except Exception as error:
			self.fail("failed to initialize the database (error: {0})".format(error.__class__.__name__))

	def test_get_tables_id(self):
		tables = ['alert_subscriptions', 'campaigns', 'credentials', 'deaddrop_connections', 'deaddrop_deployments', 'landing_pages', 'messages', 'meta_data', 'users', 'visits']
		tables_with_id = get_tables_with_column_id('id')
		self.assertEqual(len(tables), len(tables_with_id))
		for table in tables:
			self.assertTrue(table in tables_with_id)

	def test_get_tables_campaign_id(self):
		tables = ['deaddrop_deployments', 'alert_subscriptions', 'credentials', 'landing_pages', 'messages', 'deaddrop_connections', 'visits']
		self.assertListEqual(get_tables_with_column_id('campaign_id'), tables)

	def test_get_tables_message_id(self):
		tables = ['credentials', 'visits']
		self.assertListEqual(get_tables_with_column_id('message_id'), tables)

	def test_meta_data(self):
		try:
			db = create_database(':memory:')
		except Exception as error:
			self.fail("failed to initialize the database (error: {0})".format(error.__class__.__name__))
		self.assertIsInstance(db, KingPhisherDatabase)
		self.assertEqual(db.schema_version, SCHEMA_VERSION)
		key = random_string(10)
		value = random_string(20)
		try:
			db.set_meta_data(key, value)
			self.assertEqual(db.get_meta_data(key), value)
		except Exception as error:
			self.fail("failed to set a database meta data (error: {0})".format(error.__class__.__name__))

class ServerDatabaseUIDTests(unittest.TestCase):
	def test_create_uid_length(self):
		self.assertEqual(len(make_uid(10)), 10)
		self.assertEqual(len(make_uid(15)), 15)

	def test_create_uid_random(self):
		uid1 = make_uid(15)
		uid2 = make_uid(15)
		self.assertNotEqual(uid1, uid2)

if __name__ == '__main__':
	unittest.main()
