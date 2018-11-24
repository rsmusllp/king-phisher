#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  king_phisher/server/graphql/types/templates.py
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

from __future__ import absolute_import
import datetime
import functools
import itertools
import json
import logging
import os

from . import misc as gql_misctypes
from king_phisher import utilities
from king_phisher.server import web_tools

import graphene.relay
import graphene.types.resolver
import graphene.types.utils
import jsonschema
import smoke_zephyr.utilities
import yaml

__all__ = ('SiteTemplate', 'SiteTemplateConnection', 'SiteTemplateMetadata')

logger = logging.getLogger('KingPhisher.Server.GraphQL.Types.Templates')

def _find_metadata(path):
	prefixes = ('.', '_')
	serializers = {
		'.json': json,
		'.yaml': yaml,
		'.yml': yaml,
	}
	for prefix, (suffix, serializer) in itertools.product(prefixes, serializers.items()):
		file_path = os.path.join(path, prefix + 'metadata' + suffix)
		if not os.path.isfile(file_path):
			continue
		if not os.access(file_path, os.R_OK):
			continue
		return file_path, serializer
	return None, None

def _load_metadata(path):
	file_path, serializer = _find_metadata(path)
	if file_path is None:
		logger.info('found no metadata file for path: ' + path)
		return
	with open(file_path, 'r') as file_h:
		metadata = serializer.load(file_h)
	# manually set the version to a string so the input format is more forgiving
	if isinstance(metadata.get('version'), (float, int)):
		metadata['version'] = str(metadata['version'])
	try:
		utilities.validate_json_schema(metadata, 'king-phisher.template.site.metadata')
	except jsonschema.exceptions.ValidationError:
		logger.error("template metadata file: {0} failed to pass schema validation".format(file_path), exc_info=True)
		return None
	return metadata

def _search_filter(path):
	file_path, serializer = _find_metadata(path)
	return file_path is not None

class SiteTemplateMetadata(graphene.ObjectType):
	class Meta:
		default_resolver = graphene.types.resolver.dict_resolver
	authors = graphene.List(graphene.String)
	classifiers = graphene.List(graphene.String)
	description = graphene.Field(graphene.String)
	homepage = graphene.Field(graphene.String)
	pages = graphene.List(graphene.String)
	reference_urls = graphene.List(graphene.String)
	title = graphene.Field(graphene.String)
	version = graphene.Field(graphene.String)

class SiteTemplate(graphene.ObjectType):
	class Meta:
		interfaces = (gql_misctypes.RelayNode,)
	created = gql_misctypes.DateTimeScalar()
	hostname = graphene.Field(graphene.String)
	path = graphene.Field(graphene.String)
	metadata = graphene.Field(SiteTemplateMetadata)
	def __init__(self, disk_path, *args, **kwargs):
		self._disk_path = disk_path
		super(SiteTemplate, self).__init__(*args, **kwargs)

	@classmethod
	def from_path(cls, disk_path, resource_path, **kwargs):
		if not os.path.isdir(disk_path):
			logger.warning("requested template path: {0} is not a directory".format(disk_path))
			return None
		created = utilities.datetime_local_to_utc(datetime.datetime.fromtimestamp(os.path.getctime(disk_path)))
		return cls(disk_path, created=created, path=resource_path, **kwargs)

	@classmethod
	def resolve(cls, info, **kwargs):
		server_config = info.context.get('server_config')
		if server_config is None:
			logger.warning('can not resolve templates without the server configuration')
			return
		web_root = os.path.normpath(server_config.get('server.web_root'))
		hostname = kwargs.get('hostname')

		resource_path = kwargs.get('path')
		if resource_path is None:
			return
		resource_path = resource_path.lstrip('/')
		if server_config.get('server.vhost_directories'):
			if hostname is None:
				logger.warning('can not resolve templates without a hostname when vhost_directories is enabled')
				return
			disk_path = os.path.join(web_root, hostname, resource_path)
		else:
			if hostname is not None:
				logger.debug('ignoring the hostname parameter because vhost_directories is not enabled')
				hostname = None
			disk_path = os.path.join(web_root, resource_path)
		disk_path = os.path.abspath(disk_path)
		# check for directory traversal
		if not disk_path.startswith(web_root + os.path.sep):
			logger.warning('can not resolve templates when the normalized path is outside of the web root')
			return
		return cls.from_path(disk_path, resource_path, hostname=hostname)

	def resolve_metadata(self, info, **kwargs):
		return _load_metadata(self._disk_path)

class SiteTemplateConnection(graphene.relay.Connection):
	class Meta:
		node = SiteTemplate
	total = graphene.Int()
	@classmethod
	def resolve(cls, info, **kwargs):
		server_config = info.context.get('server_config')
		if server_config is None:
			logger.warning('can not resolve templates without the server configuration')
			return []
		web_root = os.path.normpath(server_config.get('server.web_root'))
		hostname = kwargs.get('hostname')

		if server_config.get('server.vhost_directories'):
			if hostname is None:
				directories = ((vhost, os.path.join(web_root, vhost)) for vhost in web_tools.get_vhost_directories(server_config))
			else:
				directory = os.path.join(web_root, hostname)
				if not os.path.isdir(directory):
					logger.warning("can not resolve templates for hostname: {0} (invalid directory)".format(hostname))
					return []
				directories = ((hostname, os.path.join(web_root, hostname)),)
		else:
			if hostname is not None:
				logger.debug('ignoring the hostname parameter because vhost_directories is not enabled')
			directories = ((None, web_root),)

		iterate_templates = functools.partial(
			smoke_zephyr.utilities.FileWalker,
			absolute_path=True,
			filter_func=_search_filter,
			follow_links=True,
			max_depth=kwargs.get('max_depth')
		)
		templates = []
		for hostname, directory in directories:
			for disk_path in iterate_templates(directory):
				resource_path = os.path.relpath(disk_path, directory)
				templates.append(SiteTemplate.from_path(disk_path, resource_path, hostname=hostname))
		return templates
