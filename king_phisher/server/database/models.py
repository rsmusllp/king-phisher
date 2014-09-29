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

import sqlalchemy
import sqlalchemy.ext.declarative
import sqlalchemy.orm

DATABASE_TABLES = {}
"""A dictionary which contains all the database tables and their columns."""
DATABASE_TABLE_OBJECTS = {}
"""A dictionary which contains all the database tables and their primitive objects."""
SCHEMA_VERSION = 2
"""The schema version of the database, used for compatibility checks."""

Base = sqlalchemy.ext.declarative.declarative_base()

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
	:rtype: list
	"""
	return map(lambda x: x[0], filter(lambda x: column_id in x[1], DATABASE_TABLES.items()))

def register_table(table):
	"""
	Register a database table. This will populate the information provided in
	DATABASE_TABLES dictionary.

	:param table: The table to register.
	"""
	columns = tuple(map(lambda c: c.name, table.__table__.columns))
	DATABASE_TABLES[table.__tablename__] = columns
	DATABASE_TABLE_OBJECTS[table.__tablename__] = table
	return table

@register_table
class AlertSubscription(Base):
	__tablename__ = 'alert_subscriptions'
	id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True)
	user_id = sqlalchemy.Column(sqlalchemy.String, sqlalchemy.ForeignKey('users.id'), nullable=False)
	user = sqlalchemy.orm.relationship('User', backref=sqlalchemy.orm.backref('alert_subscriptions', order_by=id))
	campaign_id = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey('campaigns.id'), nullable=False)
	campaign = sqlalchemy.orm.relationship('Campaign', backref=sqlalchemy.orm.backref('alert_subscriptions', order_by=id))

@register_table
class Campaign(Base):
	__tablename__ = 'campaigns'
	id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True)
	name = sqlalchemy.Column(sqlalchemy.String, unique=True, nullable=False)
	user_id = sqlalchemy.Column(sqlalchemy.String, sqlalchemy.ForeignKey('users.id'), nullable=False)
	user = sqlalchemy.orm.relationship('User', backref=sqlalchemy.orm.backref('campaigns', order_by=id))
	created = sqlalchemy.Column(sqlalchemy.DateTime, default=current_timestamp)
	reject_after_credentials = sqlalchemy.Column(sqlalchemy.Boolean, default=False)

@register_table
class Credential(Base):
	__tablename__ = 'credentials'
	id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True)
	visit_id = sqlalchemy.Column(sqlalchemy.String, sqlalchemy.ForeignKey('visits.id'), nullable=False)
	visit = sqlalchemy.orm.relationship('Visit', backref=sqlalchemy.orm.backref('credentials', order_by=id))
	message_id = sqlalchemy.Column(sqlalchemy.String, sqlalchemy.ForeignKey('messages.id'), nullable=False)
	message = sqlalchemy.orm.relationship('Message', backref=sqlalchemy.orm.backref('credentials', order_by=id))
	campaign_id = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey('campaigns.id'), nullable=False)
	campaign = sqlalchemy.orm.relationship('Campaign', backref=sqlalchemy.orm.backref('credentials', order_by=id))
	username = sqlalchemy.Column(sqlalchemy.String)
	password = sqlalchemy.Column(sqlalchemy.String)
	submitted = sqlalchemy.Column(sqlalchemy.DateTime, default=current_timestamp)

@register_table
class DeaddropDeployment(Base):
	__tablename__ = 'deaddrop_deployments'
	id = sqlalchemy.Column(sqlalchemy.String, primary_key=True)
	campaign_id = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey('campaigns.id'), nullable=False)
	campaign = sqlalchemy.orm.relationship('Campaign', backref=sqlalchemy.orm.backref('deaddrop_deployments', order_by=id))
	destination = sqlalchemy.Column(sqlalchemy.String)

@register_table
class DeaddropConnection(Base):
	__tablename__ = 'deaddrop_connections'
	id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True)
	deployment_id = sqlalchemy.Column(sqlalchemy.String, sqlalchemy.ForeignKey('deaddrop_deployments.id'), nullable=False)
	deployment = sqlalchemy.orm.relationship('DeaddropDeployment', backref=sqlalchemy.orm.backref('deaddrop_connections', order_by=id))
	campaign_id = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey('campaigns.id'), nullable=False)
	campaign = sqlalchemy.orm.relationship('Campaign', backref=sqlalchemy.orm.backref('deaddrop_connections', order_by=id))
	visit_count = sqlalchemy.Column(sqlalchemy.Integer, default=1)
	visitor_ip = sqlalchemy.Column(sqlalchemy.String)
	local_username = sqlalchemy.Column(sqlalchemy.String)
	local_hostname = sqlalchemy.Column(sqlalchemy.String)
	local_ip_addresses = sqlalchemy.Column(sqlalchemy.String)
	first_visit = sqlalchemy.Column(sqlalchemy.DateTime, default=current_timestamp)
	last_visit = sqlalchemy.Column(sqlalchemy.DateTime, default=current_timestamp)

@register_table
class LandingPage(Base):
	__tablename__ = 'landing_pages'
	id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True)
	campaign_id = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey('campaigns.id'), nullable=False)
	campaign = sqlalchemy.orm.relationship('Campaign', backref=sqlalchemy.orm.backref('landing_pages', order_by=id))
	hostname = sqlalchemy.Column(sqlalchemy.String, nullable=False)
	page = sqlalchemy.Column(sqlalchemy.String, nullable=False)

@register_table
class Message(Base):
	__tablename__ = 'messages'
	id = sqlalchemy.Column(sqlalchemy.String, primary_key=True)
	campaign_id = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey('campaigns.id'), nullable=False)
	campaign = sqlalchemy.orm.relationship('Campaign', backref=sqlalchemy.orm.backref('messages', order_by=id))
	target_email = sqlalchemy.Column(sqlalchemy.String)
	company_name = sqlalchemy.Column(sqlalchemy.String)
	first_name = sqlalchemy.Column(sqlalchemy.String)
	last_name = sqlalchemy.Column(sqlalchemy.String)
	opened = sqlalchemy.Column(sqlalchemy.DateTime)
	sent = sqlalchemy.Column(sqlalchemy.DateTime, default=current_timestamp)
	trained = sqlalchemy.Column(sqlalchemy.Boolean, default=False)

@register_table
class MetaData(Base):
	__tablename__ = 'meta_data'
	id = sqlalchemy.Column(sqlalchemy.String, primary_key=True)
	value_type = sqlalchemy.Column(sqlalchemy.String, default='str')
	value = sqlalchemy.Column(sqlalchemy.String)

@register_table
class User(Base):
	__tablename__ = 'users'
	id = sqlalchemy.Column(sqlalchemy.String, primary_key=True)
	phone_carrier = sqlalchemy.Column(sqlalchemy.String)
	phone_number = sqlalchemy.Column(sqlalchemy.String)

@register_table
class Visit(Base):
	__tablename__ = 'visits'
	id = sqlalchemy.Column(sqlalchemy.String, primary_key=True)
	message_id = sqlalchemy.Column(sqlalchemy.String, sqlalchemy.ForeignKey('messages.id'), nullable=False)
	messages = sqlalchemy.orm.relationship('Message', backref=sqlalchemy.orm.backref('visits', order_by=id))
	campaign_id = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey('campaigns.id'), nullable=False)
	campaign = sqlalchemy.orm.relationship('Campaign', backref=sqlalchemy.orm.backref('visits', order_by=id))
	visit_count = sqlalchemy.Column(sqlalchemy.Integer, default=1)
	visitor_ip = sqlalchemy.Column(sqlalchemy.String)
	visitor_details = sqlalchemy.Column(sqlalchemy.String)
	first_visit = sqlalchemy.Column(sqlalchemy.DateTime, default=current_timestamp)
	last_visit = sqlalchemy.Column(sqlalchemy.DateTime, default=current_timestamp)
