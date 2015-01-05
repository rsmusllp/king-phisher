#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  king_phisher/client/gui_utilities.py
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

import contextlib
import logging
import os
import threading

from king_phisher import find
from king_phisher import utilities

from gi.repository import GLib
from gi.repository import GObject
from gi.repository import Gtk

GOBJECT_PROPERTY_MAP = {
	'checkbutton': 'active',
	'combobox': (
		lambda c, v: c.set_active_iter(search_list_store(c.get_model(), v)),
		lambda c: c.get_model().get_value(c.get_active_iter() or c.get_model().get_iter_first(), 0)
	),
	'entry': 'text',
	'spinbutton': 'value',
	'switch': 'active',
	'textview': (
		lambda t, v: t.get_buffer().set_text(v),
		lambda t: t.get_buffer().get_text(t.get_buffer().get_start_iter(), t.get_buffer().get_end_iter(), False)
	)
}
"""
The dictionary which maps GObjects to either the names of properties to
store text or a tuple which contains a set and get function. If a tuple
of two functions is specified the set function will be provided two
parameters, the object and the value and the get function will just be
provided the object.
"""

if isinstance(Gtk.Window, utilities.Mock):
	_Gtk_FileChooserDialog = type('Gtk.FileChooserDialog', (object,), {})
	_Gtk_FileChooserDialog.__module__ = ''
else:
	_Gtk_FileChooserDialog = Gtk.FileChooserDialog

def which_glade():
	"""
	Locate the glade data file.

	:return: The path to the glade data file.
	:rtype: str
	"""
	return find.find_data_file(os.environ['KING_PHISHER_GLADE_FILE'])

def glib_idle_add_wait(function, *args):
	"""
	Execute *function* in the main GTK loop using :py:func:`GLib.idle_add`
	and block until it has completed. This is useful for threads that need
	to update GUI data.

	:param function function: The function to call.
	:param args: The arguments to *functoin*.
	:return: The result of the function call.
	"""
	gsource_completed = threading.Event()
	results = []
	def wrapper():
		results.append(function(*args))
		gsource_completed.set()
		return False
	GLib.idle_add(wrapper)
	gsource_completed.wait()
	return results.pop()

def gobject_get_value(gobject, gtype=None):
	"""
	Retreive the value of a GObject widget. Only objects with value
	retrieving functions present in the :py:data:`.GOBJECT_PROPERTY_MAP`
	can be processed by this function.

	:param gobject: The object to retrieve the value for.
	:type gobject: :py:class:`GObject.GObject`
	:param str gtype: An explicit type to treat *gobject* as.
	:return: The value of *gobject*.
	:rtype: str
	"""
	gtype = (gtype or gobject.__class__.__name__)
	gtype = gtype.lower()
	if isinstance(GOBJECT_PROPERTY_MAP[gtype], (list, tuple)):
		try:
			value = GOBJECT_PROPERTY_MAP[gtype][1](gobject)
		except AttributeError:
			return None
	else:
		value = gobject.get_property(GOBJECT_PROPERTY_MAP[gtype])
	return value

@contextlib.contextmanager
def gobject_signal_blocked(gobject, signal_name):
	"""
	This is a context manager that can be used with the 'with' statement
	to execute a block of code while *signal_name* is blocked.

	:param gobject: The object to block the signal on.
	:type gobject: :py:class:`GObject.GObject`
	:param str signal_name: The name of the signal to block.
	"""
	signal_id = GObject.signal_lookup(signal_name, gobject.__class__)
	handler_id = GObject.signal_handler_find(gobject, GObject.SignalMatchType.ID, signal_id, 0, None, 0, 0)
	GObject.signal_handler_block(gobject, handler_id)
	yield
	GObject.signal_handler_unblock(gobject, handler_id)

def gtk_sync():
	"""Process all pending GTK events."""
	while Gtk.events_pending():
		Gtk.main_iteration()

def gtk_widget_destroy_children(widget):
	"""
	Destroy all GTK child objects of *widget*.

	:param widget: The widget to destroy all the children of.
	:type widget: :py:class:`Gtk.Widget`
	"""
	map(lambda child: child.destroy(), widget.get_children())

def search_list_store(list_store, value):
	"""
	Search a GTK ListStore for a value.

	:param list_store: The list store to search.
	:type list_store: :py:class:`Gtk.ListStore`
	:param value: The value to search for.
	:return: The row on which the value was found.
	:rtype: :py:class:`Gtk.TreeIter`
	"""
	for row in list_store:
		if row[0] == value:
			return row.iter
	return None

