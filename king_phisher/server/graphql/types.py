#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  king_phisher/server/graphql/types.py
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

import graphene.types.utils
import graphql.language.ast

# replacement graphql scalars
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

# misc definitions
class RelayNode(graphene.relay.Node):
	@classmethod
	def from_global_id(cls, global_id):
		return global_id

	@classmethod
	def to_global_id(cls, _, local_id):
		return local_id

class FilterOperatorEnum(graphene.Enum):
	EQ = 'eq'
	GE = 'ge'
	GT = 'gt'
	LE = 'le'
	LT = 'lt'
	NE = 'ne'

class FilterInput(graphene.InputObjectType):
	AND = graphene.List('king_phisher.server.graphql.types.FilterInput', name='and')
	OR = graphene.List('king_phisher.server.graphql.types.FilterInput', name='or')
	field = graphene.String()
	value = AnyScalar()
	operator = FilterOperatorEnum()

class SortDirectionEnum(graphene.Enum):
	AESC = 'aesc'
	DESC = 'desc'

class SortInput(graphene.InputObjectType):
	field = graphene.String(required=True)
	direction = SortDirectionEnum()
