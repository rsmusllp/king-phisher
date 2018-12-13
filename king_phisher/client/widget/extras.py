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
import datetime
import logging
import os

from king_phisher import its
from king_phisher import templates
from king_phisher import utilities
from king_phisher.client import gui_utilities

import boltons.strutils
import jinja2
import markdown
import mdx_partial_gfm
from gi.repository import Gdk
from gi.repository import GObject
from gi.repository import Gtk

try:
	from gi.repository import WebKit2 as WebKitX
	has_webkit2 = True
except ImportError:
	from gi.repository import WebKit as WebKitX
	has_webkit2 = False

if its.mocked:
	_Gtk_CellRendererText = type('Gtk.CellRendererText', (object,), {'__module__': ''})
	_Gtk_FileChooserDialog = type('Gtk.FileChooserDialog', (object,), {'__module__': ''})
	_Gtk_Frame = type('Gtk.Frame', (object,), {'__module__': ''})
	_WebKitX_WebView = type('WebKitX.WebView', (object,), {'__module__': ''})
else:
	_Gtk_CellRendererText = Gtk.CellRendererText
	_Gtk_FileChooserDialog = Gtk.FileChooserDialog
	_Gtk_Frame = Gtk.Frame
	_WebKitX_WebView = WebKitX.WebView

################################################################################
# Cell renderers
################################################################################
class CellRendererPythonText(_Gtk_CellRendererText):
	python_value = GObject.Property(type=object, flags=GObject.ParamFlags.READWRITE)
	__gtype_name__ = 'CellRendererPythonText'
	def __init__(self, *args, **kwargs):
		Gtk.CellRendererText.__init__(self, *args, **kwargs)

	def do_render(self, *args, **kwargs):
		value = self.render_python_value(self.get_property('python-value'))
		value = '' if value is None else str(value)
		self.set_property('text', value)
		Gtk.CellRendererText.do_render(self, *args, **kwargs)

class CellRendererBytes(CellRendererPythonText):
	"""A custom :py:class:`Gtk.CellRendererText` to render numeric values representing bytes."""
	python_value = GObject.Property(type=int, flags=GObject.ParamFlags.READWRITE)
	@staticmethod
	def render_python_value(value):
		if isinstance(value, int):
			return boltons.strutils.bytes2human(value, 1)

class CellRendererDatetime(CellRendererPythonText):
	format = GObject.Property(type=str, flags=GObject.ParamFlags.READWRITE, default=utilities.TIMESTAMP_FORMAT)
	def render_python_value(self, value):
		if isinstance(value, datetime.datetime):
			return value.strftime(self.props.format)

class CellRendererInteger(CellRendererPythonText):
	"""A custom :py:class:`Gtk.CellRendererText` to render numeric values with comma separators."""
	python_value = GObject.Property(type=int, flags=GObject.ParamFlags.READWRITE)
	@staticmethod
	def render_python_value(value):
		if isinstance(value, int):
			return "{:,}".format(value)

################################################################################
# Column definitions
################################################################################
class ColumnDefinitionBase(object):
	__slots__ = ('title', 'width')
	cell_renderer = g_type = python_type = sort_function = None
	def __init__(self, title, width):
		self.title = title
		self.width = width

	@property
	def name(self):
		return self.title.lower().replace(' ', '_')

class ColumnDefinitionBytes(ColumnDefinitionBase):
	cell_renderer = CellRendererBytes()
	g_type = python_type = int
	def __init__(self, title, width=25):
		super(ColumnDefinitionBytes, self).__init__(title, width)

class ColumnDefinitionDatetime(ColumnDefinitionBase):
	cell_renderer = CellRendererDatetime()
	g_type = object
	python_type = datetime.datetime
	sort_function = staticmethod(gui_utilities.gtk_treesortable_sort_func)
	def __init__(self, title, width=25):
		super(ColumnDefinitionDatetime, self).__init__(title, width)

class ColumnDefinitionInteger(ColumnDefinitionBase):
	cell_renderer = CellRendererInteger()
	g_type = python_type = int
	def __init__(self, title, width=15):
		super(ColumnDefinitionInteger, self).__init__(title, width)

class ColumnDefinitionString(ColumnDefinitionBase):
	cell_renderer = Gtk.CellRendererText()
	g_type = python_type = str
	def __init__(self, title, width=30):
		super(ColumnDefinitionString, self).__init__(title, width)

