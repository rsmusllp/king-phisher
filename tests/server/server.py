#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  tests/server/server.py
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

from tests.testing import KingPhisherServerTestCase, random_string

class ServerTests(KingPhisherServerTestCase):
	def test_existing_resources(self):
		for phile in self.web_root_files(3):
			http_response = self.http_request(phile)
			self.assertHTTPStatus(http_response, 200)

	def test_non_existing_resources(self):
		http_response = self.http_request(random_string(30) + '.html')
		self.assertHTTPStatus(http_response, 404)
		http_response = self.http_request(random_string(30) + '.html')
		self.assertHTTPStatus(http_response, 404)

	def test_secret_id(self):
		old_require_id = self.config.get('server.require_id')
		self.config.set('server.require_id', True)
		for phile in self.web_root_files(3):
			http_response = self.http_request(phile, include_id=True)
			self.assertHTTPStatus(http_response, 200)
			http_response = self.http_request(phile, include_id=False)
			self.assertHTTPStatus(http_response, 404)
		self.config.set('server.require_id', False)
		for phile in self.web_root_files(3):
			http_response = self.http_request(phile, include_id=False)
			self.assertHTTPStatus(http_response, 200)
		self.config.set('server.require_id', old_require_id)

	def test_static_resource_dead_drop(self):
		http_response = self.http_request('kpdd', include_id=False)
		self.assertHTTPStatus(http_response, 200)

	def test_static_resource_javascript_hook(self):
		http_response = self.http_request('kp.js')
		self.assertHTTPStatus(http_response, 200)
		content_type = http_response.getheader('Content-Type')
		error_message = "HTTP Response received Content-Type {0} when {1} was expected".format(content_type, 'text/javascript')
		self.assertEqual(content_type, 'text/javascript', msg=error_message)
		javascript = http_response.read()
		load_script = 'function loadScript(url, callback) {'
		error_message = "Javascript did not defined the loadScript function"
		self.assertTrue(load_script in javascript, msg=error_message)

		beef_hook_url = "http://{0}:3000/hook.js".format(random_string(30))
		self.config.set('beef.hook_url', beef_hook_url)
		http_response = self.http_request('kp.js')
		self.assertHTTPStatus(http_response, 200)
		javascript = http_response.read()
		load_script = "loadScript('{0}');".format(beef_hook_url)
		error_message = "Javascript did not load the beef hook from the config"
		self.assertTrue(load_script in javascript, msg=error_message)

	def test_static_resource_tracking_image(self):
		http_response = self.http_request(self.config.get('server.tracking_image'), include_id=False)
		self.assertHTTPStatus(http_response, 200)
		image_data = http_response.read()
		self.assertTrue(image_data.startswith('GIF'))

if __name__ == '__main__':
	unittest.main()
