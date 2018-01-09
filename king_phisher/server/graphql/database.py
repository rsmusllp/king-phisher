#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  king_phisher/server/graphql/database.py
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

import functools
import operator

import king_phisher.server.database.models as db_models
import king_phisher.server.graphql.types as gql_types
import king_phisher.server.graphql.geolocation as gql_geolocation
import king_phisher.server.graphql.middleware as gql_middleware

import graphene
import graphene.relay.connection
import graphene.types
import graphene.types.utils
import graphene_sqlalchemy
import graphql_relay.connection.arrayconnection
import smoke_zephyr.utilities
import sqlalchemy.orm
import sqlalchemy.orm.query

def sa_get_relationship(session, model, name):
	"""
	Resolve the relationship on a SQLAlchemy model to either an object (in the
	case of one-to-one relationships) or a query to all of the objects (in the
	case of one-to-many relationships).

	:param session: The SQLAlchemy session to associate the query with.
	:param model: The SQLAlchemy model of the object associated with the relationship.
	:param name: The name of the relationship as it exists in the *model*.
	:return: Either the object or a SQLAlchemy query for the objects.
	"""
	mapper = sqlalchemy.inspect(model.__class__)
	relationship = mapper.relationships[name]
	foreign_model = db_models.database_tables[relationship.table.name].model
	query = session.query(foreign_model)
	if relationship.uselist:
		column_name = relationship.primaryjoin.right.name
		return query.filter(getattr(foreign_model, column_name) == model.id)
	column_name = relationship.primaryjoin.left.name
	query = query.filter(getattr(foreign_model, column_name) == getattr(model, relationship.primaryjoin.right.name))
	return query.first()

def sa_object_resolver(attname, default_value, model, info, **kwargs):
	"""
	Resolve the attribute for the given SQLAlchemy model object. If the
	attribute is a relationship, use :py:func:`.sq_get_relationship` to resolve
	it.

	:param str attname: The name of the attribute to resolve on the object.
	:param default_value: The default value to return if the attribute is unavailable.
	:param model: The SQLAlchemy model to resolve the attribute for.
	:type model: :py:class:`sqlalchemy.ext.declarative.api.Base`
	:param info: The resolve information for this execution.
	:type info: :py:class:`graphql.execution.base.ResolveInfo`
	"""
	mapper = sqlalchemy.inspect(model.__class__)
	if attname in mapper.relationships:
		return sa_get_relationship(info.context['session'], model, attname)
	return getattr(model, attname, default_value)

sa_object_meta = functools.partial(dict, default_resolver=sa_object_resolver, interfaces=(gql_types.RelayNode,))

