#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  king_phisher/server/database/models.py
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
import logging
import operator

from king_phisher import errors
from king_phisher import utilities
from king_phisher.server import signals

import sqlalchemy
import sqlalchemy.event
import sqlalchemy.ext.declarative
import sqlalchemy.orm

DATABASE_TABLE_REGEX = '[a-z_]+'
"""A regular expression which will match all valid database table names."""
SCHEMA_VERSION = 7
"""The schema version of the database, used for compatibility checks."""

database_tables = {}
"""A dictionary which contains all the database tables and their column names."""
database_table_objects = {}
"""A dictionary which contains all the database tables and their primitive objects."""
logger = logging.getLogger('KingPhisher.Server.Database.Models')

def current_timestamp(*args, **kwargs):
	"""
	The function used for creating the timestamp used by database objects.

	:return: The current timestamp.
	:rtype: :py:class:`datetime.datetime`
	"""
	return datetime.datetime.utcnow()

def get_tables_with_column_id(column_id):
	"""
	Get all tables which contain a column named *column_id*.

	:param str column_id: The column name to get all the tables of.
	:return: The list of matching tables.
	:rtype: set
	"""
	return set(x[0] for x in database_tables.items() if column_id in x[1])

def forward_signal_delete(mapper, connection, target):
	signals.safe_send('db-table-delete', logger, target.__tablename__, mapper=mapper, connection=connection, target=target)

def forward_signal_insert(mapper, connection, target):
	signals.safe_send('db-table-insert', logger, target.__tablename__, mapper=mapper, connection=connection, target=target)

def forward_signal_update(mapper, connection, target):
	signals.safe_send('db-table-update', logger, target.__tablename__, mapper=mapper, connection=connection, target=target)

def register_table(table):
	"""
	Register a database table. This will populate the information provided in
	DATABASE_TABLES dictionary. This also forwards signals to the appropriate
	listeners within the :py:mod:`server.signal` module.

	:param cls table: The table to register.
	"""
	columns = tuple(col.name for col in table.__table__.columns)
	database_tables[table.__tablename__] = columns
	database_table_objects[table.__tablename__] = table

	sqlalchemy.event.listen(table, 'before_delete', forward_signal_delete)
	sqlalchemy.event.listen(table, 'before_insert', forward_signal_insert)
	sqlalchemy.event.listen(table, 'before_update', forward_signal_update)
	return table

class BaseRowCls(object):
	"""
	The base class from which other database table objects inherit from.
	Provides a standard ``__repr__`` method and default permission checks which
	are to be overridden as desired by subclasses.
	"""
	__repr_attributes__ = ()
	"""Attributes which should be included in the __repr__ method."""
	is_private = False
	"""Whether the table is only allowed to be accessed by the server or not."""
	def __repr__(self):
		description = "<{0} id={1} ".format(self.__class__.__name__, repr(self.id))
		for repr_attr in self.__repr_attributes__:
			description += "{0}={1!r} ".format(repr_attr, getattr(self, repr_attr))
		description += '>'
		return description

	def assert_session_has_permissions(self, *args, **kwargs):
		"""
		A convenience function which wraps :py:meth:`~.session_has_permissions`
		and raises a :py:exc:`~king_phisher.errors.KingPhisherPermissionError`
		if the session does not have the specified permissions.
		"""
		if self.session_has_permissions(*args, **kwargs):
			return
		raise errors.KingPhisherPermissionError()

	def session_has_permissions(self, access, session):
		"""
		Check that the authenticated session has the permissions specified in
		*access*. The permissions in *access* are abbreviated with the first
		letter of create, read, update, and delete.

		:param str access: The desired permissions.
		:param session: The authenticated session to check access for.
		:return: Whether the session has the desired permissions.
		:rtype: bool
		"""
		if self.is_private:
			return False
		access = access.lower()
		for case in utilities.switch(access, comp=operator.contains, swapped=True):
			if case('c') and not self.session_has_create_access(session):
				break
			if case('r') and not self.session_has_read_access(session):
				break
			if case('u') and not self.session_has_update_access(session):
				break
			if case('d') and not self.session_has_delete_access(session):
				break
		else:
			return True
		return False

	def session_has_create_access(self, session):
		if self.is_private:
			return False
		return True

	def session_has_delete_access(self, session):
		if self.is_private:
			return False
		return True

	def session_has_read_access(self, session):
		if self.is_private:
			return False
		return True

	def session_has_read_prop_access(self, session, prop):
		return self.session_has_read_access(session)

	def session_has_update_access(self, session):
		if self.is_private:
			return False
		return True
