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

import logging
import os
import re

from king_phisher import find
from king_phisher import its
from king_phisher import serializers

from gi.repository import GObject
from gi.repository import Gtk
from gi.repository import GtkSource

if its.mocked:
	_GObject_GObject = type('GObject.GObject', (object,), {'__module__': ''})
	_GtkSource_CompletionProvider = type('GtkSource.CompletionProvider', (object,), {'__module__': ''})
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

class CustomCompletionProviderBase(GObject.GObject, GtkSource.CompletionProvider):
	"""
	This class is used to create completion providers that will provide syntax
	completion options and recognize special characters.
	"""
	data_file = None
	"""A JSON encoded data file from which to load completion data."""
	extraction_regex = r''
	"""The regular expression used to match completion string extracted with the :py:attr:`.left_delimiter`."""
	left_delimiter = None
	"""The delimiter used to terminate the left end of the match string."""
	left_delimiter_adjustment = 0
	"""A number of characters to adjust to beyond the delimiter string."""
	left_limit = 512
	"""The maximum number of characters to search backwards for the :py:attr:`.left_delimiter`."""
	name = 'Undefined'
	"""The name of this completion provider as it should appear in the UI."""
	def __init__(self):
		super(CustomCompletionProviderBase, self).__init__()
		self.logger = logging.getLogger('KingPhisher.Client.' + self.__class__.__name__)
		if self.data_file is not None:
			completion_data = find.data_file(os.path.join('completion', self.data_file))
			if completion_data is None:
				raise RuntimeError("failed to find completion data file '{0}'".format(self.data_file))
			self.logger.debug("loading {0} completion data from: {1}".format(self.name, completion_data))
			with open(completion_data, 'r') as file_h:
				completion_data = serializers.JSON.load(file_h)
			self.load_data(completion_data)

	def do_get_name(self):
		return self.name

	def load_data(self, completion_data):
		"""
		When :py:attr:`.CustomCompletionProviderBase.data_file` is defined, this
		function is called on initialization after loading the JSON data encoded
		within it. This method can then be overridden by subclasses to provide
		additional setup and define completion data prior to the class being
		registered as a provider.

		:param completion_data: The arbitrary JSON encoded data contained within the specified file.
		"""
		pass

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
		limit_iter = end_iter.copy()
		if self.left_limit:
			limit_iter.backward_chars(self.left_limit)
		mov_iter = mov_iter.backward_search(self.left_delimiter, Gtk.TextSearchFlags.VISIBLE_ONLY, limit=limit_iter)
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
		Called by GtkSourceCompletion to determine if this provider matches the
		context. This returns true if the :py:meth:`.extract` returns a valid
		match object from the regular expression.

		:param context: The context for the completion.
		:type context: :py:class:`GtkSource.CompletionContext`
		:return: Whether or not the :py:meth:`.extract` method returned a match.
		:rtype: bool
		"""
		return self.extract(context) is not None

	def do_populate(self, context):
		"""
		An automated function called by GtkSource.Completion, when
		:py:meth:`.do_match` returns True. This function is used to provide
		suggested completion words (referred to as proposals) for the context
		based on the match. This is done by creating a list of suggestions and
		adding them with :py:meth:`GtkSource.CompletionContext.add_proposals`.
		If :py:meth:`.extract` returns None, then
		:py:meth:`~.CustomCompletionProviderBase.populate` will not be called.

		:param context: The context for the completion.
		:type context: :py:class:`GtkSource.CompletionContext`
		"""
		match = self.extract(context)
		if match is None:
			# if extract returns none, return here without calling self.populate
			return

		proposals = []
		try:
			matching_suggestions = self.populate(context, match)
		except Exception:
			self.logger.warning('encountered an exception in the completion populate routine', exc_info=True)
			return
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

class HTMLCompletionProvider(CustomCompletionProviderBase):
	"""
	A completion provider which supports HTML5 tags and attributes.
	"""
	data_file = 'html.json'
	"""
	A JSON encoded data file from which to load completion data in the format
	specified in the :ref:`completion-data-html` section.
	"""
	left_delimiter = '<'
	extraction_regex = re.compile(
		r'<(?P<tag>[a-z]+)'
		r'(?P<is_attr>\s+(?:[a-z_]+(=(?P<quote>["\'])(?:(\\.|[^\4])*)\4)?\s+)*(?P<attr>[a-z_]*))?'
		r'$'
	)
	name = 'HTML'
	def load_data(self, completion_data):
		self.html_tags = completion_data

	def populate(self, context, match):
		proposal_terms = []
		tag = match.group('tag')
		if match.group('is_attr'):
			if tag in self.html_tags:
				comp_attr = match.group('attr') or ''
				attrs = (self.html_tags[tag] or []) + ['class', 'id', 'style', 'title']
				proposal_terms = [term for term in attrs if term.startswith(comp_attr)]
				proposal_terms = [(term[:-1], term[:-1] + ' ') if term[-1] == '!' else (term, term + '="') for term in proposal_terms]
		else:
			proposal_terms = [(term, term + ' ') for term in self.html_tags.keys() if term.startswith(tag)]
		return proposal_terms

class JinjaCompletionProvider(CustomCompletionProviderBase):
	"""
	Used as the base completion provider for King Phisher's Jinja2 template
	editing.
	"""
	data_file = 'jinja.json'
	"""
	A JSON encoded data file from which to load completion data in the format
	specified in the :ref:`completion-data-jinja` section.
	"""
	left_delimiter = '{'
	left_delimiter_adjustment = -1
	extraction_regex = re.compile(
		r'.*(?:{{\s*|{%\s+(?:if|elif|for\s+[a-z_]+\s+in)\s+)(?P<var>[a-z_.]+)'
		r'('
		r'(?P<is_test>\s+is\s+(?P<test>[a-z_]+))'
		r'|'
		r'(?P<is_filter>\s*\|\s*(?:[a-z_]+\s*\|\s*)*(?P<filter>[a-z_]*(?!\|)))'
		r')?'
		r'$'
	)
	name = 'Jinja'
	var_context = None
	def load_data(self, completion_data):
		self.jinja_filters = completion_data['global']['filters']
		self.jinja_tests = completion_data['global']['tests']
		self.jinja_tokens = completion_data['global']['tokens']
		if self.var_context is not None:
			context = completion_data['context']
			if not self.var_context in context:
				raise RuntimeError('the specified context is not defined')
			context = context[self.var_context]
			if 'filters' in context:
				self.jinja_filters.extend(context['filters'])
			if 'tests' in context:
				self.jinja_tests.extend(context['tests'])
			if 'tokens' in context:
				self.jinja_tokens.update(context['tokens'])

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
		elif match.group('is_test'):
			jinja_test = match.group('test') or ''
			proposal_terms = [term for term in self.jinja_tests if term.startswith(jinja_test)]
		elif match.group('var'):
			tokens = match.group('var')
			tokens = tokens.split('.')
			proposal_terms = get_proposal_terms(self.jinja_tokens, tokens)
		proposal_terms = [(term.split('(', 1)[0], term) for term in proposal_terms]
		return proposal_terms

class JinjaEmailCompletionProvider(JinjaCompletionProvider):
	"""
	Completion provider for Jinja syntax within an Email.
	"""
	var_context = 'email'

class JinjaPageCompletionProvider(JinjaCompletionProvider):
	"""
	Completion provider for Jinja syntax within a web page.
	"""
	var_context = 'page'
