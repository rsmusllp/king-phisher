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

import logging
import os
import unittest

from king_phisher import testing
from king_phisher import utilities

class UtilitiesTests(testing.KingPhisherTestCase):
	def test_assert_arg_type(self):
		with self.assertRaisesRegex(TypeError, r'test_assert_arg_type\(\) argument 1 must be str, not int'):
			utilities.assert_arg_type(0, str)
		try:
			utilities.assert_arg_type('', str)
		except TypeError:
			self.fail('assert_arg_type raised a TypeError when it should not have')

	def test_configure_stream_logger(self):
		logger = utilities.configure_stream_logger('KingPhisher', 'INFO')
		self.assertEqual(logger.level, logging.INFO)

	def test_is_valid_email_address(self):
		valid_emails = [
			'aliddle@wonderland.com',
			'aliddle@wonderland.co.uk',
			'alice.liddle1+spam@wonderland.com',
			'alice.liddle@wonderland.support'
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
			self.assertTrue(utilities.is_valid_email_address(address))
		for address in invalid_emails:
			self.assertFalse(utilities.is_valid_email_address(address))

	def test_mock_calls(self):
		mock = utilities.Mock()
		result = mock()
		self.assertIsInstance(result, utilities.Mock)

	def test_mock_class_attribute(self):
		mock_cls = utilities.Mock
		mock_cls.foobar = 123
		self.assertEqual(mock_cls.foobar, 123)

	def test_mock_instance_attributes(self):
		mock = utilities.Mock()
		self.assertIsInstance(mock.foo, utilities.Mock)
		self.assertIsInstance(mock.foo.bar, utilities.Mock)
		self.assertEqual(mock.__file__, os.devnull)
		self.assertEqual(mock.__path__, os.devnull)

	def test_nonempty_string(self):
		self.assertEqual(utilities.nonempty_string('test'), 'test')
		self.assertIsNone(utilities.nonempty_string(''))
		self.assertIsNone(utilities.nonempty_string(None))

	def test_password_is_complex(self):
		valid_passwords = [
			'Thisisatestf00l',
			'Welcome2SS!!!!!',
			'HelloAndGoodbyeW0rld'
		]
		invalid_passwords = [
			'THISISATESTFOOL',
			'THISISATESTF00L',
			'Thisisatestfool',
			'i know this is spam',
			'123456789101112',
			'Fo0',
			''
		]
		for password in valid_passwords:
			self.assertTrue(utilities.password_is_complex(password))
		for password in invalid_passwords:
			self.assertFalse(utilities.password_is_complex(password))

if __name__ == '__main__':
	unittest.main()
