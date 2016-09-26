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

import datetime
import functools
import logging
import threading

from king_phisher import errors
from king_phisher import geoip
from king_phisher import ipaddress
from king_phisher import version
from king_phisher.constants import ConnectionErrorReason
from king_phisher.server import signals
from king_phisher.server.database import manager as db_manager
from king_phisher.server.database import models as db_models

import advancedhttpserver
import pyotp

CONFIG_READABLE = (
	'beef.hook_url',
	'server.address.host',
	'server.address.port',
	'server.require_id',
	'server.secret_id',
	'server.tracking_image',
	'server.web_root'
)
"""Configuration options that can be accessed by the client."""
CONFIG_WRITEABLE = ('beef.hook_url',)
"""Configuration options that can be changed by the client at run time."""
RPC_AUTH_HEADER = 'X-RPC-Auth'
"""The header which contains the RPC authorization / session token."""
VIEW_ROW_COUNT = 50
"""The default number of rows to return when one of the /view methods are called."""

database_tables = db_models.database_tables
database_table_objects = db_models.database_table_objects

rpc_logger = logging.getLogger('KingPhisher.Server.RPC')

def register_rpc(path, database_access=False, log_call=False):
	"""
	Register an RPC function with the HTTP request handler. This allows the
	method to be remotely invoked using King Phisher's standard RPC interface.
	If *database_access* is specified, a SQLAlchemy session will be passed as
	the second argument, after the standard
	:py:class:`~advancedhttpserver.RequestHandler` instance.

	:param str path: The path for the RPC function.
	:param bool database_access: Whether or not the function requires database access.
	:param bool log_call: Whether or not to log the arguments which the function is called with.
	"""
	path = '^' + path + '$'
	def decorator(function):
		@functools.wraps(function)
		def wrapper(handler_instance, *args, **kwargs):
			if log_call and rpc_logger.isEnabledFor(logging.DEBUG):
				args_repr = ', '.join(map(repr, args))
				if kwargs:
					for key, value in sorted(kwargs.items()):
						args_repr += ", {0}={1!r}".format(key, value)
				msg = "calling RPC method {0}({1})".format(function.__name__, args_repr)
				if getattr(handler_instance, 'rpc_session', False):
					msg = handler_instance.rpc_session.user + ' is ' + msg
				rpc_logger.debug(msg)
			signals.rpc_method_call.send(path[1:-1], request_handler=handler_instance, args=args, kwargs=kwargs)
			if database_access:
				session = db_manager.Session()
				try:
					result = function(handler_instance, session, *args, **kwargs)
				finally:
					session.close()
			else:
				result = function(handler_instance, *args, **kwargs)
			signals.rpc_method_called.send(path[1:-1], request_handler=handler_instance, args=args, kwargs=kwargs, retval=result)
			return result
		advancedhttpserver.RegisterPath(path, is_rpc=True)(wrapper)
		return wrapper
	return decorator

@register_rpc('/ping', log_call=True)
def rpc_ping(handler):
	"""
	An RPC method that can be used by clients to assert the status
	and responsiveness of this server.

	:return: This method always returns True.
	:rtype: bool
	"""
	return True

@register_rpc('/shutdown', log_call=True)
def rpc_shutdown(handler):
	"""
	This method can be used to shut down the server. This function will
	return, however no subsequent requests will be processed.

	.. warning::
		This action will stop the server process and there is no
		confirmation before it takes place.
	"""
	shutdown_thread = threading.Thread(target=handler.server.kp_shutdown)
	shutdown_thread.start()
	return

@register_rpc('/version', log_call=True)
def rpc_version(handler):
	"""
	Get the version information of the server. This returns a
	dictionary with keys of version, version_info and rpc_api_version.
	These values are provided for the client to determine
	compatibility.

	:return: A dictionary with version information.
	:rtype: dict
	"""
	if not ipaddress.ip_address(handler.client_address[0]).is_loopback:
		message = "an rpc request to /version was received from non-loopback IP address: {0}".format(handler.client_address[0])
		rpc_logger.error(message)
		raise errors.KingPhisherAPIError(message)

	vinfo = {
		'rpc_api_version': version.rpc_api_version,
		'version': version.version,
		'version_info': version.version_info._asdict()
	}
	return vinfo

@register_rpc('/config/get')
def rpc_config_get(handler, option_name):
	"""
	Retrieve a value from the server's configuration.

	:param str option_name: The name of the configuration option.
	:return: The option's value.
	"""
	if isinstance(option_name, (list, tuple)):
		option_names = option_name
		option_values = {}
		for option_name in option_names:
			if not option_name in CONFIG_READABLE:
				raise errors.KingPhisherPermissionError('permission denied to read config option: ' + option_name)
			if handler.config.has_option(option_name):
				option_values[option_name] = handler.config.get(option_name)
		return option_values
	if not option_name in CONFIG_READABLE:
		raise errors.KingPhisherPermissionError('permission denied to read config option: ' + option_name)
	if handler.config.has_option(option_name):
		return handler.config.get(option_name)
	return

