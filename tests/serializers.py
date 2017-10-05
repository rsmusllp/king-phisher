#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  tests/serializers.py
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

import datetime
import xml.etree.ElementTree as ET

from king_phisher import testing
from king_phisher import serializers

class _SerializerTests(testing.KingPhisherServerTestCase):
	serializer = None
	serializer_output_type = None
	test_objects = ('test', True, 100)
	def test_dump_basic_types(self):
		for obj in self.test_objects:
			self.assertIsInstance(self.serializer.dumps(obj), self.serializer_output_type)

	def test_simple_reload(self):
		for obj in self.test_objects:
			try:
				self.serializer.loads(self.serializer.dumps(obj))
			except ValueError:
				self.fail("Invalid data type for serializer.{0}.loads()".format(self.serializer.name))

	def test_special_types(self):
		now = datetime.datetime.now()
		serialized = self.serializer.dumps(now)
		self.assertIsInstance(serialized, self.serializer_output_type)
		self.assertNotEqual(now, serialized)
		self.assertNotEqual(type(now), type(serialized))
		now_loaded = self.serializer.loads(serialized)
		self.assertEqual(now, now_loaded)

class _ElementTreeSerializer(object):
	# this class defines a pseudo serializer that allows the functions to be
	# tested in the same way as the serializers that are implemented as classes
	def dumps(self, value):
		parent = ET.Element('parent')
		return serializers.to_elementtree_subelement(parent, 'child', value)

	def loads(self, element):
		return serializers.from_elementtree_element(element)

class ElementTreeTests(_SerializerTests):
	serializer = _ElementTreeSerializer()
	serializer_output_type = ET.Element

class JSONSerializerTests(_SerializerTests):
	serializer = serializers.JSON
	serializer_output_type = str

	def test_loads_invalid(self):
		with self.assertRaises(ValueError):
			serializers.JSON.loads("'test")

class MsgPackSerializerTests(_SerializerTests):
	serializer = serializers.MsgPack
	serializer_output_type = bytes
