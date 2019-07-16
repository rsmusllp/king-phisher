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

import collections
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
import sqlalchemy.sql.expression

DATABASE_TABLE_REGEX = '[a-z_]+'
"""A regular expression which will match all valid database table names."""
SCHEMA_VERSION = 9
"""The schema version of the database, used for compatibility checks."""

MetaTable = collections.namedtuple('MetaTable', ('column_names', 'model', 'name', 'table'))
"""Metadata describing a table and its various attributes.

.. py:attribute:: column_names

   A tuple of strings representing the table's column names.

.. py:attribute:: model

   The SQLAlchemy model class associated with this table.

.. py:attribute:: name

   The name of this table.
"""

database_tables = {}
"""A dictionary which contains all the database tables and their :py:class:`.MetaTable` instances."""
logger = logging.getLogger('KingPhisher.Server.Database.Models')

sql_null = sqlalchemy.sql.expression.null
"""
Return a literal SQL NULL expression. This can be used, for example, to
explicitly set a model property to NULL even if it has a default value.

:return: A literal SQL NULL expression.
"""

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
	return set(name for (name, metatable) in database_tables.items() if column_id in metatable.column_names)

def forward_signal_delete(mapper, connection, target):
	signals.send_safe('db-table-delete', logger, target.__tablename__, mapper=mapper, connection=connection, target=target)

def forward_signal_insert(mapper, connection, target):
	signals.send_safe('db-table-insert', logger, target.__tablename__, mapper=mapper, connection=connection, target=target)

def forward_signal_update(mapper, connection, target):
	signals.send_safe('db-table-update', logger, target.__tablename__, mapper=mapper, connection=connection, target=target)

def register_table(table):
	"""
	Register a database table. This will populate the information provided in
	DATABASE_TABLES dictionary. This also forwards signals to the appropriate
	listeners within the :py:mod:`server.signal` module.

	:param cls table: The table to register.
	"""
	metatable = table.metatable()
	database_tables[metatable.name] = metatable

	sqlalchemy.event.listen(table, 'before_delete', forward_signal_delete)
	sqlalchemy.event.listen(table, 'before_insert', forward_signal_insert)
	sqlalchemy.event.listen(table, 'before_update', forward_signal_update)
	return table

