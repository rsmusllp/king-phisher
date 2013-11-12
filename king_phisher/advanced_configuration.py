#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  AdvancedConfiguration.py
#
#  Copyright 2013 Spencer McIntyre <zeroSteiner@gmail.com>
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
#

import json
import string

from gi.repository import GObject

class AdvancedConfiguration(object):
	def __init__(self, file_name = None, restore = False):
		super(AdvancedConfiguration, self).__init__()
		self._data = {}
		self._vars = {}
		self.file_name = file_name
		if self.file_name and restore:
			self.restore_config()

	def __repr__(self):
		return repr(self._data)

	def __str__(self):
		return self.dumps()

	def load_config(self):
		if not self.file_name:
			return
		self.loads(open(self.file_name, 'rb').read())

	def save_config(self):
		if not self.file_name:
			return
		open(self.file_name, 'wb').write(self.dumps())

	def dumps(self):
		return json.dumps(self._data, sort_keys = True, indent = 4)

	def loads(self, data):
		self._data = json.loads(data)

	def set_var(self, key, value):
		key = str(key)
		if key.startswith('$'):
			key = key[1:]
		self._vars[key] = value

	def transform_key(self, key):
		key = string.Template(key)
		key = key.substitute(**self._vars)
		return key

	def __getitem__(self, key):
		return self.get(key)

	def __setitem__(self, key, value):
		key = self.transform_key(key)
		dataset = self._data
		key_last_part = key.split('.')[-1]
		for subset in key.split('.')[:-1]:
			if dataset.get(subset) == None:
				dataset[subset] = {}
			dataset = dataset[subset]
		dataset[key_last_part] = value

	def get(self, key, *args, **kwargs):
		key = self.transform_key(key)
		dataset = self._data
		key_last_part = key.split('.')[-1]
		for subset in key.split('.')[:-1]:
			dataset = dataset.get(subset)
			if not dataset:
				break
		if not dataset:
			return None
		return dataset.get(key_last_part)

	def items(self, base_key = None):
		if base_key:
			dataset = self.get(base_key)
		else:
			dataset = self._data
		return dataset.items()

	def keys(self, base_key = None):
		if base_key:
			dataset = self.get(base_key)
		else:
			dataset = self._data
		return dataset.keys()

	def values(self, base_key = None):
		if base_key:
			dataset = self.get(base_key)
		else:
			dataset = self._data
		return dataset.values()

class GObjectAdvancedConfiguration(AdvancedConfiguration, GObject.Object):
	__gsignals__ = {
		'updated': (GObject.SIGNAL_RUN_FIRST, None, ())
	}

	def __init__(self, *args, **kwargs):
		super(GObjectAdvancedConfiguration, self).__init__(*args, **kwargs)

	def do_updated(self):
		self.save_config()

	def __setitem__(self, *args, **kwargs):
		super(GObjectAdvancedConfiguration, self).__setitem__(*args, **kwargs)
		self.emit('updated')
