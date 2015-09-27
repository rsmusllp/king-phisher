#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  tests/client/client_rpc.py
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
from king_phisher.client import client_rpc
from king_phisher.server.database import models

class ClientRPCRemoteRowTests(testing.KingPhisherTestCase):
	def test_table_row_classes_are_populated(self):
		self.assertGreater(len(client_rpc.database_table_objects), 0)
		public_tables = tuple(table for table in models.database_table_objects.values() if not table.is_private)
		self.assertEqual(len(client_rpc.database_table_objects), len(public_tables))
		for remote_row in client_rpc.database_table_objects.values():
			self.assertTrue(issubclass(remote_row, client_rpc.RemoteRow))

	def test_table_row_classes_are_named(self):
		for table_name, remote_row in client_rpc.database_table_objects.items():
			self.assertEqual(table_name, remote_row.__table__)

	def test_table_row_classes_xrefs_are_valid(self):
		all_xrefs = tuple(row.__xref_attr__ for row in client_rpc.database_table_objects.values() if row.__xref_attr__ is not None)
		self.assertEqual(len(all_xrefs), len(set(all_xrefs)), 'all xrefs must be unique')
		for remote_row in client_rpc.database_table_objects.values():
			for xref_attr in remote_row.__slots__:
				if not xref_attr.endswith('_id'):
					continue
				xref_attr = xref_attr[:-3]
				self.assertIn(xref_attr, all_xrefs)

if __name__ == '__main__':
	unittest.main()
