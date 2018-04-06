#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  king_phisher/client/widget/managers.py
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

import collections
import functools

from king_phisher import utilities
from king_phisher.client import gui_utilities

from gi.repository import Gdk
from gi.repository import Gtk

class ButtonGroupManager(object):
	"""
	Manage a set of buttons. The buttons should all be of the same type (such as
	"checkbutton" or "radiobutton") and include a common group name prefix. The
	intent is to make managing buttons of similar functionality easier by
	grouping them together.
	"""
	def __init__(self, glade_gobject, widget_type, group_name):
		"""
		:param glade_gobject: The gobject which has the radio buttons set.
		:type glade_gobject: :py:class:`.GladeGObject`
		:param str group_name: The name of the group of buttons.
		"""
		utilities.assert_arg_type(glade_gobject, gui_utilities.GladeGObject)
		self.group_name = group_name
		name_prefix = widget_type + '_' + self.group_name + '_'
		self.buttons = utilities.FreezableDict()
		for gobj_name in glade_gobject.dependencies.children:
			if not gobj_name.startswith(name_prefix):
				continue
			button_name = gobj_name[len(name_prefix):]
			self.buttons[button_name] = glade_gobject.gobjects[gobj_name]
		if not len(self.buttons):
			raise ValueError('found no ' + widget_type + ' of group: ' + self.group_name)
		self.buttons.freeze()

	def __repr__(self):
		return "<{0} group_name={1!r} active={2!r} >".format(self.__class__.__name__, self.group_name, self.__str__())

class RadioButtonGroupManager(ButtonGroupManager):
	"""
	Manage a group of :py:class:`Gtk.RadioButton` objects together to allow the
	active one to be easily set and identified. The buttons are retrieved from a
	:py:class:`.GladeGObject` instance and must be correctly named
	in the :py:attr:`.dependencies` attribute as
	'radiobutton_group_name_button_name'.
	"""
	def __init__(self, glade_gobject, group_name):
		"""
		:param glade_gobject: The gobject which has the radio buttons set.
		:type glade_gobject: :py:class:`.GladeGObject`
		:param str group_name: The name of the group of buttons.
		"""
		super(RadioButtonGroupManager, self).__init__(glade_gobject, 'radiobutton', group_name)

	def __str__(self):
		return self.get_active() or ''

	def get_active(self):
		"""
		Return the name of the active button if one in the group is active. If
		no button in the group is active, None is returned.

		:return: The name of the active button.
		:rtype: str
		"""
		for name, button in self.buttons.items():
			if button.get_active():
				return name
		return

	def set_active(self, button):
		"""
		Set a button in the group as active.

		:param str button: The name of the button to set as active.
		"""
		button = self.buttons[button]
		button.set_active(True)
		button.toggled()

class ToggleButtonGroupManager(ButtonGroupManager):
	"""
	Manage a mapping of button names to a boolean value indicating whether they
	are active or not.
	"""
	def __str__(self):
		return ', '.join(name for name, active in self.get_active().items() if active)

	def get_active(self):
		"""
		Get the button names and whether or not they are active.

		:return: A mapping of button names to whether or not they are active.
		:rtype: dict
		"""
		return {name: button.get_active() for name, button in self.buttons.items()}

	def set_active(self, buttons):
		"""
		Set the specified buttons to active or not.

		:param dict buttons: A mapping of button names to boolean values.
		"""
		for name, active in buttons.items():
			button = self.buttons.get(name)
			if button is None:
				raise ValueError('invalid button name: ' + name)
			button.set_active(active)

