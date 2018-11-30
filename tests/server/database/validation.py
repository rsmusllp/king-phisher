#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  tests/server/database/validation.py
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
from king_phisher.server.database import models as db_models
from king_phisher.server.database import validation as db_validation

class DatabaseValidateCredentialTests(testing.KingPhisherTestCase):
	campaign = db_models.Campaign(credential_regex_username=r'a\S+')
	def test_credential_collection_members(self):
		for field in db_validation.CredentialCollection._fields:
			self.assertHasAttribute(db_models.Credential, field)

	def test_empty_configuration_returns_none(self):
		self.assertIsNone(db_validation.validate_credential(
			db_validation.CredentialCollection(username='alice', password='Wonderland!123', mfa_token='031337'),
			db_models.Campaign()
		))
		self.assertIsNone(db_validation.validate_credential(
			db_validation.CredentialCollection(username=None, password=None, mfa_token=None),
			db_models.Campaign()
		))

	def test_extra_fields_are_ignored(self):
		self.assertTrue(db_validation.validate_credential(
			db_validation.CredentialCollection(username='alice', password='Wonderland!123', mfa_token=None),
			self.campaign
		))
		self.assertTrue(db_validation.validate_credential(
			db_validation.CredentialCollection(username='alice', password=None, mfa_token='031337'),
			self.campaign
		))
		self.assertTrue(db_validation.validate_credential(
			db_validation.CredentialCollection(username='alice', password='Wonderland!123', mfa_token='031337'),
			self.campaign
		))

	def test_validation_methods(self):
		cred = db_validation.CredentialCollection(username='alice', password=None, mfa_token=None)
		self.assertEqual(
			db_validation.validate_credential_fields(cred, self.campaign),
			db_validation.CredentialCollection(username=True, password=None, mfa_token=None)
		)
		self.assertTrue(db_validation.validate_credential(cred, self.campaign))

		cred = db_validation.CredentialCollection(username='calie', password=None, mfa_token=None)
		self.assertEqual(
			db_validation.validate_credential_fields(cred, self.campaign),
			db_validation.CredentialCollection(username=False, password=None, mfa_token=None)
		)
		self.assertFalse(db_validation.validate_credential(cred, self.campaign))

		cred = db_validation.CredentialCollection(username='alice', password=None, mfa_token=None)
		campaign = db_models.Campaign(credential_regex_username=r'a\S+', credential_regex_password=r'a\S+')
		self.assertEqual(
			db_validation.validate_credential_fields(cred, campaign),
			db_validation.CredentialCollection(username=True, password=False, mfa_token=None)
		)
		self.assertFalse(db_validation.validate_credential(cred, campaign))

	def test_empty_fields_fail(self):
		self.assertEqual(db_validation.validate_credential_fields(
			db_validation.CredentialCollection(username='', password=None, mfa_token=None),
			self.campaign
		), db_validation.CredentialCollection(username=False, password=None, mfa_token=None))

	def test_none_fields_fail(self):
		self.assertEqual(db_validation.validate_credential_fields(
			db_validation.CredentialCollection(username=None, password=None, mfa_token=None),
			self.campaign
		), db_validation.CredentialCollection(username=False, password=None, mfa_token=None))

	def test_bad_regexs_are_skipped(self):
		self.assertEqual(db_validation.validate_credential_fields(
			db_validation.CredentialCollection(username='alice', password=None, mfa_token=None),
			db_models.Campaign(credential_regex_username=r'\S+[')
		), db_validation.CredentialCollection(username=None, password=None, mfa_token=None))

if __name__ == '__main__':
	unittest.main()
