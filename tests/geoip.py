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

import ipaddress
import os
import unittest

from king_phisher import geoip
from king_phisher.testing import KingPhisherTestCase
from king_phisher.testing import KingPhisherServerTestCase

GEO_TEST_IP = '8.8.8.8'

class GeoIPTests(KingPhisherTestCase):
	def setUp(self):
		self.db_path = os.environ.get('KING_PHISHER_TEST_GEOIP_DB', './GeoLite2-City.mmdb')
		self.__geoip_db = geoip.init_database(self.db_path)

	def tearDown(self):
		self.__geoip_db.close()

	def test_geoip_lookup(self):
		result = geoip.lookup(GEO_TEST_IP)
		self.assertIsInstance(result, dict)
		for field in geoip.DB_RESULT_FIELDS:
			self.assertIn(field, result)

	def test_geoip_lookup_private(self):
		with self.assertRaises(RuntimeError):
			geoip.lookup('192.168.1.1')

	def test_geoip_lookup_ipv6(self):
		with self.assertRaises(TypeError):
			geoip.lookup('2607:f8b0:4002:c07::68')

	def test_geoip_raw_geolocation(self):
		loc = geoip.GeoLocation(GEO_TEST_IP)
		loc_raw = geoip.GeoLocation(GEO_TEST_IP, result=geoip.lookup(GEO_TEST_IP))
		for field in geoip.DB_RESULT_FIELDS:
			self.assertEqual(getattr(loc, field), getattr(loc_raw, field))
		self.assertIsInstance(loc.ip_address, ipaddress.IPv4Address)
		self.assertEqual(loc.ip_address, ipaddress.IPv4Address(GEO_TEST_IP))

class GeoIPRPCTests(KingPhisherServerTestCase):
	def test_geoip_lookup_rpc(self):
		result = self.rpc.geoip_lookup(GEO_TEST_IP)
		self.assertIsInstance(result, geoip.GeoLocation)

if __name__ == '__main__':
	unittest.main()
