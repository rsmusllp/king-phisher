#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  tests/client/gtk_builder_lint.py
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
import xml.etree.ElementTree as ElementTree

from king_phisher import find
from king_phisher import testing

GOBJECT_TOP_REGEX = r'^[A-Z][a-zA-Z0-9]+$'

class ClientGtkBuilderLint(testing.KingPhisherTestCase):
	def setUp(self):
		find.data_path_append('data/client')
		builder_xml = find.data_file('king-phisher-client.ui')
		self.xml_tree = ElementTree.parse(builder_xml)
		self.xml_root = self.xml_tree.getroot()

	def test_object_ids_are_valid(self):
		for child in self.xml_root:
			if child.tag != 'object':
				continue
			gobject_id = child.attrib['id']
			self.assertRegex(gobject_id, GOBJECT_TOP_REGEX, "invalid gobject id '{0}'".format(gobject_id))

if __name__ == '__main__':
	unittest.main()
