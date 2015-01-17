#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  tests/sms.py
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

from king_phisher import testing
from king_phisher.sms import CARRIERS, get_smtp_servers, lookup_carrier_gateway
from king_phisher.utilities import random_string

class SMSTests(testing.KingPhisherTestCase):
	def test_lookup_carrier_gateway(self):
		rstring = random_string(16)
		self.assertIsNone(lookup_carrier_gateway(rstring))
		self.assertEqual(lookup_carrier_gateway('att'), 'txt.att.net')
		self.assertEqual(lookup_carrier_gateway('aTt'), 'txt.att.net')
		self.assertEqual(lookup_carrier_gateway('AT&T'), 'txt.att.net')

	def test_major_carrier_smtp_server_resolution(self):
		major_carriers = ['att', 'sprint', 'verizon']
		for carrier_name in major_carriers:
			gateway = lookup_carrier_gateway(carrier_name)
			self.assertIsInstance(gateway, str)
			smtp_servers = get_smtp_servers(gateway)
			self.assertGreater(len(smtp_servers), 0)

if __name__ == '__main__':
	unittest.main()
