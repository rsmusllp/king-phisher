#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  tests/server/database/manager.py
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

class DatabaseManagerTests(testing.KingPhisherTestCase):
	def _init_db(self):
		try:
			db_manager.init_database('sqlite://')
		except Exception as error:
			self.fail("failed to initialize the database (error: {0})".format(error.__class__.__name__))

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

	def test_models_convert_to_dictionaries(self):
		model = db_models.User(name='alice')
		dictionary = model.to_dict()
		self.assertIsInstance(dictionary, dict)
		self.assertIn('name', dictionary)

if __name__ == '__main__':
	unittest.main()
