#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  tests/testing.py
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

import httplib
import os
import random
import string
import threading
import unittest

from king_phisher import configuration
from king_phisher import find
from king_phisher.server.server import *

random_string = lambda size: ''.join(random.choice(string.ascii_letters + string.digits) for x in range(size))

class KingPhisherRequestHandlerTest(KingPhisherRequestHandler):
	def custom_authentication(self, *args, **kwargs):
		return True

class KingPhisherServerTestCase(unittest.TestCase):
	def setUp(self):
		find.data_path_append('data/server')
		web_root = os.path.join(os.getcwd(), 'data', 'server', 'king_phisher')
		config = configuration.Configuration(find.find_data_file('server_config.yml'))
		config.set('server.address.port', random.randint(2000, 10000))
		config.set('server.database', ':memory:')
		config.set('server.web_root', web_root)
		self.config = config
		self.server = build_king_phisher_server(config, HandlerClass=KingPhisherRequestHandlerTest)
		self.assertIsInstance(self.server, KingPhisherServer)
		self.server.init_database(config.get('server.database'))
		self.server_thread = threading.Thread(target=self.server.serve_forever)
		self.server_thread.daemon = True
		self.server_thread.start()
		self.assertTrue(self.server_thread.is_alive())
		self.shutdown_requested = False

	def assertHTTPStatus(self, http_response, status):
		self.assertIsInstance(http_response, httplib.HTTPResponse)
		error_message = "HTTP Response received status {0} when {1} was expected".format(http_response.status, status)
		self.assertEqual(http_response.status, status, msg=error_message)

	def http_request(self, resource, method='GET', include_id=True):
		if include_id:
			resource += "{0}id={1}".format('&' if '?' in resource else '?', self.config.get('server.secret_id'))
		conn = httplib.HTTPConnection('localhost', self.config.get('server.address.port'))
		conn.request(method, resource)
		response = conn.getresponse()
		conn.close()
		return response

	def web_root_files(self, limit=None):
		limit = (limit or float('inf'))
		philes_yielded = 0
		web_root = self.config.get('server.web_root')
		self.assertTrue(os.path.isdir(web_root), msg='The test web root does not exist')
		directories = filter(lambda p: os.path.isdir(os.path.join(web_root, p)), os.listdir(web_root))
		for directory in directories:
			full_directory = os.path.join(web_root, directory)
			for phile in filter(lambda p: os.path.isfile(os.path.join(full_directory, p)), os.listdir(full_directory)):
				phile = os.path.join(directory, phile)
				if philes_yielded < limit:
					yield phile
				philes_yielded += 1
		self.assertGreater(philes_yielded, 0, msg='No files were found in the web root')

	def tearDown(self):
		if not self.shutdown_requested:
			self.assertTrue(self.server_thread.is_alive())
		self.server.shutdown()
		self.server_thread.join(5.0)
		self.assertFalse(self.server_thread.is_alive())
		del self.server
