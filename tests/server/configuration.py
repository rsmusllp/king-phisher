#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  tests/server/configuration.py
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

import king_phisher.find as find
import king_phisher.testing as testing
import king_phisher.server.configuration as configuration

class ServerConfigurationTests(testing.KingPhisherTestCase):
	def setUp(self):
		find.init_data_path('server')

	def test_server_config(self):
		config_file = find.data_file('server_config.yml')
		self.assertIsNotNone(config_file)
		self.assertTrue(os.path.isfile(config_file))
		config = configuration.Configuration.from_file(config_file)
		self.assertTrue(config.has_section('server'))
		self.assertTrue(config.has_option('server.addresses'))
		addresses = config.get('server.addresses')
		self.assertIsInstance(addresses, list)
		self.assertGreater(len(addresses), 0)

	def test_server_config_verification(self):
		config_file = find.data_file('server_config.yml')
		self.assertIsNotNone(config_file)
		config_schema = find.data_file(os.path.join('schemas', 'json', 'king-phisher.server.config.json'))
		self.assertIsNotNone(config_schema)
		config = configuration.Configuration.from_file(config_file)
		self.assertIsEmpty(config.schema_errors(config_schema))

if __name__ == '__main__':
	unittest.main()
