#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  king_phisher/server/graphql.py
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

import datetime
import functools

import king_phisher.geoip as geoip
import king_phisher.ipaddress as ipaddress
import king_phisher.server.database.models as db_models
import king_phisher.version as version

import graphene
import graphene.relay.connection
import graphene.types
import graphene.types.utils
import graphql_relay.connection.arrayconnection
import graphene_sqlalchemy

class SQLAlchemyConnectionField(graphene_sqlalchemy.SQLAlchemyConnectionField):
	__connection_types = {}
	def __init__(self, node, *args, **kwargs):
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
		if isinstance(iterable, Query):
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

	@property
	def type(self):
		# this is to bypass the one from
		# graphene_sqlalchemy.SQLAlchemyConnectionField which breaks
		return graphene.types.utils.get_type(self._type)

# replacement graphql types
class DateTime(graphene.types.Scalar):
	@staticmethod
	def serialize(dt):
		return dt

	@staticmethod
	def parse_literal(node):
		if isinstance(node, graphene.language.ast.StringValue):
			return datetime.datetime.strptime(node.value, '%Y-%m-%dT%H:%M:%S.%f')

	@staticmethod
	def parse_value(value):
		return datetime.datetime.strptime(value, '%Y-%m-%dT%H:%M:%S.%f')

class RelayNode(graphene.relay.Node):
	@classmethod
	def from_global_id(cls, global_id):
		return global_id

	@classmethod
	def to_global_id(cls, _, local_id):
		return local_id

# misc graphql objects
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

# database graphql objects
class AlertSubscription(graphene_sqlalchemy.SQLAlchemyObjectType):
	class Meta:
		model = db_models.AlertSubscription
		interfaces = (RelayNode,)
	mute_timestamp = DateTime()

class Credential(graphene_sqlalchemy.SQLAlchemyObjectType):
	class Meta:
		model = db_models.Credential
		interfaces = (RelayNode,)
	submitted = DateTime()

class DeaddropConnection(graphene_sqlalchemy.SQLAlchemyObjectType):
	class Meta:
		model = db_models.DeaddropConnection
		interfaces = (RelayNode,)
	first_seen = DateTime()
	last_seen = DateTime()
	visitor_geoloc = graphene.Field(GeoLocation)
	def resolve_visitor_geoloc(self, info, **kwargs):
		visitor_ip = self.visitor_ip
		if not visitor_ip:
			return
		return GeoLocation.from_ip_address(visitor_ip)

class DeaddropDeployment(graphene_sqlalchemy.SQLAlchemyObjectType):
	class Meta:
		model = db_models.DeaddropDeployment
		interfaces = (RelayNode,)
	# relationships
	deaddrop_connections = SQLAlchemyConnectionField(DeaddropConnection)

class Visit(graphene_sqlalchemy.SQLAlchemyObjectType):
	class Meta:
		model = db_models.Visit
		interfaces = (RelayNode,)
	first_seen = DateTime()
	last_seen = DateTime()
	visitor_geoloc = graphene.Field(GeoLocation)
	# relationships
	credentials = SQLAlchemyConnectionField(Credential)
	def resolve_visitor_geoloc(self, info, **kwargs):
		visitor_ip = self.visitor_ip
		if not visitor_ip:
			return
		return GeoLocation.from_ip_address(visitor_ip)

class LandingPage(graphene_sqlalchemy.SQLAlchemyObjectType):
	class Meta:
		model = db_models.LandingPage
		interfaces = (RelayNode,)
	first_visits = SQLAlchemyConnectionField(Visit)

class Message(graphene_sqlalchemy.SQLAlchemyObjectType):
	class Meta:
		model = db_models.Message
		interfaces = (RelayNode,)
	opened = DateTime()
	opener_geoloc = graphene.Field(GeoLocation)
	reported = DateTime()
	sent = DateTime()
	# relationships
	credentials = SQLAlchemyConnectionField(Credential)
	visits = SQLAlchemyConnectionField(Visit)
	def resolve_opener_geoloc(self, info, **kwargs):
		opener_ip = self.opener_ip
		if not opener_ip:
			return
		return GeoLocation.from_ip_address(opener_ip)

