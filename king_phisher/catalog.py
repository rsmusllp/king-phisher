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
import collections
import logging
import os
import sys
import weakref

from king_phisher import security_keys
from king_phisher import serializers
from king_phisher import utilities

import dateutil.parser
import requests
import requests_file
import smoke_zephyr.utilities

if sys.version_info[:3] >= (3, 3, 0):
	_Mapping = collections.abc.Mapping
else:
	_Mapping = collections.Mapping

COLLECTION_TYPES = ('plugins/client', 'plugins/server', 'templates/client', 'templates/server')
"""
A tuple of the known collection type identity strings. Collection types are
logical groupings of published data types. These type identifiers provide some
context as to how the data is intended to be used and what parts of the
application may be interested in using it.
"""

class CollectionItemFile(object):
	"""
	An object representing a single remote file and the necessary data to
	validate it's integrity. In order to validate the data integrity both the
	:py:attr:`.signature` and :py:attr:`.signed_by` attributes must be
	available. These attributes must either both be present or absent, i.e.
	one can not be set without the other.
	"""
	__slots__ = ('__weakref__', 'path_destination', 'path_source', 'signature', 'signed_by')
	def __init__(self, path_destination, path_source, signature=None, signed_by=None):
		if bool(signature) ^ bool(signed_by):
			raise ValueError('collection item file must either have both signature and signed-by keys or neither')
		self.path_destination = path_destination
		"""The relative path of where this file should be placed."""
		self.path_source = path_source
		"""The relative path of where this file should be retrieved from."""
		self.signed_by = signed_by
		"""The identity of the :py:class:`~king_phisher.security_keys.SigningKey` which generated the :py:attr:`.signature`"""
		self.signature = signature
		"""The signature data used for integrity verification of the represented resource."""

	@classmethod
	def from_dict(cls, value):
		"""
		Load the collection item file from the specified dict object.

		:param dict value: The dictionary to load the data from.
		:return:
		"""
		# make sure both keys are present or neither are present
		return cls(value.get('path-destination', value['path-source']), value['path-source'], signature=value.get('signature'), signed_by=value.get('signed-by'))

	def to_dict(self):
		"""
		Dump the instance to a dictionary suitable for being reloaded with
		:py:meth:`.from_dict`.

		:return: The instance represented as a dictionary.
		:rtype: dict
		"""
		data = {
			'path-destination': self.path_destination,
			'path-source': self.path_source
		}
		if self.signature and self.signed_by:
			data['signature'] = self.signature
			data['signed-by'] = self.signed_by
		return data

class Collection(_Mapping):
	"""
	An object representing a set of :py:class:`CollectionItemFile` instances,
	each of which represent a piece of of add on data that are all of the same
	type (see :py:data:`.COLLECTION_TYPES`). A collection is also a logical
	domain where the items contained within it must each have a unique identity
	in the form of its name attribute.
	"""
	#__slots__ = ('__weakref__', '__repo_ref', '_storage', 'type')
	logger = logging.getLogger('KingPhisher.Catalog.Collection')
	def __init__(self, repo, type, items):
		"""
		:param repo: The repository this collection is associated with.
		:type repo: :py:class:`.Repository`
		:param str type: The collection type of these items.
		:param dict items: The items that are members of this collection, keyed by their name.
		"""
		self.__repo_ref = weakref.ref(repo)
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

	@classmethod
	def from_dict(cls, value, repo):
		"""
		Load the collection item file from the specified dict object.

		:param dict value: The dictionary to load the data from.
		:return:
		"""
		items = utilities.FreezableDict()
		for item in value['items']:
			item['files'] = tuple(CollectionItemFile.from_dict(file) for file in item['files'])
			items[item['title']] = item
		items.freeze()
		return cls(repo, value['type'], items)

	def to_dict(self):
		"""
		Dump the instance to a dictionary suitable for being reloaded with
		:py:meth:`.from_dict`.

		:return: The instance represented as a dictionary.
		:rtype: dict
		"""
		data = {'type': self.type}
		items = []
		for item in self.values():
			item = dict(item)
			item['authors'] = list(item['authors'])
			item['files'] = [cif.to_dict() for cif in item['files']]
			items.append(item)
		data['items'] = items
		return data

	@property
	def _repo_ref(self):
		repo = self.__repo_ref()
		if repo is None:
			raise RuntimeError('the repository reference is invalid')
		return repo

	def get_file(self, *args, **kwargs):
		"""
		A simple convenience method which forwards to the associated
		:py:class:`~.Repository`'s :py:meth:`~.Repository.get_file` method.
		"""
		return self._repo_ref.get_file(*args, **kwargs)

	def get_item(self, *args, **kwargs):
		"""
		A simple convenience method which forwards to the associated
		:py:class:`~.Repository`'s :py:meth:`~.Repository.get_item` method.
		"""
		return self._repo_ref.get_item(self.type, *args, **kwargs)

	def get_item_files(self, *args, **kwargs):
		"""
		A simple convenience method which forwards to the associated
		:py:class:`~.Repository`'s :py:meth:`~.Repository.get_item_files`
		method.
		"""
		return self._repo_ref.get_item_files(self.type, *args, **kwargs)

