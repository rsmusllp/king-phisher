#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  king_phisher/templates.py
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

import base64
import codecs
import datetime
import hashlib
import html
import json
import logging
import os
import random
import re

from king_phisher import find
from king_phisher import its
from king_phisher import ua_parser
from king_phisher import utilities
from king_phisher import version

import boltons.strutils
import jinja2
import requests
import requests.exceptions
import requests_file

__all__ = ('FindFileSystemLoader', 'TemplateEnvironmentBase', 'MessageTemplateEnvironment')

class FindFileSystemLoader(jinja2.BaseLoader):
	"""
	A :py:class:`~jinja2.BaseLoader` which loads templates by name from the file
	system. Templates are searched for using the
	:py:func:`~king_phisher.find.data_file` function.
	"""
	def get_source(self, environment, template):
		template_path = find.data_file(template, os.R_OK)
		if template_path is None:
			raise jinja2.TemplateNotFound(template)
		mtime = os.path.getmtime(template_path)
		with codecs.open(template_path, 'r', encoding='utf-8') as file_h:
			source = file_h.read()
		return source, template_path, lambda: mtime == os.path.getmtime(template_path)

class TemplateEnvironmentBase(jinja2.Environment):
	"""
	A configured Jinja2 :py:class:`~jinja2.Environment` with additional filters
	and default settings.
	"""
	def __init__(self, loader=None, global_vars=None):
		"""
		:param loader: The loader to supply to the environment.
		:type loader: :py:class:`jinja2.BaseLoader`
		:param dict global_vars: Additional global variables for the environment.
		"""
		self.logger = logging.getLogger('KingPhisher.TemplateEnvironment')
		autoescape = jinja2.select_autoescape(['html', 'htm', 'xml'], default_for_string=False)
		extensions = ['jinja2.ext.autoescape', 'jinja2.ext.do']
		super(TemplateEnvironmentBase, self).__init__(autoescape=autoescape, extensions=extensions, loader=loader, trim_blocks=True)

		# misc. string filters
		self.filters['cardinalize'] = boltons.strutils.cardinalize
		self.filters['ordinalize'] = boltons.strutils.ordinalize
		self.filters['pluralize'] = boltons.strutils.pluralize
		self.filters['singularize'] = boltons.strutils.singularize
		self.filters['possessive'] = lambda word: word + ('\'' if word.endswith('s') else '\'s')
		self.filters['encode'] = self._filter_encode
		self.filters['decode'] = self._filter_decode
		self.filters['hash'] = self._filter_hash
		# counter part to https://jinja.readthedocs.io/en/stable/templates.html#tojson
		self.filters['fromjson'] = self._filter_json

		# time filters
		self.filters['strftime'] = self._filter_strftime
		self.filters['timedelta'] = self._filter_timedelta
		self.filters['tomorrow'] = lambda dt: dt + datetime.timedelta(days=1)
		self.filters['next_week'] = lambda dt: dt + datetime.timedelta(weeks=1)
		self.filters['next_month'] = lambda dt: dt + datetime.timedelta(days=30)
		self.filters['next_year'] = lambda dt: dt + datetime.timedelta(days=365)
		self.filters['yesterday'] = lambda dt: dt + datetime.timedelta(days=-1)
		self.filters['last_week'] = lambda dt: dt + datetime.timedelta(weeks=-1)
		self.filters['last_month'] = lambda dt: dt + datetime.timedelta(days=-30)
		self.filters['last_year'] = lambda dt: dt + datetime.timedelta(days=-365)

		# global variables
		self.globals['version'] = version.version

		# global functions
		self.globals['fetch'] = self._func_fetch
		self.globals['parse_user_agent'] = ua_parser.parse_user_agent
		self.globals['password_is_complex'] = utilities.password_is_complex
		self.globals['random_integer'] = random.randint

		# additional globals
		self.globals.update(global_vars or {})

	def from_file(self, path, **kwargs):
		"""
		A convenience method to load template data from a specified file,
		passing it to :py:meth:`~jinja2.Environment.from_string`.

		.. warning::
			Because this method ultimately passes the template data to the
			:py:meth:`~jinja2.Environment.from_string` method, the data will not
			be automatically escaped based on the file extension as it would be
			when using :py:meth:`~jinja2.Environment.get_template`.

		:param str path: The path from which to load the template data.
		:param kwargs: Additional keyword arguments to pass to :py:meth:`~jinja2.Environment.from_string`.
		"""
		with codecs.open(path, 'r', encoding='utf-8') as file_h:
			source = file_h.read()
		return self.from_string(source, **kwargs)

	def join_path(self, template, parent):
		"""
		Over ride the default :py:meth:`jinja2.Environment.join_path` method to
		explicitly specifying relative paths by prefixing the path with either
		"./" or "../".

		:param str template: The path of the requested template file.
		:param str parent: The path of the template file which requested the load.
		:return: The new path to the template.
		:rtype: str
		"""
		if re.match(r'\.\.?/', template) is None:
			return template
		template = os.path.join(os.path.dirname(parent), template)
		return os.path.normpath(template)

	@property
	def standard_variables(self):
		"""
		Additional standard variables that can optionally be used in templates.
		"""
		std_vars = {
			'time': {
				'local': datetime.datetime.now(),
				'utc': datetime.datetime.utcnow()
			}
		}
		return std_vars

	def _filter_decode(self, data, encoding):
		if its.py_v3 and isinstance(data, bytes):
			data = data.decode('utf-8')
		encoding = encoding.lower()
		encoding = re.sub(r'^(base|rot)-(\d\d)$', r'\1\2', encoding)

		if encoding == 'base16' or encoding == 'hex':
			data = base64.b16decode(data)
		elif encoding == 'base32':
			data = base64.b32decode(data)
		elif encoding == 'base64':
			data = base64.b64decode(data)
		elif encoding == 'rot13':
			data = codecs.getdecoder('rot-13')(data)[0]
		else:
			raise ValueError('Unknown encoding type: ' + encoding)
		if its.py_v3 and isinstance(data, bytes):
			data = data.decode('utf-8')
		return data

	def _filter_encode(self, data, encoding):
		if its.py_v3 and isinstance(data, str):
			data = data.encode('utf-8')
		encoding = encoding.lower()
		encoding = re.sub(r'^(base|rot)-(\d\d)$', r'\1\2', encoding)

		if encoding == 'base16' or encoding == 'hex':
			data = base64.b16encode(data)
		elif encoding == 'base32':
			data = base64.b32encode(data)
		elif encoding == 'base64':
			data = base64.b64encode(data)
		elif encoding == 'rot13':
			data = codecs.getencoder('rot-13')(data.decode('utf-8'))[0]
		else:
			raise ValueError('Unknown encoding type: ' + encoding)
		if its.py_v3 and isinstance(data, bytes):
			data = data.decode('utf-8')
		return data

	def _filter_hash(self, data, hash_type):
		if its.py_v3 and isinstance(data, str):
			data = data.encode('utf-8')
		hash_type = hash_type.lower()
		hash_type = hash_type.replace('-', '')

		hash_obj = hashlib.new(hash_type, data)
		return hash_obj.digest()

	def _filter_json(self, data):
		try:
			data = json.loads(data)
		except json.JSONDecodeError:
			self.logger.error('template failed to load json data')
			data = None
		return data

	def _filter_strftime(self, dt, fmt):
		try:
			result = dt.strftime(fmt)
		except ValueError:
			self.logger.error("invalid time format '{0}'".format(fmt))
			result = ''
		return result

	def _filter_timedelta(self, dt, *args, **kwargs):
		try:
			result = dt + datetime.timedelta(*args, **kwargs)
		except ValueError:
			self.logger.error('invalid timedelta specification')
			result = ''
		return result

	def _func_fetch(self, url, allow_file=False):
		session = requests.Session()
		if allow_file:
			session.mount('file://', requests_file.FileAdapter())
		try:
			response = session.get(url)
		except requests.exceptions.RequestException:
			self.logger.error('template failed to load url: ' + url)
			return None
		return response.text

