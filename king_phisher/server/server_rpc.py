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

import collections
import datetime
import functools
import logging
import os
import re
import threading

from king_phisher import errors
from king_phisher import geoip
from king_phisher import ipaddress
from king_phisher import startup
from king_phisher import version
from king_phisher.constants import ConnectionErrorReason
from king_phisher.server import letsencrypt
from king_phisher.server import signals
from king_phisher.server import web_tools
from king_phisher.server.database import manager as db_manager
from king_phisher.server.database import models as db_models
from king_phisher.server.graphql import schema

import advancedhttpserver
import boltons.typeutils
import pyotp

CONFIG_READABLE = (
	'beef.hook_url',
	'server.addresses',
	'server.cookie_name',
	'server.require_id',
	'server.rest_api.enabled',
	'server.secret_id',
	'server.tracking_image',
	'server.vhost_directories',
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
graphql_schema = schema.Schema()
rpc_logger = logging.getLogger('KingPhisher.Server.RPC')

_REDACTED = boltons.typeutils.make_sentinel('REDACTED', 'REDACTED')
"""Used with :py:func:`_log_rpc_call` as a place holder for sensitive arguments such as database row values."""

class _lend_semaphore(object):
	def __init__(self, handler):
		self.handler = handler

	def __enter__(self):
		self.handler.semaphore_release()

	def __exit__(self, exc_type, exc_val, exc_tb):
		self.handler.semaphore_acquire()

def _log_rpc_call(handler_instance, function_name, *args, **kwargs):
	if not rpc_logger.isEnabledFor(logging.DEBUG):
		return
	args_repr = ', '.join(map(repr, args))
	if kwargs:
		for key, value in sorted(kwargs.items()):
			args_repr += ", {0}={1!r}".format(key, value)
	user_id = getattr(handler_instance.rpc_session, 'user', 'N/A')
	msg = "user id: {0} calling RPC method {1}({2})".format(user_id, function_name, args_repr)
	rpc_logger.debug(msg)

def _ssl_is_enabled(handler):
	"""
	Returns whether or not SSL is enabled for any of the addresses that the
	server is bound with.
	"""
	return any(address.get('ssl', False) for address in handler.config.get('server.addresses'))

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
			if log_call:
				_log_rpc_call(handler_instance, function.__name__, *args, **kwargs)
			signals.send_safe('rpc-method-call', rpc_logger, path[1:-1], request_handler=handler_instance, args=args, kwargs=kwargs)
			if database_access:
				session = db_manager.Session()
				try:
					result = function(handler_instance, session, *args, **kwargs)
				finally:
					session.close()
			else:
				result = function(handler_instance, *args, **kwargs)
			signals.send_safe('rpc-method-called', rpc_logger, path[1:-1], request_handler=handler_instance, args=args, kwargs=kwargs, retval=result)
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
	rpc_logger.debug("shutdown routine running in tid: 0x{0:x}".format(shutdown_thread.ident))
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

@register_rpc('/config/get', log_call=True)
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
	if rpc_logger.isEnabledFor(logging.DEBUG):
		_log_rpc_call(handler, 'rpc_config_set', dict((key, _REDACTED) for key in options.keys()))
	for key, value in options.items():
		if key not in CONFIG_WRITEABLE:
			raise errors.KingPhisherPermissionError('permission denied to write config option: ' + key)
		handler.config.set(key, value)
	return

@register_rpc('/campaign/new', database_access=True, log_call=True)
def rpc_campaign_new(handler, session, name, description=None):
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
	campaign = db_models.Campaign(name=name, description=description, user_id=handler.rpc_session.user)
	campaign.assert_session_has_permissions('c', handler.rpc_session)
	session.add(campaign)
	session.commit()
	return campaign.id

@register_rpc('/campaign/alerts/is_subscribed', database_access=True, log_call=True)
def rpc_campaign_alerts_is_subscribed(handler, session, campaign_id):
	"""
	Check if the user is subscribed to alerts for the specified campaign.

	:param int campaign_id: The ID of the campaign.
	:return: The alert subscription status.
	:rtype: bool
	"""
	query = session.query(db_models.AlertSubscription)
	query = query.filter_by(campaign_id=campaign_id, user_id=handler.rpc_session.user)
	return query.count()

@register_rpc('/campaign/alerts/subscribe', database_access=True, log_call=True)
def rpc_campaign_alerts_subscribe(handler, session, campaign_id):
	"""
	Subscribe to alerts for the specified campaign.

	:param int campaign_id: The ID of the campaign.
	"""
	user_id = handler.rpc_session.user
	query = session.query(db_models.AlertSubscription)
	query = query.filter_by(campaign_id=campaign_id, user_id=user_id)
	if query.count() == 0:
		subscription = db_models.AlertSubscription(campaign_id=campaign_id, user_id=user_id)
		subscription.assert_session_has_permissions('c', handler.rpc_session)
		session.add(subscription)
		session.commit()

@register_rpc('/campaign/alerts/unsubscribe', database_access=True, log_call=True)
def rpc_campaign_alerts_unsubscribe(handler, session, campaign_id):
	"""
	Unsubscribe to alerts for the specified campaign.

	:param int campaign_id: The ID of the campaign.
	"""
	user_id = handler.rpc_session.user
	query = session.query(db_models.AlertSubscription)
	query = query.filter_by(campaign_id=campaign_id, user_id=user_id)
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

def _message_new(handler, session, campaign_id, email_id, target_email, first_name, last_name, department_name=None):
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
	return message

@register_rpc('/campaign/message/new', database_access=True, log_call=True)
def rpc_campaign_message_new(handler, session, campaign_id, email_id, target_email, first_name, last_name, department_name=None):
	"""
	Record a message that has been sent as part of a campaign. These details can
	be retrieved later for value substitution in template pages.

	:param int campaign_id: The ID of the campaign.
	:param str email_id: The message id of the sent email.
	:param str target_email: The email address that the message was sent to.
	:param str first_name: The first name of the message's recipient.
	:param str last_name: The last name of the message's recipient.
	:param str department_name: The name of the company department that the message's recipient belongs to.
	"""
	message = _message_new(handler, session, campaign_id, email_id, target_email, first_name, last_name, department_name=department_name)
	message.assert_session_has_permissions('c', handler.rpc_session)
	session.add(message)
	session.commit()

@register_rpc('/campaign/message/new/deferred', database_access=True, log_call=True)
def rpc_campaign_message_new(handler, session, campaign_id, email_id, target_email, first_name, last_name, department_name=None):
	"""
	Record a message that has been sent as part of a campaign. These details can
	be retrieved later for value substitution in template pages.

	:param int campaign_id: The ID of the campaign.
	:param str email_id: The message id of the sent email.
	:param str target_email: The email address that the message was sent to.
	:param str first_name: The first name of the message's recipient.
	:param str last_name: The last name of the message's recipient.
	:param str department_name: The name of the company department that the message's recipient belongs to.
	"""
	message = _message_new(handler, session, campaign_id, email_id, target_email, first_name, last_name, department_name=department_name)
	message.sent = db_models.sql_null()
	message.assert_session_has_permissions('c', handler.rpc_session)
	session.add(message)
	session.commit()

@register_rpc('/campaign/stats', database_access=True, log_call=True)
def rpc_campaign_stats(handler, session, campaign_id):
	"""
	Generate statistics regarding the specified campaign and return them in a
	dictionary. The dictionary will contain the keys credentials,
	credentials-unique, messages, messages-trained, visits, visits-unique.
	Values with unique in the key are counted unique by the message id for
	which they are associated.

	:param campaign_id: The unique ID of the campaign to generate statistics for.
	:return: The statistics for the specified campaign.
	:rtype: dict
	"""
	stats = {}
	stats['credentials'] = session.query(db_models.Credential).filter_by(campaign_id=campaign_id).count()
	stats['credentials-unique'] = session.query(db_models.Credential).filter_by(campaign_id=campaign_id).distinct(db_models.Credential.message_id).count()
	stats['messages'] = session.query(db_models.Message).filter_by(campaign_id=campaign_id).count()
	stats['messages-trained'] = session.query(db_models.Message).filter_by(campaign_id=campaign_id, trained=True).count()
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
	metatable = database_tables.get(table_name)
	if not metatable:
		raise errors.KingPhisherAPIError("failed to get table object for: {0}".format(table_name))
	query_filter = query_filter or {}
	for column in query_filter.keys():
		if column not in metatable.column_names:
			raise errors.KingPhisherAPIError("column {0} is invalid for table {1}".format(column, table_name))
	query = session.query(metatable.model)
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
	metatable = handler.server.tables_api.get(table_name)
	if not metatable:
		raise errors.KingPhisherAPIError("failed to get table object for: {0}".format(table_name))
	query_filter = query_filter or {}
	for column in query_filter.keys():
		if column not in metatable.column_names:
			raise errors.KingPhisherAPIError("column {0} is invalid for table {1}".format(column, table_name))

	offset = page * VIEW_ROW_COUNT
	# it's critical that the columns are in the order that the client is expecting
	rows = []
	query = session.query(metatable.model)
	query = query.filter_by(**query_filter)
	total_rows = query.count()
	for row in query[offset:]:
		if len(rows) == VIEW_ROW_COUNT:
			break
		if row.session_has_permissions('r', handler.rpc_session):
			rows.append([getattr(row, c) for c in metatable.column_names])
	if not len(rows):
		return None
	return {'columns': metatable.column_names, 'rows': rows, 'total_rows': total_rows, 'page_size': VIEW_ROW_COUNT}

@register_rpc('/db/table/delete', database_access=True, log_call=True)
def rpc_database_delete_row_by_id(handler, session, table_name, row_id):
	"""
	Delete the row from the table with the specified value in the id column.
	If the row does not exist, no error is raised.

	:param str table_name: The name of the database table to delete a row from.
	:param row_id: The id value.
	"""
	metatable = database_tables.get(table_name)
	if not metatable:
		raise errors.KingPhisherAPIError("failed to get table object for: {0}".format(table_name))
	row = db_manager.get_row_by_id(session, metatable.model, row_id)
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
	metatable = database_tables.get(table_name)
	if not metatable:
		raise errors.KingPhisherAPIError("failed to get table object for: {0}".format(table_name))
	deleted_rows = []
	for row_id in row_ids:
		row = db_manager.get_row_by_id(session, metatable.model, row_id)
		if not row:
			continue
		if not row.session_has_permissions('d', handler.rpc_session):
			continue
		session.delete(row)
		deleted_rows.append(row_id)
	session.commit()
	return deleted_rows

@register_rpc('/db/table/get', database_access=True, log_call=True)
def rpc_database_get_row_by_id(handler, session, table_name, row_id):
	"""
	Retrieve a row from a given table with the specified value in the
	id column.

	:param str table_name: The name of the database table to retrieve a row from.
	:param row_id: The id value.
	:return: The specified row data.
	:rtype: dict
	"""
	metatable = handler.server.tables_api.get(table_name)
	if not metatable:
		raise errors.KingPhisherAPIError("failed to get table object for: {0}".format(table_name))
	row = db_manager.get_row_by_id(session, metatable.model, row_id)
	if row:
		row.assert_session_has_permissions('r', handler.rpc_session)
		row = dict(zip(metatable.column_names, (getattr(row, c) for c in metatable.column_names)))
	elif metatable.model.is_private:
		raise errors.KingPhisherPermissionError()
	return row

@register_rpc('/db/table/insert', database_access=True)
def rpc_database_insert_row(handler, session, table_name, keys, values):
	"""
	Insert a new row into the specified table.

	:param str table_name: The name of the database table to insert a new row into.
	:param list keys: The column names of *values*.
	:param list values: The values to be inserted in the row.
	:return: The id of the new row that has been added.
	"""
	_log_rpc_call(handler, 'rpc_database_insert_row', table_name, keys, _REDACTED)
	if not isinstance(keys, (list, tuple)):
		keys = (keys,)
	if not isinstance(values, (list, tuple)):
		values = (values,)
	if len(keys) != len(values):
		raise errors.KingPhisherAPIError('the number of keys does not match the number of values')
	metatable = database_tables.get(table_name)
	if not metatable:
		raise errors.KingPhisherAPIError("failed to get table object for: {0}".format(table_name))
	for key in keys:
		if key not in metatable.column_names:
			raise errors.KingPhisherAPIError("column {0} is invalid for table {1}".format(key, table_name))

	row = metatable.model()
	for key, value in zip(keys, values):
		setattr(row, key, value)
	row.assert_session_has_permissions('c', handler.rpc_session)
	session.add(row)
	session.commit()
	return row.id

@register_rpc('/db/table/insert/multi', database_access=True)
def rpc_database_insert_row_multi(handler, session, table_name, keys, rows, deconflict_ids=False):
	"""
	Insert multiple new rows into the specified table. If *deconflict_ids* is
	true, new id values will be assigned as necessary to merge the data into
	the database. This function will fail if constraints for the table are
	not met.

	:param str table_name: The name of the database table to insert data into.
	:param list keys: The column names of the values in *rows*.
	:param list rows: A list of rows, each row is a list of values ordered and identified by *keys* to be inserted.
	:return: List of ids of the newly inserted rows.
	:rtype: list
	"""
	_log_rpc_call(handler, 'rpc_database_insert_row_multi', table_name, keys, _REDACTED, deconflict_ids=deconflict_ids)
	inserted_rows = collections.deque()
	if not isinstance(keys, list):
		keys = list(keys)
	if not isinstance(rows, list):
		rows = list(rows)

	metatable = database_tables.get(table_name)
	if not metatable:
		raise errors.KingPhisherAPIError('failed to get table object for: {0}'.format(table_name))
	for key in keys:
		if key not in metatable.column_names:
			raise errors.KingPhisherAPIError('column {0} is invalid for table {1}'.format(keys, table_name))

	for row in rows:
		if len(row) != len(keys):
			raise errors.KingPhisherAPIError('row is not the same length as the number of values defined')
		row = dict(zip(keys, row))
		if 'id' in row and db_manager.get_row_by_id(session, metatable.model, row['id']) is not None:
			if deconflict_ids:
				row['id'] = None
			else:
				raise errors.KingPhisherAPIError('row id conflicts with an existing value')

		table_row = metatable.model(**row)
		table_row.assert_session_has_permissions('c', handler.rpc_session)
		session.add(table_row)
		inserted_rows.append(table_row)
	session.commit()
	return [row.id for row in inserted_rows]

@register_rpc('/db/table/set', database_access=True)
def rpc_database_set_row_value(handler, session, table_name, row_id, keys, values):
	"""
	Set values for a row in the specified table with an id of *row_id*.

	:param str table_name: The name of the database table to set the values of the specified row.
	:param tuple keys: The column names of *values*.
	:param tuple values: The values to be updated in the row.
	"""
	_log_rpc_call(handler, 'rpc_database_rpc_row_value', table_name, row_id, keys, _REDACTED)
	if not isinstance(keys, (list, tuple)):
		keys = (keys,)
	if not isinstance(values, (list, tuple)):
		values = (values,)
	if len(keys) != len(values):
		raise errors.KingPhisherAPIError('the number of keys does not match the number of values')
	metatable = database_tables.get(table_name)
	if not metatable:
		raise errors.KingPhisherAPIError("failed to get table object for: {0}".format(table_name))
	for key, value in zip(keys, values):
		if key not in metatable.column_names:
			raise errors.KingPhisherAPIError("column {0} is invalid for table {1}".format(key, table_name))
	row = db_manager.get_row_by_id(session, metatable.model, row_id)
	if not row:
		raise errors.KingPhisherAPIError("failed to get row id: {0} from table: {1}".format(row_id, table_name))
	row.assert_session_has_permissions('u', handler.rpc_session)
	for key, value in zip(keys, values):
		setattr(row, key, value)
	row.assert_session_has_permissions('u', handler.rpc_session)
	session.commit()

@register_rpc('/events/is_subscribed', log_call=True)
def rpc_events_is_subscribed(handler, event_id, event_type):
	"""
	Check if the client is currently subscribed to the specified server event.

	:param str event_id: The identifier of the event to subscribe to.
	:param str event_type: A sub-type for the corresponding event.
	:return: Whether or not the client is subscribed to the event.
	:rtype: bool
	"""
	if not isinstance(event_id, str):
		raise errors.KingPhisherAPIError('a valid event id must be specified')
	if not isinstance(event_type, str):
		raise errors.KingPhisherAPIError('a valid event type must be specified')
	event_socket = handler.rpc_session.event_socket
	if event_socket is None:
		raise errors.KingPhisherAPIError('the event socket is not open for this session')
	return event_socket.is_subscribed(event_id, event_type)

@register_rpc('/events/subscribe', log_call=True)
def rpc_events_subscribe(handler, event_id, event_types=None, attributes=None):
	"""
	Subscribe the client to the specified event published by the server.
	When the event is published the specified *attributes* of it and it's
	corresponding id and type information will be sent to the client.

	:param str event_id: The identifier of the event to subscribe to.
	:param list event_types: A list of sub-types for the corresponding event.
	:param list attributes: A list of attributes of the event object to be sent to the client.
	"""
	if not isinstance(event_id, str):
		raise errors.KingPhisherAPIError('a valid event id must be specified')
	event_socket = handler.rpc_session.event_socket
	if event_socket is None:
		raise errors.KingPhisherAPIError('the event socket is not open for this session')
	if not event_id.startswith('db-'):
		# db-<table name> events are the only ones that are valid right now
		raise errors.KingPhisherAPIError('invalid event_id: ' + event_id)
	table_name = event_id[3:]
	table_name = table_name.replace('-', '_')
	metatable = database_tables.get(table_name)
	if metatable is None:
		raise errors.KingPhisherAPIError("invalid table object: {0}".format(table_name))
	for event_type in event_types:
		if event_type not in ('deleted', 'inserted', 'updated'):
			raise errors.KingPhisherAPIError("event type {0} is invalid for db-* events".format(event_type))
	for column in attributes:
		if column not in metatable.column_names:
			raise errors.KingPhisherAPIError("column {0} is invalid for table {1}".format(column, table_name))
	return event_socket.subscribe(event_id, event_types=event_types, attributes=attributes)

@register_rpc('/events/unsubscribe', log_call=True)
def rpc_events_unsubscribe(handler, event_id, event_types=None, attributes=None):
	"""
	Unsubscribe from an event published by the server that the client
	previously subscribed to.

	:param str event_id: The identifier of the event to subscribe to.
	:param list event_types: A list of sub-types for the corresponding event.
	:param list attributes: A list of attributes of the event object to be sent to the client.
	"""
	if not isinstance(event_id, str):
		raise errors.KingPhisherAPIError('a valid event id must be specified')
	event_socket = handler.rpc_session.event_socket
	if event_socket is None:
		raise errors.KingPhisherAPIError('the event socket is not open for this session')
	return event_socket.unsubscribe(event_id, event_types=event_types, attributes=attributes)

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

@register_rpc('/hostnames/add', log_call=True)
def rpc_hostnames_add(handler, hostname):
	"""
	Add a hostname to the list of values that are configured for use with this
	server. At this time, these changes (like other config changes) are not
	persisted in the server so they will be lost when the server reboots.

	.. versionadded:: 1.13.0

	:param str hostname: The hostname to add.
	"""
	hostnames = handler.config.get_if_exists('server.hostnames', [])
	if hostname not in hostnames:
		hostnames.append(hostname)
	handler.config.set('server.hostnames', hostnames)
	# don't return a value indicating whether it was added or not because it could have been a vhost directory

@register_rpc('/hostnames/get', log_call=True)
def rpc_hostnames_get(handler):
	"""
	Get the hostnames that are configured for use with this server. This is not
	related to the ``ssl/hostnames`` RPC methods which deal with hostnames as
	they relate to SSL for the purposes of certificate usage.

	.. versionadded:: 1.13.0

	:return: The configured hostnames.
	:rtype: list
	"""
	return list(web_tools.get_hostnames(handler.config))

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

	user = session.query(db_models.User).filter_by(name=username).first()
	if not user:
		logger.info('creating new user object with name: ' + username)
		user = db_models.User(name=username)
	elif user.has_expired:
		logger.warning("failed login request from {0} for user {1}, (user has expired)".format(handler.client_address[0], username))
		return fail_default
	elif user.otp_secret:
		if otp is None:
			logger.debug("failed login request from {0} for user {1}, (missing otp)".format(handler.client_address[0], username))
			return fail_otp
		if not (isinstance(otp, str) and len(otp) == 6 and otp.isdigit()):
			logger.warning("failed login request from {0} for user {1}, (invalid otp)".format(handler.client_address[0], username))
			return fail_otp
		totp = pyotp.TOTP(user.otp_secret)
		now = datetime.datetime.now()
		if otp not in (totp.at(now + datetime.timedelta(seconds=offset)) for offset in (0, -30, 30)):
			logger.warning("failed login request from {0} for user {1}, (invalid otp)".format(handler.client_address[0], username))
			return fail_otp
	user.last_login = db_models.current_timestamp()
	session.add(user)
	session.commit()
	session_id = handler.server.session_manager.put(user)
	logger.info("successful login request from {0} for user {1} (id: {2})".format(handler.client_address[0], username, user.id))
	signals.send_safe('rpc-user-logged-in', logger, handler, session=session_id, name=username)
	return True, ConnectionErrorReason.SUCCESS, session_id

@register_rpc('/logout', database_access=True, log_call=True)
def rpc_logout(handler, session):
	rpc_session = handler.rpc_session
	if rpc_session.event_socket is not None:
		rpc_session.event_socket.close()
	handler.server.session_manager.remove(handler.rpc_session_id)
	logger = logging.getLogger('KingPhisher.Server.Authentication')
	logger.info("successful logout request from {0} for user id: {1}".format(handler.client_address[0], rpc_session.user))
	user = session.query(db_models.User).filter_by(id=rpc_session.user).first()
	signals.send_safe('rpc-user-logged-out', logger, handler, session=handler.rpc_session_id, name=user.name)

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
			'authors': plugin.authors,
			'classifiers': plugin.classifiers,
			'description': plugin.description,
			'homepage': plugin.homepage,
			'name': plugin.name,
			'reference_urls': plugin.reference_urls,
			'title': plugin.title,
			'version': plugin.version
		}
	return plugins

