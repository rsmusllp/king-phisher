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
import collections.abc
import logging
import os

from king_phisher import find
from king_phisher import serializers
from king_phisher import utilities

import dateutil.parser
import ecdsa
import ecdsa.curves
import requests
import requests_file

COLLECTION_TYPES = ('plugins/client', 'plugins/server', 'templates/client', 'templates/server')
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
	logger = logging.getLogger('KingPhisher.Catalog.SecurityKeys')
	def __init__(self):
		self.keys = utilities.FreezableDict()
		if not self._load_key_store('security.json'):
			raise RuntimeError('failed to load any keys from the primary store')
		self._load_key_store('security.local.json')
		self.keys.freeze()

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
		self.logger.debug("loaded {0} key{1} from: {2}".format(loaded, ('' if loaded == 1 else 's'), file_path))
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

CollectionItemFile = collections.namedtuple('ItemFile', ('path', 'signed_by', 'signature'))
class Collection(collections.abc.Mapping):
	__slots__ = ('_storage', 'type')
	logger = logging.getLogger('KingPhisher.Catalog.Collection')
	def __init__(self, type, items):
		self.type = type
		self._storage = items

	def __repr__(self):
		return "<{0} type={1!r} >".format(self.__class__.__name__, self.type)

	def __getitem__(self, key):
		return self._storage[key]

	def __iter__(self):
		return iter(self._storage)

	def __len__(self):
		return len(self._storage)