class MessageTemplateEnvironment(TemplateEnvironmentBase):
	"""A configured Jinja2 environment for formatting messages."""
	MODE_PREVIEW = 0
	MODE_ANALYZE = 1
	MODE_SEND = 2
	def __init__(self, *args, **kwargs):
		super(MessageTemplateEnvironment, self).__init__(*args, **kwargs)
		self._mode = None
		self.set_mode(self.MODE_PREVIEW)
		self.globals['inline_image'] = self._inline_image_handler
		self.attachment_images = {}
		"""A dictionary collecting the images that are going to be embedded and sent inline in the message."""

	def set_mode(self, mode):
		"""
		Set the operation mode for the environment. Valid values are the MODE_*
		constants.

		:param int mode: The operation mode.
		"""
		if mode not in (self.MODE_PREVIEW, self.MODE_ANALYZE, self.MODE_SEND):
			raise ValueError('mode must be one of the MODE_* constants')
		self._mode = mode
		if mode == self.MODE_ANALYZE:
			self.attachment_images = {}

	def _inline_image_handler(self, image_path, style=None, alt=None):
		image_path = os.path.abspath(image_path)
		if not os.path.isfile(image_path):
			self.logger.warning('the specified inline image path is not a file')
		elif not os.access(image_path, os.R_OK):
			self.logger.warning('the specified inline image path can not be read')
		if self._mode == self.MODE_PREVIEW:
			if os.path.sep == '\\':
				image_path = '/'.join(image_path.split('\\'))
			if not image_path.startswith('/'):
				image_path = '/' + image_path
			image_path = 'file://' + image_path
		else:
			if image_path in self.attachment_images:
				attachment_name = self.attachment_images[image_path]
			else:
				attachment_name = 'img_' + utilities.random_string_lower_numeric(8) + os.path.splitext(image_path)[-1]
				while attachment_name in self.attachment_images.values():
					attachment_name = 'img_' + utilities.random_string_lower_numeric(8) + os.path.splitext(image_path)[-1]
				self.attachment_images[image_path] = attachment_name
			image_path = 'cid:' + attachment_name
		image_path = html.escape(image_path, quote=True)
		img_tag = "<img src=\"{0}\"".format(image_path)
		if style is not None:
			img_tag += " style=\"{0}\"".format(html.escape(str(style), quote=True))
		if alt is not None:
			img_tag += " alt=\"{0}\"".format(html.escape(str(alt), quote=True))
		img_tag += '>'
		return img_tag
