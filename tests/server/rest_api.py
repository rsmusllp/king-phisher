#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  tests/server/rest_api.py
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
import unittest

from king_phisher.server import rest_api
from king_phisher.testing import KingPhisherServerTestCase

class ServerRESTAPITests(KingPhisherServerTestCase):
	def test_rest_api_token(self):
		response = self.http_request('/' + rest_api.REST_API_BASE + 'geoip/lookup', include_id=False)
		self.assertHTTPStatus(response, 401)
		response = self.http_request('/' + rest_api.REST_API_BASE + 'geoip/lookup?token=fake', include_id=False)
		self.assertHTTPStatus(response, 401)

	def test_rest_api_geoip_lookup(self):
		resource = '/' + rest_api.REST_API_BASE + 'geoip/lookup'
		resource += '?token=' + self.config.get('server.rest_api.token')
		resource += '&ip=8.8.8.8'
		response = self.http_request(resource, include_id=False)
		self.assertHTTPStatus(response, 200)
		self.assertEqual(response.getheader('Content-Type'), 'application/json')
		response = response.read()
		if not isinstance(response, str):
			response = response.decode('utf-8')
		response = json.loads(response)
		self.assertIn('result', response)
		self.assertIsInstance(response['result'], dict)

if __name__ == '__main__':
	unittest.main()