# custom sqlalchemy related objects
class SQLAlchemyConnectionField(graphene_sqlalchemy.SQLAlchemyConnectionField):
	__connection_types = {}
	def __init__(self, node, *args, **kwargs):
		if 'filter' not in kwargs:
			kwargs['filter'] = gql_types.FilterInput()
		if 'sort' not in kwargs:
			kwargs['sort'] = graphene.List(gql_types.SortInput)
		node = self.connection_factory(node)
		super(SQLAlchemyConnectionField, self).__init__(node, *args, **kwargs)

	@classmethod
	def connection_factory(cls, node):
		name = node.__name__ + 'Connection'
		if name in cls.__connection_types:
			return cls.__connection_types[name]
		connection_type = type(
			node.__name__ + 'Connection',
			(graphene.relay.Connection,),
			{
				'Meta': type('Meta', (), {'node': node}),
				'total': graphene.Int()
			}
		)
		cls.__connection_types[name] = connection_type
		return connection_type

	@classmethod
	def connection_resolver(cls, resolver, connection, model, root, info, **kwargs):
		iterable = resolver(root, info, **kwargs)
		if iterable is None:
			iterable = cls.get_query(model, info, **kwargs)
			_len = iterable.count()
		elif isinstance(iterable, sqlalchemy.orm.query.Query):
			iterable = cls.query_shim(model, info, iterable, **kwargs)
			_len = iterable.count()
		else:
			_len = len(iterable)
		connection = graphql_relay.connection.arrayconnection.connection_from_list_slice(
			iterable,
			kwargs,
			slice_start=0,
			list_length=_len,
			list_slice_length=_len,
			connection_type=functools.partial(connection, total=_len),
			pageinfo_type=graphene.relay.connection.PageInfo,
			edge_type=connection.Edge
		)
		connection.iterable = iterable
		connection.length = _len
		return connection

	@classmethod
	def _query_filter(cls, model, info, query, gql_filter):
		sql_filter = cls.__query_filter(model, info, gql_filter)
		if sql_filter is not None:
			query = query.filter(sql_filter)
		return query

	@classmethod
	def __query_filter(cls, model, info, gql_filter):
		# precedence: AND, OR, field
		sql_filter = None
		if gql_filter.get('AND'):
			sql_filter = sqlalchemy.and_(*cls._query_filter_list(model, info, gql_filter['AND']))
		if gql_filter.get('OR'):
			if sql_filter is not None:
				raise ValueError('the \'and\', \'or\', and \'field\' filter operators are mutually exclusive')
			sql_filter = sqlalchemy.or_(*cls._query_filter_list(model, info, gql_filter['OR']))

		if gql_filter.get('field'):
			if sql_filter is not None:
				raise ValueError('the \'and\', \'or\', and \'field\' filter operators are mutually exclusive')
			operator_name = gql_filter.get('operator', 'eq')
			if operator_name not in ('eq', 'ge', 'gt', 'le', 'lt', 'ne'):
				raise ValueError('invalid operator: ' + operator_name)
			comparison_operator = getattr(operator, operator_name)
			gql_field = gql_filter['field']
			sql_field = smoke_zephyr.utilities.parse_case_camel_to_snake(gql_field)
			if '_' in gql_field or sql_field not in model.metatable().column_names:
				raise ValueError('invalid filter field: ' + gql_field)
			if gql_middleware.AuthorizationMiddleware.info_has_read_prop_access(info, model, sql_field):
				sql_filter = comparison_operator(getattr(model, sql_field), gql_filter.get('value', None))
		return sql_filter

	@classmethod
	def _query_filter_list(cls, model, info, gql_filters):
		query_filter_list = [cls.__query_filter(model, info, gql_filter) for gql_filter in gql_filters]
		return [query_filter for query_filter in query_filter_list if query_filter is not None]

	@classmethod
	def _query_sort(cls, model, info, query, gql_sort):
		for field in gql_sort:
			direction = field.get('direction', 'aesc')
			gql_field = field['field']
			sql_field = smoke_zephyr.utilities.parse_case_camel_to_snake(gql_field)
			if '_' in gql_field or sql_field not in model.metatable().column_names:
				raise ValueError('invalid sort field: ' + gql_field)
			if not gql_middleware.AuthorizationMiddleware.info_has_read_prop_access(info, model, sql_field):
				continue
			if direction == 'aesc':
				field = getattr(model, sql_field)
			elif direction == 'desc':
				field = getattr(model, sql_field).desc()
			else:
				raise ValueError('sort direction must be either \'aesc\' or \'desc\'')
			query = query.order_by(field)
		return query

	@classmethod
	def query_shim(cls, model, info, query, **kwargs):
		if kwargs.get('filter'):
			query = cls._query_filter(model, info, query, kwargs['filter'])
		if kwargs.get('sort'):
			query = cls._query_sort(model, info, query, kwargs['sort'])
		return query

	@classmethod
	def get_query(cls, model, info, **kwargs):
		query = super(SQLAlchemyConnectionField, cls).get_query(model, info, **kwargs)
		query = query.options(sqlalchemy.orm.raiseload('*'))
		return cls.query_shim(model, info, query, **kwargs)

	@property
	def type(self):
		# this is to bypass the one from
		# graphene_sqlalchemy.SQLAlchemyConnectionField which breaks
		return graphene.types.utils.get_type(self._type)

