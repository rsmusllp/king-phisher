#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  king_phisher/server/database/storage.py
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

import collections.abc
import contextlib

from . import manager as db_manager
from . import models as db_models
from king_phisher import serializers

class KeyValueStorage(collections.abc.MutableMapping):
	"""
	This class provides key-value storage of arbitrary data in the database.
	The :py:mod:`.serializers` module is used for converting data into a format
	suitable for storing in the database. This object, once initialized,
	provides an interface just like a standard dictionary object. An optional
	namespace should be specified as a unique identifier, allowing different
	sources to store data using the same keys. All keys must be strings but
	data can be anything that is serializable.
	"""
	serializer = serializers.MsgPack
	def __init__(self, namespace=None):
		"""
		:param str namespace: The unique identifier of this namespace.
		"""
		self.namespace = namespace

	@contextlib.contextmanager
	def _session(self):
		session = db_manager.Session()
		try:
			yield session
		finally:
			session.close()

	def _query(self, session):
		return session.query(db_models.StorageData).filter_by(namespace=self.namespace)

	def __delitem__(self, key):
		if not isinstance(key, str):
			raise TypeError('key must be a str instance')
		with self._session() as session:
			obj = self._query(session).filter_by(key=key).first()
			if obj is None:
				raise KeyError(key)
			session.delete(obj)
			session.commit()

	def __getitem__(self, key):
		if not isinstance(key, str):
			raise TypeError('key must be a str instance')
		with self._session() as session:
			obj = self._query(session).filter_by(key=key).first()
			if obj is None:
				raise KeyError(key)
			value = obj.value
		if value is not None:
			value = self.serializer.loads(value)
		return value

	def __iter__(self):
		with self._session() as session:
			for obj in self._query(session):
				yield obj.key

	def __len__(self):
		with self._session() as session:
			return self._query(session).count()

	def __repr__(self):
		return "<{0} namespace={1!r} >".format(self.__class__.__name__, self.namespace)

	def __setitem__(self, key, value):
		if not isinstance(key, str):
			raise TypeError('key must be a str instance')
		if value is not None:
			value = self.serializer.dumps(value)
		with self._session() as session:
			obj = self._query(session).filter_by(key=key).first()
			if obj is None:
				obj = db_models.StorageData(namespace=self.namespace, key=key, value=value)
			elif obj.value != value:
				obj.value = value
				obj.modified = db_models.current_timestamp()
			session.add(obj)
			session.commit()
