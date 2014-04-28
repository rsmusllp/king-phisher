#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  king_phisher/configuration.py
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

import yaml
try:
	from yaml import CLoader as Loader, CDumper as Dumper
except ImportError:
	from yaml import Loader, Dumper

class Configuration(object):
	def __init__(self, configuration_file):
		self.configuration_file = configuration_file
		file_h = open(self.configuration_file, 'r')
		self._storage = dict(yaml.load(file_h, Loader = Loader))
		file_h.close()

	def dumps(self, obj):
		return yaml.dump(obj, default_flow_style = False, Dumper = Dumper)

	def get_storage(self):
		return copy.deepcopy(self._storage)

	def get(self, item_name):
		item_names = item_name.split('.')
		node = self._storage
		for item_name in item_names:
			node = node[item_name]
		return node

	def has_option(self, option_name):
		item_names = option_name.split('.')
		node = self._storage
		for item_name in item_names:
			if not item_name in node:
				return False
			node = node[item_name]
		return True

	def has_section(self, section_name):
		return isinstance(self.get(section_name), dict)

	def set(self, item_name, item_value):
		item_names = item_name.split('.')
		item_last = item_names.pop()
		node = self._storage
		for item_name in item_names:
			if not item_name in node:
				node[item_name] = {}
			node = node[item_name]
		node[item_last] = item_value
		return

	def save(self):
		file_h = open(self.configuration_file, 'w')
		file_h.write(self.dumps(self._storage))
		file_h.close()