class SQLAlchemyObjectType(graphene_sqlalchemy.SQLAlchemyObjectType):
	class Meta:
		abstract = True

	@classmethod
	def get_query(cls, info, **kwargs):
		query = super(SQLAlchemyObjectType, cls).get_query(info)
		query = query.options(sqlalchemy.orm.raiseload('*'))
		model = cls._meta.model
		for field, value in kwargs.items():
			query = query.filter(getattr(model, field) == value)
		return query

# database graphql objects
class AlertSubscription(SQLAlchemyObjectType):
	Meta = sa_object_meta(model=db_models.AlertSubscription)
	expiration = gql_types.DateTimeScalar()
	has_expired = graphene.Boolean()

class Credential(SQLAlchemyObjectType):
	Meta = sa_object_meta(model=db_models.Credential)
	submitted = gql_types.DateTimeScalar()

class DeaddropConnection(SQLAlchemyObjectType):
	Meta = sa_object_meta(model=db_models.DeaddropConnection)
	first_seen = gql_types.DateTimeScalar()
	last_seen = gql_types.DateTimeScalar()
	ip_geoloc = graphene.Field(gql_geolocation.GeoLocation)
	def resolve_ip_geoloc(self, info, **kwargs):
		ip = self.ip
		if not ip:
			return
		return gql_geolocation.GeoLocation.from_ip_address(ip)

class DeaddropDeployment(SQLAlchemyObjectType):
	Meta = sa_object_meta(model=db_models.DeaddropDeployment)
	# relationships
	deaddrop_connections = SQLAlchemyConnectionField(DeaddropConnection)

class Visit(SQLAlchemyObjectType):
	Meta = sa_object_meta(model=db_models.Visit)
	first_seen = gql_types.DateTimeScalar()
	last_seen = gql_types.DateTimeScalar()
	ip_geoloc = graphene.Field(gql_geolocation.GeoLocation)
	# relationships
	credentials = SQLAlchemyConnectionField(Credential)
	def resolve_ip_geoloc(self, info, **kwargs):
		ip = self.ip
		if not ip:
			return
		return gql_geolocation.GeoLocation.from_ip_address(ip)

class LandingPage(SQLAlchemyObjectType):
	Meta = sa_object_meta(model=db_models.LandingPage)
	first_visits = SQLAlchemyConnectionField(Visit)

class Message(SQLAlchemyObjectType):
	Meta = sa_object_meta(model=db_models.Message)
	opened = gql_types.DateTimeScalar()
	opener_ip_geoloc = graphene.Field(gql_geolocation.GeoLocation)
	reported = gql_types.DateTimeScalar()
	sent = gql_types.DateTimeScalar()
	# relationships
	credentials = SQLAlchemyConnectionField(Credential)
	visits = SQLAlchemyConnectionField(Visit)
	def resolve_opener_ip_geoloc(self, info, **kwargs):
		opener_ip = self.opener_ip
		if not opener_ip:
			return
		return gql_geolocation.GeoLocation.from_ip_address(opener_ip)

class Campaign(SQLAlchemyObjectType):
	Meta = sa_object_meta(model=db_models.Campaign)
	created = gql_types.DateTimeScalar()
	expiration = gql_types.DateTimeScalar()
	has_expired = graphene.Boolean()
	# relationships
	alert_subscriptions = SQLAlchemyConnectionField(AlertSubscription)
	credentials = SQLAlchemyConnectionField(Credential)
	deaddrop_connections = SQLAlchemyConnectionField(DeaddropConnection)
	deaddrop_deployments = SQLAlchemyConnectionField(DeaddropDeployment)
	landing_pages = SQLAlchemyConnectionField(LandingPage)
	messages = SQLAlchemyConnectionField(Message)
	visits = SQLAlchemyConnectionField(Visit)

class CampaignType(SQLAlchemyObjectType):
	Meta = sa_object_meta(model=db_models.CampaignType)
	# relationships
	campaigns = SQLAlchemyConnectionField(Campaign)

class Company(SQLAlchemyObjectType):
	Meta = sa_object_meta(model=db_models.Company)
	# relationships
	campaigns = SQLAlchemyConnectionField(Campaign)