def show_dialog(message_type, message, parent, secondary_text=None, message_buttons=Gtk.ButtonsType.OK):
	"""
	Display a dialog and return the response. The response is dependent on
	the value of *message_buttons*.

	:param message_type: The GTK message type to display.
	:type message_type: :py:class:`Gtk.MessageType`
	:param str message: The text to display in the dialog.
	:param parent: The parent window that the dialog should belong to.
	:type parent: :py:class:`Gtk.Window`
	:param str secondary_text: Optional subtext for the dialog.
	:param message_buttons: The buttons to display in the dialog box.
	:type message_buttons: :py:class:`Gtk.ButtonsType`
	:return: The response of the dialog.
	:rtype: int
	"""
	dialog = Gtk.MessageDialog(parent, Gtk.DialogFlags.DESTROY_WITH_PARENT, message_type, message_buttons, message)
	if secondary_text:
		dialog.format_secondary_text(secondary_text)
	dialog.show_all()
	response = dialog.run()
	dialog.destroy()
	return response

def show_dialog_error(*args, **kwargs):
	"""Display an error dialog with :py:func:`.show_dialog`."""
	return show_dialog(Gtk.MessageType.ERROR, *args, **kwargs)

def show_dialog_info(*args, **kwargs):
	"""Display an informational dialog with :py:func:`.show_dialog`."""
	return show_dialog(Gtk.MessageType.INFO, *args, **kwargs)

def show_dialog_warning(*args, **kwargs):
	"""Display an warning dialog with :py:func:`.show_dialog`."""
	return show_dialog(Gtk.MessageType.WARNING, *args, **kwargs)

def show_dialog_yes_no(*args, **kwargs):
	"""
	Display a dialog which asks a yes or no question with
	:py:func:`.show_dialog`.

	:return: True if the response is Yes.
	:rtype: bool
	"""
	kwargs['message_buttons'] = Gtk.ButtonsType.YES_NO
	return show_dialog(Gtk.MessageType.QUESTION, *args, **kwargs) == Gtk.ResponseType.YES

class UtilityGladeGObject(object):
	"""
	A base object to wrap GTK widgets loaded from Glade data files. This
	provides a number of convenience methods for managing the main widget
	and child widgets. This class is meant to be subclassed by classes
	representing objects from the Glade data file. The class names must
	be identical to the name of the object they represent in the Glade
	data file.
	"""
	gobject_ids = []
	"""A list of children GObjects to load from the Glade data file."""
	top_level_dependencies = []
	"""Additional top level GObjects to load from the Glade data file."""
	config_prefix = ''
	"""A prefix to be used for keys when looking up value in the :py:attr:`~.UtilityGladeGObject.config`."""
	top_gobject = 'gobject'
	"""The name of the attribute to set a reference of the top level GObject to."""
	def __init__(self, config, parent):
		"""
		:param dict config: The King Phisher client configuration.
		:param parent: The parent window for this object.
		:type parent: :py:class:`Gtk.Window`
		"""
		self.config = config
		"""A reference to the King Phisher client configuration."""
		self.parent = parent
		"""The parent :py:class:`Gtk.Window` instance."""
		self.logger = logging.getLogger('KingPhisher.Client.' + self.__class__.__name__)

		builder = Gtk.Builder()
		self.gtk_builder = builder
		"""A :py:class:`Gtk.Builder` instance used to load Glade data with."""

		glade_file = which_glade()
		builder.add_objects_from_file(glade_file, self.top_level_dependencies + [self.__class__.__name__])
		builder.connect_signals(self)
		gobject = builder.get_object(self.__class__.__name__)
		if isinstance(gobject, Gtk.Window):
			gobject.set_transient_for(self.parent)
		setattr(self, self.top_gobject, gobject)

		self.gobjects = {}
		for gobject_id in self.gobject_ids:
			gobject = self.gtk_builder_get(gobject_id)
			# The following five lines ensure that the types match up, this is
			# primarily to enforce clean development.
			gtype = gobject_id.split('_', 1)[0]
			if gobject == None:
				raise TypeError("gobject {0} could not be found in the glade file".format(gobject_id))
			elif gobject.__class__.__name__.lower() != gtype:
				raise TypeError("gobject {0} is of type {1} expected {2}".format(gobject_id, gobject.__class__.__name__, gtype))
			self.gobjects[gobject_id] = gobject
		self.objects_load_from_config()

	def gtk_builder_get(self, gobject_id):
		"""
		Find the child GObject with name *gobject_id* from the GTK builder.

		:param str gobject_id: The object name to look for.
		:return: The GObject as found by the GTK builder.
		:rtype: :py:class:`GObject.GObject`
		"""
		gtkbuilder_id = "{0}.{1}".format(self.__class__.__name__, gobject_id)
		self.logger.debug('loading GTK builder object with id: ' + gtkbuilder_id)
		return self.gtk_builder.get_object(gtkbuilder_id)

	def objects_load_from_config(self):
		"""
		Iterate through :py:attr:`.gobjects` and set the GObject's value
		from the corresponding value in the :py:attr:`~.UtilityGladeGObject.config`.
		"""
		for gobject_id, gobject in self.gobjects.items():
			gtype, config_name = gobject_id.split('_', 1)
			config_name = self.config_prefix + config_name
			if not gtype in GOBJECT_PROPERTY_MAP or not config_name in self.config:
				continue
			value = self.config[config_name]
			if value == None:
				continue
			if isinstance(GOBJECT_PROPERTY_MAP[gtype], (list, tuple)):
				GOBJECT_PROPERTY_MAP[gtype][0](gobject, value)
			else:
				gobject.set_property(GOBJECT_PROPERTY_MAP[gtype], value)

	def objects_save_to_config(self):
		for gobject_id, gobject in self.gobjects.items():
			gtype, config_name = gobject_id.split('_', 1)
			config_name = self.config_prefix + config_name
			if not gtype in GOBJECT_PROPERTY_MAP:
				continue
			self.config[config_name] = gobject_get_value(gobject, gtype)