class TreeViewManager(object):
	"""
	A class that wraps :py:class:`Gtk.TreeView` objects that use `Gtk.ListStore`
	models with additional functions for conveniently displaying text data.

	If *cb_delete* is specified, the callback will be called with the treeview
	instance, and the selection as the parameters.

	If *cb_refresh* is specified, the callback will be called without any
	parameters.
	"""
	def __init__(self, treeview, selection_mode=None, cb_delete=None, cb_refresh=None):
		"""
		:param treeview: The treeview to wrap and manage.
		:type treeview: :py:class:`Gtk.TreeView`
		:param selection_mode: The selection mode to set for the treeview.
		:type selection_mode: :py:class:`Gtk.SelectionMode`
		:param cb_delete: An optional callback that can be used to delete entries.
		:type cb_delete: function
		"""
		self.treeview = treeview
		"""The :py:class:`Gtk.TreeView` instance being managed."""
		self.cb_delete = cb_delete
		"""An optional callback for deleting entries from the treeview's model."""
		self.cb_refresh = cb_refresh
		"""An optional callback for refreshing the data in the treeview's model."""
		self.column_titles = collections.OrderedDict()
		"""An ordered dictionary of storage data columns keyed by their respective column titles."""
		self.column_views = {}
		"""A dictionary of column treeview's keyed by their column titles."""
		self.treeview.connect('key-press-event', self.signal_key_pressed)
		if selection_mode is None:
			selection_mode = Gtk.SelectionMode.SINGLE
		treeview.get_selection().set_mode(selection_mode)

	def _call_cb_delete(self):
		if not self.cb_delete:
			return
		selection = self.treeview.get_selection()
		if not selection.count_selected_rows():
			return
		self.cb_delete(self.treeview, selection)

	def get_popup_menu(self, handle_button_press=True):
		"""
		Create a :py:class:`Gtk.Menu` with entries for copying and optionally
		delete cell data from within the treeview. The delete option will only
		be available if a delete callback was previously set.

		:param bool handle_button_press: Whether or not to connect a handler for displaying the popup menu.
		:return: The populated popup menu.
		:rtype: :py:class:`Gtk.Menu`
		"""
		popup_copy_submenu = self.get_popup_copy_submenu()
		popup_menu = Gtk.Menu.new()
		menu_item = Gtk.MenuItem.new_with_label('Copy')
		menu_item.set_submenu(popup_copy_submenu)
		popup_menu.append(menu_item)
		if self.cb_delete:
			menu_item = Gtk.SeparatorMenuItem()
			popup_menu.append(menu_item)
			menu_item = Gtk.MenuItem.new_with_label('Delete')
			menu_item.connect('activate', self.signal_activate_popup_menu_delete)
			popup_menu.append(menu_item)
		popup_menu.show_all()
		if handle_button_press:
			self.treeview.connect('button-press-event', self.signal_button_pressed, popup_menu)
		return popup_menu

	def get_popup_copy_submenu(self):
		"""
		Create a :py:class:`Gtk.Menu` with entries for copying cell data from
		the treeview.

		:return: The populated copy popup menu.
		:rtype: :py:class:`Gtk.Menu`
		"""
		copy_menu = Gtk.Menu.new()
		for column_title, store_id in self.column_titles.items():
			menu_item = Gtk.MenuItem.new_with_label(column_title)
			menu_item.connect('activate', self.signal_activate_popup_menu_copy, store_id)
			copy_menu.append(menu_item)
		if len(self.column_titles) > 1:
			menu_item = Gtk.SeparatorMenuItem()
			copy_menu.append(menu_item)
			menu_item = Gtk.MenuItem.new_with_label('All')
			menu_item.connect('activate', self.signal_activate_popup_menu_copy, self.column_titles.values())
			copy_menu.append(menu_item)
		return copy_menu

	def set_column_titles(self, column_titles, column_offset=0, renderers=None):
		"""
		Populate the column names of a GTK TreeView and set their sort IDs. This
		also populates the :py:attr:`.column_titles` attribute.

		:param list column_titles: The titles of the columns.
		:param int column_offset: The offset to start setting column names at.
		:param list renderers: A list containing custom renderers to use for each column.
		:return: A dict of all the :py:class:`Gtk.TreeViewColumn` objects keyed by their column id.
		:rtype: dict
		"""
		self.column_titles.update((v, k) for (k, v) in enumerate(column_titles, column_offset))
		columns = gui_utilities.gtk_treeview_set_column_titles(self.treeview, column_titles, column_offset=column_offset, renderers=renderers)
		for store_id, column_title in enumerate(column_titles, column_offset):
			self.column_views[column_title] = columns[store_id]
		return columns

	def set_column_color(self, background=None, foreground=None, column_titles=None):
		"""
		Set a column in the model to be used as either the background or
		foreground RGBA color for a cell.

		:param int background: The column id of the model to use as the background color.
		:param int foreground: The column id of the model to use as the foreground color.
		:param column_titles: The columns to set the color for, if None is specified all columns will be set.
		:type column_titles: str, tuple
		"""
		if background is None and foreground is None:
			raise RuntimeError('either background of foreground must be set')
		if column_titles is None:
			column_titles = self.column_titles.keys()
		elif isinstance(column_titles, str):
			column_titles = (column_titles,)
		for column_title in column_titles:
			column = self.column_views[column_title]
			cell = column.get_cells()[0]
			props = {'text': self.column_titles[column_title]}
			if background is not None:
				props['background-rgba'] = background
				props['background-set'] = True
			if foreground is not None:
				props['foreground-rgba'] = foreground
				props['foreground-set'] = True
			column.set_attributes(cell, **props)

	def signal_button_pressed(self, treeview, event, popup_menu):
		if not (event.type == Gdk.EventType.BUTTON_PRESS and event.button == Gdk.BUTTON_SECONDARY):
			return
		selection = treeview.get_selection()
		if not selection.count_selected_rows():
			return
		popup_menu.popup(None, None, functools.partial(gui_utilities.gtk_menu_position, event), None, event.button, event.time)
		return True

	def signal_key_pressed(self, treeview, event):
		if event.type != Gdk.EventType.KEY_PRESS:
			return
		keyval = event.get_keyval()[1]
		if event.get_state() == Gdk.ModifierType.CONTROL_MASK:
			if keyval == Gdk.KEY_c and self.column_titles:
				gui_utilities.gtk_treeview_selection_to_clipboard(treeview, list(self.column_titles.values())[0])
		elif keyval == Gdk.KEY_F5 and self.cb_refresh:
			self.cb_refresh()
		elif keyval == Gdk.KEY_Delete:
			self._call_cb_delete()

	def signal_activate_popup_menu_copy(self, menuitem, column_ids):
		gui_utilities.gtk_treeview_selection_to_clipboard(self.treeview, column_ids)

	def signal_activate_popup_menu_delete(self, menuitem):
		self._call_cb_delete()
