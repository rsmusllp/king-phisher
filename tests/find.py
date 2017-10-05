#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  tests/find.py
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

import json
import os
import unittest

from king_phisher import find
from king_phisher import testing

class FindTests(testing.KingPhisherTestCase):
	def setUp(self):
		find.init_data_path()

	def test_find_data_file(self):
		self.assertIsNotNone(find.data_file('security.json'))

	def test_find_data_directory(self):
		self.assertIsNotNone(find.data_directory('schemas'))

class JSONSchemaDataTests(testing.KingPhisherTestCase):
	def test_json_schema_directories(self):
		find.init_data_path()

		directory = find.data_directory(os.path.join('schemas', 'json'))
		self.assertIsNotNone(directory)
		for schema_file in os.listdir(directory):
			self.assertTrue(schema_file.endswith('.json'))
			schema_file = os.path.join(directory, schema_file)
			with open(schema_file, 'r') as file_h:
				schema_data = json.load(file_h)

			self.assertIsInstance(schema_data, dict)
			self.assertEqual(schema_data.get('$schema'), 'http://json-schema.org/draft-04/schema#')
			self.assertEqual(schema_data.get('id'), os.path.basename(schema_file)[:-5])

if __name__ == '__main__':
	unittest.main()