Base = sqlalchemy.ext.declarative.declarative_base(cls=BaseRowCls)
metadata = Base.metadata

class TagMixIn(object):
	__repr_attributes__ = ('name',)
	id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True)
	name = sqlalchemy.Column(sqlalchemy.String, nullable=False)
	description = sqlalchemy.Column(sqlalchemy.String)

@register_table
class AlertSubscription(Base):
	__repr_attributes__ = ('campaign_id', 'user_id')
	__tablename__ = 'alert_subscriptions'
	id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True)
	user_id = sqlalchemy.Column(sqlalchemy.String, sqlalchemy.ForeignKey('users.id'), nullable=False)
	campaign_id = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey('campaigns.id'), nullable=False)
	type = sqlalchemy.Column(sqlalchemy.Enum('email', 'sms', name='alert_subscription_type'), default='sms', server_default='sms', nullable=False)
	mute_timestamp = sqlalchemy.Column(sqlalchemy.DateTime)

	def session_has_create_access(self, session):
		return session.user == self.user_id

	def session_has_delete_access(self, session):
		return session.user == self.user_id

	def session_has_read_access(self, session):
		return session.user == self.user_id

	def session_has_update_access(self, session):
		return session.user == self.user_id

@register_table
class AuthenticatedSession(Base):
	__repr_attributes__ = ('user_id',)
	__tablename__ = 'authenticated_sessions'
	is_private = True
	id = sqlalchemy.Column(sqlalchemy.String, primary_key=True)
	created = sqlalchemy.Column(sqlalchemy.Integer, nullable=False)
	last_seen = sqlalchemy.Column(sqlalchemy.Integer, nullable=False)
	user_id = sqlalchemy.Column(sqlalchemy.String, sqlalchemy.ForeignKey('users.id'), nullable=False)

@register_table
class Campaign(Base):
	__repr_attributes__ = ('name',)
	__tablename__ = 'campaigns'
	id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True)
	name = sqlalchemy.Column(sqlalchemy.String, unique=True, nullable=False)
	description = sqlalchemy.Column(sqlalchemy.String)
	user_id = sqlalchemy.Column(sqlalchemy.String, sqlalchemy.ForeignKey('users.id'), nullable=False)
	created = sqlalchemy.Column(sqlalchemy.DateTime, default=current_timestamp)
	reject_after_credentials = sqlalchemy.Column(sqlalchemy.Boolean, default=False)
	expiration = sqlalchemy.Column(sqlalchemy.DateTime)
	campaign_type_id = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey('campaign_types.id'))
	company_id = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey('companies.id'))
	# relationships
	alert_subscriptions = sqlalchemy.orm.relationship('AlertSubscription', backref='campaign', cascade='all, delete-orphan')
	credentials = sqlalchemy.orm.relationship('Credential', backref='campaign', cascade='all, delete-orphan')
	deaddrop_connections = sqlalchemy.orm.relationship('DeaddropConnection', backref='campaign', cascade='all, delete-orphan')
	deaddrop_deployments = sqlalchemy.orm.relationship('DeaddropDeployment', backref='campaign', cascade='all, delete-orphan')
	landing_pages = sqlalchemy.orm.relationship('LandingPage', backref='campaign', cascade='all, delete-orphan')
	messages = sqlalchemy.orm.relationship('Message', backref='campaign', cascade='all, delete-orphan')
	visits = sqlalchemy.orm.relationship('Visit', backref='campaign', cascade='all, delete-orphan')

	@property
	def has_expired(self):
		if self.expiration is None:
			return False
		if self.expiration > current_timestamp():
			return False
		return True

