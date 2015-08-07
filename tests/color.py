#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  tests/color.py
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

from king_phisher import color
from king_phisher import testing

class ColorConversionTests(testing.KingPhisherTestCase):
	def test_convert_hex_to_tuple(self):
		value = (1.0, 0.5019608, 0.0)
		converted = color.convert_hex_to_tuple('#ff8000')
		for v, c in zip(value, converted):
			self.assertAlmostEqual(v, c)
		value = (0.0705882, 0.2039216, 0.3372549)
		converted = color.convert_hex_to_tuple('#123456')
		for v, c in zip(value, converted):
			self.assertAlmostEqual(v, c)

	def test_convert_hex_to_tuple_invalid(self):
		with self.assertRaises(ValueError):
			color.convert_hex_to_tuple('#1234567')

	def test_convert_hex_to_tuple_raw(self):
		self.assertEqual(color.convert_hex_to_tuple('#ff8000', raw=True), (255, 128, 0))
		self.assertEqual(color.convert_hex_to_tuple('102040', raw=True), (16, 32, 64))

	def test_convert_tuple_to_hex(self):
		self.assertEqual(color.convert_tuple_to_hex((1.0, 0.5019608, 0.0)), '#ff8000')
		self.assertEqual(color.convert_tuple_to_hex((0.0705882, 0.2039216, 0.3372549)), '#123456')

	def test_convert_tuple_to_hex_raw(self):
		self.assertEqual(color.convert_tuple_to_hex((255, 128, 0), raw=True), '#ff8000')
		self.assertEqual(color.convert_tuple_to_hex((16, 32, 64), raw=True), '#102040')

if __name__ == '__main__':
	unittest.main()
