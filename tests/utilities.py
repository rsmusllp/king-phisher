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

from king_phisher.utilities import *

class UtilitiesTests(unittest.TestCase):
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

	def test_timedef_to_seconds(self):
		self.assertRaises(ValueError, timedef_to_seconds, 'fake')
		self.assertEqual(timedef_to_seconds(''), 0)
		self.assertEqual(timedef_to_seconds('30'), 30)
		self.assertEqual(timedef_to_seconds('1m30s'), 90)
		self.assertEqual(timedef_to_seconds('2h1m30s'), 7290)
		self.assertEqual(timedef_to_seconds('3d2h1m30s'), 266490)

if __name__ == '__main__':
	unittest.main()