class BaseRowCls(object):
	"""
	The base class from which other database table objects inherit from.
	Provides a standard ``__repr__`` method and default permission checks which
	are to be overridden as desired by subclasses.

	.. warning::
		Subclasses should not directly override the ``session_has_*_access``
		methods. These contain wrapping logic to do things like checking if the
		session is an administrator, etc. Instead subclasses looking to control
		access should override the individual private variants
		``_session_has_*_access``. Each of these use the same call signature as
		their public counterparts.
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
		letter of create, read, update, and delete. For example, to check for
		read and update permissions, *access* would be ``'ru'``.

		.. note::
			This will always return ``True`` for sessions which are for
			administrative users. To maintain this logic, this method **should
			not** be overridden in subclasses. Instead override the specific
			``_session_has_*_access`` methods as necessary.

		:param str access: The desired permissions.
		:param session: The authenticated session to check access for.
		:return: Whether the session has the desired permissions.
		:rtype: bool
		"""
		if session.user_is_admin:
			return True
		cls = self.__class__
		if cls.is_private:
			return False
		access = access.lower()
		for case in utilities.switch(access, comp=operator.contains, swapped=True):
			if case('c') and not cls.session_has_create_access(session, instance=self):
				break
			if case('r') and not cls.session_has_read_access(session, instance=self):
				break
			if case('u') and not cls.session_has_update_access(session, instance=self):
				break
			if case('d') and not cls.session_has_delete_access(session, instance=self):
				break
		else:
			return True
		return False

	@classmethod
	def session_has_create_access(cls, session, instance=None):
		"""
		Check that the authenticated *session* has access to create the
		specified model *instance*.

		:param session: The authenticated session to check access for.
		:param instance: The optional model instance to inspect.
		:return: Whether the session has the desired permissions.
		:rtype: bool
		"""
		if session.user_is_admin:
			return True
		return cls._session_has_create_access(session, instance=instance)

	@classmethod
	def session_has_delete_access(cls, session, instance=None):
		"""
		Check that the authenticated *session* has access to delete the
		specified model *instance*.

		:param session: The authenticated session to check access for.
		:param instance: The optional model instance to inspect.
		:return: Whether the session has the desired permissions.
		:rtype: bool
		"""
		if session.user_is_admin:
			return True
		return cls._session_has_delete_access(session, instance=instance)

	@classmethod
	def session_has_read_access(cls, session, instance=None):
		"""
		Check that the authenticated *session* has access to read the
		specified model *instance*.

		:param session: The authenticated session to check access for.
		:param instance: The optional model instance to inspect.
		:return: Whether the session has the desired permissions.
		:rtype: bool
		"""
		if session.user_is_admin:
			return True
		return cls._session_has_read_access(session, instance=instance)

	@classmethod
	def session_has_read_prop_access(cls, session, prop, instance=None):
		"""
		Check that the authenticated *session* has access to read the property
		of the specified model *instance*. This allows models to only explicitly
		control which of their attributes can be read by a particular *session*.

		:param session: The authenticated session to check access for.
		:param instance: The optional model instance to inspect.
		:return: Whether the session has the desired permissions.
		:rtype: bool
		"""
		if session.user_is_admin:
			return True
		return cls._session_has_read_prop_access(session, prop, instance=instance)

	@classmethod
	def session_has_update_access(cls, session, instance=None):
		"""
		Check that the authenticated *session* has access to update the
		specified model *instance*.

		:param session: The authenticated session to check access for.
		:param instance: The optional model instance to inspect.
		:return: Whether the session has the desired permissions.
		:rtype: bool
		"""
		if session.user_is_admin:
			return True
		return cls._session_has_update_access(session, instance=instance)

	@classmethod
	def _session_has_create_access(cls, session, instance=None):
		return not cls.is_private

	@classmethod
	def _session_has_delete_access(cls, session, instance=None):
		return not cls.is_private

	@classmethod
	def _session_has_read_access(cls, session, instance=None):
		return not cls.is_private

	@classmethod
	def _session_has_read_prop_access(cls, session, prop, instance=None):
		return cls._session_has_read_access(session, instance=instance)

	@classmethod
	def _session_has_update_access(cls, session, instance=None):
		return not cls.is_private

	@classmethod
	def metatable(cls):
		"""
		Generate a :py:class:`.MetaTable` instance for this model class.

		:return: The appropriate metadata for the table represented by this model.
		:rtype: :py:class:`.MetaTable`
		"""
		columns = tuple(col.name for col in cls.__table__.columns)
		return MetaTable(column_names=columns, model=cls, name=cls.__tablename__, table=cls.__table__)

	def to_dict(self):
		# versionadded:: 1.13.0
		return collections.OrderedDict((col.name, getattr(self, col.name)) for col in self.__class__.__table__.columns)

Base = sqlalchemy.ext.declarative.declarative_base(cls=BaseRowCls)
metadata = Base.metadata

class ExpireMixIn(object):
	expiration = sqlalchemy.Column(sqlalchemy.DateTime)

	@property
	def has_expired(self):
		if self.expiration is None:
			return False
		if self.expiration > current_timestamp():
			return False
		return True

class TagMixIn(object):
	__repr_attributes__ = ('name',)
	id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True)
	name = sqlalchemy.Column(sqlalchemy.String, nullable=False)
	description = sqlalchemy.Column(sqlalchemy.String)

@register_table
class AlertSubscription(ExpireMixIn, Base):
	__repr_attributes__ = ('campaign_id', 'user_id')
	__tablename__ = 'alert_subscriptions'
	id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True)
	user_id = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey('users.id'), nullable=False)
	campaign_id = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey('campaigns.id'), nullable=False)

	@classmethod
	def _session_has_create_access(cls, session, instance=None):
		return instance and session.user == instance.user_id

	@classmethod
	def _session_has_delete_access(cls, session, instance=None):
		return instance and session.user == instance.user_id

	@classmethod
	def _session_has_read_access(cls, session, instance=None):
		return instance and session.user == instance.user_id

	@classmethod
	def _session_has_update_access(cls, session, instance=None):
		return instance and session.user == instance.user_id