@register_rpc('/graphql', database_access=True)
def rpc_graphql(handler, session, query, query_vars=None):
	"""
	Execute a GraphQL query and return the results. If the query fails to
	execute the errors returned are populated in the **errors** key of the
	results dictionary. If the query executes successfully the returned data
	is available in the **data** key of the results dictionary.

	:param str query: The GraphQL query to execute.
	:param dict query_vars: Any variables needed by the *query*.
	:return: The results of the query as a dictionary.
	:rtype: dict
	"""
	query_vars = query_vars or {}
	result = graphql_schema.execute(
		query,
		context_value={
			'plugin_manager': handler.server.plugin_manager,
			'rpc_session': handler.rpc_session,
			'server_config': handler.config,
			'session': session
		},
		variable_values=query_vars
	)
	errors = None
	if result.errors:
		errors = []
		for error in result.errors:
			if hasattr(error, 'message'):
				errors.append(error.message)
			elif hasattr(error, 'args') and error.args:
				errors.append(str(error.args[0]))
			else:
				errors.append(repr(error))
	return {'data': result.data, 'errors': errors}

@register_rpc('/ssl/letsencrypt/certbot_version', database_access=False, log_call=True)
def rpc_ssl_letsencrypt_certbot_version(handler):
	"""
	Find the certbot binary and retrieve it's version information. If the
	certbot binary could not be found, ``None`` is returned.

	.. versionadded:: 1.14.0

	:return: The version of certbot.
	:rtype: str
	"""
	bin_path = letsencrypt.get_certbot_bin_path(handler.config)
	if bin_path is None:
		return None
	results = startup.run_process((bin_path, '--version'))
	match = re.match(r'^certbot (?P<version>\d+\.\d+\.\d+)$', results.stdout)
	if match is None:
		return None
	return match.group('version')

