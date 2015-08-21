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

import functools
import threading

from king_phisher import geoip
from king_phisher import version
from king_phisher.server.database import manager as db_manager
from king_phisher.server.database import models as db_models

VIEW_ROW_COUNT = 50
"""The default number of rows to return when one of the /view methods are called."""

database_tables = db_models.database_tables
database_table_objects = db_models.database_table_objects

def database_access(function):
	"""
	A wrapping function that provides the consumer with a database session in
	an exception handling block that will automatically be closed.
	"""
	@functools.wraps(function)
	def wrapper(handler_instance, *args, **kwargs):
		session = db_manager.Session()
		try:
			result = function(handler_instance, session, *args, **kwargs)
		finally:
			session.close()
		return result
	return wrapper

class KingPhisherRequestHandlerRPC(object):
	"""
	This superclass of :py:class:`.KingPhisherRequestHandler` maintains
	all of the RPC call back functions.

	:RPC API: :ref:`rpc-api-label`
	"""
	def install_handlers(self):
		super(KingPhisherRequestHandlerRPC, self).install_handlers()
		self.rpc_handler_map['^/ping$'] = self.rpc_ping
		self.rpc_handler_map['^/shutdown$'] = self.rpc_shutdown
		self.rpc_handler_map['^/version$'] = self.rpc_version
		self.rpc_handler_map['^/geoip/lookup$'] = self.rpc_geoip_lookup
		self.rpc_handler_map['^/geoip/lookup/multi$'] = self.rpc_geoip_lookup_multi

		self.rpc_handler_map['^/client/initialize$'] = self.rpc_client_initialize
		self.rpc_handler_map['^/config/get$'] = self.rpc_config_get
		self.rpc_handler_map['^/config/set$'] = self.rpc_config_set

		self.rpc_handler_map['^/campaign/alerts/is_subscribed$'] = self.rpc_campaign_alerts_is_subscribed
		self.rpc_handler_map['^/campaign/alerts/subscribe$'] = self.rpc_campaign_alerts_subscribe
		self.rpc_handler_map['^/campaign/alerts/unsubscribe$'] = self.rpc_campaign_alerts_unsubscribe
		self.rpc_handler_map['^/campaign/landing_page/new$'] = self.rpc_campaign_landing_page_new
		self.rpc_handler_map['^/campaign/message/new$'] = self.rpc_campaign_message_new
		self.rpc_handler_map['^/campaign/new$'] = self.rpc_campaign_new

		# all the direct database methods
		self.rpc_handler_map['^/db/table/count$'] = self.rpc_database_count_rows
		self.rpc_handler_map['^/db/table/delete$'] = self.rpc_database_delete_row_by_id
		self.rpc_handler_map['^/db/table/delete/multi$'] = self.rpc_database_delete_rows_by_id
		self.rpc_handler_map['^/db/table/get$'] = self.rpc_database_get_row_by_id
		self.rpc_handler_map['^/db/table/insert$'] = self.rpc_database_insert_row
		self.rpc_handler_map['^/db/table/set$'] = self.rpc_database_set_row_value
		self.rpc_handler_map['^/db/table/view$'] = self.rpc_database_view_rows

	def rpc_ping(self):
		"""
		An RPC method that can be used by clients to assert the status
		and responsiveness of this server.

		:return: This method always returns True.
		:rtype: bool
		"""
		return True

	@database_access
	def rpc_client_initialize(self, session):
		"""
		Initialize any client information necessary.

		:return: This method always returns True.
		:rtype: bool
		"""
		username = self.basic_auth_user
		if not username:
			return True
		if not db_manager.get_row_by_id(session, db_models.User, username):
			user = db_models.User(id=username)
			session.add(user)
			session.commit()
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

	@database_access
	def rpc_campaign_new(self, session, name, description=None):
		"""
		Create a new King Phisher campaign and initialize the database
		information.

		:param str name: The new campaign's name.
		:param str description: The new campaign's description.
		:return: The ID of the new campaign.
		:rtype: int
		"""
		if session.query(db_models.Campaign).filter_by(name=name).count():
			raise ValueError('the specified campaign name already exists')
		campaign = db_models.Campaign(name=name, description=description, user_id=self.basic_auth_user)
		session.add(campaign)
		session.commit()
		return campaign.id

	@database_access
	def rpc_campaign_alerts_is_subscribed(self, session, campaign_id):
		"""
		Check if the user is subscribed to alerts for the specified campaign.

		:param int campaign_id: The ID of the campaign.
		:return: The alert subscription status.
		:rtype: bool
		"""
		username = self.basic_auth_user
		query = session.query(db_models.AlertSubscription)
		query = query.filter_by(campaign_id=campaign_id, user_id=username)
		return query.count()

	@database_access
	def rpc_campaign_alerts_subscribe(self, session, campaign_id):
		"""
		Subscribe to alerts for the specified campaign.

		:param int campaign_id: The ID of the campaign.
		"""
		username = self.basic_auth_user
		query = session.query(db_models.AlertSubscription)
		query = query.filter_by(campaign_id=campaign_id, user_id=username)
		if query.count() == 0:
			subscription = db_models.AlertSubscription(campaign_id=campaign_id, user_id=username)
			session.add(subscription)
			session.commit()

	@database_access
	def rpc_campaign_alerts_unsubscribe(self, session, campaign_id):
		"""
		Unsubscribe to alerts for the specified campaign.

		:param int campaign_id: The ID of the campaign.
		"""
		username = self.basic_auth_user
		query = session.query(db_models.AlertSubscription)
		query = query.filter_by(campaign_id=campaign_id, user_id=username)
		subscription = query.first()
		if subscription:
			session.delete(subscription)
			session.commit()

	@database_access
	def rpc_campaign_landing_page_new(self, session, campaign_id, hostname, page):
		"""
		Add a landing page for the specified campaign. Landing pages refer
		to resources that when visited by a user should cause the visit
		counter to be incremented.

		:param int campaign_id: The ID of the campaign.
		:param str hostname: The VHOST for the request.
		:param str page: The request resource.
		"""
		page = page.lstrip('/')
		query = session.query(db_models.LandingPage)
		query = query.filter_by(campaign_id=campaign_id, hostname=hostname, page=page)
		if query.count() == 0:
			landing_page = db_models.LandingPage(campaign_id=campaign_id, hostname=hostname, page=page)
			session.add(landing_page)
			session.commit()

	@database_access
	def rpc_campaign_message_new(self, session, campaign_id, email_id, target_email, first_name, last_name, department_name=None):
		"""
		Record a message that has been sent as part of a campaign. These
		details can be retrieved later for value substitution in template
		pages.

		:param int campaign_id: The ID of the campaign.
		:param str email_id: The message id of the sent email.
		:param str target_email: The email address that the message was sent to.
		:param str first_name: The first name of the message's recipient.
		:param str last_name: The last name of the message's recipient.
		:param str department_name: The name of the company department that the message's recipient belongs to.
		"""
		department = None
		if department_name is not None:
			department = session.query(db_models.CompanyDepartment).filter_by(name=department_name).first()
			if department is None:
				department = db_models.CompanyDepartment(name=department_name)
				session.add(department)
				session.commit()
		message = db_models.Message()
		message.id = email_id
		message.campaign_id = campaign_id
		message.target_email = target_email
		message.first_name = first_name
		message.last_name = last_name
		if department is not None:
			message.company_department_id = department.id
		session.add(message)
		session.commit()

	@database_access
	def rpc_database_count_rows(self, session, table_name, query_filter=None):
		"""
		Get a count of the rows in the specified table where the search
		criteria matches.

		:param str table_name: The name of the database table to query.
		:param dict query_filter: A dictionary mapping optional search criteria for matching the query.
		:return: The number of matching rows.
		:rtype: int
		"""
		table = database_table_objects.get(table_name)
		assert table
		query_filter = query_filter or {}
		columns = database_tables[table_name]
		for column in query_filter.keys():
			assert column in columns
		query = session.query(table)
		query = query.filter_by(**query_filter)
		return query.count()

	@database_access
	def rpc_database_view_rows(self, session, table_name, page=0, query_filter=None):
		"""
		Retrieve the rows from the specified table where the search
		criteria matches.

		:param str table_name: The name of the database table to query.
		:param int page: The page number to retrieve results for.
		:param dict query_filter: A dictionary mapping optional search criteria for matching the query.
		:return: A dictionary with columns and rows keys.
		:rtype: dict
		"""
		table = database_table_objects.get(table_name)
		assert table
		query_filter = query_filter or {}
		columns = database_tables[table_name]
		for column in query_filter.keys():
			assert column in columns

		offset = page * VIEW_ROW_COUNT
		# it's critical that the columns are in the order that the client is expecting
		rows = []
		query = session.query(table)
		query = query.filter_by(**query_filter)
		total_rows = query.count()
		for row in query[offset:offset + VIEW_ROW_COUNT]:
			rows.append([getattr(row, c) for c in columns])
		if not len(rows):
			return None
		return {'columns': columns, 'rows': rows, 'total_rows': total_rows, 'page_size': VIEW_ROW_COUNT}

	@database_access
	def rpc_database_delete_row_by_id(self, session, table_name, row_id):
		"""
		Delete a row from a table with the specified value in the id column.

		:param str table_name: The name of the database table to delete a row from.
		:param row_id: The id value.
		"""
		table = database_table_objects.get(table_name)
		assert table
		session.delete(db_manager.get_row_by_id(session, table, row_id))
		session.commit()

	@database_access
	def rpc_database_delete_rows_by_id(self, session, table_name, row_ids):
		"""
		Delete multiple rows from a table with the specified values in the id
		column. If a row id specified in *row_ids* does not exist, then it will
		be skipped and no error will be thrown.

		:param str table_name: The name of the database table to delete rows from.
		:param list row_ids: The row ids to delete.
		:return: The row ids that were deleted.
		:rtype: list
		"""
		table = database_table_objects.get(table_name)
		assert table
		deleted_rows = []
		for row_id in row_ids:
			row = db_manager.get_row_by_id(session, table, row_id)
			if not row:
				continue
			session.delete(row)
			deleted_rows.append(row_id)
		session.commit()
		return deleted_rows

	@database_access
	def rpc_database_get_row_by_id(self, session, table_name, row_id):
		"""
		Retrieve a row from a given table with the specified value in the
		id column.

		:param str table_name: The name of the database table to retrieve a row from.
		:param row_id: The id value.
		:return: The specified row data.
		:rtype: dict
		"""
		table = database_table_objects.get(table_name)
		assert table
		columns = database_tables[table_name]
		row = db_manager.get_row_by_id(session, table, row_id)
		if row:
			row = dict(zip(columns, (getattr(row, c) for c in columns)))
		return row

	@database_access
	def rpc_database_insert_row(self, session, table_name, keys, values):
		"""
		Insert a new row into the specified table.

		:param str table_name: The name of the database table to insert a new row into.
		:param tuple keys: The column names of *values*.
		:param tuple values: The values to be inserted in the row.
		:return: The id of the new row that has been added.
		"""
		if not isinstance(keys, (list, tuple)):
			keys = (keys,)
		if not isinstance(values, (list, tuple)):
			values = (values,)
		assert len(keys) == len(values)
		for key, value in zip(keys, values):
			assert key in database_tables[table_name]
		table = database_table_objects.get(table_name)
		assert table

		row = table()
		for key, value in zip(keys, values):
			setattr(row, key, value)
		session.add(row)
		session.commit()
		return row.id

	@database_access
	def rpc_database_set_row_value(self, session, table_name, row_id, keys, values):
		"""
		Set values for a row in the specified table with an id of *row_id*.

		:param str table_name: The name of the database table to set the values of the specified row.
		:param tuple keys: The column names of *values*.
		:param tuple values: The values to be updated in the row.
		"""
		if not isinstance(keys, (list, tuple)):
			keys = (keys,)
		if not isinstance(values, (list, tuple)):
			values = (values,)
		assert len(keys) == len(values)
		for key, value in zip(keys, values):
			assert key in database_tables[table_name]
		table = database_table_objects.get(table_name)
		assert table
		row = db_manager.get_row_by_id(session, table, row_id)
		if not row:
			session.close()
			assert row
		for key, value in zip(keys, values):
			setattr(row, key, value)
		session.commit()

	def rpc_geoip_lookup(self, ip, lang=None):
		"""
		Look up an IP address in the servers GeoIP database. If the IP address
		can not be found in the database, None will be returned.

		:param str ip: The IP address to look up.
		:param str lang: The language to prefer for regional names.
		:return: The geographic information for the specified IP address.
		:rtype: dict
		"""
		try:
			result = geoip.lookup(ip, lang=lang)
		except geoip.AddressNotFoundError:
			result = None
		return result

	def rpc_geoip_lookup_multi(self, ips, lang=None):
		"""
		Look up multiple IP addresses in the servers GeoIP database. Each IP
		address that can not be found in the database will have its result set
		to None.

		:param list ips: The list of IP addresses to look up.
		:param str lang: The language to prefer for regional names.
		:return: A dictionary containing the results keyed by the specified IP
			addresses.
		:rtype: dict
		"""
		results = {}
		for ip in ips:
			try:
				result = geoip.lookup(ip, lang=lang)
			except geoip.AddressNotFoundError:
				result = None
			results[ip] = result
		return results
