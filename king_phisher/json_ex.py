#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  king_phisher/its.py
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

from king_phisher.utilities import switch

def _json_default(obj):
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
	return {'__complex_type__': obj_type, 'value': obj_value}

def _json_object_hook(obj):
	obj_type = obj.get('__complex_type__')
	obj_value = obj.get('value')
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
		return obj
	return value

def dump(data, file_h, *args, **kwargs):
	"""
	Write a Python object to a file by encoding it into a JSON string. The
	underlying logic is provided by the :py:func:`.dumps` function.

	:param data:  The object to encode.
	:param file file_h: The file to write the encoded string to.
	"""
	return file_h.write(dumps(data, *args, **kwargs))

def dumps(data, pretty=True):
	"""
	Convert a Python object to a JSON encoded string. This also provides
	support for additional Python types such as :py:class:`datetime.datetime`
	instances.

	:param data: The object to encode.
	:param bool pretty: Set options to make the resulting JSON data more readable.
	:return: The encoded data.
	:rtype: str
	"""
	kwargs = {'default': _json_default}
	if pretty:
		kwargs['sort_keys'] = True
		kwargs['indent'] = 2
		kwargs['separators'] = (',', ': ')
	return json.dumps(data, **kwargs)

def load(file_h):
	"""
	Load JSON encoded data from a file handle. The underlying logic is provided
	by the :py:func:`.loads` function.

	:param file file_h: The file to read and load encoded data from.
	:return: The Python object represented by the encoded data.
	"""
	return loads(file_h.read())

def loads(data):
	"""
	Load a string of JSON encoded data. This also provides support for
	additional Python types such as :py:class:`datetime.datetime` instances.

	:param str data: The encoded data to load.
	:return: The Python object represented by the encoded data.
	"""
	return json.loads(data, object_hook=_json_object_hook)
