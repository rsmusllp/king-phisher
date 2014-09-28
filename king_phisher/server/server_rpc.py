#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  king_phisher/server/server_rpc.py
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

import threading

from king_phisher import version
from king_phisher.server.database import manager as db_manager
from king_phisher.server.database import models as db_models

VIEW_ROW_COUNT = 25
"""The default number of rows to return when one of the /view methods are called."""
DATABASE_TABLES = db_models.DATABASE_TABLES

class KingPhisherRequestHandlerRPC(object):
	"""
	This superclass of :py:class:`.KingPhisherRequestHandler` maintains
	all of the RPC call back functions.

	:RPC API: :ref:`rpc-api-label`
	"""
	def install_handlers(self):
		super(KingPhisherRequestHandlerRPC, self).install_handlers()
		self.rpc_handler_map['/ping'] = self.rpc_ping
		self.rpc_handler_map['/shutdown'] = self.rpc_shutdown
		self.rpc_handler_map['/version'] = self.rpc_version

		self.rpc_handler_map['/client/initialize'] = self.rpc_client_initialize
		self.rpc_handler_map['/config/get'] = self.rpc_config_get
		self.rpc_handler_map['/config/set'] = self.rpc_config_set

		self.rpc_handler_map['/campaign/alerts/is_subscribed'] = self.rpc_campaign_alerts_is_subscribed
		self.rpc_handler_map['/campaign/alerts/subscribe'] = self.rpc_campaign_alerts_subscribe
		self.rpc_handler_map['/campaign/alerts/unsubscribe'] = self.rpc_campaign_alerts_unsubscribe
		self.rpc_handler_map['/campaign/landing_page/new'] = self.rpc_campaign_landing_page_new
		self.rpc_handler_map['/campaign/message/new'] = self.rpc_campaign_message_new
		self.rpc_handler_map['/campaign/new'] = self.rpc_campaign_new
		self.rpc_handler_map['/campaign/delete'] = self.rpc_campaign_delete

		for table_name in DATABASE_TABLES.keys():
			self.rpc_handler_map['/' + table_name + '/count'] = self.rpc_database_count_rows
			self.rpc_handler_map['/' + table_name + '/delete'] = self.rpc_database_delete_row_by_id
			self.rpc_handler_map['/' + table_name + '/get'] = self.rpc_database_get_row_by_id
			self.rpc_handler_map['/' + table_name + '/insert'] = self.rpc_database_insert_row
			self.rpc_handler_map['/' + table_name + '/set'] = self.rpc_database_set_row_value
			self.rpc_handler_map['/' + table_name + '/view'] = self.rpc_database_get_rows

		# Tables with a campaign_id field
		for table_name in db_models.get_tables_with_column_id('campaign_id'):
			self.rpc_handler_map['/campaign/' + table_name + '/count'] = self.rpc_database_count_rows
			self.rpc_handler_map['/campaign/' + table_name + '/view'] = self.rpc_database_get_rows

		# Tables with a message_id field
		for table_name in db_models.get_tables_with_column_id('message_id'):
			self.rpc_handler_map['/message/' + table_name + '/count'] = self.rpc_database_count_rows
			self.rpc_handler_map['/message/' + table_name + '/view'] = self.rpc_database_get_rows

	def rpc_ping(self):
		"""
		An RPC method that can be used by clients to assert the status
		and responsiveness of this server.

		:return: This method always returns True.
		:rtype: bool
		"""
		return True

	def rpc_client_initialize(self):
		"""
		Initialize any client information necessary.

		:return: This method always returns True.
		:rtype: bool
		"""
		username = self.basic_auth_user
		if not username:
			return True
		session = db_manager.Session()
		query = session.query(db_models.User)
		query = query.filter_by(id=username)
		if query.count() == 0:
			user = db_models.User(id=username)
			session.add(user)
			session.commit()
		session.close()
		return True

	def rpc_shutdown(self):
		"""
		This method can be used to shut down the server. This function will
		return, however no subsequent requests will be processed.
		"""
		shutdown_thread = threading.Thread(target=self.server.shutdown)
		shutdown_thread.start()
		return

	def rpc_version(self):
		"""
		Get the version information of the server. This returns a
		dictionary with keys of version, version_info and rpc_api_version.
		These values are provided for the client to determine
		compatibility.

		:return: A dictionary with version information.
		:rtype: dict
		"""
		vinfo = {'version': version.version, 'version_info': version.version_info._asdict()}
		vinfo['rpc_api_version'] = version.rpc_api_version
		return vinfo

	def rpc_config_get(self, option_name):
		"""
		Retrieve a value from the server's configuration.

		:param str option_name: The name of the configuration option.
		:return: The option's value.
		"""
		if isinstance(option_name, (list, tuple)):
			option_names = option_name
			option_values = {}
			for option_name in option_names:
				if self.config.has_option(option_name):
					option_values[option_name] = self.config.get(option_name)
			return option_values
		elif self.config.has_option(option_name):
			return self.config.get(option_name)
		return

	def rpc_config_set(self, options):
		"""
		Set options in the server's configuration. Any changes to the
		server's configuration are not written to disk.

		:param dict options: A dictionary of option names and values
		"""
		for option_name, option_value in options.items():
			self.config.set(option_name, option_value)
		return

	def rpc_campaign_new(self, name):
		"""
		Create a new King Phisher campaign and initialize the database
		information.

		:param str name: The new campaign's name.
		:return: The ID of the new campaign.
		:rtype: int
		"""
		session = db_manager.Session()
		campaign = db_models.Campaign(name=name, user_id=self.basic_auth_user)
		session.add(campaign)
		session.commit()
		return campaign.id

	def rpc_campaign_alerts_is_subscribed(self, campaign_id):
		"""
		Check if the user is subscribed to alerts for the specified campaign.

		:param int campaign_id: The ID of the campaign.
		:return: The alert subscription status.
		:rtype: bool
		"""
		username = self.basic_auth_user
		session = db_manager.Session()
		query = session.query(db_models.AlertSubscription)
		query = query.filter_by(campaign_id=campaign_id, user_id=username)
		result = query.count()
		session.close()
		return result

	def rpc_campaign_alerts_subscribe(self, campaign_id):
		"""
		Subscribe to alerts for the specified campaign.

		:param int campaign_id: The ID of the campaign.
		"""
		username = self.basic_auth_user
		session = db_manager.Session()
		query = session.query(db_models.AlertSubscription)
		query = query.filter_by(campaign_id=campaign_id, user_id=username)
		if query.count() == 0:
			subscription = db_models.AlertSubscription(campaign_id=campaign_id, user_id=username)
			session.add(subscription)
			session.commit()
		session.close()
		return

	def rpc_campaign_alerts_unsubscribe(self, campaign_id):
		"""
		Unsubscribe to alerts for the specified campaign.

		:param int campaign_id: The ID of the campaign.
		"""
		username = self.basic_auth_user
		session = db_models.Session()
		query = session.query(db_models.AlertSubscription)
		query = query.filter_by(campaign_id=campaign_id, user_id=username)
		subscription = query.first()
		if subscription:
			session.delete(subscription)
			session.commit()
		session.close()
		return

	def rpc_campaign_landing_page_new(self, campaign_id, hostname, page):
		"""
		Add a landing page for the specified campaign. Landing pages refer
		to resources that when visited by a user should cause the visit
		counter to be incremented.

		:param int campaign_id: The ID of the campaign.
		:param str hostname: The VHOST for the request.
		:param str page: The request resource.
		"""
		page = page.lstrip('/')
		session = db_models.Session()
		query = session.query(db_models.LandingPage)
		query = query.filter_by(campaign_id=campaign_id, hostname=hostname, page=page)
		if query.count() == 0:
			landing_page = db_models.LandingPage(campaign_id=campaign_id, hostname=hostname, page=page)
			session.add(landing_page)
			session.commit()
		session.close()
		return

	def rpc_campaign_message_new(self, campaign_id, email_id, target_email, company_name, first_name, last_name):
		"""
		Record a message that has been sent as part of a campaign. These
		details can be retrieved later for value substitution in template
		pages.

		:param int campaign_id: The ID of the campaign.
		:param str email_id: The message id of the sent email.
		:param str target_email: The email address that the message was sent to.
		:param str company_name: The company name value for the message.
		:param str first_name: The first name of the message's recipient.
		:param str last_name: The last name of the message's recipient.
		"""
		session = db_models.Session()
		message = db_models.Message()
		message.id = email_id
		message.campaign_id = campaign_id
		message.target_email = target_email
		message.company_name = company_name
		message.first_name = first_name
		message.last_name = last_name
		session.add(message)
		session.commit()
		session.close()
		return

	def rpc_campaign_delete(self, campaign_id):
		"""
		Remove a campaign from the database and delete all associated
		information with it.

		.. warning::
			This action can not be reversed and there is no confirmation before it
			takes place.
		"""
		tables = database.get_tables_with_column_id('campaign_id')
		session = db_manager.Session()
		for table in tables:
			query = session.query(db_models.DATABASE_TABLE_OBJECTS[table])
			query = query.filter_by(campaign_id=campaign_id)
			query.delete()
		query = session.query(db_models.Campaign)
		query = query.filter_by(id=campaign_id)
		query.delete()
		session.commit()
		session.close()
		return

	def rpc_database_count_rows(self, *args):
		"""
		Get a count of the rows in the specified table where the search
		criteria matches.

		:return: The number of matching rows.
		:rtype: int
		"""
		args = list(args)
		fields = self.path.split('/')[1:-2]
		assert(len(fields) == len(args))
		table = db_models.DATABASE_TABLE_OBJECTS.get(self.path.split('/')[-2])
		assert(table)
		session = db_manager.Session()
		query = session.query(table)
		query = query.filter_by(**dict(zip(map(lambda f: f + '_id', fields), args)))
		result = query.count()
		session.close()
		return result

	def rpc_database_get_rows(self, *args):
		"""
		Retrieve the rows from the specified table where the search
		criteria matches.

		:return: A dictionary with columns and rows keys.
		:rtype: dict
		"""
		args = list(args)
		offset = 0
		fields = self.path.split('/')[1:-2]
		if len(args) == (len(fields) + 1):
			offset = (args.pop() * VIEW_ROW_COUNT)
		assert(len(fields) == len(args))
		table_name = self.path.split('/')[-2]
		table = db_models.DATABASE_TABLE_OBJECTS.get(table_name)
		assert(table)

		columns = DATABASE_TABLES[table_name]
		rows = []
		session = db_manager.Session()
		query = session.query(table)
		query = query.filter_by(**dict(zip(map(lambda f: f + '_id', fields), args)))
		for row in query[offset:offset + VIEW_ROW_COUNT]:
			rows.append(map(lambda c: getattr(row, c), columns))
		session.close()
		if not len(rows):
			return None
		return {'columns': columns, 'rows': rows}

	def rpc_database_delete_row_by_id(self, row_id):
		"""
		Delete a row from a table with the specified value in the id column.

		:param row_id: The id value.
		"""
		table = db_models.DATABASE_TABLE_OBJECTS.get(self.path.split('/')[-2])
		assert(table)
		session = db_manager.Session()
		query = session.query(table)
		query = query.filter_by(id=row_id)
		query.delete()
		session.commit()
		session.close()
		return

	def rpc_database_get_row_by_id(self, row_id):
		"""
		Retrieve a row from a given table with the specified value in the
		id column.

		:param row_id: The id value.
		:return: The specified row data.
		:rtype: dict
		"""
		table_name = self.path.split('/')[-2]
		table = db_models.DATABASE_TABLE_OBJECTS.get(table_name)
		assert(table)
		columns = DATABASE_TABLES[table_name]
		session = db_manager.Session()
		query = session.query(table)
		query = query.filter_by(id=row_id)
		row = query.first()
		if row:
			row = dict(zip(columns, map(lambda c: getattr(row, c), columns)))
		session.close()
		return row

	def rpc_database_insert_row(self, keys, values):
		"""
		Insert a new row into the specified table.

		:param tuple keys: The column names of *values*.
		:param tuple values: The values to be inserted in the row.
		"""
		if not isinstance(keys, (list, tuple)):
			keys = (keys,)
		if not isinstance(values, (list, tuple)):
			values = (values,)
		assert(len(keys) == len(values))
		table_name = self.path.split('/')[-2]
		for key, value in zip(keys, values):
			assert(key in DATABASE_TABLES[table_name])
		table = db_models.DATABASE_TABLE_OBJECTS.get(table_name)
		assert(table)
		session = db_manager.Session()
		row = table()
		for key, value in zip(keys, values):
			setattr(row, key, value)
		session.add(row)
		session.close()
		return

	def rpc_database_set_row_value(self, row_id, keys, values):
		"""
		Set values for a row in the specified table with an id of *row_id*.

		:param tuple keys: The column names of *values*.
		:param tuple values: The values to be updated in the row.
		"""
		if not isinstance(keys, (list, tuple)):
			keys = (keys,)
		if not isinstance(values, (list, tuple)):
			values = (values,)
		assert(len(keys) == len(values))
		table_name = self.path.split('/')[-2]
		for key, value in zip(keys, values):
			assert(key in DATABASE_TABLES[table_name])
		table = DATABASE_TABLE_OBJECTS.get(table_name)
		assert(table)
		session = db_manager.Session()
		query = session.query(table)
		query = query.filter_by(id=row_id)
		row = query.first()
		if not row:
			session.close()
			assert(row)
		for key, value in zip(keys, values):
			setattr(row, key, value)
		session.commit()
		session.close()
		return
