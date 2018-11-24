#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  king_phisher/server/graphql/schema.py
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
import logging

import king_phisher.version as version
import king_phisher.server.web_tools as web_tools
import king_phisher.server.graphql.middleware as gql_middleware
import king_phisher.server.graphql.types as gql_types

import graphene.types.utils

logger = logging.getLogger('KingPhisher.Server.GraphQL.Schema')

# top level query object for the schema
class Query(graphene.ObjectType):
	"""
	This is the root query object used for GraphQL queries.
	"""
	db = graphene.Field(gql_types.Database)
	geoloc = graphene.Field(gql_types.GeoLocation, ip=graphene.String())
	hostnames = graphene.List(graphene.String)
	plugin = graphene.Field(gql_types.Plugin, name=graphene.String())
	plugins = gql_types.ConnectionField(gql_types.PluginConnection)
	site_template = graphene.Field(gql_types.SiteTemplate, hostname=graphene.String(), path=graphene.String())
	site_templates = gql_types.ConnectionField(gql_types.SiteTemplateConnection, hostname=graphene.String(), max_depth=graphene.Int())
	version = graphene.Field(graphene.String)
	def resolve_db(self, info, **kwargs):
		return gql_types.Database()

	def resolve_geoloc(self, info, **kwargs):
		ip_address = kwargs.get('ip')
		if ip_address is None:
			return
		return gql_types.GeoLocation.from_ip_address(ip_address)

	def resolve_hostnames(self, info, **kwargs):
		server_config = info.context.get('server_config')
		if server_config is None:
			logger.warning('can not determine hostnames without the server configuration')
			return
		return web_tools.get_hostnames(server_config)

	def resolve_plugin(self, info, **kwargs):
		return gql_types.Plugin.resolve(info, **kwargs)

	def resolve_plugins(self, info, **kwargs):
		return gql_types.PluginConnection.resolve(info, **kwargs)

	def resolve_site_template(self, info, **kwargs):
		return gql_types.SiteTemplate.resolve(info, **kwargs)

	def resolve_site_templates(self, info, **kwargs):
		return gql_types.SiteTemplateConnection.resolve(info, **kwargs)

	def resolve_version(self, info, **kwargs):
		return version.version

class Schema(graphene.Schema):
	"""
	This is the top level schema object for GraphQL. It automatically sets up
	sane defaults to be used by the King Phisher server including setting
	the query to :py:class:`.Query` and adding the
	:py:class:`.AuthorizationMiddleware` to each execution.
	"""
	def __init__(self, **kwargs):
		kwargs['auto_camelcase'] = True
		kwargs['query'] = Query
		super(Schema, self).__init__(**kwargs)

	def execute(self, *args, **kwargs):
		if 'context_value' not in kwargs:
			kwargs['context_value'] = {}
		middleware = list(kwargs.pop('middleware', []))
		middleware.insert(0, gql_middleware.AuthorizationMiddleware())
		kwargs['middleware'] = middleware
		return super(Schema, self).execute(*args, **kwargs)

	def execute_file(self, path, *args, **kwargs):
		with open(path, 'r') as file_h:
			query = file_h.read()
		return self.execute(query, *args, **kwargs)