class Campaign(graphene_sqlalchemy.SQLAlchemyObjectType):
	class Meta:
		model = db_models.Campaign
		interfaces = (RelayNode,)
	created = DateTime()
	expiration = DateTime()
	# relationships
	alert_subscriptions = SQLAlchemyConnectionField(AlertSubscription)
	credentials = SQLAlchemyConnectionField(Credential)
	deaddrop_connections = SQLAlchemyConnectionField(DeaddropConnection)
	deaddrop_deployments = SQLAlchemyConnectionField(DeaddropDeployment)
	landing_pages = SQLAlchemyConnectionField(LandingPage)
	messages = SQLAlchemyConnectionField(Message)
	visits = SQLAlchemyConnectionField(Visit)

class CampaignType(graphene_sqlalchemy.SQLAlchemyObjectType):
	class Meta:
		model = db_models.CampaignType
		interfaces = (RelayNode,)
	# relationships
	campaigns = SQLAlchemyConnectionField(Campaign)

class Company(graphene_sqlalchemy.SQLAlchemyObjectType):
	class Meta:
		model = db_models.Company
		interfaces = (RelayNode,)
	# relationships
	campaigns = SQLAlchemyConnectionField(Campaign)

class CompanyDepartment(graphene_sqlalchemy.SQLAlchemyObjectType):
	class Meta:
		model = db_models.CompanyDepartment
		interfaces = (RelayNode,)
	# relationships
	messages = SQLAlchemyConnectionField(Message)

class Industry(graphene_sqlalchemy.SQLAlchemyObjectType):
	class Meta:
		model = db_models.Industry
		interfaces = (RelayNode,)
	# relationships
	companies = SQLAlchemyConnectionField(Company)

class User(graphene_sqlalchemy.SQLAlchemyObjectType):
	class Meta:
		model = db_models.User
		interfaces = (RelayNode,)
	expiration = DateTime()
	last_login = DateTime()
	# relationships
	alert_subscriptions = SQLAlchemyConnectionField(AlertSubscription)
	campaigns = SQLAlchemyConnectionField(Campaign)

class Database(graphene.ObjectType):
	alert_subscription = graphene.Field(AlertSubscription, id=graphene.String())
	alert_subscriptions = SQLAlchemyConnectionField(AlertSubscription)
	campaign_type = graphene.Field(CampaignType, id=graphene.String())
	campaign_types = SQLAlchemyConnectionField(CampaignType)
	campaign = graphene.Field(Campaign, id=graphene.String())
	campaigns = SQLAlchemyConnectionField(Campaign)
	company = graphene.Field(Company, id=graphene.String())
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
	user = graphene.Field(User, id=graphene.String())
	users = SQLAlchemyConnectionField(User)
	visit = graphene.Field(Visit, id=graphene.String())
	visits = SQLAlchemyConnectionField(Visit)
	def resolve_alert_subscription(self, info, **kwargs):
		query = AlertSubscription.get_query(info)
		query = query.filter_by(**kwargs)
		return query.first()

	def resolve_alert_subscriptions(self, info, **kwargs):
		query = AlertSubscription.get_query(info)
		return query.all()

	def resolve_campaign(self, info, **kwargs):
		query = Campaign.get_query(info)
		query = query.filter_by(**kwargs)
		return query.first()

	def resolve_campaigns(self, info, **kwargs):
		query = Campaign.get_query(info)
		return query.all()

	def resolve_campaign_type(self, info, **kwargs):
		query = CampaignType.get_query(info)
		query = query.filter_by(**kwargs)
		return query.first()

	def resolve_campaign_types(self, info, **kwargs):
		query = CampaignType.get_query(info)
		return query.all()

	def resolve_company(self, info, **kwargs):
		query = Company.get_query(info)
		query = query.filter_by(**kwargs)
		return query.first()

	def resolve_companies(self, info, **kwargs):
		query = Company.get_query(info)
		return query.all()

	def resolve_company_department(self, info, **kwargs):
		query = CompanyDepartment.get_query(info)
		query = query.filter_by(**kwargs)
		return query.first()

	def resolve_company_departments(self, info, **kwargs):
		query = CompanyDepartment.get_query(info)
		return query.all()

	def resolve_credential(self, info, **kwargs):
		query = Credential.get_query(info)
		query = query.filter_by(**kwargs)
		return query.first()

	def resolve_credentials(self, info, **kwargs):
		query = Credential.get_query(info)
		return query.all()

	def resolve_deaddrop_connection(self, info, **kwargs):
		query = DeaddropConnection.get_query(info)
		query = query.filter_by(**kwargs)
		return query.first()

	def resolve_deaddrop_connections(self, info, **kwargs):
		query = DeaddropConnection.get_query(info)
		return query.all()

	def resolve_deaddrop_deployment(self, info, **kwargs):
		query = DeaddropDeployment.get_query(info)
		query = query.filter_by(**kwargs)
		return query.first()

	def resolve_deaddrop_deployments(self, info, **kwargs):
		query = DeaddropDeployment.get_query(info)
		return query.all()

	def resolve_industry(self, info, **kwargs):
		query = Industry.get_query(info)
		query = query.filter_by(**kwargs)
		return query.first()

	def resolve_industries(self, info, **kwargs):
		query = Industry.get_query(info)
		return query.all()

	def resolve_landing_page(self, info, **kwargs):
		query = LandingPage.get_query(info)
		query = query.filter_by(**kwargs)
		return query.first()

	def resolve_landing_pages(self, info, **kwargs):
		query = LandingPage.get_query(info)
		return query.all()

	def resolve_message(self, info, **kwargs):
		query = Message.get_query(info)
		query = query.filter_by(**kwargs)
		return query.first()

	def resolve_messages(self, info, **kwargs):
		query = Message.get_query(info)
		return query.all()

	def resolve_user(self, info, **kwargs):
		query = User.get_query(info)
		query = query.filter_by(**kwargs)
		return query.first()

	def resolve_users(self, info, **kwargs):
		query = User.get_query(info)
		return query.all()

	def resolve_visit(self, info, **kwargs):
		query = Visit.get_query(info)
		query = query.filter_by(**kwargs)
		return query.first()

	def resolve_visits(self, info, **kwargs):
		query = Visit.get_query(info)
		return query.all()

