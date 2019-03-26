#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  tests/server/letsencrypt.py
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
import tempfile

from king_phisher import find
from king_phisher.testing import KingPhisherTestCase
from king_phisher.server import letsencrypt
from king_phisher.server import configuration
from king_phisher.utilities import random_string

class ServerSNIHostnameTests(KingPhisherTestCase):
	def setUp(self):
		self.config = configuration.Configuration.from_file(find.data_file('server_config.yml'))
		self.tmp_directory = tempfile.mkdtemp()

	def test_get_sni_hostnames(self):
		sni_hostnames = letsencrypt.get_sni_hostnames()
		self.assertIsInstance(sni_hostnames, dict)

	def test_get_sni_hostname_config(self):
		hostname = random_string(16)
		sni_config = letsencrypt.get_sni_hostname_config(hostname)
		self.assertIsNone(sni_config)

		certfile = os.path.join(self.tmp_directory, hostname + '.pem')
		keyfile = os.path.join(self.tmp_directory, hostname + '-key.pem')
		letsencrypt.set_sni_hostname(hostname, certfile, keyfile, enabled=False)
		sni_config = letsencrypt.get_sni_hostname_config(hostname)
		self.assertIsNone(sni_config)

		open(certfile, 'wb')
		open(keyfile, 'wb')
		sni_config = letsencrypt.get_sni_hostname_config(hostname)
		os.remove(certfile)
		os.remove(keyfile)
		self.assertIsInstance(sni_config, letsencrypt.SNIHostnameConfiguration)
		self.assertFalse(sni_config.enabled)
		self.assertEqual(sni_config.certfile, certfile)
		self.assertEqual(sni_config.keyfile, keyfile)
