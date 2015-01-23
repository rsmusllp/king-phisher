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

import os
import unittest

from king_phisher.client import client_rpc
from king_phisher.server.database import manager as db_manager
from king_phisher.server.database import models as db_models
from king_phisher.testing import KingPhisherServerTestCase
from king_phisher.utilities import random_string

class ServerTests(KingPhisherServerTestCase):
	def test_http_method_get(self):
		for phile in self.web_root_files(3):
			http_response = self.http_request(phile)
			self.assertHTTPStatus(http_response, 200)

	def test_http_method_head(self):
		for phile in self.web_root_files(3):
			http_response = self.http_request(phile, method='HEAD')
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
		self.assertTrue(image_data.startswith(b'GIF'))

class CampaignWorkflowTests(KingPhisherServerTestCase):
	"""
	This is a monolithic test broken down into steps which represent the basic
	workflow of a normal campaign.
	"""
	def step_1_create_campaign(self):
		self.campaign_id = self.rpc('campaign/new', 'Unit Test Campaign')

	def step_2_send_messages(self):
		self.landing_page = list(filter(lambda f: os.path.splitext(f)[1] == '.html', self.web_root_files()))[0]
		self.rpc('campaign/landing_page/new', self.campaign_id, 'localhost', self.landing_page)
		message_count = self.rpc('campaign/messages/count', self.campaign_id)
		self.assertEqual(message_count, 0)
		self.message_id = random_string(16)
		self.rpc('campaign/message/new', self.campaign_id, self.message_id, 'test@test.com', 'testers, inc.', 'test', 'test')
		message_count = self.rpc('campaign/messages/count', self.campaign_id)
		self.assertEqual(message_count, 1)

	def step_3_get_visits(self):
		visit_count = self.rpc('campaign/visits/count', self.campaign_id)
		self.assertEqual(visit_count, 0)
		response = self.http_request('/' + self.landing_page, include_id=self.message_id)
		self.assertHTTPStatus(response, 200)
		visit_count = self.rpc('campaign/visits/count', self.campaign_id)
		self.assertEqual(visit_count, 1)
		cookie = response.getheader('Set-Cookie')
		self.assertIsNotNone(cookie)
		cookie = cookie.split(';')[0]
		cookie_name = self.config.get('server.cookie_name')
		self.assertEqual(cookie[:len(cookie_name) + 1], cookie_name + '=')
		self.visit_id = cookie[len(cookie_name) + 1:]

	def step_4_get_passwords(self):
		creds_count = self.rpc('campaign/credentials/count', self.campaign_id)
		self.assertEqual(creds_count, 0)
		username = random_string(8)
		password = random_string(10)
		body = {'username': username, 'password': password}
		headers = {'Cookie': "{0}={1}".format(self.config.get('server.cookie_name'), self.visit_id)}
		response = self.http_request('/' + self.landing_page, method='POST', include_id=False, body=body, headers=headers)
		self.assertHTTPStatus(response, 200)
		creds_count = self.rpc('campaign/credentials/count', self.campaign_id)
		self.assertEqual(creds_count, 1)
		cred = next(self.rpc.remote_table('campaign/credentials', self.campaign_id))
		self.assertEqual(cred['username'], username)
		self.assertEqual(cred['password'], password)
		self.assertEqual(cred['message_id'], self.message_id)
		self.assertEqual(cred['visit_id'], self.visit_id)

	def step_5_get_repeat_visit(self):
		visit = self.rpc.remote_table_row('visits', self.visit_id)
		visit_count = visit['visit_count']
		headers = {'Cookie': "{0}={1}".format(self.config.get('server.cookie_name'), self.visit_id)}
		response = self.http_request('/' + self.landing_page, include_id=False, headers=headers)
		self.assertHTTPStatus(response, 200)
		visit = self.rpc.remote_table_row('visits', self.visit_id)
		self.assertEqual(visit['visit_count'], visit_count + 1)

	def steps(self):
		steps = filter(lambda f: f.startswith('step_'), dir(self))
		steps = sorted(steps, key=lambda x: int(x.split('_')[1]))
		for name in steps:
			yield name, getattr(self, name)

	def test_campaign_workflow(self):
		self.config.set('server.require_id', True)
		for name, step in self.steps():
			step()

if __name__ == '__main__':
	unittest.main()