class UtilityFileChooser(_Gtk_FileChooserDialog):
	"""Display a file chooser dialog."""
	def __init__(self, *args, **kwargs):
		super(UtilityFileChooser, self).__init__(*args, **kwargs)
		self.parent = self.get_parent_window()

	def quick_add_filter(self, name, patterns):
		"""
		Add a filter for displaying files, this is useful in conjunction
		with :py:meth:`.run_quick_open`.

		:param str name: The name of the filter.
		:param patterns: The pattern(s) to match.
		:type patterns: list, str
		"""
		if not isinstance(patterns, (list, tuple)):
			patterns = (patterns,)
		new_filter = Gtk.FileFilter()
		new_filter.set_name(name)
		for pattern in patterns:
			new_filter.add_pattern(pattern)
		self.add_filter(new_filter)

	def run_quick_open(self):
		"""
		Display a dialog asking a user which file should be opened. The
		value of target_path in the returned dictionary is an absolute path.

		:return: A dictionary with target_uri and target_path keys representing the path choosen.
		:rtype: dict
		"""
		self.set_action(Gtk.FileChooserAction.OPEN)
		self.add_button(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL)
		self.add_button(Gtk.STOCK_OPEN, Gtk.ResponseType.ACCEPT)
		self.show_all()
		response = self.run()
		if response == Gtk.ResponseType.CANCEL:
			return None
		target_path = self.get_filename()
		if not os.access(target_path, os.R_OK):
			show_dialog_error('Can not read the selected file', self.parent)
			return None
		target_uri = self.get_uri()
		return {'target_uri': target_uri, 'target_path': target_path}

	def run_quick_save(self, current_name=None):
		"""
		Display a dialog which asks the user where a file should be saved. The
		value of target_path in the returned dictionary is an absolute path.

		:param set current_name: The name of the file to save.
		:return: A dictionary with target_uri and target_path keys representing the path choosen.
		:rtype: dict
		"""
		self.set_action(Gtk.FileChooserAction.SAVE)
		self.add_button(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL)
		self.add_button(Gtk.STOCK_SAVE, Gtk.ResponseType.ACCEPT)
		self.set_do_overwrite_confirmation(True)
		if current_name:
			self.set_current_name(current_name)
		self.show_all()
		response = self.run()
		if response == Gtk.ResponseType.CANCEL:
			return None
		target_path = self.get_filename()
		if os.path.isfile(target_path):
			if not os.access(target_path, os.W_OK):
				show_dialog_error('Can not write to the selected file', self.parent)
				return None
		elif not os.access(os.path.dirname(target_path), os.W_OK):
			show_dialog_error('Can not create the selected file', self.parent)
			return None
		target_uri = self.get_uri()
		return {'target_uri': target_uri, 'target_path': target_path}

	def run_quick_select_directory(self):
		"""
		Display a dialog which asks the user to select a directory to use. The
		value of target_path in the returned dictionary is an absolute path.

		:return: A dictionary with target_uri and target_path keys representing the path choosen.
		:rtype: dict
		"""
		self.set_action(Gtk.FileChooserAction.SELECT_FOLDER)
		self.add_button(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL)
		self.add_button(Gtk.STOCK_OPEN, Gtk.ResponseType.ACCEPT)
		self.show_all()
		response = self.run()
		if response == Gtk.ResponseType.CANCEL:
			return None
		target_uri = self.get_uri()
		target_path = self.get_filename()
		return {'target_uri': target_uri, 'target_path': target_path}