class Repository(object):
	"""
	An object representing a single logical source of add on data.
	"""
	__slots__ = ('__weakref__', 'id', '_req_sess', 'collections', 'description', 'security_keys', 'homepage', 'title', 'url_base')
	logger = logging.getLogger('KingPhisher.Catalog.Repository')
	def __init__(self, data, keys=None):
		"""
		:param dict data: The formatted repository data.
		:param keys: The keys to use for verifying remote data.
		:type keys: :py:class:`~king_phisher.security_keys.SecurityKeys`
		"""
		self.security_keys = keys or security_keys.SecurityKeys()
		"""The :py:class:`~king_phisher.security_keys.SecurityKeys` used for verifying remote data."""

		self._req_sess = requests.Session()
		self._req_sess.mount('file://', requests_file.FileAdapter())
		self.description = data.get('description')
		self.homepage = data.get('homepage')
		"""The URL of the homepage for this repository if it was specified."""
		self.id = data['id']
		"""The unique identifier of this repository."""
		self.title = data['title']
		"""The title string of this repository."""
		self.url_base = data['url-base']
		"""The base URL string of files included in this repository."""
		self.collections = utilities.FreezableDict()
		"""The dictionary of the different collection types included in this repository."""
		if 'collections-include' in data:
			# include-files is reversed so the dictionary can get .update()'ed and the first seen will be the value kept
			for include in reversed(data['collections-include']):
				include_data = self._fetch_json(include)
				utilities.validate_json_schema(include_data, 'king-phisher.catalog.collections')
				include_data = include_data['collections']
				for collection_type in include.get('types', COLLECTION_TYPES):
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
			self.collections[collection_type] = Collection(self, collection_type, collection)
		self.collections.freeze()

	def __repr__(self):
		return "<{0} title={1!r} >".format(self.__class__.__name__, self.title)

	def _add_collection_data(self, collection_type, collection_items):
		if collection_type not in COLLECTION_TYPES:
			self.logger.warning('unknown repository collection type: ' + collection_type)
			return
		collection = self.collections.get(collection_type)
		if collection is None:
			collection = utilities.FreezableDict()
		# validate each of the items so we know that the basic keys we expect
		# to be present are set to with the correct value types
		for item in collection_items:
			item['authors'] = tuple(item['authors'])
			item_files = []
			for item_file in item['files']:
				# normalize empty strings to None for signed-by and signature
				if not item_file.get('signature'):
					item_file['signature'] = None
				if not item_file.get('signed-by'):
					item_file['signed-by'] = None
				item_files.append(CollectionItemFile.from_dict(item_file))
			item['files'] = tuple(item_files)
			item = utilities.FreezableDict(sorted(item.items(), key=lambda i: i[0]))
			item.freeze()
			collection[item['name']] = item
		self.collections[collection_type] = collection

	def _fetch(self, item_file, encoding=None, verify=True):
		if isinstance(item_file, dict):
			item_file = CollectionItemFile.from_dict(item_file)
		url = self.url_base + '/' + item_file.path_source
		self.logger.debug("fetching repository data item from: {0} (integrity check: {1})".format(url, ('enabled' if verify else 'disabled')))
		data = self._fetch_url(url)
		if verify:
			self.logger.debug("verifying detached signature from {0} for {1}".format(item_file.signed_by, url))
			self.security_keys.verify(item_file.signed_by, data, binascii.a2b_base64(item_file.signature))
		if encoding:
			data = data.decode(encoding)
		return data

	def _fetch_json(self, item_file, encoding='utf-8', verify=True):
		url = self.url_base + '/'
		if isinstance(item_file, dict):
			url += item_file['path-source']
		else:
			url += item_file.path_source
		self.logger.debug("fetching repository json item from: {0} (integrity check: {1})".format(url, ('enabled' if verify else 'disabled')))
		data = self._fetch_url(url)
		if encoding:
			data = data.decode(encoding)
		data = serializers.JSON.loads(data)
		if verify:
			self.logger.debug("verifying inline signature from {0} for {1}".format(data['signed-by'], url))
			self.security_keys.verify_dict(data, signature_encoding='base64')
		return data

	def _fetch_url(self, url):
		resp = self._req_sess.get(url)
		if not resp.ok:
			self.logger.warning("request to {0} failed with status {1} {2}".format(url, resp.status_code, resp.reason))
			raise RuntimeError('failed to fetch data from: ' + url)
		return resp.content

	def to_dict(self):
		"""
		Dump the instance to a dictionary suitable for being reloaded with
		:py:meth:`.__init__`.

		:return: The instance represented as a dictionary.
		:rtype: dict
		"""
		data = {
			'id': self.id,
			'title': self.title,
			'url-base': self.url_base
		}
		if self.collections:
			data['collections'] = {key: value.to_dict()['items'] for key, value in self.collections.items()}
		if self.description:
			data['description'] = self.description
		if self.homepage:
			data['homepage'] = self.homepage
		return data

	def get_file(self, item_file, encoding=None):
		"""
		Download and return the file data from the repository. If no encoding
		is specified, the data is return as bytes, otherwise it is decoded to a
		string using the specified encoding. The file's contents are verified
		using the signature that must be specified by the *item_file*
		information.

		:param item_file: The information for the file to download.
		:type item_file: :py:class:`.CollectionItemFile`
		:param str encoding: An optional encoding of the remote data.
		:return: The files contents.
		:rtype: bytes, str
		"""
		if not isinstance(item_file, CollectionItemFile):
			raise TypeError('the file object must be a CollectionItemFile instance')
		return self._fetch(item_file, encoding=encoding)

	def get_item(self, collection_type, name):
		"""
		Get the item by it's name from the specified collection type. If the
		repository does not provide the named item, None is returned.

		:param str collection_type: The type of collection the specified item is in.
		:param str name: The name of the item to retrieve.
		:return: The item if the repository provides it, otherwise None.
		"""
		collection = self.collections.get(collection_type, {})
		return collection.get(name)

	def get_item_files(self, collection_type, name, destination):
		"""
		Download all of the file references from the named item.

		:param str collection_type: The type of collection the specified item is in.
		:param str name: The name of the item to retrieve.
		:param str destination: The path of where to save the downloaded files to.
		"""
		item = self.get_item(collection_type, name)
		destination = os.path.abspath(destination)
		self.logger.debug("fetching catalog item: {0}/{1} to {2}".format(collection_type, name, destination))
		if not os.path.isdir(destination):
			os.makedirs(destination, exist_ok=True)
		for item_file in item['files']:
			data = self._fetch(item_file)
			file_destination = os.path.abspath(os.path.join(destination, item_file.path_destination))
			if not file_destination.startswith(destination + os.path.sep):
				raise RuntimeError('file destination is outside of the specified path')
			dir_name = os.path.dirname(file_destination)
			os.makedirs(dir_name, exist_ok=True)
			with open(file_destination, 'wb') as file_h:
				file_h.write(data)

