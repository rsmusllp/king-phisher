#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  king_phisher/client/application.py
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

import copy
import json
import logging
import os
import shutil

from king_phisher import find
from king_phisher import utilities
from king_phisher.client import client
from king_phisher.client import graphs
from king_phisher.client import tools

from gi.repository import GLib
from gi.repository import GObject
from gi.repository import Gtk

CONFIG_FILE_PATH = '~/.king_phisher.json'
"""The default search location for the client configuration file."""

if isinstance(Gtk.Application, utilities.Mock):
	_Gtk_Application = type('Gtk.Application', (object,), {})
	_Gtk_Application.__module__ = ''
else:
	_Gtk_Application = Gtk.Application

class KingPhisherClientApplication(_Gtk_Application):
	def __init__(self, config_file=None):
		super(KingPhisherClientApplication, self).__init__()
		self.logger = logging.getLogger('KingPhisher.Client.Application')
		# print version information for debugging purposes
		self.logger.debug("gi.repository GLib version: {0}".format('.'.join(map(str, GLib.glib_version))))
		self.logger.debug("gi.repository GObject version: {0}".format('.'.join(map(str, GObject.pygobject_version))))
		self.logger.debug("gi.repository Gtk version: {0}.{1}.{2}".format(Gtk.get_major_version(), Gtk.get_minor_version(), Gtk.get_micro_version()))
		if tools.has_vte:
			self.logger.debug("gi.repository VTE version: {0}".format(tools.Vte._version))
		if graphs.has_matplotlib:
			self.logger.debug("matplotlib version: {0}".format(graphs.matplotlib.__version__))
		self.set_property('application-id', 'org.king-phisher.client')
		self.set_property('register-session', True)
		self.config_file = (config_file or CONFIG_FILE_PATH)
		"""The file containing the King Phisher client configuration."""
		self.config = None
		"""The main King Phisher client configuration."""
		try:
			self.load_config(load_defaults=True)
		except Exception:
			self.logger.critical('failed to load the client configuration')
			raise

	def do_activate(self):
		Gtk.Application.do_activate(self)
		win = client.KingPhisherClient(self.config, self)
		win.set_position(Gtk.WindowPosition.CENTER)
		win.show_all()

	def do_shutdown(self):
		Gtk.Application.do_shutdown(self)
		self.save_config()

	def load_config(self, load_defaults=False):
		"""
		Load the client configuration from disk and set the
		:py:attr:`~.KingPhisherClientApplication.config` attribute.

		:param bool load_defaults: Load missing options from the template configuration file.
		"""
		self.logger.info('loading the config from disk')
		config_file = os.path.expanduser(self.config_file)
		client_template = find.find_data_file('client_config.json')
		if not (os.path.isfile(config_file) and os.stat(config_file).st_size):
			shutil.copy(client_template, config_file)
		with open(config_file, 'r') as tmp_file:
			self.config = json.load(tmp_file)
		if load_defaults:
			with open(client_template, 'r') as tmp_file:
				client_template = json.load(tmp_file)
			for key, value in client_template.items():
				if not key in self.config:
					self.config[key] = value

	def save_config(self):
		"""Write the client configuration to disk."""
		self.logger.info('writing the client configuration to disk')
		config = copy.copy(self.config)
		for key in self.config.keys():
			if 'password' in key or key == 'server_config':
				del config[key]
		config_file = os.path.expanduser(self.config_file)
		config_file_h = open(config_file, 'w')
		json.dump(config, config_file_h, sort_keys=True, indent=4)
