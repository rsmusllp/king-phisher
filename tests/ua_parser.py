#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  tests/ua_parser.py
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
#  * Neither the name of the  nor the names of its
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

from king_phisher.ua_parser import *

class UserAgentParserTests(unittest.TestCase):
	def test_matches(self):
		ua = parse_user_agent('BAD USER AGENT')
		self.assertIsNone(ua)
		valid_user_agents = [
			'Mozilla/5.0 (Linux; U; Android 4.1.2; en-us; DROID RAZR Build/9.8.2O-72_VZW-16-5) AppleWebKit/534.30 (KHTML, like Gecko) Version/4.0 Mobile Safari/534.30',
			'Mozilla/5.0 (BlackBerry; U; BlackBerry 9800; en-US) AppleWebKit/534.8+ (KHTML, like Gecko) Version/6.0.0.466 Mobile Safari/534.8+',
			'Mozilla/5.0 (iPhone; CPU iPhone OS 6_1_4 like Mac OS X) AppleWebKit/536.26 (KHTML, like Gecko) Version/6.0 Mobile/10B350 Safari/8536.25',
			'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/33.0.1750.152 Safari/537.36',
			'Mozilla/5.0 (compatible; MSIE 10.0; Windows NT 6.1; WOW64; Trident/6.0)',
			'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_6_8) AppleWebKit/534.59.10 (KHTML, like Gecko) Version/5.1.9 Safari/534.59.10',
		]
		for user_agent in valid_user_agents:
			ua = parse_user_agent(user_agent)
			self.assertIsInstance(ua, UserAgent)

	def test_os_android(self):
		ua = parse_user_agent('Mozilla/5.0 (Linux; U; Android 4.1.2; en-us; DROID RAZR Build/9.8.2O-72_VZW-16-5) AppleWebKit/534.30 (KHTML, like Gecko) Version/4.0 Mobile Safari/534.30')
		self.assertIsInstance(ua, UserAgent)
		self.assertEqual(ua.os_name, 'Android')
		self.assertEqual(ua.os_version, '4.1.2')
		self.assertIsNone(ua.os_arch)

	def test_os_ios(self):
		ua = parse_user_agent('Mozilla/5.0 (iPhone; U; CPU iPhone OS 3_0 like Mac OS X; en-us) AppleWebKit/528.18 (KHTML, like Gecko) Version/4.0 Mobile/7A341 Safari/528.1')
		self.assertIsInstance(ua, UserAgent)
		self.assertEqual(ua.os_name, 'iOS')
		self.assertEqual(ua.os_version, '3.0')
		self.assertIsNone(ua.os_arch)
		ua = parse_user_agent('Mozilla/5.0 (iPad; CPU OS 7_0_4 like Mac OS X) AppleWebKit/537.51.1 (KHTML, like Gecko) Version/7.0 Mobile/11B554a Safari/9537.53')
		self.assertIsInstance(ua, UserAgent)
		self.assertEqual(ua.os_name, 'iOS')
		self.assertEqual(ua.os_version, '7.0.4')
		self.assertIsNone(ua.os_arch)

	def test_os_linux(self):
		ua = parse_user_agent('Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/33.0.1750.152 Safari/537.36')
		self.assertIsInstance(ua, UserAgent)
		self.assertEqual(ua.os_name, 'Linux')
		self.assertIsNone(ua.os_version)
		self.assertEqual(ua.os_arch, 'x86-64')

	def test_os_osx(self):
		ua = parse_user_agent('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_6_8) AppleWebKit/534.59.10 (KHTML, like Gecko) Version/5.1.9 Safari/534.59.10')
		self.assertIsInstance(ua, UserAgent)
		self.assertEqual(ua.os_name, 'OS X')
		self.assertEqual(ua.os_version, '10.6.8')
		self.assertIsNone(ua.os_arch)

	def test_os_windows(self):
		ua = parse_user_agent('Mozilla/5.0 (compatible; MSIE 10.0; Windows NT 6.1; WOW64; Trident/6.0)')
		self.assertIsInstance(ua, UserAgent)
		self.assertEqual(ua.os_name, 'Windows NT')
		self.assertEqual(ua.os_version, '6.1')
		self.assertEqual(ua.os_arch, 'x86-64')

if __name__ == '__main__':
	unittest.main()
