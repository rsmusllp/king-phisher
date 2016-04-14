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
import re
import gi
gi.require_version('Gtk', '3.0')
gi.require_version('GtkSource', '3.0')

from gi.repository import GObject
from gi.repository import Gtk
from gi.repository import GtkSource

class CustomCompletionProviderBase(GObject.GObject, GtkSource.CompletionProvider):
	"""
	A custom GtkSource.CompletionProvider
	This class is used to create GtkSource Completion Providers that will provide syntax
	options and recognize special characters according to the defined extraction_regex
	and left delimiter.

	check class that inherits this class must:
	define its own populate function
	and set the following variables
	 - left_delimiter
	 - extraction_regex
	 - name
	"""
	left_delimiter = None
	extraction_regex = ''
	name = 'Undefined'

	def __init__(self):
		super(CustomCompletionProviderBase, self).__init__()

	def do_get_name(self):
		return self.name

	def populate(self, context, match):
		"""
		This must be defined in class that is inheriting CustomCompletionProviderBase
		:param context:
		:type context: :py:class:`GtkSource.CompletionContextClass`
		:param re.MatchObject match: the match from the regex.match()
		"""
		raise NotImplementedError()

	def extract(self, context):
		"""
		Used to extract the text according to the left_delimiter and
		extraction_regex

		:param context:
		:type context: :py:class:`GtkSource.CompletionContextClass`
		:return: re.MatchObject
		"""
		end_iter = context.get_iter()
		if not isinstance(end_iter, Gtk.TextIter):
			_, end_iter = context.get_iter()

		if not end_iter:
			return
		buf = end_iter.get_buffer()
		mov_iter = end_iter.copy()
		if not mov_iter.backward_search(self.left_delimiter, Gtk.TextSearchFlags.VISIBLE_ONLY):
			return
		mov_iter, _ = mov_iter.backward_search(self.left_delimiter, Gtk.TextSearchFlags.VISIBLE_ONLY)
		left_text = buf.get_text(mov_iter, end_iter, True)

		return self.extraction_regex.match(left_text)

	def do_match(self, context):
		"""
		Always return true as though there is a match.
		This is done to reduce the amount of caching occurring.

		:param context:
		:type context: :py:class:`GtkSource.CompletionContextClass`
		:return: True
		"""
		return True

	def do_populate(self, context):
		"""
		An automated function called GtkSource.CompletionClass when a do_match
		is True.

		This function is used to provide suggested completion words for the match

		:param context:
		:type context: :py:class:`GtkSource.CompletionContext`
		:return: a list of GtkSource.CompletionItemClass of suggestions.
		:rtype: list
		"""
		match = self.extract(context)
		if match is None:
			return
		proposals = []
		matching_suggestions = self.populate(match)
		matching_suggestions.sort()
		for suggestion in matching_suggestions:
			if suggestion:
				proposals.append(
					GtkSource.CompletionItem(label=suggestion, text=suggestion)
				)
		context.add_proposals(self, proposals, True)

	def find_match(self, search, match):
		"""
		Used to iterate through the dictionaries of looking for possible matches.

		:param dict search: The Dictionary to iterate through.
		:param List match: string for matching split at any '.' as a list
		:return: A list of words that are a possible match.
		:rtype: list
		"""
		found = search.get(match[0], [])
		if found:
			if match[1:]:
				found = self.find_match(found, match[1:])
		else:
			search_term = match[0]
			found = [term for term in search.keys() if term.startswith(search_term) and term != search_term]
		return found

class JinjaComletionProvider(CustomCompletionProviderBase):
	"""
	Used as the base GtkSource.CompletionProviderClass for
	King Phisher's template editing.
	"""
	left_delimiter = '{{'
	extraction_regex = re.compile(r'{{\s*([a-z_.]+)$')
	name = 'Jinja'
	__common_jinja_vars = {
		'time': {
			'local': None,
			'utc': None
		},
		'version': None,
		'random_integer': None,
		'parse_user_agent': None,
	}
	jinja_vars = {}

	def __init__(self, *args, **kwargs):
		"""
		Used to init the super class and update the Jinja Dictionary.
		:param args:
		:param kwargs:
		"""
		super(JinjaComletionProvider, self).__init__(*args, **kwargs)
		self.jinja_vars.update(self.__common_jinja_vars)

	def populate(self, match):
		"""
		Utilizes the match from the regex check to see if there
		is a possible match in the dictionary, then returns
		the suggests to from the match to be populated.

		:param match: The matching object.
		:types match: `re.MatchObject`
		:return: List of strings to for population.
		:rtype: list
		"""
		matching = match.group(1)
		if '.' in matching:
			split_match = matching.split('.')
			sug_words = self.find_match(self.jinja_vars, split_match)
		else:
			sug_words = self.find_match(self.jinja_vars, [matching])
		return sug_words

class JinjaEmailCompletionProvider(JinjaComletionProvider):
	"""
	Class used to update the Jinja base completion provider.
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
		'inline_image': None,
	}

class JinjaPageComletionProvider(JinjaComletionProvider):
	"""
	Class used to update the Jinja base completion provider.
	"""
	name = 'Jinja Page'
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
