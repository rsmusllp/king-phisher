#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  tests/server/authenticator.py
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

import time
import unittest

from king_phisher import testing
from king_phisher.server import aaa

class ServerAuthenticationTests(testing.KingPhisherTestCase):
	def test_authenticator_bad_credentials(self):
		auth = aaa.ForkedAuthenticator()
		self.assertFalse(auth.authenticate('fakeuser', 'FakePassword1'))
		self.assertFalse(auth.authenticate('root', 'FakePassword1'))
		auth.stop()

class ServerAuthenticatedSessionManagerTests(testing.KingPhisherTestCase):
	def test_session_creation(self):
		manager = aaa.AuthenticatedSessionManager()
		original_session_count = len(manager)
		username = 'alice'
		manager.put(username)
		self.assertEqual(len(manager), original_session_count + 1)
		manager.put(username)
		self.assertEqual(len(manager), original_session_count + 1)

	def test_session_expiration(self):
		manager = aaa.AuthenticatedSessionManager(timeout=0.5)
		session_id = manager.put('alice')
		self.assertIsNotNone(manager.get(session_id))
		time.sleep(0.75)
		self.assertIsNone(manager.get(session_id))
		self.assertEqual(len(manager), 0)

if __name__ == '__main__':
	unittest.main()
