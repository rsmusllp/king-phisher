#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  king_phisher/catalog.py
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

import binascii
import logging
import os

from king_phisher import find
from king_phisher import serializers

import dateutil.parser
import ecdsa
import ecdsa.curves
import requests
import requests_file

ecdsa_curves = dict((c.name, c) for c in ecdsa.curves.curves)
ecdsa_curves.update((c.openssl_name, c) for c in ecdsa.curves.curves)

class VerifyingKey(ecdsa.VerifyingKey):
	@classmethod
	def from_string(cls, string, **kwargs):
		if 'curve' in kwargs:
			curve = kwargs.pop('curve')
			if isinstance(curve, str):
				if not curve in ecdsa_curves:
					raise ValueError('unknown curve: ' + curve)
				curve = ecdsa_curves[curve]
			elif not isinstance(curve, ecdsa.curves.Curve):
				raise TypeError('curve must either be a curve name or ecdsa.curves.Curve instance')
			kwargs['curve'] = curve
		return super(VerifyingKey, cls).from_string(string, **kwargs)

	@classmethod
	def from_dict(cls, value):
		return cls.from_string(value['data'], curve=value['type'])

class SecurityKeys(object):
	logger = logging.getLogger('KingPhisher.Catalog.Security')
	def __init__(self):
		self.keys = {}
		if not self._load_key_store('security.json'):
			raise RuntimeError('failed to load any keys from the primary store')
		self._load_key_store('security.local.json')

	def _load_key_store(self, file_name):
		file_path = find.data_file(file_name)
		if not file_path:
			return 0
		with open(file_path, 'r') as file_h:
			key_store = serializers.JSON.load(file_h)
		key_store = key_store.get('keys', [])
		loaded = 0
		for key_idx, key in enumerate(key_store, 1):
			identifier = key.get('id')
			if not identifier:
				self.logger.warning("skipping loading {0}:{1} due to missing id".format(file_name, key_idx))
				continue
			if identifier in self.keys:
				self.logger.warning("skipping loading {0}:{1} due to a duplicate id".format(file_name, key_idx))
				continue
			if 'verifying-key' in key:
				verifying_key = key['verifying-key']
				verifying_key['data'] = binascii.a2b_base64(verifying_key['data'])
				key['verifying-key'] = VerifyingKey.from_dict(verifying_key)
			self.keys[identifier] = key
			loaded += 1
		self.logger.debug("loaded {0} keys from the {1} store".format(loaded, file_path))
		return loaded

	def verify(self, key_id, data, signature):
		key = self.keys.get(key_id)
		if key is None:
			self.logger.warning("verification of data with key {0} failed (unknown key)".format(key_id))
			raise ecdsa.keys.BadSignatureError('unknown key for signature')
		verifying_key = key.get('verifying-key')
		if verifying_key is None:
			self.logger.warning("verification of data with key {0} failed (missing verifying-key)".format(key_id))
			raise ecdsa.keys.BadSignatureError('unknown key for signature')
		return verifying_key.verify(signature, data)

class CatalogRepository(object):
	logger = logging.getLogger('KingPhisher.Catalog.Repository')
	collection_types = ('plugins/client', 'plugins/server', 'templates/client', 'templates/server')
	def __init__(self, data, keys=None):
		self.security_keys = keys or SecurityKeys()
		self._req_sess = requests.Session()
		self._req_sess.mount('file://', requests_file.FileAdapter())
		self.homepage = data.get('homepage')
		self.title = data['title']
		self.url_base = data['url-base']
		self.collections = {}
		if 'collections-include' in data:
			# include-files is reversed so the dictionary can get .update()'ed and the first seen will be the value kept
			for include in reversed(data['collections-include']):
				include_data = serializers.JSON.loads(self._fetch(include, encoding='utf-8', verify=False))
				for collection_type in include['types']:
					if collection_type not in self.collection_types:
						self.logger.warning('unknown repository collection type: ' + collection_type)
						continue
					self._add_collections(collection_type, include_data[collection_type])
		if 'collections' in data:
			for collection_type in self.collection_types:
				collection = data['collections'].get(collection_type)
				if not collection:
					continue
				self._add_collections(collection_type, collection)

	def __repr__(self):
		return "<{0} title={1!r} >".format(self.__class__.__name__, self.title)

	def _add_collections(self, collection_type, collection):
		existing = self.collections.get(collection_type, {})
		existing.update(dict((item['name'], item) for item in collection))
		self.collections[collection_type] = existing

	def _fetch(self, obj, encoding=None, verify=True):
		url = self.url_base + '/' + obj['path']
		self.logger.debug('retrieving: ' + url)
		resp = self._req_sess.get(url)
		if not resp.ok:
			self.logger.warning("request failed with status {0} {1}".format(resp.status_code, resp.reason))
		data = resp.content
		if verify:
			self.logger.debug('verifying data signature from ' + obj['signed-by'])
			self.security_keys.verify(obj['signed-by'], data, binascii.a2b_base64(obj['signature']))
		if encoding:
			data = data.decode(encoding)
		return data

	def get_file(self, file_obj, encoding=None):
		if not isinstance(file_obj, dict):
			raise TypeError('the file object must be a dict instance')
		if not all(isinstance(file_obj.get(key), str) for key in ('path', 'signature', 'signed-by')):
			raise ValueError('the file object is missing a required key')
		return self._fetch(file_obj, encoding=encoding)

	def get_item(self, collection_type, name):
		collection = self.collections.get(collection_type, {})
		return collection.get(name)

	def get_item_files(self, collection_type, name, destination):
		item = self.get_item(collection_type, name)
		destination = os.path.abspath(destination)
		self.logger.debug("fetching catalog item: {0}/{1} to {2}".format(collection_type, name, destination))
		if not os.path.isdir(destination):
			os.makedirs(destination)
		for file_ref in item['files']:
			data = self._fetch(file_ref)
			file_destination = os.path.abspath(os.path.join(destination, file_ref['path']))
			if not file_destination.startswith(destination + os.path.sep):
				raise RuntimeError('file destination is outside of the specified path')
			dir_name = os.path.dirname(file_destination)
			os.makedirs(dir_name)
			with open(file_destination, 'wb') as file_h:
				file_h.write(data)

class Catalog(object):
	logger = logging.getLogger('KingPhisher.Catalog')
	def __init__(self, data, keys=None):
		self.security_keys = keys or SecurityKeys()
		self._data = data
		self.maintainers = tuple(m['id'] for m in data.get('maintainers', []))
		self.repositories = tuple(CatalogRepository(repo, keys=self.security_keys) for repo in data['repositories'])

	@property
	def generated(self):
		generated = self._data.get('generated')
		if generated:
			generated = dateutil.parser.parse(generated)
		return generated

	@classmethod
	def from_url(cls, url, *args, encoding='utf-8', **kwargs):
		req_sess = requests.Session()
		req_sess.mount('file://', requests_file.FileAdapter())
		resp = req_sess.get(url)
		data = resp.content.decode(encoding)
		data = serializers.JSON.loads(data)

		return cls(data, *args, **kwargs)
