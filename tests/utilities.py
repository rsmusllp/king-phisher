#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  tests/utilities.py
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

from king_phisher import testing
from king_phisher.utilities import *

class UtilitiesTests(testing.KingPhisherTestCase):
	def test_is_valid_email_address(self):
		valid_emails = [
			'aliddle@wonderland.com',
			'aliddle@wonderland.co.uk',
			'alice.liddle1+spam@wonderland.com',
		]
		invalid_emails = [
			'aliddle.wonderland.com'
			'aliddle+',
			'aliddle@',
			'aliddle',
			'',
			'@wonderland.com',
			'@wonder@land.com',
			'aliddle@.com'
		]
		for address in valid_emails:
			self.assertTrue(is_valid_email_address(address))
		for address in invalid_emails:
			self.assertFalse(is_valid_email_address(address))

	def test_is_valid_ip_address(self):
		valid_ips = [
			'127.0.0.1',
			'10.0.0.1',
			'200.100.0.1',
			'fe80::1',
			'::1'
		]
		invalid_ips = [
			'localhost',
			'www.google.com',
			''
		]
		for address in valid_ips:
			self.assertTrue(is_valid_ip_address(address))
		for address in invalid_ips:
			self.assertFalse(is_valid_ip_address(address))

	def test_mock_attributes(self):
		mock = Mock()
		self.assertIsInstance(mock.foo, Mock)
		self.assertIsInstance(mock.foo.bar, Mock)
		self.assertEqual(mock.__file__, os.devnull)
		self.assertEqual(mock.__path__, os.devnull)
		mock_cls = Mock
		mock_cls.foobar = 123
		self.assertEqual(mock_cls.foobar, 123)

	def test_mock_calls(self):
		mock = Mock()
		result = mock()
		self.assertIsInstance(result, Mock)

if __name__ == '__main__':
	unittest.main()