class Catalog(object):
	"""
	An object representing a set of :py:class:`.Repositories` containing add on
	data for the application. This information can then be loaded from an
	arbitrary source.
	"""
	__slots__ = ('__weakref__', 'id', 'created', 'created_by', 'maintainers', 'repositories', 'security_keys')
	logger = logging.getLogger('KingPhisher.Catalog')
	def __init__(self, data, keys=None):
		"""
		:param dict data: The formatted catalog data.
		:param keys: The keys to use for verifying remote data.
		:type keys: :py:class:`~king_phisher.security_keys.SecurityKeys`
		"""
		self.security_keys = keys or security_keys.SecurityKeys()
		"""The :py:class:`~king_phisher.security_keys.SecurityKeys` used for verifying remote data."""
		self.created = dateutil.parser.parse(data['created'])
		"""The timestamp of when the remote data was generated."""
		self.created_by = data['created-by']
		self.id = data['id']
		"""The unique identifier of this catalog."""
		self.maintainers = tuple(maintainer['id'] for maintainer in data['maintainers'])
		"""
		A tuple containing the maintainers of the catalog and repositories.
		These are also the key identities that should be present for verifying
		the remote data.
		"""
		self.repositories = dict((repo['id'], Repository(repo, keys=self.security_keys)) for repo in data['repositories'])
		"""A dict of the :py:class:`.Repository` objects included in this catalog keyed by their id."""
		self.logger.info("initialized catalog with {0:,} repositories".format(len(self.repositories)))

	@classmethod
	def from_url(cls, url, keys=None, encoding='utf-8'):
		"""
		Initialize a new :py:class:`.Catalog` object from a resource at the
		specified URL. The resulting data is validated against a schema file
		with :py:func:`~king_phisher.utilities.validate_json_schema` before
		being passed to :py:meth:`~.__init__`.

		:param str url: The URL to the catalog data to load.
		:param keys: The keys to use for verifying remote data.
		:type keys: :py:class:`~king_phisher.security_keys.SecurityKeys`
		:param str encoding: The encoding of the catalog data.
		:return: The new catalog instance.
		:rtype: :py:class:`.Catalog`
		"""
		keys = keys or security_keys.SecurityKeys()
		req_sess = requests.Session()
		req_sess.mount('file://', requests_file.FileAdapter())
		cls.logger.debug('fetching catalog from: ' + url)
		resp = req_sess.get(url)
		data = resp.content.decode(encoding)
		data = serializers.JSON.loads(data)
		utilities.validate_json_schema(data, 'king-phisher.catalog')
		keys.verify_dict(data, signature_encoding='base64')
		return cls(data, keys=keys)

	def to_dict(self):
		"""
		Dump the instance to a dictionary suitable for being reloaded with
		:py:meth:`.__init__`.

		:return: The instance represented as a dictionary.
		:rtype: dict
		"""
		data = {
			'created': self.created.isoformat() + '+00:00',
			'created-by': self.created_by,
			'id': self.id,
			'maintainers': [{'id': maintainer} for maintainer in self.maintainers],
			'repositories': [repo.to_dict() for repo in self.repositories.values()]
		}
		return data

