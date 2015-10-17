#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  tests/client/gui_utilities.py
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
from king_phisher.client import gui_utilities

from gi.repository import Gtk

def make_test_list_store():
	store = Gtk.ListStore(str, str)
	store.append(('row0 col0', 'row0 col1'))
	store.append(('row1 col0', 'row1 col1'))
	return store

class ClientGUIUtilityTests(testing.KingPhisherTestCase):
	def test_gtk_list_store_search(self):
		store = make_test_list_store()
		result = gui_utilities.gtk_list_store_search(store, 'row0 col0', 0)
		self.assertIsInstance(result, Gtk.TreeIter)
		self.assertEqual(store.get_path(result).to_string(), '0')

		result = gui_utilities.gtk_list_store_search(store, 'row1 col1', 1)
		self.assertIsInstance(result, Gtk.TreeIter)
		self.assertEqual(store.get_path(result).to_string(), '1')

		result = gui_utilities.gtk_list_store_search(store, 'fake', 0)
		self.assertIsNone(result)

if __name__ == '__main__':
	unittest.main()