@register_rpc('/config/set')
def rpc_config_set(handler, options):
	"""
	Set options in the server's configuration. Any changes to the
	server's configuration are not written to disk.

	:param dict options: A dictionary of option names and values
	"""
	for option_name, option_value in options.items():
		if not option_name in CONFIG_WRITEABLE:
			raise errors.KingPhisherPermissionError('permission denied to write config option: ' + option_name)
		handler.config.set(option_name, option_value)
	return

@register_rpc('/campaign/new', database_access=True, log_call=True)
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
	campaign = db_models.Campaign(name=name, description=description, user_id=self.rpc_session.user)
	campaign.assert_session_has_permissions('c', self.rpc_session)
	session.add(campaign)
	session.commit()
	return campaign.id

@register_rpc('/campaign/alerts/is_subscribed', database_access=True, log_call=True)
def rpc_campaign_alerts_is_subscribed(self, session, campaign_id):
	"""
	Check if the user is subscribed to alerts for the specified campaign.

	:param int campaign_id: The ID of the campaign.
	:return: The alert subscription status.
	:rtype: bool
	"""
	username = self.rpc_session.user
	query = session.query(db_models.AlertSubscription)
	query = query.filter_by(campaign_id=campaign_id, user_id=username)
	return query.count()

@register_rpc('/campaign/alerts/subscribe', database_access=True, log_call=True)
def rpc_campaign_alerts_subscribe(handler, session, campaign_id):
	"""
	Subscribe to alerts for the specified campaign.

	:param int campaign_id: The ID of the campaign.
	"""
	username = handler.rpc_session.user
	query = session.query(db_models.AlertSubscription)
	query = query.filter_by(campaign_id=campaign_id, user_id=username)
	if query.count() == 0:
		subscription = db_models.AlertSubscription(campaign_id=campaign_id, user_id=username)
		subscription.assert_session_has_permissions('c', handler.rpc_session)
		session.add(subscription)
		session.commit()

@register_rpc('/campaign/alerts/unsubscribe', database_access=True, log_call=True)
def rpc_campaign_alerts_unsubscribe(handler, session, campaign_id):
	"""
	Unsubscribe to alerts for the specified campaign.

	:param int campaign_id: The ID of the campaign.
	"""
	username = handler.rpc_session.user
	query = session.query(db_models.AlertSubscription)
	query = query.filter_by(campaign_id=campaign_id, user_id=username)
	subscription = query.first()
	if subscription:
		subscription.assert_session_has_permissions('d', handler.rpc_session)
		session.delete(subscription)
		session.commit()

@register_rpc('/campaign/landing_page/new', database_access=True, log_call=True)
def rpc_campaign_landing_page_new(handler, session, campaign_id, hostname, page):
	"""
	Add a landing page for the specified campaign. Landing pages refer
	to resources that when visited by a user should cause the visit
	counter to be incremented.

	:param int campaign_id: The ID of the campaign.
	:param str hostname: The hostname which will be used to serve the request.
	:param str page: The request resource.
	"""
	hostname = hostname.split(':', 1)[0]
	page = page.lstrip('/')
	query = session.query(db_models.LandingPage)
	query = query.filter_by(campaign_id=campaign_id, hostname=hostname, page=page)
	if query.count() == 0:
		landing_page = db_models.LandingPage(campaign_id=campaign_id, hostname=hostname, page=page)
		landing_page.assert_session_has_permissions('c', handler.rpc_session)
		session.add(landing_page)
		session.commit()

@register_rpc('/campaign/message/new', database_access=True, log_call=True)
def rpc_campaign_message_new(handler, session, campaign_id, email_id, target_email, first_name, last_name, department_name=None):
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
			department.assert_session_has_permissions('c', handler.rpc_session)
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
	message.assert_session_has_permissions('c', handler.rpc_session)
	session.add(message)
	session.commit()

@register_rpc('/campaign/stats', database_access=True, log_call=True)
def rpc_campaign_stats(handler, session, campaign_id):
	"""
	Generate statistics regarding the specified campaign and return them in a
	dictionary. The dictionary will contain the keys credentials,
	credentials-unique, messages, visits, visits-unique. Values with unique in
	the key are counted unique by the message id for which they are associated.

	:param campaign_id: The unique ID of the campaign to generate statistics for.
	:return: The statistics for the specified campaign.
	:rtype: dict
	"""
	stats = {}
	stats['credentials'] = session.query(db_models.Credential).filter_by(campaign_id=campaign_id).count()
	stats['credentials-unique'] = session.query(db_models.Credential).filter_by(campaign_id=campaign_id).distinct(db_models.Credential.message_id).count()
	stats['messages'] = session.query(db_models.Message).filter_by(campaign_id=campaign_id).count()
	stats['visits'] = session.query(db_models.Visit).filter_by(campaign_id=campaign_id).count()
	stats['visits-unique'] = session.query(db_models.Visit).filter_by(campaign_id=campaign_id).distinct(db_models.Visit.message_id).count()
	return stats

