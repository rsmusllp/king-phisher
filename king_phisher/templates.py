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

import datetime
import logging
import os
import random

from king_phisher import its
from king_phisher import utilities
from king_phisher import version

import boltons.strutils
import jinja2

if its.py_v2:
	import cgi as html
else:
	import html

__all__ = ['BaseTemplateEnvironment', 'MessageTemplateEnvironment']

class BaseTemplateEnvironment(jinja2.Environment):
	"""A configured Jinja2 environment with additional filters."""
	def __init__(self, loader=None, global_vars=None):
		"""
		:param loader: The loader to supply to the environment.
		:type loader: :py:class:`jinja2.BaseLoader`
		:param dict global_vars: Additional global variables for the environment.
		"""
		self.logger = logging.getLogger('KingPhisher.TemplateEnvironment')
		autoescape = lambda name: isinstance(name, str) and os.path.splitext(name)[1][1:] in ('htm', 'html', 'xml')
		extensions = ['jinja2.ext.autoescape', 'jinja2.ext.do']
		super(BaseTemplateEnvironment, self).__init__(autoescape=autoescape, extensions=extensions, loader=loader, trim_blocks=True)

		# misc. string filters
		self.filters['cardinalize'] = boltons.strutils.cardinalize
		self.filters['ordinalize'] = boltons.strutils.ordinalize
		self.filters['pluralize'] = boltons.strutils.pluralize
		self.filters['singularize'] = boltons.strutils.singularize
		self.filters['possessive'] = lambda word: word + ('\'' if word.endswith('s') else '\'s')

		# time filters
		self.filters['strftime'] = self._filter_strftime
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
		self.globals['random_integer'] = random.randint

		# additional globals
		if global_vars:
			for key, value in global_vars.items():
				self.globals[key] = value

	@property
	def standard_variables(self):
		"""Additional standard variables that can optionally be used for templates."""
		std_vars = {
			'time': {
				'local': datetime.datetime.now(),
				'utc': datetime.datetime.utcnow()
			}
		}
		return std_vars

	def _filter_strftime(self, dt, fmt):
		try:
			result = dt.strftime(fmt)
		except ValueError:
			self.logger.error("invalid time format '{0}'".format(fmt))
			result = ''
		return result

class MessageTemplateEnvironment(BaseTemplateEnvironment):
	"""A configured Jinja2 environment for formatting messages."""
	MODE_PREVIEW = 0
	MODE_ANALYZE = 1
	MODE_SEND = 2
	def __init__(self, *args, **kwargs):
		super(MessageTemplateEnvironment, self).__init__(*args, **kwargs)
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
		assert(mode in [self.MODE_PREVIEW, self.MODE_ANALYZE, self.MODE_SEND])
		self._mode = mode
		if mode == self.MODE_ANALYZE:
			self.attachment_images = {}

	def _inline_image_handler(self, image_path):
		image_path = os.path.abspath(image_path)
		if self._mode == self.MODE_PREVIEW:
			if os.path.sep == '\\':
				image_path = '/'.join(image_path.split('\\'))
			if not image_path.startswith('/'):
				image_path = '/' + image_path
			image_path = 'file://' + image_path
			return "<img src=\"{0}\">".format(html.escape(image_path, quote=True))
		if image_path in self.attachment_images:
			attachment_name = self.attachment_images[image_path]
		else:
			attachment_name = 'img_' + utilities.random_string_lower_numeric(8) + os.path.splitext(image_path)[-1]
			while attachment_name in self.attachment_images.values():
				attachment_name = 'img_' + utilities.random_string_lower_numeric(8) + os.path.splitext(image_path)[-1]
			self.attachment_images[image_path] = attachment_name
		return "<img src=\"cid:{0}\">".format(html.escape(attachment_name, quote=True))