@register_rpc('/ssl/letsencrypt/issue', log_call=True)
def rpc_ssl_letsencrypt_issue(handler, hostname, load=True):
	"""
	Issue a certificate with Let's Encrypt. This operation can fail for a wide
	variety of reasons, check the ``message`` key of the returned dictionary for
	a string description of what occurred. Successful operation requires that
	the certbot utility be installed, and the server's Let's Encrypt data path
	is configured.

	.. versionadded:: 1.14.0

	:param str hostname: The hostname of the certificate to issue.
	:param bool load: Whether or not to load the certificate once it has been issued.
	:return: A dictionary containing the results of the operation.
	:rtype: dict
	"""
	config = handler.config
	result = {'success': False}

	letsencrypt_config = config.get_if_exists('server.letsencrypt', {})
	# step 1: ensure that a letsencrypt configuration is available
	data_path = letsencrypt_config.get('data_path')
	if not data_path:
		result['message'] = 'Let\'s Encrypt is not configured for use.'
		return result
	if not os.path.isdir(data_path):
		rpc_logger.info('creating the letsencrypt data directory')
		os.mkdir(data_path)

	# step 2: ensure that SSL is enabled already
	if not _ssl_is_enabled(handler):
		result['message'] = 'Can not issue certificates when SSL is not in use.'
		return result
	if not advancedhttpserver.g_ssl_has_server_sni:
		result['message'] = 'Can not issue certificates when SNI is not available.'
		return result

	# step 3: ensure that the certbot utility is available
	bin_path = letsencrypt_config.get('certbot_path') or startup.which('certbot')
	if not bin_path:
		result['message'] = 'Can not issue certificates without the certbot utility.'
		return result

	# step 4: ensure the hostname looks legit (TM) and hasn't already been issued
	if re.match(r'^[a-z0-9][a-z0-9-]*(\.[a-z0-9-]+)+$', hostname, flags=re.IGNORECASE) is None:
		result['message'] = 'Can not issue certificates for invalid hostnames.'
		return result
	if letsencrypt.get_sni_hostname_config(hostname, config):
		result['message'] = 'The specified hostname already has the necessary files.'
		return result

	# step 5: determine the web_root path for this hostname and create it if necessary
	web_root = config.get('server.web_root')
	if config.get('server.vhost_directories'):
		web_root = os.path.join(web_root, hostname)
		if not os.path.isdir(web_root):
			rpc_logger.info('vhost directory does not exist for hostname: ' + hostname)
			os.mkdir(web_root)

	# step 6: issue the certificate with certbot, this starts the subprocess and may take a few seconds
	with _lend_semaphore(handler):
		status = letsencrypt.certbot_issue(web_root, hostname, bin_path=bin_path, unified_directory=data_path)
	if status != os.EX_OK:
		result['message'] = 'Failed to issue the certificate.'
		return result

	# step 7: ensure the necessary files were created
	sni_config = letsencrypt.get_sni_hostname_config(hostname, config)
	if sni_config is None:
		result['message'] = 'The certificate files were not generated.'
		return result

	# step 8: store the data in the database so it can be loaded next time the server starts
	if load:
		handler.server.add_sni_cert(hostname, ssl_certfile=sni_config.certfile, ssl_keyfile=sni_config.keyfile)
	else:
		letsencrypt.set_sni_hostname(hostname, sni_config.certfile, sni_config.certfile, enabled=False)

	result['success'] = True
	result['message'] = 'The operation completed successfully.'
	return result

