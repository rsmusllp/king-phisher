#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  king_phisher/serializers.py
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
import json
import re

from king_phisher import its
from king_phisher.utilities import switch

import msgpack

CLEAN_JSON_REGEX = re.compile(r',(\s+[}\]])')

def _serialize_ext_dump(obj):
	for case in switch(obj.__class__):
		if case(datetime.date):
			obj_type, obj_value = 'datetime.date', obj.isoformat()
			break
		if case(datetime.datetime):
			obj_type, obj_value = 'datetime.datetime', obj.isoformat()
			break
		if case(datetime.time):
			obj_type, obj_value = 'datetime.time', obj.isoformat()
			break
	else:
		raise TypeError('Unknown type: ' + repr(obj))
	return obj_type, obj_value

def _serialize_ext_load(obj_type, obj_value, default):
	for case in switch(obj_type):
		if case('datetime.date'):
			value = datetime.datetime.strptime(obj_value, '%Y-%m-%d').date()
			break
		if case('datetime.datetime'):
			value = datetime.datetime.strptime(obj_value, '%Y-%m-%dT%H:%M:%S' + ('.%f' if '.' in obj_value else ''))
			break
		if case('datetime.time'):
			value = datetime.datetime.strptime(obj_value, '%H:%M:%S' + ('.%f' if '.' in obj_value else '')).time()
			break
	else:
		return default
	return value

class Serializer(object):
	"""
	The base class for serializer objects of different formats and protocols.
	These serializers are extended using a King Phisher-specific protocol for
	serializing additional types, most notably Python's
	:py:class:`datetime.datetime` type.

	.. note::
		None of the serializers handle Python 3's ``bytes`` type. These objects
		will be treated as strings and silently converted.
	"""
	encoding = 'utf-8'
	"""The encoding which this serializer uses for handling strings."""
	@classmethod
	def dump(cls, data, file_h, *args, **kwargs):
		"""
		Write a Python object to a file by encoding it with this serializer.

		:param data:  The object to encode.
		:param file file_h: The file to write the encoded string to.
		"""
		return file_h.write(cls.dumps(data, *args, **kwargs))

	@classmethod
	def load(cls, file_h, *args, **kwargs):
		"""
		Load encoded data from the specified file.

		:param file file_h: The file to read and load encoded data from.
		:param bool strict: Do not try remove trailing commas from the JSON data.
		:return: The Python object represented by the encoded data.
		"""
		return cls.loads(file_h.read(), *args, **kwargs)

class JSON(Serializer):
	name = 'JSON'
	@classmethod
	def _json_default(cls, obj):
		obj_type, obj_value = _serialize_ext_dump(obj)
		return {'__complex_type__': obj_type, 'value': obj_value}

	@classmethod
	def _json_object_hook(cls, obj):
		return _serialize_ext_load(obj.get('__complex_type__'), obj.get('value'), obj)

	@classmethod
	def dumps(cls, data, pretty=True):
		"""
		Convert a Python object to a JSON encoded string.

		:param data: The object to encode.
		:param bool pretty: Set options to make the resulting JSON data more readable.
		:return: The encoded data.
		:rtype: str
		"""
		kwargs = {'default': cls._json_default}
		if pretty:
			kwargs['sort_keys'] = True
			kwargs['indent'] = 2
			kwargs['separators'] = (',', ': ')
		return json.dumps(data, **kwargs)

	@classmethod
	def loads(cls, data, strict=True):
		"""
		Load JSON encoded data.

		:param str data: The encoded data to load.
		:param bool strict: Do not try remove trailing commas from the JSON data.
		:return: The Python object represented by the encoded data.
		"""
		if not strict:
			data = CLEAN_JSON_REGEX.sub(r'\1', data)
		return json.loads(data, object_hook=cls._json_object_hook)

class MsgPack(Serializer):
	name = 'MsgPack'
	_ext_types = {10: 'datetime.datetime', 11: 'datetime.date', 12: 'datetime.time'}
	@classmethod
	def _msgpack_default(cls, obj):
		obj_type, obj_value = _serialize_ext_dump(obj)
		obj_type = next(i[0] for i in cls._ext_types.items() if i[1] == obj_type)
		if its.py_v3 and isinstance(obj_value, str):
			obj_value = obj_value.encode('utf-8')
		return msgpack.ExtType(obj_type, obj_value)

	@classmethod
	def _msgpack_ext_hook(cls, code, obj_value):
		default = msgpack.ExtType(code, obj_value)
		if its.py_v3 and isinstance(obj_value, bytes):
			obj_value = obj_value.decode('utf-8')
		obj_type = cls._ext_types.get(code)
		return _serialize_ext_load(obj_type, obj_value, default)

	@classmethod
	def dumps(cls, data):
		"""
		Convert a Python object to a MsgPack encoded ``bytes`` instance.

		:param data: The object to encode.
		:param bool pretty: Set options to make the resulting JSON data more readable.
		:return: The encoded data.
		:rtype: str
		"""
		return msgpack.dumps(data, default=cls._msgpack_default)

	@classmethod
	def loads(cls, data):
		"""
		Load MsgPack encoded data.

		:param bytes data: The encoded data to load.
		:return: The Python object represented by the encoded data.
		"""
		return msgpack.loads(data, encoding=cls.encoding, ext_hook=cls._msgpack_ext_hook)
