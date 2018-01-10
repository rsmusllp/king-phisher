#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  king_phisher/server/graphql/types/misc.py
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

import king_phisher.geoip as geoip
import king_phisher.ipaddress as ipaddress

import graphene.types.utils
import graphql.language.ast

__all__ = ('GeoLocation', 'Plugin', 'PluginConnection', 'RelayNode')

# custom enum types
class FilterOperatorEnum(graphene.Enum):
	EQ = 'eq'
	GE = 'ge'
	GT = 'gt'
	LE = 'le'
	LT = 'lt'
	NE = 'ne'

class SortDirectionEnum(graphene.Enum):
	AESC = 'aesc'
	DESC = 'desc'

# misc definitions
class RelayNode(graphene.relay.Node):
	@classmethod
	def from_global_id(cls, global_id):
		return global_id

	@classmethod
	def to_global_id(cls, _, local_id):
		return local_id

# custom scalar types
class AnyScalar(graphene.types.Scalar):
	@staticmethod
	def serialize(dt):
		raise NotImplementedError()

	@staticmethod
	def parse_literal(node):
		if isinstance(node, graphql.language.ast.FloatValue):
			return float(node.value)
		if isinstance(node, graphql.language.ast.IntValue):
			return int(node.value)
		return node.value

	@staticmethod
	def parse_value(value):
		return value

class DateTimeScalar(graphene.types.Scalar):
	@staticmethod
	def serialize(dt):
		return dt

	@staticmethod
	def parse_literal(node):
		if isinstance(node, graphql.language.ast.StringValue):
			return datetime.datetime.strptime(node.value, '%Y-%m-%dT%H:%M:%S.%f')

	@staticmethod
	def parse_value(value):
		return datetime.datetime.strptime(value, '%Y-%m-%dT%H:%M:%S.%f')

# custom compound types
class GeoLocation(graphene.ObjectType):
	city = graphene.Field(graphene.String)
	continent = graphene.Field(graphene.String)
	coordinates = graphene.List(graphene.Float)
	country = graphene.Field(graphene.String)
	postal_code = graphene.Field(graphene.String)
	time_zone = graphene.Field(graphene.String)
	@classmethod
	def from_ip_address(cls, ip_address):
		ip_address = ipaddress.ip_address(ip_address)
		if ip_address.is_private:
			return
		result = geoip.lookup(ip_address)
		if result is None:
			return
		return cls(**result)

class Plugin(graphene.ObjectType):
	class Meta:
		interfaces = (RelayNode,)
	authors = graphene.List(graphene.String)
	title = graphene.Field(graphene.String)
	description = graphene.Field(graphene.String)
	homepage = graphene.Field(graphene.String)
	name = graphene.Field(graphene.String)
	version = graphene.Field(graphene.String)
	@classmethod
	def from_plugin(cls, plugin):
		return cls(
			authors=plugin.authors,
			description=plugin.description,
			homepage=plugin.homepage,
			name=plugin.name,
			title=plugin.title,
			version=plugin.version
		)

class PluginConnection(graphene.relay.Connection):
	class Meta:
		node = Plugin
	total = graphene.Int()
	def resolve_total(self, info, **kwargs):
		return len(info.context.get('plugin_manager', {}))

# custom compound input types
class FilterInput(graphene.InputObjectType):
	and_ = graphene.List('king_phisher.server.graphql.types.misc.FilterInput', name='and')
	or_ = graphene.List('king_phisher.server.graphql.types.misc.FilterInput', name='or')
	field = graphene.String()
	value = AnyScalar()
	operator = FilterOperatorEnum()

class SortInput(graphene.InputObjectType):
	field = graphene.String(required=True)
	direction = SortDirectionEnum()
