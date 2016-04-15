#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  king_phisher/client/widget/completion_providers.py
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

import re

from king_phisher import utilities

from gi.repository import GObject
from gi.repository import Gtk
from gi.repository import GtkSource

if isinstance(Gtk.Widget, utilities.Mock):
	_GObject_GObject = type('GObject.GObject', (object,), {})
	_GObject_GObject.__module__ = ''
	_GtkSource_CompletionProvider = type('GtkSource.CompletionProvider', (object,), {})
	_GtkSource_CompletionProvider.__module__ = ''
else:
	_GObject_GObject = GObject.GObject
	_GtkSource_CompletionProvider = GtkSource.CompletionProvider

def get_proposal_terms(search, tokens):
	"""
	Used to iterate through the *search* dictionary definition representing
	tokens for completion. Terms within this dictionary have a hierarchy to
	their definition in which keys are always terms represented as strings and
	values are either sub-dictionaries following the same pattern or None in the
	case that the term is a leaf node.

	:param dict search: The dictionary to iterate through looking for proposals.
	:param tokens: List of tokens split on the hierarchy delimiter.
	:type tokens: list, str
	:return: A list of strings to be used for completion proposals.
	:rtype: list
	"""
	if isinstance(tokens, str):
		tokens = [tokens]
	found = search.get(tokens[0], {})
	if found:
		if tokens[1:]:
			found = get_proposal_terms(found, tokens[1:])
		else:
			found = []
	else:
		token_0 = tokens[0]
		found = [term for term in search.keys() if term.startswith(token_0) and term != token_0]
	return found

class CustomCompletionProviderBase(_GObject_GObject, _GtkSource_CompletionProvider):
	"""
	This class is used to create GtkSource Completion Providers that will
	provide syntax completion options and recognize special characters according
	to the defined extraction_regex and left delimiter.
	"""
	extraction_regex = r''
	"""The regular expression used to match completion string extracted with the :py:attr:`.left_delimiter`."""
	left_delimiter = None
	"""The delimiter used to terminate the left end of the match string."""
	left_delimiter_adjustment = 0
	"""A number of characters to adjust to beyond the delimiter string."""
	name = 'Undefined'
	"""The name of this completion provider as it should appear in the UI."""
	def __init__(self):
		super(CustomCompletionProviderBase, self).__init__()

	def do_get_name(self):
		return self.name

	def populate(self, context, match):
		"""
		This is called when the :py:attr:`.extraction_regex` returns a match.
		Subclasses must then use this opportunity to populate the *context* with
		proposals.

		:param context: The context for the completion.
		:type context: :py:class:`GtkSource.CompletionContext`
		:param match: The resulting match from the :py:attr:`.extraction_regex`.
		:type match: :py:class:`re.MatchObject`
		"""
		raise NotImplementedError()

	def extract(self, context):
		"""
		Used to extract the text according to the :py:attr:`.left_delimiter` and
		:py:attr:`.extraction_regex`. If the extraction regular expression does
		not match, None is returned.

		:param context: The context for the completion.
		:type context: :py:class:`GtkSource.CompletionContext`
		:return: The resulting match from the :py:attr:`.extraction_regex`.
		:rtype: :py:class:`re.MatchObject`
		"""
		end_iter = context.get_iter()
		if not isinstance(end_iter, Gtk.TextIter):
			_, end_iter = context.get_iter()

		if not end_iter:
			return
		buf = end_iter.get_buffer()
		mov_iter = end_iter.copy()
		mov_iter = mov_iter.backward_search(self.left_delimiter, Gtk.TextSearchFlags.VISIBLE_ONLY)
		if not mov_iter:
			return
		mov_iter, _ = mov_iter
		if self.left_delimiter_adjustment > 0:
			mov_iter.forward_chars(self.left_delimiter_adjustment)
		elif self.left_delimiter_adjustment < 0:
			mov_iter.backward_chars(abs(self.left_delimiter_adjustment))
		left_text = buf.get_text(mov_iter, end_iter, True)

		return self.extraction_regex.match(left_text)

	def do_match(self, context):
		"""
		Called by GtkSourceCompletion when text is typed. Always return true as
		though there is a match. This is done to eliminate the need to cache the
		text which is extracted and matched against a regular expression from
		the context.

		:param context: The context for the completion.
		:type context: :py:class:`GtkSource.CompletionContext`
		:return: Always true to cause :py:meth:`.do_populate` to be called.
		:rtype: bool
		"""
		return True

	def do_populate(self, context):
		"""
		An automated function called by GtkSource.Completion, when
		:py:meth:`.do_match` returns True. This function is used to provide
		suggested completion words (referred to as proposals) for the context
		based on the match. This is done by creating a list of suggestions and
		adding them with :py:meth:`GtkSource.CompletionContext.add_proposals`.
		If :py:meth:`.extract` returns None, then :py:meth:`.populate` will not
		be called.

		:param context: The context for the completion.
		:type context: :py:class:`GtkSource.CompletionContext`
		"""
		match = self.extract(context)
		if match is None:
			# if extract returns none, return here without calling self.populate
			return

		proposals = []
		matching_suggestions = self.populate(context, match)
		matching_suggestions.sort()
		for suggestion in matching_suggestions:
			if not suggestion:
				continue
			if isinstance(suggestion, str):
				item = GtkSource.CompletionItem(label=suggestion, text=suggestion)
			else:
				item = GtkSource.CompletionItem(label=suggestion[0], text=suggestion[1])
			proposals.append(item)
		context.add_proposals(self, proposals, True)