@register_rpc('/ssl/sni_hostnames/get', log_call=True)
def rpc_ssl_sni_hostnames_get(handler):
	"""
	Get the hostnames that have available Server Name Indicator (SNI)
	configurations for use with SSL.

	.. versionadded:: 1.14.0

	:return: A dictionary keyed by hostnames with values of dictionaries containing additional metadata.
	:rtype: dict
	"""
	if not advancedhttpserver.g_ssl_has_server_sni:
		rpc_logger.warning('can not enumerate SNI hostnames when SNI is not available')
		return
	hostnames = {}
	for hostname, sni_config in letsencrypt.get_sni_hostnames(handler.config).items():
		hostnames[hostname] = {'enabled': sni_config.enabled}
	return hostnames

@register_rpc('/ssl/sni_hostnames/load', log_call=True)
def rpc_ssl_sni_hostnames_load(handler, hostname):
	"""
	Load the SNI configuration for the specified *hostname*, effectively
	enabling it. If SSL is not enabled, SNI is not available, or the necessary
	data files are not available, this function returns ``False``.

	.. versionadded:: 1.14.0

	:param str hostname: The hostname to configure SSL for.
	:return: Returns ``True`` only if the SNI configuration for *hostname* was
		either able to be loaded or was already loaded.
	:rtype: bool
	"""
	if not _ssl_is_enabled(handler):
		rpc_logger.warning('can not add an SNI hostname when SSL is not in use')
		return False
	if not advancedhttpserver.g_ssl_has_server_sni:
		rpc_logger.warning('can not add an SNI hostname when SNI is not available')
		return False

	for sni_cert in handler.server.get_sni_certs():
		if sni_cert.hostname == hostname:
			rpc_logger.info('ignoring directive to add an SNI hostname that already exists')
			return True
	sni_config = letsencrypt.get_sni_hostname_config(hostname, handler.config)
	if not sni_config:
		rpc_logger.warning('can not add an SNI hostname without the necessary files')
		return False
	handler.server.add_sni_cert(hostname, sni_config.certfile, sni_config.keyfile)
	return True

