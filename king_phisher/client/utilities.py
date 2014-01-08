#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  king_phisher/client/utilities.py
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

import contextlib
import logging
import os
import threading

from gi.repository import GLib
from gi.repository import GObject
from gi.repository import Gtk

GOBJECT_PROPERTY_MAP = {
	'combobox': (
		lambda c, v: c.set_active_iter(search_list_store(c.get_model(), v)),
		lambda c: c.get_model().get_value(c.get_active_iter(), 0)
	),
	'entry': 'text',
	'spinbutton': 'value',
	'checkbutton': 'active',
	'textview': (
		lambda t, v: t.get_buffer().set_text(v),
		lambda t: t.get_buffer().get_text(t.get_buffer().get_start_iter(), t.get_buffer().get_end_iter(), False)
	),
}

def get_gobject_value(gobject, gtype = None):
	gtype = (gtype or gobject.__class__.__name__)
	gtype = gtype.lower()
	if isinstance(GOBJECT_PROPERTY_MAP[gtype], (list, tuple)):
		value = GOBJECT_PROPERTY_MAP[gtype][1](gobject)
	else:
		value = gobject.get_property(GOBJECT_PROPERTY_MAP[gtype])
	return value

DEFAULT_GLADE_PATH = '/usr/share:/usr/local/share:data/client:.'
def which_glade(glade):
	is_readable = lambda gpath: (os.path.isfile(gpath) and os.access(gpath, os.R_OK))
	glade_path = os.environ.get('GLADE_PATH', DEFAULT_GLADE_PATH)
	for path in glade_path.split(os.pathsep):
		path = path.strip('"')
		glade_file = os.path.join(path, glade)
		if is_readable(glade_file):
			return glade_file
	return None

def which(program):
	is_exe = lambda fpath: (os.path.isfile(fpath) and os.access(fpath, os.X_OK))
	for path in os.environ["PATH"].split(os.pathsep):
		path = path.strip('"')
		exe_file = os.path.join(path, program)
		if is_exe(exe_file):
			return exe_file
	return None

def gtk_sync():
	while Gtk.events_pending():
		Gtk.main_iteration()

@contextlib.contextmanager
def gtk_signal_blocked(gobject, signal_name):
	signal_id = GObject.signal_lookup(signal_name, gobject.__class__)
	handler_id = GObject.signal_handler_find(gobject, GObject.SignalMatchType.ID, signal_id, 0, None, 0, 0)
	GObject.signal_handler_block(gobject, handler_id)
	yield
	GObject.signal_handler_unblock(gobject, handler_id)

def glib_idle_add_wait(function, *args):
	gsource_completed = threading.Event()
	def wrapper():
		function(*args)
		gsource_completed.set()
	GLib.idle_add(wrapper)
	gsource_completed.wait()

def search_list_store(list_store, value):
	for row in list_store:
		if row[0] == value:
			return row.iter
	return None

def server_parse(server, default_port):
	server = server.split(':')
	host = server[0]
	if len(server) == 1:
		return (host, default_port)
	else:
		port = server[1]
		if not port:
			port = default_port
		else:
			port = int(port)
		return (host, port)

def show_dialog(message_type, message, parent, secondary_text = None, message_buttons = Gtk.ButtonsType.OK):
	dialog = Gtk.MessageDialog(parent, Gtk.DialogFlags.DESTROY_WITH_PARENT, message_type, message_buttons, message)
	if secondary_text:
		dialog.format_secondary_text(secondary_text)
	dialog.show_all()
	response = dialog.run()
	dialog.destroy()
	return response

def show_dialog_error(*args, **kwargs):
	return show_dialog(Gtk.MessageType.ERROR, *args, **kwargs)

def show_dialog_info(*args, **kwargs):
	return show_dialog(Gtk.MessageType.INFO, *args, **kwargs)

def show_dialog_warning(*args, **kwargs):
	return show_dialog(Gtk.MessageType.WARNING, *args, **kwargs)

def show_dialog_yes_no(*args, **kwargs):
	kwargs['message_buttons'] = Gtk.ButtonsType.YES_NO
	return show_dialog(Gtk.MessageType.QUESTION, *args, **kwargs) == Gtk.ResponseType.YES

class UtilityGladeGObject(object):
	gobject_ids = [ ]
	top_level_dependencies = [ ]
	config_prefix = ''
	top_gobject = 'gobject'
	def __init__(self, config, parent):
		self.config = config
		self.parent = parent
		self.logger = logging.getLogger('KingPhisher.Client.' + self.__class__.__name__)

		builder = Gtk.Builder()
		self.gtk_builder = builder

		glade_file = which_glade(os.environ['GLADE_FILE'])
		builder.add_objects_from_file(glade_file, self.top_level_dependencies + [self.__class__.__name__])
		builder.connect_signals(self)
		gobject = builder.get_object(self.__class__.__name__)
		if isinstance(gobject, Gtk.Window):
			gobject.set_transient_for(self.parent)
		setattr(self, self.top_gobject, gobject)

		self.gobjects = {}
		for gobject_id in self.gobject_ids:
			gobject = self.gtk_builder_get(gobject_id)
			# The following three lines ensure that the types match up, this is
			# primarily to enforce clean development.
			gtype = gobject_id.split('_', 1)[0]
			if gobject == None:
				raise TypeError("gobject {0} could not be found in the glade file".format(gtkbuilder_id))
			elif gobject.__class__.__name__.lower() != gtype:
				raise TypeError("gobject {0} is of type {1} expected {2}".format(gtkbuilder_id, gobject.__class__.__name__, gtype))
			self.gobjects[gobject_id] = gobject
		self.objects_load_from_config()

	def gtk_builder_get(self, gobject_id):
		gtkbuilder_id = "{0}.{1}".format(self.__class__.__name__, gobject_id)
		self.logger.debug('loading GTK builder object with id: ' + gtkbuilder_id)
		return self.gtk_builder.get_object(gtkbuilder_id)

	def objects_load_from_config(self):
		for gobject_id, gobject in self.gobjects.items():
			gtype, config_name = gobject_id.split('_', 1)
			config_name = self.config_prefix + config_name
			if not gtype in GOBJECT_PROPERTY_MAP or not config_name in self.config:
				continue
			value = self.config[config_name]
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
			self.config[config_name] = get_gobject_value(gobject, gtype)

class UtilityFileChooser(Gtk.FileChooserDialog):
	def __init__(self, *args, **kwargs):
		super(UtilityFileChooser, self).__init__(*args, **kwargs)

	def run_quick_save(self, current_name = None):
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
		target_uri = self.get_uri()
		target_filename = self.get_filename()
		return {'target_uri':target_uri, 'target_filename':target_filename}

	def quick_add_filter(self, name, patterns):
		if not isinstance(patterns, (list, tuple)):
			patterns = (patterns,)
		new_filter = Gtk.FileFilter()
		new_filter.set_name(name)
		for pattern in patterns:
			new_filter.add_pattern(pattern)
		self.add_filter(new_filter)

	def run_quick_open(self):
		self.set_action(Gtk.FileChooserAction.OPEN)
		self.add_button(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL)
		self.add_button(Gtk.STOCK_OPEN, Gtk.ResponseType.ACCEPT)
		self.show_all()
		response = self.run()
		if response == Gtk.ResponseType.CANCEL:
			return None
		target_uri = self.get_uri()
		target_filename = self.get_filename()
		return {'target_uri':target_uri, 'target_filename':target_filename}
