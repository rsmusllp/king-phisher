#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  tests/client/graphs.py
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

from king_phisher import constants
from king_phisher import testing
from king_phisher.client import graphs
from king_phisher.utilities import random_string

class ClientGraphsTests(testing.KingPhisherTestCase):
	def test_graph_classes(self):
		for graph in graphs.get_graphs():
			self.assertTrue(isinstance(graph, str))
			self.assertTrue(issubclass(graphs.get_graph(graph), graphs.CampaignGraph))

	def test_graphs_found(self):
		self.assertGreaterEqual(len(graphs.get_graphs()), 6)

	def test_graphs_os_colors(self):
		for os_name in constants.OSFamily.values():
			self.assertIn(os_name, graphs.MPL_OS_COLORS)
		bad_os_name = random_string(10)
		self.assertEqual(graphs.MPL_OS_COLORS[bad_os_name], graphs.MPL_COLOR_NULL)

if __name__ == '__main__':
	unittest.main()