class Repository(object):
	__slots__ = ('_req_sess', 'collections', 'created', 'security_keys', 'homepage', 'title', 'url_base')
	logger = logging.getLogger('KingPhisher.Catalog.Repository')
	def __init__(self, data, keys=None):
		self.security_keys = keys or SecurityKeys()
		created = data.get('created')
		if isinstance(created, str):
			self.created = dateutil.parser.parse(created)
		else:
			self.created = None
		self._req_sess = requests.Session()
		self._req_sess.mount('file://', requests_file.FileAdapter())
		self.homepage = data.get('homepage')
		for key in ('title', 'url-base'):
			if isinstance(data.get(key), str) and data[key]:
				continue
			raise KeyError('repository data is missing non-empty string key: ' + key)
		self.title = data['title']
		self.url_base = data['url-base']
		self.collections = utilities.FreezableDict()
		if 'collections-include' in data:
			# include-files is reversed so the dictionary can get .update()'ed and the first seen will be the value kept
			for include in reversed(data['collections-include']):
				include_data = serializers.JSON.loads(self._fetch(include, encoding='utf-8', verify=False))
				if 'collections' not in include_data:
					self.logger.warning("included file {0} missing 'collections' entry".format(include['path']))
					continue
				include_data = include_data['collections']
				for collection_type in include.get('types', COLLECTION_TYPES):
					if collection_type not in include_data:
						continue
					collection = include_data.get(collection_type)
					if collection is None:
						continue
					self._add_collection_data(collection_type, collection)
		if 'collections' in data:
			for collection_type in COLLECTION_TYPES:
				collection = data['collections'].get(collection_type)
				if collection is None:
					continue
				self._add_collection_data(collection_type, collection)
		item_count = sum(len(collection) for collection in self.collections.values())
		self.logger.debug("initialized catalog repository with {0} collection types and {1} total items".format(len(self.collections), item_count))
		for collection_type, collection in self.collections.items():
			collection.freeze()
			self.collections[collection_type] = Collection(collection_type, collection)
		self.collections.freeze()

	def __repr__(self):
		return "<{0} title={1!r} >".format(self.__class__.__name__, self.title)

	def _add_collection_data(self, collection_type, collection_items):
		if collection_type not in COLLECTION_TYPES:
			self.logger.warning('unknown repository collection type: ' + collection_type)
			return
		if not isinstance(collection_items, list):
			self.logger.warning('invalid repository collection information for type: ' + collection_type)
			return
		if not collection_items:
			return
		collection = self.collections.get(collection_type)
		if collection is None:
			collection = utilities.FreezableDict()
		# validate each of the items so we know that the basic keys we expect
		# to be present are set to with the correct value types
		for item in collection_items:
			if not isinstance(item, dict):
				raise TypeError('collection item is not a dict')
			for key in ('authors', 'files'):
				if isinstance(item.get(key), list) and item[key]:
					continue
				raise KeyError('collection item is missing non-empty list key: ' + key)
			for key in ('description', 'name', 'title', 'version'):
				if isinstance(item.get(key), str) and item[key]:
					continue
				raise KeyError('collection item is missing non-empty string key: ' + key)

			if not all(isinstance(value, str) for value in item['authors']):
				raise TypeError('collection item has non-string item in list: authors')
			item['authors'] = tuple(item['authors'])

			if not all(isinstance(value, dict) for value in item['files']):
				raise TypeError('collection item has non-dict item in list: files')

			item_files = []
			for item_file in item['files']:
				if not (isinstance(item_file.get('path'), str) and item_file['path']):
					raise KeyError('collection item file is missing non-empty string key: path')
				if not isinstance(item_file.get('signed-by'), (str, type(None))):
					raise TypeError('collection item file has invalid item: signed-by')
				if not isinstance(item_file.get('signature'), (str, type(None))):
					raise TypeError('collection item file has invalid item: signed-by')
				# normalize empty strings to None for signed-by and signature
				if not item_file.get('signature'):
					item_file['signature'] = None
				if not item_file.get('signed-by'):
					item_file['signed-by'] = None
				# make sure both keys are present or neither are present
				if bool(item_file['signature']) ^ bool(item_file['signed-by']):
					raise ValueError('collection item file must either have both signature and signed-by keys or neither')
				item_file['signed_by'] = item_file.pop('signed-by')
				item_files.append(CollectionItemFile(**item_file))
			item['files'] = tuple(item_files)
			item = utilities.FreezableDict(sorted(item.items(), key=lambda i: i[0]))
			item.freeze()
			collection[item['name']] = item
		self.collections[collection_type] = collection

	def _fetch(self, item_file, encoding=None, verify=True):
		if isinstance(item_file, dict):
			item_file = CollectionItemFile(path=item_file['path'], signature=item_file.get('signature'), signed_by=item_file.get('signed-by'))
		url = self.url_base + '/' + item_file.path
		self.logger.debug("fetching repository item from: {0} (integrity check: {1})".format(url, ('enabled' if verify else 'disabled')))
		resp = self._req_sess.get(url)
		if not resp.ok:
			self.logger.warning("request to {0} failed with status {1} {2}".format(url, resp.status_code, resp.reason))
		data = resp.content
		if verify:
			self.logger.debug("verifying signature from {0} for {1}".format(item_file.signed_by, url))
			self.security_keys.verify(item_file.signed_by, data, binascii.a2b_base64(item_file.signature))
		if encoding:
			data = data.decode(encoding)
		return data

	def get_file(self, item_file, encoding=None):
		if not isinstance(item_file, CollectionItemFile):
			raise TypeError('the file object must be a CollectionItemFile instance')
		if not all(isinstance(item_file.get(key), str) for key in ('path', 'signature', 'signed-by')):
			raise ValueError('the file object is missing a required key')
		return self._fetch(item_file, encoding=encoding)

	def get_item(self, collection_type, name):
		collection = self.collections.get(collection_type, {})
		return collection.get(name)

	def get_item_files(self, collection_type, name, destination):
		item = self.get_item(collection_type, name)
		destination = os.path.abspath(destination)
		self.logger.debug("fetching catalog item: {0}/{1} to {2}".format(collection_type, name, destination))
		if not os.path.isdir(destination):
			os.makedirs(destination)
		for item_file in item['files']:
			data = self._fetch(item_file)
			file_destination = os.path.abspath(os.path.join(destination, item_file.path))
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
		created = data.get('created')
		if isinstance(created, str):
			self.created = dateutil.parser.parse(created)
		else:
			self.created = None
		self.maintainers = tuple(maintainer['id'] for maintainer in data.get('maintainers', []))
		self.repositories = tuple(Repository(repo, keys=self.security_keys) for repo in data['repositories'])
		self.logger.info("initialized catalog with {0:,} repositories".format(len(self.repositories)))

	@classmethod
	def from_url(cls, url, *args, encoding='utf-8', **kwargs):
		req_sess = requests.Session()
		req_sess.mount('file://', requests_file.FileAdapter())
		cls.logger.debug('fetching catalog from: ' + url)
		resp = req_sess.get(url)
		data = resp.content.decode(encoding)
		data = serializers.JSON.loads(data)
		return cls(data, *args, **kwargs)
