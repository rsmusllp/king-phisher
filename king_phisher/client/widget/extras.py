#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  king_phisher/client/widget/extras.py
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

import codecs
import logging
import os

from king_phisher import utilities
from king_phisher.client import gui_utilities

import boltons.strutils
from gi.repository import Gdk
from gi.repository import GObject
from gi.repository import Gtk

try:
	from gi.repository import WebKit2 as WebKitX
	has_webkit2 = True
except ImportError:
	from gi.repository import WebKit as WebKitX
	has_webkit2 = False

if isinstance(Gtk.Widget, utilities.Mock):
	_Gtk_CellRendererText = type('Gtk.CellRendererText', (object,), {'__module__': ''})
	_Gtk_FileChooserDialog = type('Gtk.FileChooserDialog', (object,), {'__module__': ''})
	_WebKitX_WebView = type('WebKitX.WebView', (object,), {'__module__': ''})
else:
	_Gtk_CellRendererText = Gtk.CellRendererText
	_Gtk_FileChooserDialog = Gtk.FileChooserDialog
	_WebKitX_WebView = WebKitX.WebView

class CellRendererBytes(_Gtk_CellRendererText):
	"""A custom :py:class:`Gtk.CellRendererText` to render numeric values representing bytes."""
	def do_render(self, *args, **kwargs):
		original = self.get_property('text')
		if original.isdigit():
			self.set_property('text', boltons.strutils.bytes2human(int(original), 1))
		Gtk.CellRendererText.do_render(self, *args, **kwargs)

class FileChooserDialog(_Gtk_FileChooserDialog):
	"""Display a file chooser dialog with additional convenience methods."""
	def __init__(self, title, parent, **kwargs):
		"""
		:param str title: The title for the file chooser dialog.
		:param parent: The parent window for the dialog.
		:type parent: :py:class:`Gtk.Window`
		"""
		assert isinstance(parent, Gtk.Window)
		super(FileChooserDialog, self).__init__(title, parent, **kwargs)
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

		:return: A dictionary with target_uri and target_path keys representing the path chosen.
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
			gui_utilities.show_dialog_error('Can not read the selected file', self.parent)
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
				gui_utilities.show_dialog_error('Can not write to the selected file', self.parent)
				return None
		elif not os.access(os.path.dirname(target_path), os.W_OK):
			gui_utilities.show_dialog_error('Can not create the selected file', self.parent)
			return None
		target_uri = self.get_uri()
		return {'target_uri': target_uri, 'target_path': target_path}

	def run_quick_select_directory(self):
		"""
		Display a dialog which asks the user to select a directory to use. The
		value of target_path in the returned dictionary is an absolute path.

		:return: A dictionary with target_uri and target_path keys representing the path chosen.
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

class WebKitHTMLView(_WebKitX_WebView):
	"""
	A WebView widget with additional convenience methods for rendering simple
	HTML content from either files or strings. If a link is opened within the
	document, the webview will emit the 'open-uri' signal instead of navigating
	to it.
	"""
	__gsignals__ = {
		'open-remote-uri': (GObject.SIGNAL_RUN_FIRST, None, (str, (WebKitX.NavigationPolicyDecision if has_webkit2 else WebKitX.WebPolicyDecision)))
	}

	def __init__(self):
		super(WebKitHTMLView, self).__init__()
		self.logger = logging.getLogger('KingPhisher.Client.' + self.__class__.__name__)

		if has_webkit2:
			self.get_context().set_cache_model(WebKitX.CacheModel.DOCUMENT_VIEWER)
			self.connect('decide-policy', self.signal_decide_policy)
		else:
			self.connect('navigation-policy-decision-requested', self.signal_decide_policy_webkit)

		self.connect('button-press-event', self.signal_button_pressed)

	def do_open_remote_uri(self, uri, decision):
		self.logger.debug('received request to open uri: ' + uri)

	def load_html_data(self, html_data, html_file_uri=None):
		"""
		Load arbitrary HTML data into the WebKit engine to be rendered.

		:param str html_data: The HTML data to load into WebKit.
		:param str html_file_uri: The URI of the file where the HTML data came from.
		"""
		if isinstance(html_file_uri, str) and not html_file_uri.startswith('file://'):
			html_file_uri = 'file://' + html_file_uri

		if has_webkit2:
			self.load_html(html_data, html_file_uri)
		else:
			self.load_string(html_data, 'text/html', 'UTF-8', html_file_uri)

	def load_html_file(self, html_file):
		with codecs.open(html_file, 'r', encoding='utf-8') as file_h:
			html_data = file_h.read()
		self.load_html_data(html_data, html_file)

	def signal_button_pressed(self, _, event):
		if event.button == Gdk.BUTTON_SECONDARY:
			# disable right click altogether
			return True

	# webkit2 signal handler
	def signal_decide_policy(self, _, decision, decision_type):
		if decision_type == WebKitX.PolicyDecisionType.NAVIGATION_ACTION:
			uri_request = decision.get_request()
			uri = uri_request.get_uri()
			if uri.startswith('file:'):
				decision.use()
			else:
				decision.ignore()
				self.emit('open-remote-uri', uri, decision)

	# webkit signal handler
	def signal_decide_policy_webkit(self, view, frame, request, action, policy):
		uri = request.get_uri()
		if uri.startswith('file://'):
			policy.use()
		else:
			policy.ignore()
			self.emit('open-remote-uri', uri, policy)
