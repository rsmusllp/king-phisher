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

import ConfigParser
import httplib
import os
import random
import string
import threading
import unittest

from king_phisher import find
from king_phisher.server.server import *

random_string = lambda size: ''.join(random.choice(string.ascii_letters + string.digits) for x in range(size))

class ServerTests(unittest.TestCase):
	def setUp(self):
		web_root = os.path.join(os.getcwd(), 'data', 'server', 'king_phisher')
		config = ConfigParser.ConfigParser()
		config.add_section('server')
		config.set('server', 'database', ':memory:')
		config.set('server', 'port', '8080')
		config.set('server', 'require_id', 'False')
		config.set('server', 'web_root', web_root)
		self.config = config

		# Configure environment variables
		find.data_path_append('data/server')

		self.server = build_king_phisher_server(config, 'server')
		self.assertIsInstance(self.server, KingPhisherServer)
		self.server.load_database(config.get('server', 'database'))
		self.server_thread = threading.Thread(target=self.server.serve_forever)
		self.server_thread.daemon = True
		self.server_thread.start()
		self.assertTrue(self.server_thread.is_alive())

	def http_request(self, resource, method = 'GET'):
		conn = httplib.HTTPConnection('localhost', self.config.getint('server', 'port'))
		conn.request(method, resource)
		response = conn.getresponse()
		conn.close()
		return response

	def tearDown(self):
		self.server.shutdown()
		self.server_thread.join(5.0)
		self.assertFalse(self.server_thread.is_alive())
		del self.server

	def test_existing_resources(self):
		web_root = self.config.get('server', 'web_root')
		directories = filter(lambda p: os.path.isdir(os.path.join(web_root, p)), os.listdir(web_root))
		for directory in directories:
			full_directory = os.path.join(web_root, directory)
			for phile in filter(lambda p: os.path.isfile(os.path.join(full_directory, p)), os.listdir(full_directory)):
				phile = os.path.join(directory, phile)
				http_response = self.http_request(phile)
				self.assertEqual(http_response.status, 200)

	def test_non_existing_resources(self):
		http_response = self.http_request(random_string(30) + '.html')
		self.assertEqual(http_response.status, 404)

if __name__ == '__main__':
	unittest.main()
