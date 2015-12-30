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
from king_phisher.client import widget_managers

from gi.repository import Gtk

class ClientTreeViewManagerTests(testing.KingPhisherTestCase):
	def test_column_titles(self):
		treeview = Gtk.TreeView()
		treeview_manager = widget_managers.TreeViewManager(treeview)
		self.assertEqual(len(treeview_manager.column_titles), 0)
		treeview_manager.set_column_titles(('col0', 'col1'))
		self.assertEqual(len(treeview_manager.column_titles), 2)
		self.assertEqual(treeview_manager.column_titles.get('col0'), 0)
		self.assertEqual(treeview_manager.column_titles.get('col1'), 1)

	def test_popup_copy_submenu(self):
		treeview = Gtk.TreeView()
		treeview_manager = widget_managers.TreeViewManager(treeview)
		treeview_manager.set_column_titles(('col0',))
		menu = treeview_manager.get_popup_copy_submenu()
		self.assertEqual(len(menu.get_children()), 1, msg='the copy submenu contains an invalid number or entries')

		treeview_manager.set_column_titles(('col0', 'col1'))
		menu = treeview_manager.get_popup_copy_submenu()
		self.assertEqual(len(menu.get_children()), 4, msg='the copy submenu contains an invalid number or entries')
		treeview.destroy()

	def test_popup_menu(self):
		treeview = Gtk.TreeView()
		treeview_manager = widget_managers.TreeViewManager(treeview)
		treeview_manager.set_column_titles(('col0', 'col1'))
		menu = treeview_manager.get_popup_menu()
		self.assertEqual(len(menu.get_children()), 1, msg='the popup menu contains more than one entry')
		copy_submenuitem = menu.get_children()[0]
		self.assertEqual(copy_submenuitem.get_label(), 'Copy')
		copy_submenu = copy_submenuitem.get_submenu()
		self.assertEqual(len(copy_submenu.get_children()), 4, msg='the copy submenu contains an invalid number or entries')
		treeview.destroy()

	def test_selection_mode(self):
		treeview = Gtk.TreeView()
		_ = widget_managers.TreeViewManager(treeview)
		self.assertEqual(treeview.get_selection().get_mode(), Gtk.SelectionMode.SINGLE)
		treeview.destroy()

		treeview = Gtk.TreeView()
		_ = widget_managers.TreeViewManager(treeview, selection_mode=Gtk.SelectionMode.NONE)
		self.assertEqual(treeview.get_selection().get_mode(), Gtk.SelectionMode.NONE)
		treeview.destroy()

if __name__ == '__main__':
	unittest.main()