@register_rpc('/db/table/count', database_access=True)
def rpc_database_count_rows(handler, session, table_name, query_filter=None):
	"""
	Get a count of the rows in the specified table where the search
	criteria matches.

	:param str table_name: The name of the database table to query.
	:param dict query_filter: A dictionary mapping optional search criteria for matching the query.
	:return: The number of matching rows.
	:rtype: int
	"""
	table = database_table_objects.get(table_name)
	if not table:
		raise errors.KingPhisherAPIError("failed to get table object for: {0}".format(table_name))
	query_filter = query_filter or {}
	columns = database_tables[table_name]
	for column in query_filter.keys():
		if column not in columns:
			raise errors.KingPhisherAPIError("column {0} is invalid for table {1}".format(column, table_name))
	query = session.query(table)
	query = query.filter_by(**query_filter)
	return query.count()

@register_rpc('/db/table/view', database_access=True)
def rpc_database_view_rows(handler, session, table_name, page=0, query_filter=None):
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
	if not table:
		raise errors.KingPhisherAPIError("failed to get table object for: {0}".format(table_name))
	query_filter = query_filter or {}
	columns = database_tables[table_name]
	for column in query_filter.keys():
		if column not in columns:
			raise errors.KingPhisherAPIError("column {0} is invalid for table {1}".format(column, table_name))

	offset = page * VIEW_ROW_COUNT
	# it's critical that the columns are in the order that the client is expecting
	rows = []
	query = session.query(table)
	query = query.filter_by(**query_filter)
	total_rows = query.count()
	for row in query[offset:]:
		if len(rows) == VIEW_ROW_COUNT:
			break
		if row.session_has_permissions('r', handler.rpc_session):
			rows.append([getattr(row, c) for c in columns])
	if not len(rows):
		return None
	return {'columns': columns, 'rows': rows, 'total_rows': total_rows, 'page_size': VIEW_ROW_COUNT}

@register_rpc('/db/table/delete', database_access=True, log_call=True)
def rpc_database_delete_row_by_id(handler, session, table_name, row_id):
	"""
	Delete the row from the table with the specified value in the id column.
	If the row does not exist, no error is raised.

	:param str table_name: The name of the database table to delete a row from.
	:param row_id: The id value.
	"""
	table = database_table_objects.get(table_name)
	if not table:
		raise errors.KingPhisherAPIError("failed to get table object for: {0}".format(table_name))
	row = db_manager.get_row_by_id(session, table, row_id)
	if row is None:
		logger = logging.getLogger('KingPhisher.Server.API.RPC')
		logger.debug("received delete request for non existing row with id {0} from table {1}".format(row_id, table_name))
		return
	row.assert_session_has_permissions('d', handler.rpc_session)
	session.delete(row)
	session.commit()

@register_rpc('/db/table/delete/multi', database_access=True, log_call=True)
def rpc_database_delete_rows_by_id(handler, session, table_name, row_ids):
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
	if not table:
		raise errors.KingPhisherAPIError("failed to get table object for: {0}".format(table_name))
	deleted_rows = []
	for row_id in row_ids:
		row = db_manager.get_row_by_id(session, table, row_id)
		if not row:
			continue
		if not row.session_has_permissions('d', handler.rpc_session):
			continue
		session.delete(row)
		deleted_rows.append(row_id)
	session.commit()
	return deleted_rows

@register_rpc('/db/table/get', database_access=True)
def rpc_database_get_row_by_id(handler, session, table_name, row_id):
	"""
	Retrieve a row from a given table with the specified value in the
	id column.

	:param str table_name: The name of the database table to retrieve a row from.
	:param row_id: The id value.
	:return: The specified row data.
	:rtype: dict
	"""
	table = database_table_objects.get(table_name)
	if not table:
		raise errors.KingPhisherAPIError("failed to get table object for: {0}".format(table_name))
	columns = database_tables[table_name]
	row = db_manager.get_row_by_id(session, table, row_id)
	if row:
		row.assert_session_has_permissions('r', handler.rpc_session)
		row = dict(zip(columns, (getattr(row, c) for c in columns)))
	return row

