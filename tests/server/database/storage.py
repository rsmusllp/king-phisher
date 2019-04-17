#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  tests/server/database/storage.py
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
import unittest

from king_phisher import testing
from king_phisher.server.database import storage as db_storage

class DatabaseStorageTests(testing.KingPhisherTestCase):
	def test_storage_accepts_native_types(self):
		storage = db_storage.KeyValueStorage('testing.accepts-native-types')
		self.assertNotIsInstance(storage, dict)
		storage['data'] = {
			'key1': 1,
			'key2': 'hello world',
			'key3': True,
			'key4': datetime.datetime.utcnow()
		}
		self.assertEquals(len(storage), 1)

	def test_storage_keys_must_be_strings(self):
		storage = db_storage.KeyValueStorage('testing.keys-must-be-strings')
		with self.assertRaises(TypeError):
			storage[1] = 'test'

	def test_storage_missing_values_raise_keyerror(self):
		storage = db_storage.KeyValueStorage('testing.missing-values-raise-keyerror')
		with self.assertRaises(KeyError):
			storage['missing']

	def test_storage_order(self):
		storage = db_storage.KeyValueStorage('testing.order')
		self.assertEqual(storage.order_by, 'created')
		storage['c'] = True
		storage['a'] = True
		storage['t'] = True
		storage = db_storage.KeyValueStorage('testing.order', order_by='created')
		self.assertEqual(''.join(storage.keys()), 'cat')
		storage = db_storage.KeyValueStorage('testing.order', order_by='key')
		self.assertEqual(''.join(storage.keys()), 'act')
		with self.assertRaises(ValueError):
			storage.order_by = 'doesnotexist'

if __name__ == '__main__':
	unittest.main()
