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
from king_phisher.ua_parser import *

class UserAgentParserTests(testing.KingPhisherTestCase):
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
			'Mozilla/4.0 (compatible; MSIE 7.0; Windows Phone OS 7.0; Trident/3.1; IEMobile/7.0; NOKIA; Lumia 1520)'
		]
		for user_agent in valid_user_agents:
			ua = parse_user_agent(user_agent)
			self.assertIsInstance(ua, UserAgent)

	def _parse_user_agent(self, user_agent, os_name, os_version, os_arch):
		ua = parse_user_agent(user_agent)
		self.assertIsInstance(ua, UserAgent)
		self.assertEqual(ua.os_name, os_name, msg='detected os name does not match')
		if os_version == None:
			self.assertIsNone(ua.os_version)
		else:
			self.assertEqual(ua.os_version, os_version, msg='detected os version does not match')
		if os_arch == None:
			self.assertIsNone(ua.os_arch)
		else:
			self.assertEqual(ua.os_arch, os_arch, msg='detected os architecture does not match')
		return ua

	def test_os_android(self):
		ua = 'Mozilla/5.0 (Linux; U; Android 4.1.2; en-us; DROID RAZR Build/9.8.2O-72_VZW-16-5) AppleWebKit/534.30 (KHTML, like Gecko) Version/4.0 Mobile Safari/534.30'
		self._parse_user_agent(ua, 'Android', '4.1.2', None)

	def test_os_blackberry(self):
		ua = 'Mozilla/5.0 (BB10; Touch) AppleWebKit/537.35+ (KHTML, like Gecko) Version/10.2.1.2141 Mobile Safari/537.35+'
		self._parse_user_agent(ua, 'BlackBerry', '10.2.1.2141', None)

	def test_os_ios(self):
		ua = 'Mozilla/5.0 (iPhone; U; CPU iPhone OS 3_0 like Mac OS X; en-us) AppleWebKit/528.18 (KHTML, like Gecko) Version/4.0 Mobile/7A341 Safari/528.1'
		self._parse_user_agent(ua, 'iOS', '3.0', None)
		ua = 'Mozilla/5.0 (iPad; CPU OS 7_0_4 like Mac OS X) AppleWebKit/537.51.1 (KHTML, like Gecko) Version/7.0 Mobile/11B554a Safari/9537.53'
		self._parse_user_agent(ua, 'iOS', '7.0.4', None)

	def test_os_linux(self):
		ua = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/33.0.1750.152 Safari/537.36'
		self._parse_user_agent(ua, 'Linux', None, 'x86-64')
		ua = 'Mozilla/5.0 (Linux; U; en-us; KFTHWI Build/JDQ39) AppleWebKit/535.19 (KHTML, like Gecko) Silk/3.21 Safari/535.19 Silk-Accelerated=true'
		self._parse_user_agent(ua, 'Linux', None, None)

	def test_os_osx(self):
		ua = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_6_8) AppleWebKit/534.59.10 (KHTML, like Gecko) Version/5.1.9 Safari/534.59.10'
		self._parse_user_agent(ua, 'OS X', '10.6.8', None)
		ua = 'Mozilla/5.0 (Macintosh; U; PPC Mac OS X; en) AppleWebKit/521.25 (KHTML, like Gecko) Safari/521.24'
		self._parse_user_agent(ua, 'OS X', None, 'PPC')

	def test_os_windows(self):
		ua = 'Mozilla/5.0 (compatible; MSIE 10.0; Windows NT 6.1; WOW64; Trident/6.0)'
		self._parse_user_agent(ua, 'Windows NT', '6.1', 'x86-64')

	def test_os_windows_phone(self):
		ua = 'Mozilla/4.0 (compatible; MSIE 7.0; Windows Phone OS 7.0; Trident/3.1; IEMobile/7.0; NOKIA; Lumia 1520)'
		self._parse_user_agent(ua, 'Windows Phone', '7.0', None)

if __name__ == '__main__':
	unittest.main()