@register_table
class CampaignType(TagMixIn, Base):
	__tablename__ = 'campaign_types'
	# relationships
	campaigns = sqlalchemy.orm.relationship('Campaign', backref='campaign_type')

@register_table
class Company(Base):
	__repr_attributes__ = ('name',)
	__tablename__ = 'companies'
	id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True)
	name = sqlalchemy.Column(sqlalchemy.String, unique=True, nullable=False)
	description = sqlalchemy.Column(sqlalchemy.String)
	industry_id = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey('industries.id'))
	url_main = sqlalchemy.Column(sqlalchemy.String)
	url_email = sqlalchemy.Column(sqlalchemy.String)
	url_remote_access = sqlalchemy.Column(sqlalchemy.String)
	# relationships
	campaigns = sqlalchemy.orm.relationship('Campaign', backref='company', cascade='all')

@register_table
class CompanyDepartment(TagMixIn, Base):
	__tablename__ = 'company_departments'
	# relationships
	messages = sqlalchemy.orm.relationship('Message', backref='company_department')

@register_table
class Credential(Base):
	__repr_attributes__ = ('campaign_id', 'username')
	__tablename__ = 'credentials'
	id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True)
	visit_id = sqlalchemy.Column(sqlalchemy.String, sqlalchemy.ForeignKey('visits.id'), nullable=False)
	message_id = sqlalchemy.Column(sqlalchemy.String, sqlalchemy.ForeignKey('messages.id'), nullable=False)
	campaign_id = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey('campaigns.id'), nullable=False)
	username = sqlalchemy.Column(sqlalchemy.String)
	password = sqlalchemy.Column(sqlalchemy.String)
	submitted = sqlalchemy.Column(sqlalchemy.DateTime, default=current_timestamp)

@register_table
class DeaddropDeployment(Base):
	__repr_attributes__ = ('campaign_id', 'destination')
	__tablename__ = 'deaddrop_deployments'
	id = sqlalchemy.Column(sqlalchemy.String, default=lambda: utilities.random_string(16), primary_key=True)
	campaign_id = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey('campaigns.id'), nullable=False)
	destination = sqlalchemy.Column(sqlalchemy.String)
	# relationships
	deaddrop_connections = sqlalchemy.orm.relationship('DeaddropConnection', backref='deaddrop_deployment', cascade='all, delete-orphan')

@register_table
class DeaddropConnection(Base):
	__repr_attributes__ = ('campaign_id', 'deployment_id', 'visitor_ip')
	__tablename__ = 'deaddrop_connections'
	id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True)
	deployment_id = sqlalchemy.Column(sqlalchemy.String, sqlalchemy.ForeignKey('deaddrop_deployments.id'), nullable=False)
	campaign_id = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey('campaigns.id'), nullable=False)
	visit_count = sqlalchemy.Column(sqlalchemy.Integer, default=1)
	visitor_ip = sqlalchemy.Column(sqlalchemy.String)
	local_username = sqlalchemy.Column(sqlalchemy.String)
	local_hostname = sqlalchemy.Column(sqlalchemy.String)
	local_ip_addresses = sqlalchemy.Column(sqlalchemy.String)
	first_visit = sqlalchemy.Column(sqlalchemy.DateTime, default=current_timestamp)
	last_visit = sqlalchemy.Column(sqlalchemy.DateTime, default=current_timestamp)

@register_table
class Industry(TagMixIn, Base):
	__tablename__ = 'industries'
	# relationships
	companies = sqlalchemy.orm.relationship('Company', backref='industry')

@register_table
class LandingPage(Base):
	__repr_attributes__ = ('campaign_id', 'hostname', 'page')
	__tablename__ = 'landing_pages'
	id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True)
	campaign_id = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey('campaigns.id'), nullable=False)
	hostname = sqlalchemy.Column(sqlalchemy.String, nullable=False)
	page = sqlalchemy.Column(sqlalchemy.String, nullable=False)

