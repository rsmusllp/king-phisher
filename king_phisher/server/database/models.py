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

from . import register_table

import sqlalchemy
import sqlalchemy.ext.declarative

Base = sqlalchemy.ext.declarative.declarative_base()

@register_table
class AlertSubscription(Base):
	__tablename__ = 'alert_subscriptions'
	id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True)
	user_id = sqlalchemy.Column(sqlalchemy.String, sqlalchemy.ForeignKey('users.id'), nullable=False)
	campaign_id = sqlalchemy.Column(sqlalchemy.Integer)

@register_table
class Campaign(Base):
	__tablename__ = 'campaigns'
	id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True)
	name = sqlalchemy.Column(sqlalchemy.String, unique=True, nullable=False)
	creator = sqlalchemy.Column(sqlalchemy.String, sqlalchemy.ForeignKey('users.id'), nullable=False)
	created = sqlalchemy.Column(sqlalchemy.DateTime, default=lambda _: datetime.datetime.utcnow())
	reject_after_credentials = sqlalchemy.Column(sqlalchemy.Boolean, default=False)

@register_table
class Credential(Base):
	__tablename__ = 'credentials'
	id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True)
	visit_id = sqlalchemy.Column(sqlalchemy.String, sqlalchemy.ForeignKey('visits.id'), nullable=False)
	message_id = sqlalchemy.Column(sqlalchemy.String, sqlalchemy.ForeignKey('messages.id'), nullable=False)
	campaign_id = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey('campaigns.id'), nullable=False)
	username = sqlalchemy.Column(sqlalchemy.String)
	password = sqlalchemy.Column(sqlalchemy.String)
	submitted = sqlalchemy.Column(sqlalchemy.DateTime, default=lambda _: datetime.datetime.utcnow())

@register_table
class DeaddropDeployment(Base):
	__tablename__ = 'deaddrop_deployments'
	id = sqlalchemy.Column(sqlalchemy.String, primary_key=True)
	campaign_id = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey('campaigns.id'), nullable=False)
	destination = sqlalchemy.Column(sqlalchemy.String)

@register_table
class DeaddropConnection(Base):
	__tablename__ = 'deaddrop_connections'
	id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True)
	deployment_id = sqlalchemy.Column(sqlalchemy.String, sqlalchemy.ForeignKey('deaddrop_deployments.id'), nullable=False)
	campaign_id = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey('campaigns.id'), nullable=False)
	visit_count = sqlalchemy.Column(sqlalchemy.Integer, default=1)
	visitor_ip = sqlalchemy.Column(sqlalchemy.String)
	local_username = sqlalchemy.Column(sqlalchemy.String)
	local_hostname = sqlalchemy.Column(sqlalchemy.String)
	local_ip_addresses = sqlalchemy.Column(sqlalchemy.String)
	first_visit = sqlalchemy.Column(sqlalchemy.DateTime, default=lambda _: datetime.datetime.utcnow())
	last_visit = sqlalchemy.Column(sqlalchemy.DateTime, default=lambda _: datetime.datetime.utcnow())

@register_table
class LandingPage(Base):
	__tablename__ = 'landing_pages'
	id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True)
	campaign_id = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey('campaigns.id'), nullable=False)
	hostname = sqlalchemy.Column(sqlalchemy.String, nullable=False)
	page = sqlalchemy.Column(sqlalchemy.String, nullable=False)

@register_table
class Message(Base):
	__tablename__ = 'messages'
	id = sqlalchemy.Column(sqlalchemy.String, primary_key=True)
	campaign_id = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey('campaigns.id'), nullable=False)
	target_email = sqlalchemy.Column(sqlalchemy.String)
	company_name = sqlalchemy.Column(sqlalchemy.String)
	first_name = sqlalchemy.Column(sqlalchemy.String)
	last_name = sqlalchemy.Column(sqlalchemy.String)
	opened = sqlalchemy.Column(sqlalchemy.DateTime)
	sent = sqlalchemy.Column(sqlalchemy.DateTime, default=lambda _: datetime.datetime.utcnow())
	trained = sqlalchemy.Column(sqlalchemy.Boolean, default=False)

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
	campaign_id = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey('campaigns.id'), nullable=False)
	visit_count = sqlalchemy.Column(sqlalchemy.Integer, default=1)
	visitor_ip = sqlalchemy.Column(sqlalchemy.String)
	visitor_details = sqlalchemy.Column(sqlalchemy.String)
	first_visit = sqlalchemy.Column(sqlalchemy.DateTime, default=lambda _: datetime.datetime.utcnow())
	last_visit = sqlalchemy.Column(sqlalchemy.DateTime, default=lambda _: datetime.datetime.utcnow())