# top level query object for the schema
class Query(graphene.ObjectType):
	"""
	This is the root query object used for GraphQL queries.
	"""
	db = graphene.Field(Database)
	geoloc = graphene.Field(GeoLocation, ip=graphene.String())
	plugin = graphene.Field(Plugin, name=graphene.String())
	plugins = graphene.relay.ConnectionField(PluginConnection)
	version = graphene.Field(graphene.String)
	def resolve_db(self, info, **kwargs):
		return Database()

	def resolve_geoloc(self, info, **kwargs):
		ip_address = kwargs.get('ip')
		if ip_address is None:
			return
		return GeoLocation.from_ip_address(ip_address)

	def resolve_plugin(self, info, **kwargs):
		plugin_manager = info.context.get('plugin_manager', {})
		for _, plugin in plugin_manager:
			if plugin.name != kwargs.get('name'):
				continue
			return Plugin.from_plugin(plugin)

	def resolve_plugins(self, info, **kwargs):
		plugin_manager = info.context.get('plugin_manager', {})
		return [Plugin.from_plugin(plugin) for _, plugin in sorted(plugin_manager, key=lambda i: i[0])]

	def resolve_version(self, info, **kwargs):
		return version.version

class AuthorizationMiddleware(object):
	"""
	An authorization provider to ensure that the permissions on the objects
	that are queried are respected. If no **rpc_session** key is provided in
	the **context** dictionary then no authorization checks can be performed
	and all objects and operations will be accessible. The **rpc_session**
	key's value must be an instance of :py:class:`~.AuthenticatedSession`.
	"""
	def resolve(self, next_, root, info, **kwargs):
		rpc_session = info.context.get('rpc_session')
		if isinstance(root, db_models.Base) and rpc_session is not None:
			if not root.session_has_read_prop_access(rpc_session, info.field_name):
				return
		return next_(root, info, **kwargs)

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
		middleware.insert(0, AuthorizationMiddleware())
		kwargs['middleware'] = middleware
		return super(Schema, self).execute(*args, **kwargs)

	def execute_file(self, path, *args, **kwargs):
		with open(path, 'r') as file_h:
			query = file_h.read()
		return self.execute(query, *args, **kwargs)

schema = Schema()