@register_table
class StorageData(Base):
	__repr_attributes__ = ('namespace', 'key', 'value')
	__tablename__ = 'storage_data'
	is_private = True
	id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True)
	created = sqlalchemy.Column(sqlalchemy.DateTime, default=current_timestamp)
	namespace = sqlalchemy.Column(sqlalchemy.String)
	key = sqlalchemy.Column(sqlalchemy.String, nullable=False)
	value = sqlalchemy.Column(sqlalchemy.Binary)

@register_table
class Message(Base):
	__repr_attributes__ = ('campaign_id', 'target_email')
	__tablename__ = 'messages'
	id = sqlalchemy.Column(sqlalchemy.String, default=utilities.make_message_uid, primary_key=True)
	campaign_id = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey('campaigns.id'), nullable=False)
	target_email = sqlalchemy.Column(sqlalchemy.String)
	first_name = sqlalchemy.Column(sqlalchemy.String)
	last_name = sqlalchemy.Column(sqlalchemy.String)
	opened = sqlalchemy.Column(sqlalchemy.DateTime)
	opener_ip = sqlalchemy.Column(sqlalchemy.String)
	opener_user_agent = sqlalchemy.Column(sqlalchemy.String)
	sent = sqlalchemy.Column(sqlalchemy.DateTime, default=current_timestamp)
	trained = sqlalchemy.Column(sqlalchemy.Boolean, default=False)
	company_department_id = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey('company_departments.id'))
	# relationships
	credentials = sqlalchemy.orm.relationship('Credential', backref='message', cascade='all, delete-orphan')
	visits = sqlalchemy.orm.relationship('Visit', backref='message', cascade='all, delete-orphan')

@register_table
class MetaData(Base):
	__repr_attributes__ = ('value_type', 'value')
	__tablename__ = 'meta_data'
	is_private = True
	id = sqlalchemy.Column(sqlalchemy.String, primary_key=True)
	value_type = sqlalchemy.Column(sqlalchemy.String, default='str')
	value = sqlalchemy.Column(sqlalchemy.String)

@register_table
class User(Base):
	__tablename__ = 'users'
	id = sqlalchemy.Column(sqlalchemy.String, default=lambda: utilities.random_string(16), primary_key=True)
	phone_carrier = sqlalchemy.Column(sqlalchemy.String)
	phone_number = sqlalchemy.Column(sqlalchemy.String)
	email_address = sqlalchemy.Column(sqlalchemy.String)
	otp_secret = sqlalchemy.Column(sqlalchemy.String(16))
	# relationships
	alert_subscriptions = sqlalchemy.orm.relationship('AlertSubscription', backref='user', cascade='all, delete-orphan')
	campaigns = sqlalchemy.orm.relationship('Campaign', backref='user', cascade='all, delete-orphan')

	def session_has_create_access(self, session):
		return False

	def session_has_delete_access(self, session):
		return False

	def session_has_read_access(self, session):
		return session.user == self.id

	def session_has_read_prop_access(self, session, prop):
		if prop in ('id', 'campaigns'):  # everyone can read the id
			return True
		return self.session_has_read_access(session)

	def session_has_update_access(self, session):
		return session.user == self.id

@register_table
class Visit(Base):
	__repr_attributes__ = ('campaign_id', 'message_id')
	__tablename__ = 'visits'
	id = sqlalchemy.Column(sqlalchemy.String, default=utilities.make_visit_uid, primary_key=True)
	message_id = sqlalchemy.Column(sqlalchemy.String, sqlalchemy.ForeignKey('messages.id'), nullable=False)
	campaign_id = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey('campaigns.id'), nullable=False)
	visit_count = sqlalchemy.Column(sqlalchemy.Integer, default=1)
	visitor_ip = sqlalchemy.Column(sqlalchemy.String)
	visitor_details = sqlalchemy.Column(sqlalchemy.String)
	first_visit = sqlalchemy.Column(sqlalchemy.DateTime, default=current_timestamp)
	last_visit = sqlalchemy.Column(sqlalchemy.DateTime, default=current_timestamp)
	# relationships
	credentials = sqlalchemy.orm.relationship('Credential', backref='visit', cascade='all, delete-orphan')