@register_rpc('/ssl/sni_hostnames/unload', log_call=True)
def rpc_ssl_sni_hostnames_unload(handler, hostname):
	"""
	Unload the SNI configuration for the specified *hostname*, effectively
	disabling it. If SNI is not available, or the specified configuration was
	not already loaded, this function returns ``False``.

	.. versionadded:: 1.14.0

	:param str hostname: The hostname to configure SSL for.
	:return: Returns ``True`` only if the SNI configuration for *hostname* was unloaded.
	:rtype: bool
	"""
	if not advancedhttpserver.g_ssl_has_server_sni:
		rpc_logger.warning('can not remove an SNI hostname when SNI is not available')
		return False
	for sni_cert in handler.server.get_sni_certs():
		if sni_cert.hostname == hostname:
			break
	else:
		rpc_logger.warning('can not remove an SNI hostname that does not exist')
		return False
	handler.server.remove_sni_cert(sni_cert.hostname)
	return True

@register_rpc('/ssl/status', log_call=True)
def rpc_ssl_status(handler):
	"""
	Get information regarding the status of SSL on the server. This method
	returns a dictionary with keys describing whether or not SSL is enabled on
	one or more interfaces, and whether or not the server possess the SNI
	support. For details regarding which addresses are using SSL, see the
	:py:func:`~rpc_config_get` method.

	.. versionadded:: 1.14.0

	:return: A dictionary with SSL status information.
	:rtype: dict
	"""
	status = {
		'enabled': _ssl_is_enabled(handler),
		'has-letsencrypt': letsencrypt.get_certbot_bin_path(handler.config) is not None,
		'has-sni': advancedhttpserver.g_ssl_has_server_sni
	}
	return status