class JinjaComletionProvider(CustomCompletionProviderBase):
	"""
	Used as the base GtkSource.CompletionProviderClass for
	King Phisher's template editing.
	"""
	left_delimiter = '{'
	left_delimiter_adjustment = -1
	extraction_regex = re.compile(r'.*(?:{{\s*|{%\s+(?:if|elif|for\s+[a-z_]+\s+in)\s+)(?P<var>[a-z_.]+)(?P<is_filter>\s*\|\s*(?P<filter>[a-z_]+)?)?$')
	name = 'Jinja'
	__common_jinja_vars = {
		'time': {
			'local': None,
			'utc': None
		},
		'version': None,
		'random_integer(': None,
		'parse_user_agent(': None,
	}
	jinja_filters = [
		# stock jinja2 filters
		'abs',
		'attr(',
		'batch(',
		'capitalize',
		'center',
		'default',
		'dictsort',
		'escape',
		'filesizeformat',
		'first',
		'float',
		'forceescape',
		'format(',
		'groupby(',
		'indent',
		'int',
		'join',
		'last',
		'length',
		'list',
		'lower',
		'map(',
		'pprint',
		'random',
		'replace(',
		'reverse',
		'round',
		'safe',
		'slice(',
		'sort',
		'string',
		'striptags',
		'sum',
		'title',
		'trim',
		'trunscate',
		'upper',
		'urlencode',
		'urlize',
		'wordcount',
		'wordwrap',
		'xmlattr',
		# date / time filters
		'strftime(',
		'timedelta(',
		'tomorrow',
		'next_week',
		'next_month',
		'next_year',
		'yesterday',
		'last_week',
		'last_month',
		'last_year',
		# misc string filters
		'cardinalize',
		'ordinalize',
		'pluralize',
		'singularize',
		'possessive',
	]
	jinja_vars = {}

	def __init__(self, *args, **kwargs):
		"""
		Used to init the super class and update the jinja dictionary,
		form any inheriting sub classes.

		:param args:
		:param kwargs:
		"""
		super(JinjaComletionProvider, self).__init__(*args, **kwargs)
		self.jinja_vars.update(self.__common_jinja_vars)

	def populate(self, context, match):
		"""
		Utilizes the match from the regular expression check to check for
		possible matches of :py:attr:`.jinja_vars`.

		:param context: The context for the completion.
		:type context: :py:class:`GtkSource.CompletionContext`
		:param match: The matching object.
		:types match: `re.MatchObject`
		:return: List of strings to be used for creation of proposals.
		:rtype: list
		"""
		proposal_terms = []
		if match.group('is_filter'):
			jinja_filter = match.group('filter') or ''
			proposal_terms = [term for term in self.jinja_filters if term.startswith(jinja_filter)]
		else:
			tokens = match.group('var')
			tokens = tokens.split('.')
			proposal_terms = get_proposal_terms(self.jinja_vars, tokens)
		proposal_terms = [(term.split('(', 1)[0], term) for term in proposal_terms]
		return proposal_terms

class JinjaEmailCompletionProvider(JinjaComletionProvider):
	"""
	Completion provider for Jinja syntax within an Email.
	"""
	jinja_vars = {
		'calendar_invite': {
			'all_day': None,
			'location': None,
			'start': None,
			'summary': None,
		},
		'client': {
			'company_name': None,
			'email_adress': None,
			'first_name': None,
			'last_name': None,
			'message_id': None,
		},
		'message_type': None,
		'sender': {
			'email': None,
			'friendly_alias': None,
			'reply_to': None,
		},
		'url': {
			'tracking_dot': None,
			'webserver': None,
			'webserver_raw': None,
		},
		'tracking_dot_image_tag': None,
		'uid': None,
		'inline_image(': None,
	}

class JinjaPageComletionProvider(JinjaComletionProvider):
	"""
	Completion provider for Jinja syntax within a web page.
	"""
	jinja_vars = {
		'client': {
			'address': None,
			'email_adress': None,
			'first_name': None,
			'last_name': None,
			'message_id': None,
			'company': {
				'name': None,
				'url_email': None,
				'url_main': None,
				'url_remote_access': None,
			},
			'is_trained': None,
			'visit_count': None,
			'visit_id': None,
		},
		'request': {
			'command': None,
			'cookies': None,
			'parameters': None,
			'user_agent': None,
		},
		'server': {
			'address': None,
			'hostname': None,
		}
	}