class CatalogManager(object):
	"""
	Base manager for handling multiple :py:class:`.Catalog` instances.
	"""
	logger = logging.getLogger('KingPhisher.Catalog.Manager')
	def __init__(self, catalog_url=None):
		self.catalogs = {}
		if catalog_url:
			self.add_catalog_url(catalog_url)

	def catalog_ids(self):
		"""
		The key names of the catalogs in the manager.

		:return: The catalogs IDs in the manager instance.
		:rtype: tuple
		"""
		return tuple(self.catalogs.keys())

	def get_repositories(self, catalog_id):
		"""
		Returns repositories from the requested catalog.

		:param str catalog_id: The name of the catalog in which to get names of repositories from.
		:return: tuple
		"""
		return tuple(self.catalogs[catalog_id].repositories.values())

	def add_catalog_url(self, url):
		"""
		Adds the specified catalog to the manager by its URL.

		:param str url: The URL of the catalog to load.
		:return: The catalog.
		:rtype: :py:class:`.Catalog`
		"""
		try:
			catalog = Catalog.from_url(url)
			self.catalogs[catalog.id] = catalog
		except Exception as error:
			self.logger.warning("failed to load catalog from url {0} due to {1}".format(url, error))
			return
		return catalog

	def add_catalog_dict(self, dict_):
		"""
		Adds the specified catalog to the manager by its dict.

		:param dict dict_: The dict of the catalog to load.
		:return: The catalog.
		:rtype: :py:class:`.Catalog`
		"""
		try:
			catalog = Catalog(dict_)
			self.catalogs[catalog.id] = catalog
		except Exception as error:
			self.logger.warning("failed to load catalog from dict due to {}".format(error))
			return
		return catalog

def sign_item_files(local_path, signing_key, repo_path=None):
	"""
	This utility function is used to create a :py:class:`.CollectionItemFile`
	iterator from the specified source to be included in either a catalog file
	or one of it's included files.

	:param str local_path: The real location of where the files exist on disk.
	:param signing_key: The key with which to sign the files for verification.
	:param str repo_path: The path of the repository as it exists on disk.
	"""
	local_path = os.path.abspath(local_path)
	if repo_path is None:
		repo_path = local_path
	else:
		repo_path = os.path.abspath(repo_path)
		if not local_path.startswith(repo_path + os.path.sep):
			raise ValueError('local_path must be a sub-directory of repo_path')
	walker = smoke_zephyr.utilities.FileWalker(local_path, absolute_path=True, skip_dirs=True)
	for local_file_path in walker:
		with open(local_file_path, 'rb') as file_h:
			signature = signing_key.sign(file_h.read())

		# source and destination are flipped here because the processing of the
		# data is done in reverse, meaning our source file as it exists on disk
		# will be the destination when the client fetches it
		source_file_path = os.path.relpath(local_file_path, repo_path)
		if os.path.isdir(local_path):
			destination_file_path = os.path.relpath(local_file_path, os.path.relpath(os.path.dirname(local_path), repo_path))
		else:
			destination_file_path = os.path.relpath(local_file_path, os.path.dirname(local_path))

		signature = binascii.b2a_base64(signature).decode('utf-8').rstrip()
		item_file = CollectionItemFile(
			path_destination=destination_file_path,
			path_source=source_file_path,
			signature=signature,
			signed_by=signing_key.id
		)
		yield item_file