@register_rpc('/db/table/insert', database_access=True)
def rpc_database_insert_row(handler, session, table_name, keys, values):
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
	if len(keys) != len(values):
		raise errors.KingPhisherAPIError('the number of keys does not match the number of values')
	table = database_table_objects.get(table_name)
	if not table:
		raise errors.KingPhisherAPIError("failed to get table object for: {0}".format(table_name))
	for key, value in zip(keys, values):
		if key not in database_tables[table_name]:
			raise errors.KingPhisherAPIError("column {0} is invalid for table {1}".format(key, table_name))

	row = table()
	for key, value in zip(keys, values):
		setattr(row, key, value)
	row.assert_session_has_permissions('c', handler.rpc_session)
	session.add(row)
	session.commit()
	return row.id

@register_rpc('/db/table/set', database_access=True)
def rpc_database_set_row_value(handler, session, table_name, row_id, keys, values):
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
	if len(keys) != len(values):
		raise errors.KingPhisherAPIError('the number of keys does not match the number of values')
	table = database_table_objects.get(table_name)
	if not table:
		raise errors.KingPhisherAPIError("failed to get table object for: {0}".format(table_name))
	for key, value in zip(keys, values):
		if key not in database_tables[table_name]:
			raise errors.KingPhisherAPIError("column {0} is invalid for table {1}".format(key, table_name))
	row = db_manager.get_row_by_id(session, table, row_id)
	if not row:
		raise errors.KingPhisherAPIError("failed to get row id: {0} from table: {1}".format(row_id, table_name))
	for key, value in zip(keys, values):
		setattr(row, key, value)
	row.assert_session_has_permissions('u', handler.rpc_session)
	session.commit()

@register_rpc('/geoip/lookup', log_call=True)
def rpc_geoip_lookup(handler, ip, lang=None):
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

@register_rpc('/geoip/lookup/multi', log_call=True)
def rpc_geoip_lookup_multi(handler, ips, lang=None):
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

@register_rpc('/login', database_access=True)
def rpc_login(handler, session, username, password, otp=None):
	logger = logging.getLogger('KingPhisher.Server.Authentication')
	if not ipaddress.ip_address(handler.client_address[0]).is_loopback:
		logger.warning("failed login request from {0} for user {1}, (invalid source address)".format(handler.client_address[0], username))
		raise ValueError('invalid source address for login')
	fail_default = (False, ConnectionErrorReason.ERROR_INVALID_CREDENTIALS, None)
	fail_otp = (False, ConnectionErrorReason.ERROR_INVALID_OTP, None)

	if not (username and password):
		logger.warning("failed login request from {0} for user {1}, (missing username or password)".format(handler.client_address[0], username))
		return fail_default
	if not handler.server.forked_authenticator.authenticate(username, password):
		logger.warning("failed login request from {0} for user {1}, (authentication failed)".format(handler.client_address[0], username))
		return fail_default

	user = db_manager.get_row_by_id(session, db_models.User, username)
	if not user:
		logger.info('creating new user object with id: ' + username)
		user = db_models.User(id=username)
		session.add(user)
		session.commit()
	elif user.otp_secret:
		if otp is None:
			logger.debug("failed login request from {0} for user {1}, (missing otp)".format(handler.client_address[0], username))
			return fail_otp
		if not (isinstance(otp, str) and len(otp) == 6 and otp.isdigit()):
			logger.warning("failed login request from {0} for user {1}, (invalid otp)".format(handler.client_address[0], username))
			return fail_otp
		totp = pyotp.TOTP(user.otp_secret)
		now = datetime.datetime.now()
		if not otp in (totp.at(now + datetime.timedelta(seconds=offset)) for offset in (0, -30, 30)):
			logger.warning("failed login request from {0} for user {1}, (invalid otp)".format(handler.client_address[0], username))
			return fail_otp
	session_id = handler.server.session_manager.put(username)
	logger.info("successful login request from {0} for user {1}".format(handler.client_address[0], username))
	signals.rpc_user_logged_in.send(handler, session=session_id, name=username)
	return True, ConnectionErrorReason.SUCCESS, session_id

@register_rpc('/logout', log_call=True)
def rpc_logout(handler):
	username = handler.rpc_session.user
	handler.server.session_manager.remove(handler.rpc_session_id)
	logger = logging.getLogger('KingPhisher.Server.Authentication')
	logger.info("successful logout request from {0} for user {1}".format(handler.client_address[0], username))
	signals.rpc_user_logged_out.send(handler, session=handler.rpc_session_id, name=username)

@register_rpc('/plugins/list', log_call=True)
def rpc_plugins_list(handler):
	"""
	Return information regarding enabled plugins in the server.

	:return: A dictionary representing enabled plugins and their meta-data.
	:rtype: dict
	"""
	plugin_manager = handler.server.plugin_manager
	plugins = {}
	for _, plugin in plugin_manager:
		plugins[plugin.name] = {
			'description': plugin.formatted_description,
			'name': plugin.name,
			'title': plugin.title,
			'version': plugin.version
		}
	return plugins
