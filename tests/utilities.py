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

from king_phisher.utilities import *

SINGLE_QUOTE_STRING_ESCAPED = """C:\\\\Users\\\\Alice\\\\Desktop\\\\Alice\\\'s Secret File.txt"""
SINGLE_QUOTE_STRING_UNESCAPED = """C:\\Users\\Alice\\Desktop\\Alice's Secret File.txt"""

class UtilitiesTests(unittest.TestCase):
	def test_check_requirements(self):
		fake_pkg = 'a' + random_string(16)
		real_pkg = 'Jinja2'
		missing_pkgs = check_requirements([real_pkg + '>=2.0', fake_pkg + '>=1.0'])
		self.assertNotIn(real_pkg, missing_pkgs, msg='A valid package is marked as missing or incompatible')
		self.assertIn(fake_pkg, missing_pkgs, msg='An invalid package is not marked as missing or incompatible')
		self.assertEqual(len(missing_pkgs), 1)

	def test_escape_single_quote(self):
		escaped_string = escape_single_quote(SINGLE_QUOTE_STRING_UNESCAPED)
		self.assertEqual(escaped_string, SINGLE_QUOTE_STRING_ESCAPED)

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

	def test_server_parse(self):
		parsed = server_parse('127.0.0.1', 80)
		self.assertIsInstance(parsed, tuple)
		self.assertEqual(len(parsed), 2)
		self.assertEqual(parsed[0], '127.0.0.1')
		self.assertEqual(parsed[1], 80)
		parsed = server_parse('127.0.0.1:8080', 80)
		self.assertIsInstance(parsed, tuple)
		self.assertEqual(len(parsed), 2)
		self.assertEqual(parsed[0], '127.0.0.1')
		self.assertEqual(parsed[1], 8080)
		parsed = server_parse('[::1]:8080', 80)
		self.assertIsInstance(parsed, tuple)
		self.assertEqual(len(parsed), 2)
		self.assertEqual(parsed[0], '::1')
		self.assertEqual(parsed[1], 8080)

	def test_timedef_to_seconds(self):
		self.assertRaises(ValueError, timedef_to_seconds, 'fake')
		self.assertEqual(timedef_to_seconds(''), 0)
		self.assertEqual(timedef_to_seconds('30'), 30)
		self.assertEqual(timedef_to_seconds('1m30s'), 90)
		self.assertEqual(timedef_to_seconds('2h1m30s'), 7290)
		self.assertEqual(timedef_to_seconds('3d2h1m30s'), 266490)

	def test_unescape_single_quote(self):
		unescaped_string = unescape_single_quote(SINGLE_QUOTE_STRING_ESCAPED)
		self.assertEqual(unescaped_string, SINGLE_QUOTE_STRING_UNESCAPED)

if __name__ == '__main__':
	unittest.main()