################################################################################
# Miscellaneous
################################################################################
class FileChooserDialog(_Gtk_FileChooserDialog):
	"""Display a file chooser dialog with additional convenience methods."""
	def __init__(self, title, parent, **kwargs):
		"""
		:param str title: The title for the file chooser dialog.
		:param parent: The parent window for the dialog.
		:type parent: :py:class:`Gtk.Window`
		"""
		utilities.assert_arg_type(parent, Gtk.Window, arg_pos=2)
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
			gui_utilities.show_dialog_error('Permissions Error', self.parent, 'Can not read the selected file.')
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
				gui_utilities.show_dialog_error('Permissions Error', self.parent, 'Can not write to the selected file.')
				return None
		elif not os.access(os.path.dirname(target_path), os.W_OK):
			gui_utilities.show_dialog_error('Permissions Error', self.parent, 'Can not write to the selected path.')
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

class MultilineEntry(_Gtk_Frame):
	"""
	A custom entry widget which can be styled to look like
	:py:class:`Gtk.Entry` but accepts multiple lines of input.
	"""
	__gproperties__ = {
		'text': (str, 'text', 'The contents of the entry.', '', GObject.ParamFlags.READWRITE),
		'text-length': (int, 'text-length', 'The length of the text in the GtkEntry.', 0, 0xffff, 0, GObject.ParamFlags.READABLE)
	}
	__gtype_name__ = 'MultilineEntry'
	def __init__(self, *args, **kwargs):
		Gtk.Frame.__init__(self, *args, **kwargs)
		self.get_style_context().add_class('multilineentry')
		textview = Gtk.TextView()
		self.add(textview)

	def do_get_property(self, prop):
		textview = self.get_child()
		if prop.name == 'text':
			buffer = textview.get_buffer()
			return buffer.get_text(buffer.get_start_iter(), buffer.get_end_iter(), False)
		elif prop.name == 'text-length':
			return 0
		raise AttributeError('unknown property: ' + prop.name)

	def do_set_property(self, prop, value):
		textview = self.get_child()
		if prop.name == 'text':
			textview.get_buffer().set_text(value)
		elif prop.name == 'text-length':
			raise ValueError('read-only property: ' + prop.name)
		else:
			raise AttributeError('unknown property: ' + prop.name)

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
	template_env = templates.TemplateEnvironmentBase(loader=templates.FindFileSystemLoader())
	"""
	The :py:class:`~king_phisher.templates.TemplateEnvironmentBase` instance to
	use when rendering template content. The environment uses the
	:py:class:`~king_phisher.templates.FindFileSystemLoader` loader.
	"""
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
			if html_file_uri is None:
				html_file_uri = 'file://' + os.getcwd()
			self.load_string(html_data, 'text/html', 'UTF-8', html_file_uri)

	def load_html_file(self, html_file):
		"""
		Load arbitrary HTML data from a file into the WebKit engine to be
		rendered.

		:param str html_file: The path to the file to load HTML data from.
		"""
		with codecs.open(html_file, 'r', encoding='utf-8') as file_h:
			html_data = file_h.read()
		self.load_html_data(html_data, html_file)

	def load_markdown_data(self, md_data, html_file_uri=None, gh_flavor=True, template=None, template_vars=None):
		"""
		Load markdown data, render it into HTML and then load it in to the
		WebKit engine. When *gh_flavor* is enabled, the markdown data is
		rendered using partial GitHub flavor support as provided by
		:py:class:`~mdx_partial_gfm.PartialGithubFlavoredMarkdownExtension`. If
		*template* is specified, it is used to load a Jinja2 template using
		:py:attr:`.template_env` into which the markdown data is passed in the
		variable ``markdown`` along with any others specified in the
		*template_vars* dictionary.

		:param str md_data: The markdown data to render into HTML for displaying.
		:param str html_file_uri: The URI of the file where the HTML data came from.
		:param bool gh_flavor: Whether or not to enable partial GitHub markdown syntax support.
		:param str template: The name of a Jinja2 HTML template to load for hosting the rendered markdown.
		:param template_vars: Additional variables to pass to the Jinja2 :py:class:`~jinja2.Template` when rendering it.
		:return:
		"""
		extensions = []
		if gh_flavor:
			extensions = [mdx_partial_gfm.PartialGithubFlavoredMarkdownExtension()]
		md_data = markdown.markdown(md_data, extensions=extensions)
		if template:
			template = self.template_env.get_template(template)
			template_vars = template_vars or {}
			template_vars['markdown'] = jinja2.Markup(md_data)
			html = template.render(template_vars)
		else:
			html = md_data
		return self.load_html_data(html, html_file_uri=html_file_uri)

	def load_markdown_file(self, md_file, **kwargs):
		"""
		Load markdown data from a file and render it using
		:py:meth:`~.load_markdown_data`.

		:param str md_file: The path to the file to load markdown data from.
		:param kwargs: Additional keyword arguments to pass to :py:meth:`~.load_markdown_data`.
		"""
		with codecs.open(md_file, 'r', encoding='utf-8') as file_h:
			md_data = file_h.read()
		return self.load_markdown_data(md_data, md_file, **kwargs)

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
