#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  tests/server/server_rpc.py
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

import random
import string
import time
import types
import unittest

from king_phisher import version
from king_phisher.server.database import models as db_models
from king_phisher.testing import KingPhisherServerTestCase
from king_phisher.third_party import AdvancedHTTPServer
from king_phisher.utilities import random_string

class ServerRPCTests(KingPhisherServerTestCase):
	def test_rpc_client_initialize(self):
		self.assertTrue(self.rpc('client/initialize'))

	def test_rpc_config_get(self):
		self.assertEqual(self.rpc('config/get', 'server.address.port'), self.config.get('server.address.port'))
		server_address = self.rpc('config/get', ['server.address.host', 'server.address.port'])
		self.assertIsInstance(server_address, dict)
		self.assertTrue('server.address.host' in server_address)
		self.assertTrue('server.address.port' in server_address)
		self.assertEqual(server_address['server.address.host'], self.config.get('server.address.host'))
		self.assertEqual(server_address['server.address.port'], self.config.get('server.address.port'))
		self.assertIsNone(self.rpc('config/get', random_string(10)))

	def test_rpc_campaign_delete(self):
		campaign_name = random_string(10)
		campaign_id = self.rpc('campaign/new', campaign_name)
		self.rpc('campaign/delete', campaign_id)

	def test_rpc_campaign_new(self):
		campaign_name = random_string(10)
		campaign_id = self.rpc('campaign/new', campaign_name)
		self.assertIsInstance(campaign_id, int)
		campaigns = self.rpc.remote_table('campaigns')
		self.assertIsInstance(campaigns, types.GeneratorType)
		campaigns = list(campaigns)
		self.assertEqual(len(campaigns), 1)
		campaign = campaigns[0]
		self.assertEqual(campaign['id'], campaign_id)
		self.assertEqual(campaign['name'], campaign_name)

	def test_rpc_config_set(self):
		config_key = random_string(10)
		config_value = random_string(10)
		self.rpc('config/set', {config_key: config_value})
		self.assertEqual(self.rpc('config/get', config_key), config_value)

	def test_rpc_is_unauthorized(self):
		http_response = self.http_request('/ping', method='RPC')
		self.assertHTTPStatus(http_response, 401)

	def test_rpc_ping(self):
		self.assertTrue(self.rpc('ping'))

	def test_rpc_remote_table(self):
		self.test_rpc_campaign_new()
		campaign = list(self.rpc.remote_table('campaigns'))[0]
		self.assertTrue(isinstance(campaign, dict))
		self.assertEqual(sorted(campaign.keys()), sorted(db_models.DATABASE_TABLES['campaigns']))

	def test_rpc_shutdown(self):
		self.assertIsNone(self.rpc('shutdown'))
		self.shutdown_requested = True

	def test_rpc_table_count(self):
		self.assertEqual(self.rpc('campaigns/count'), 0)
		self.assertEqual(self.rpc('messages/count'), 0)
		self.assertEqual(self.rpc('visits/count'), 0)
		self.test_rpc_campaign_new()
		self.assertEqual(self.rpc('campaigns/count'), 1)

	def test_rpc_table_view(self):
		self.test_rpc_campaign_new()
		campaign = self.rpc('campaigns/view')
		self.assertTrue(bool(campaign))
		self.assertEqual(len(campaign['rows']), 1)
		self.assertEqual(len(campaign['rows'][0]), len(db_models.DATABASE_TABLES['campaigns']))
		self.assertEqual(sorted(campaign['columns']), sorted(db_models.DATABASE_TABLES['campaigns']))

	def test_rpc_set_value(self):
		campaign_name = random_string(10)
		new_campaign_name = random_string(10)
		campaign_id = self.rpc('campaign/new', campaign_name)
		campaign = self.rpc.remote_table_row('campaigns', campaign_id)
		self.assertEqual(campaign['name'], campaign_name)
		self.rpc('campaigns/set', campaign_id, 'name', new_campaign_name)
		campaign = self.rpc.remote_table_row('campaigns', campaign_id)
		self.assertEqual(campaign['name'], new_campaign_name)

	def test_rpc_version(self):
		response = self.rpc('version')
		self.assertTrue('version' in response)
		self.assertTrue('version_info' in response)
		self.assertEqual(response['version'], version.version)
		self.assertEqual(response['version_info']['major'], version.version_info.major)
		self.assertEqual(response['version_info']['minor'], version.version_info.minor)
		self.assertEqual(response['version_info']['micro'], version.version_info.micro)

if __name__ == '__main__':
	unittest.main()