class CompanyDepartment(SQLAlchemyObjectType):
	Meta = sa_object_meta(model=db_models.CompanyDepartment)
	# relationships
	messages = SQLAlchemyConnectionField(Message)

class Industry(SQLAlchemyObjectType):
	Meta = sa_object_meta(model=db_models.Industry)
	# relationships
	companies = SQLAlchemyConnectionField(Company)

class User(SQLAlchemyObjectType):
	Meta = sa_object_meta(model=db_models.User)
	expiration = gql_types.DateTimeScalar()
	has_expired = graphene.Boolean()
	last_login = gql_types.DateTimeScalar()
	# relationships
	alert_subscriptions = SQLAlchemyConnectionField(AlertSubscription)
	campaigns = SQLAlchemyConnectionField(Campaign)

class Database(graphene.ObjectType):
	alert_subscription = graphene.Field(AlertSubscription, id=graphene.String())
	alert_subscriptions = SQLAlchemyConnectionField(AlertSubscription)
	campaign_type = graphene.Field(CampaignType, id=graphene.String())
	campaign_types = SQLAlchemyConnectionField(CampaignType)
	campaign = graphene.Field(Campaign, id=graphene.String(), name=graphene.String())
	campaigns = SQLAlchemyConnectionField(Campaign)
	company = graphene.Field(Company, id=graphene.String(), name=graphene.String())
	companies = SQLAlchemyConnectionField(Company)
	company_department = graphene.Field(CompanyDepartment, id=graphene.String())
	company_departments = SQLAlchemyConnectionField(CompanyDepartment)
	credential = graphene.Field(Credential, id=graphene.String())
	credentials = SQLAlchemyConnectionField(Credential)
	deaddrop_connection = graphene.Field(DeaddropConnection, id=graphene.String())
	deaddrop_connections = SQLAlchemyConnectionField(DeaddropConnection)
	deaddrop_deployment = graphene.Field(DeaddropDeployment, id=graphene.String())
	deaddrop_deployments = SQLAlchemyConnectionField(DeaddropDeployment)
	industry = graphene.Field(Industry, id=graphene.String())
	industries = SQLAlchemyConnectionField(Industry)
	landing_page = graphene.Field(LandingPage, id=graphene.String())
	landing_pages = SQLAlchemyConnectionField(LandingPage)
	message = graphene.Field(Message, id=graphene.String())
	messages = SQLAlchemyConnectionField(Message)
	user = graphene.Field(User, id=graphene.String(), name=graphene.String())
	users = SQLAlchemyConnectionField(User)
	visit = graphene.Field(Visit, id=graphene.String())
	visits = SQLAlchemyConnectionField(Visit)
	def resolve_alert_subscription(self, info, **kwargs):
		return AlertSubscription.get_query(info, **kwargs).first()

	def resolve_campaign(self, info, **kwargs):
		return Campaign.get_query(info, **kwargs).first()

	def resolve_campaign_type(self, info, **kwargs):
		return CampaignType.get_query(info, **kwargs).first()

	def resolve_company(self, info, **kwargs):
		return Company.get_query(info, **kwargs).first()

	def resolve_company_department(self, info, **kwargs):
		return CompanyDepartment.get_query(info, **kwargs).first()

	def resolve_credential(self, info, **kwargs):
		return Credential.get_query(info, **kwargs).first()

	def resolve_deaddrop_connection(self, info, **kwargs):
		return DeaddropConnection.get_query(info, **kwargs).first()

	def resolve_deaddrop_deployment(self, info, **kwargs):
		return DeaddropDeployment.get_query(info, **kwargs).first()

	def resolve_industry(self, info, **kwargs):
		return Industry.get_query(info, **kwargs).first()

	def resolve_landing_page(self, info, **kwargs):
		return LandingPage.get_query(info, **kwargs).first()

	def resolve_message(self, info, **kwargs):
		return Message.get_query(info, **kwargs).first()

	def resolve_user(self, info, **kwargs):
		return User.get_query(info, **kwargs).first()

	def resolve_visit(self, info, **kwargs):
		return Visit.get_query(info, **kwargs).first()
