#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  tests/security_keys.py
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

import binascii
import unittest

from king_phisher import find
from king_phisher import security_keys
from king_phisher import serializers
from king_phisher import testing
from king_phisher import utilities

import ecdsa
import ecdsa.keys
import jsonschema

class SecurityKeysTests(testing.KingPhisherTestCase):
	def test_schema(self):
		file_path = find.data_file('security.json')
		self.assertIsNotNone(file_path, msg='failed to find the security.json file')
		with open(file_path, 'r') as file_h:
			key_store = serializers.JSON.load(file_h)
		try:
			utilities.validate_json_schema(key_store, 'king-phisher.security')
		except jsonschema.ValidationError:
			self.fail('the security.json file failed validation')

class SigningKeyTests(testing.KingPhisherTestCase):
	def setUp(self):
		self.sk = security_keys.SigningKey.generate(curve=ecdsa.NIST521p)

	def test_dictionary_verification(self):
		test_data = {}
		for _ in range(5):
			test_data['_' + utilities.random_string(10)] = utilities.random_string(10)
		self.sk = security_keys.SigningKey.generate(curve=ecdsa.NIST521p)
		test_data = self.sk.sign_dict(test_data, signature_encoding='base64')
		self.assertIsInstance(test_data, dict)
		# make sure the 'signature' key was added
		self.assertIn('signature', test_data)
		self.assertEqual(len(test_data), 6)

		try:
			binascii.a2b_base64(test_data['signature'])
		except ValueError:
			self.fail('signature could not be decoded as base64')

		vk = self.sk.get_verifying_key()
		vk.verify_dict(test_data, signature_encoding='base64')

		test_data['_' + utilities.random_string(10)] = utilities.random_string(10)
		with self.assertRaises(ecdsa.keys.BadSignatureError):
			vk.verify_dict(test_data, signature_encoding='base64')

	def test_verifying_key(self):
		vk = self.sk.get_verifying_key()
		self.assertIsInstance(vk, security_keys.VerifyingKey)

if __name__ == '__main__':
	unittest.main()
