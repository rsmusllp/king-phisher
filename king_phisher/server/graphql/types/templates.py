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
import itertools
import json
import logging
import os

from . import misc as gql_misctypes
from king_phisher import utilities

import graphene.types.utils
import yaml

__all__ = ('Template', 'TemplateMetadata')

logger = logging.getLogger('KingPhisher.Server.GraphQL.Types.Templates')

def _load_metadata(path):
	prefixes = ('.', '_')
	serializers = {
		'.json': json,
		'.yaml': yaml,
		'.yml': yaml,
	}
	for prefix, (suffix, serializer) in itertools.product(prefixes, serializers.items()):
		metadata = os.path.join(path, prefix + 'metadata' + suffix)
		if not os.path.isfile(metadata):
			continue
		if not os.access(metadata, os.R_OK):
			continue
		with open(metadata, 'r') as file_h:
			return serializer.load(file_h)
	logger.info('found no metadata file for path: ' + path)

class TemplateMetadata(graphene.ObjectType):
	authors = graphene.List(graphene.String)
	description = graphene.Field(graphene.String)
	homepage = graphene.Field(graphene.String)
	#name = graphene.Field(graphene.String)
	title = graphene.Field(graphene.String)
	version = graphene.Field(graphene.String)
	classifiers = graphene.List(graphene.String)
	reference_urls = graphene.List(graphene.String)
	@classmethod
	def from_path(cls, disk_path):
		metadata = _load_metadata(disk_path)
		if not metadata:
			return
		# todo: need to validate the returned metadata with a json schema
		return cls(**metadata)

class Template(graphene.ObjectType):
	class Meta:
		interfaces = (gql_misctypes.RelayNode,)
	created = gql_misctypes.DateTimeScalar()
	hostname = graphene.Field(graphene.String)
	path = graphene.Field(graphene.String)
	metadata = graphene.Field(TemplateMetadata)
	def __init__(self, disk_path, *args, **kwargs):
		self._disk_path = disk_path
		super(Template, self).__init__(*args, **kwargs)

	@classmethod
	def from_path(cls, disk_path, resource_path, **kwargs):
		if not os.path.isdir(disk_path):
			logger.warning("requested template path: {0} is not a directory".format(disk_path))
			return None
		created = utilities.datetime_local_to_utc(datetime.datetime.fromtimestamp(os.path.getctime(disk_path)))
		return cls(disk_path, created=created, path=resource_path, **kwargs)

	@classmethod
	def resolve(cls, info, **kwargs):
		hostname = kwargs.get('hostname')
		resource_path = kwargs.get('path')
		if resource_path is None:
			return
		resource_path = resource_path.lstrip('/')
		server_config = info.context.get('server_config')
		if server_config is None:
			logger.warning('can not resolve templates without the server configuration')
			return
		web_root = os.path.normpath(server_config.get('server.web_root'))
		if server_config.get('server.vhost_directories'):
			if hostname is None:
				logger.warning('can not resolve templates without a hostname when vhost_directories is enabled')
				return
			disk_path = os.path.join(web_root, hostname, resource_path)
		else:
			if hostname is not None:
				logger.debug('ignoring the hostname parameter because vhost_directories is not enabled')
			disk_path = os.path.join(web_root, resource_path)
		disk_path = os.path.abspath(disk_path)
		# check for directory traversal
		if not disk_path.startswith(web_root + os.path.sep):
			logger.warning('can not resolve templates when the normalized path is outside of the web root')
			return
		return cls.from_path(disk_path, resource_path, hostname=hostname)

	def resolve_metadata(self, info, **kwargs):
		return TemplateMetadata.from_path(self._disk_path)
