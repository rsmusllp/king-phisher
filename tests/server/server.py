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
import os
import threading
import unittest

from king_phisher import find
from king_phisher.server.server import *

class ServerTests(unittest.TestCase):
	def setUp(self):
		web_root = os.path.join(os.getcwd(), 'data', 'server', 'king_phisher')
		config = ConfigParser.ConfigParser()
		config.add_section('server')
		config.set('server', 'database', ':memory:')
		config.set('server', 'port', '8080')
		config.set('server', 'web_root', web_root)
		self.config = config

		# Configure environment variables
		find.data_path_append('data/server')

		try:
			self.server = build_king_phisher_server(config, 'server')
		except SystemExit:
			os._exit(0)
		self.server.load_database(config.get('server', 'database'))
		self.server_thread = threading.Thread(target=self.server.serve_forever)
		self.server_thread.daemon = True
		self.server_thread.start()

	def test_something(self):
		self.assertTrue(True)

	def tearDown(self):
		self.server.shutdown()

if __name__ == '__main__':
	unittest.main()