@register_table
class AuthenticatedSession(Base):
	__repr_attributes__ = ('user_id',)
	__tablename__ = 'authenticated_sessions'
	is_private = True
	id = sqlalchemy.Column(sqlalchemy.String, primary_key=True)
	created = sqlalchemy.Column(sqlalchemy.DateTime, nullable=False)
	last_seen = sqlalchemy.Column(sqlalchemy.DateTime, nullable=False)
	user_id = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey('users.id'), nullable=False)

@register_table
class Campaign(ExpireMixIn, Base):
	__repr_attributes__ = ('name',)
	__tablename__ = 'campaigns'
	id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True)
	name = sqlalchemy.Column(sqlalchemy.String, unique=True, nullable=False)
	description = sqlalchemy.Column(sqlalchemy.String)
	user_id = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey('users.id'), nullable=False)
	created = sqlalchemy.Column(sqlalchemy.DateTime, default=current_timestamp)
	max_credentials = sqlalchemy.Column(sqlalchemy.Integer)
	campaign_type_id = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey('campaign_types.id'))
	company_id = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey('companies.id'))
	credential_regex_username = sqlalchemy.Column(sqlalchemy.String)
	credential_regex_password = sqlalchemy.Column(sqlalchemy.String)
	credential_regex_mfa_token = sqlalchemy.Column(sqlalchemy.String)
	# relationships
	alert_subscriptions = sqlalchemy.orm.relationship('AlertSubscription', backref='campaign', cascade='all, delete-orphan')
	credentials = sqlalchemy.orm.relationship('Credential', backref='campaign', cascade='all, delete-orphan')
	deaddrop_connections = sqlalchemy.orm.relationship('DeaddropConnection', backref='campaign', cascade='all, delete-orphan')
	deaddrop_deployments = sqlalchemy.orm.relationship('DeaddropDeployment', backref='campaign', cascade='all, delete-orphan')
	landing_pages = sqlalchemy.orm.relationship('LandingPage', backref='campaign', cascade='all, delete-orphan')
	messages = sqlalchemy.orm.relationship('Message', backref='campaign', cascade='all, delete-orphan')
	visits = sqlalchemy.orm.relationship('Visit', backref='campaign', cascade='all, delete-orphan')

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
	mfa_token = sqlalchemy.Column(sqlalchemy.String)
	submitted = sqlalchemy.Column(sqlalchemy.DateTime, default=current_timestamp)
	regex_validated = sqlalchemy.Column(sqlalchemy.Boolean)

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
	__repr_attributes__ = ('campaign_id', 'deployment_id', 'ip')
	__tablename__ = 'deaddrop_connections'
	id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True)
	deployment_id = sqlalchemy.Column(sqlalchemy.String, sqlalchemy.ForeignKey('deaddrop_deployments.id'), nullable=False)
	campaign_id = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey('campaigns.id'), nullable=False)
	count = sqlalchemy.Column(sqlalchemy.Integer, default=1)
	ip = sqlalchemy.Column(sqlalchemy.String)
	local_username = sqlalchemy.Column(sqlalchemy.String)
	local_hostname = sqlalchemy.Column(sqlalchemy.String)
	local_ip_addresses = sqlalchemy.Column(sqlalchemy.String)
	first_seen = sqlalchemy.Column(sqlalchemy.DateTime, default=current_timestamp)
	last_seen = sqlalchemy.Column(sqlalchemy.DateTime, default=current_timestamp)

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
	first_visits = sqlalchemy.orm.relationship('Visit', backref='first_landing_page', cascade='all, delete-orphan')

