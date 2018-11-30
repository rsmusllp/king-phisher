#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  tests/server/web_tools.py
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

from king_phisher import find
from king_phisher.testing import KingPhisherTestCase
from king_phisher.server import web_tools
from king_phisher.server import configuration
from king_phisher.utilities import random_string

class ServerWebToolsTests(KingPhisherTestCase):
	def setUp(self):
		self.config = configuration.Configuration.from_file(find.data_file('server_config.yml'))

	def test_get_hostnames(self):
		new_hostname = random_string(16)
		config_hostnames = self.config.get_if_exists('server.hostnames', [])
		config_hostnames.append(new_hostname)
		self.config.set('server.hostnames', config_hostnames)
		hostnames = web_tools.get_hostnames(self.config)
		self.assertIsInstance(hostnames, tuple)
		self.assertIn(new_hostname, hostnames)

	def test_get_vhost_directories(self):
		self.config.set('server.vhost_directories', True)
		directories = web_tools.get_vhost_directories(self.config)
		self.assertIsInstance(directories, tuple)

	def test_get_vhost_directories_is_none_when_vhosts_is_disabled(self):
		self.config.set('server.vhost_directories', False)
		self.assertIsNone(web_tools.get_vhost_directories(self.config))