@register_table
class StorageData(Base):
	__repr_attributes__ = ('namespace', 'key', 'value')
	__tablename__ = 'storage_data'
	is_private = True
	id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True)
	created = sqlalchemy.Column(sqlalchemy.DateTime, default=current_timestamp)
	modified = sqlalchemy.Column(sqlalchemy.DateTime, default=current_timestamp)
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
	reported = sqlalchemy.Column(sqlalchemy.DateTime)
	trained = sqlalchemy.Column(sqlalchemy.Boolean, default=False)
	delivery_status = sqlalchemy.Column(sqlalchemy.String)
	delivery_details = sqlalchemy.Column(sqlalchemy.String)
	testing = sqlalchemy.Column(sqlalchemy.Boolean, default=False, nullable=False)
	company_department_id = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey('company_departments.id'))
	# relationships
	credentials = sqlalchemy.orm.relationship('Credential', backref='message', cascade='all, delete-orphan')
	visits = sqlalchemy.orm.relationship('Visit', backref='message', cascade='all, delete-orphan')

@register_table
class User(ExpireMixIn, Base):
	__repr_attributes__ = ('name',)
	__tablename__ = 'users'
	id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True)
	name = sqlalchemy.Column(sqlalchemy.String, unique=True, nullable=False)
	description = sqlalchemy.Column(sqlalchemy.String)
	phone_carrier = sqlalchemy.Column(sqlalchemy.String)
	phone_number = sqlalchemy.Column(sqlalchemy.String)
	email_address = sqlalchemy.Column(sqlalchemy.String)
	otp_secret = sqlalchemy.Column(sqlalchemy.String(16))
	last_login = sqlalchemy.Column(sqlalchemy.DateTime)
	access_level = sqlalchemy.Column(sqlalchemy.Integer, default=1000, nullable=False)
	# relationships
	alert_subscriptions = sqlalchemy.orm.relationship('AlertSubscription', backref='user', cascade='all, delete-orphan')
	authenticated_sessions = sqlalchemy.orm.relationship('AuthenticatedSession', backref='user', cascade='all, delete-orphan')
	campaigns = sqlalchemy.orm.relationship('Campaign', backref='user', cascade='all, delete-orphan')

	@property
	def is_admin(self):
		"""True when the user is an administrative user as determined by checking the :py:attr:`.User.access_level` is ``0``."""
		return self.access_level == 0

	@classmethod
	def _session_has_create_access(cls, session, instance=None):
		return False

	@classmethod
	def _session_has_delete_access(cls, session, instance=None):
		return False

	@classmethod
	def _session_has_read_access(cls, session, instance=None):
		return instance and session.user == instance.id

	@classmethod
	def _session_has_read_prop_access(cls, session, prop, instance=None):
		if prop in ('id', 'campaigns', 'name'):  # everyone can read the id
			return True
		return cls.session_has_read_access(session, instance=instance)

	@classmethod
	def _session_has_update_access(cls, session, instance=None):
		return instance and session.user == instance.id

@register_table
class Visit(Base):
	__repr_attributes__ = ('campaign_id', 'message_id')
	__tablename__ = 'visits'
	id = sqlalchemy.Column(sqlalchemy.String, default=utilities.make_visit_uid, primary_key=True)
	message_id = sqlalchemy.Column(sqlalchemy.String, sqlalchemy.ForeignKey('messages.id'), nullable=False)
	campaign_id = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey('campaigns.id'), nullable=False)
	count = sqlalchemy.Column(sqlalchemy.Integer, default=1)
	ip = sqlalchemy.Column(sqlalchemy.String)
	details = sqlalchemy.Column(sqlalchemy.String)
	user_agent = sqlalchemy.Column(sqlalchemy.String)
	first_landing_page_id = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey('landing_pages.id'))
	first_seen = sqlalchemy.Column(sqlalchemy.DateTime, default=current_timestamp)
	last_seen = sqlalchemy.Column(sqlalchemy.DateTime, default=current_timestamp)
	# relationships
	credentials = sqlalchemy.orm.relationship('Credential', backref='visit', cascade='all, delete-orphan')
