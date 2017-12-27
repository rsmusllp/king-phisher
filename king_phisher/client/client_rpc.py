#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  king_phisher/client/client_rpc.py
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

import code
import collections
import functools
import logging
import os
import ssl
import sys

from king_phisher import errors
from king_phisher import find
from king_phisher import geoip
from king_phisher import serializers
from king_phisher import utilities

import advancedhttpserver
import boltons.typeutils
import smoke_zephyr.utilities
from gi.repository import Gtk

_tag_mixin_slots = ('id', 'name', 'description')
_tag_mixin_types = (int, str, str)
_tag_tables = ('campaigns', 'companies', 'company_departments', 'industries')
database_table_objects = utilities.FreezableDict()
UNRESOLVED = boltons.typeutils.make_sentinel('UNRESOLVED', var_name='UNRESOLVED')
"""A sentinel value used for values in rows to indicate that the data has not been loaded from the server."""

class RemoteRowMeta(type):
	def __new__(mcs, name, bases, dct):
		dct['__slots__'] = ('__rpc__',) + dct.get('__slots__', ())
		return super(RemoteRowMeta, mcs).__new__(mcs, name, bases, dct)

	def __init__(cls, *args, **kwargs):
		table_name = getattr(cls, '__table__', None)
		if table_name:
			database_table_objects[table_name] = cls
		super(RemoteRowMeta, cls).__init__(*args, **kwargs)

# stylized metaclass definition to be Python 2.7 and 3.x compatible
class RemoteRow(RemoteRowMeta('_RemoteRow', (object,), {})):
	"""
	A generic class representing a row of data from the remote King Phisher
	server.
	"""
	__table__ = None
	__xref_attr__ = None
	__slots__ = ()
	def __init__(self, rpc, *args, **kwargs):
		if not isinstance(rpc, KingPhisherRPCClient):
			raise ValueError('rpc is not a KingPhisherRPCClient instance')
		self.__rpc__ = rpc
		slots = self.__slots__[1:]
		values = collections.defaultdict(lambda: UNRESOLVED)
		if args:
			values.update(dict(zip(slots, args)))
		if kwargs:
			values.update(kwargs)
		for key in slots:
			value = values[key]
			if isinstance(value, bytes):
				value = value.decode('utf-8')
			setattr(self, key, value)

	def __getattr__(self, item):
		if hasattr(self, item + '_id'):
			row_id = getattr(self, item + '_id', None)
			for table, table_cls in database_table_objects.items():
				if table_cls.__xref_attr__ == item:
					return self.__rpc__.remote_table_row(table, row_id)
		raise AttributeError("object has no attribute '{0}'".format(item))

	def _asdict(self):
		return dict(zip(self.__slots__[1:], (getattr(self, prop) for prop in self.__slots__[1:])))

	def commit(self):
		"""Send this object to the server to update the remote instance."""
		values = tuple(getattr(self, attr) for attr in self.__slots__[1:])
		values = collections.OrderedDict(((k, v) for (k, v) in zip(self.__slots__[1:], values) if v is not UNRESOLVED))
		self.__rpc__('db/table/set', self.__table__, self.id, tuple(values.keys()), tuple(values.values()))

class AlertSubscription(RemoteRow):
	__table__ = 'alert_subscriptions'
	__slots__ = ('id', 'user_id', 'campaign_id', 'type', 'mute_timestamp')

class Campaign(RemoteRow):
	__table__ = 'campaigns'
	__xref_attr__ = 'campaign'
	__slots__ = ('id', 'name', 'description', 'user_id', 'created', 'reject_after_credentials', 'expiration', 'campaign_type_id', 'company_id')

class CampaignType(RemoteRow):
	__table__ = 'campaign_types'
	__xref_attr__ = 'campaign_type'
	__slots__ = _tag_mixin_slots

class Company(RemoteRow):
	__table__ = 'companies'
	__xref_attr__ = 'company'
	__slots__ = ('id', 'name', 'description', 'industry_id', 'url_main', 'url_email', 'url_remote_access')

class CompanyDepartment(RemoteRow):
	__table__ = 'company_departments'
	__xref_attr__ = 'company_department'
	__slots__ = _tag_mixin_slots

class Credential(RemoteRow):
	__table__ = 'credentials'
	__slots__ = ('id', 'visit_id', 'message_id', 'campaign_id', 'username', 'password', 'submitted')

class DeaddropConnection(RemoteRow):
	__table__ = 'deaddrop_connections'
	__slots__ = ('id', 'deployment_id', 'campaign_id', 'visit_count', 'visitor_ip', 'local_username', 'local_hostname', 'local_ip_addresses', 'first_visit', 'last_visit')

class DeaddropDeployment(RemoteRow):
	__table__ = 'deaddrop_deployments'
	__xref_attr__ = 'deployment'
	__slots__ = ('id', 'campaign_id', 'destination')

class Industry(RemoteRow):
	__table__ = 'industries'
	__xref_attr__ = 'industry'
	__slots__ = _tag_mixin_slots

class LandingPage(RemoteRow):
	__table__ = 'landing_pages'
	__slots__ = ('id', 'campaign_id', 'hostname', 'page')

class Message(RemoteRow):
	__table__ = 'messages'
	__xref_attr__ = 'message'
	__slots__ = ('id', 'campaign_id', 'target_email', 'first_name', 'last_name', 'opened', 'opener_ip', 'opener_user_agent', 'sent', 'trained', 'company_department_id')

class User(RemoteRow):
	__table__ = 'users'
	__xref_attr__ = 'user'
	__slots__ = ('id', 'phone_carrier', 'phone_number', 'email_address', 'otp_secret')

class Visit(RemoteRow):
	__table__ = 'visits'
	__xref_attr__ = 'visit'
	__slots__ = ('id', 'message_id', 'campaign_id', 'visit_count', 'visitor_ip', 'visitor_details', 'first_visit', 'last_visit')

database_table_objects.freeze()

class KingPhisherRPCClient(advancedhttpserver.RPCClientCached):
	"""
	The main RPC object for communicating with the King Phisher Server
	over RPC.
	"""
	def __init__(self, *args, **kwargs):
		self.logger = logging.getLogger('KingPhisher.Client.RPC')
		super(KingPhisherRPCClient, self).__init__(*args, **kwargs)
		self.set_serializer('binary/message-pack')

	def __repr__(self):
		return "<{0} '{1}@{2}:{3}{4}'>".format(self.__class__.__name__, self.username, self.host, self.port, self.uri_base)

	def graphql(self, query, query_vars=None):
		"""
		Execute a GraphQL query on the server and return the results. This will
		raise :py:exc:`~king_phisher.errors.KingPhisherGraphQLQueryError` if
		the query fails.

		:param str query: The GraphQL query string to execute.
		:param query_vars: The variables for *query*.
		:return: The query results.
		:rtype: dict
		"""
		response = self.call('graphql', query, query_vars=query_vars)
		if response['errors']:
			raise errors.KingPhisherGraphQLQueryError(
				'the query failed',
				errors=response['errors'],
				query=query,
				query_vars=query_vars
			)
		return response['data']

	def graphql_file(self, file_or_path, query_vars=None):
		"""
		This method wraps :py:meth:`~.graphql` to provide a convenient way to
		execute GraphQL queries from files.

		:param file_or_path: The file object or path to the file from which to read.
		:param query_vars: The variables for *query*.
		:return: The query results.
		:rtype: dict
		"""
		if isinstance(file_or_path, str):
			with open(file_or_path, 'r') as file_h:
				query = file_h.read()
		else:
			query = file_or_path.read()
		return self.graphql(query, query_vars=query_vars)

	def reconnect(self):
		"""Reconnect to the remote server."""
		self.lock.acquire()
		if self.use_ssl:
			if (sys.version_info[0] == 2 and sys.version_info >= (2, 7, 9)) or sys.version_info >= (3, 4, 3):
				context = ssl.create_default_context()
				context.check_hostname = False
				context.verify_mode = ssl.CERT_NONE
				self.client = advancedhttpserver.http.client.HTTPSConnection(self.host, self.port, context=context)
			else:
				self.client = advancedhttpserver.http.client.HTTPSConnection(self.host, self.port)
		else:
			self.client = advancedhttpserver.http.client.HTTPConnection(self.host, self.port)
		self.lock.release()

	def remote_row_resolve(self, row):
		"""
		Take a :py:class:`~.RemoteRow` instance and load all fields which are
		:py:data:`~.UNRESOLVED`. If all fields are present, no modifications
		are made.

		:param row: The row who's data is to be resolved.
		:rtype: :py:class:`~.RemoteRow`
		:return: The row with all of it's fields fully resolved.
		:rtype: :py:class:`~.RemoteRow`
		"""
		utilities.assert_arg_type(row, RemoteRow)
		slots = getattr(row, '__slots__')[1:]
		if not any(prop for prop in slots if getattr(row, prop) is UNRESOLVED):
			return row
		for key, value in self.call('db/table/get', getattr(row, '__table__'), row.id).items():
			setattr(row, key, value)
		return row

	def remote_table(self, table, query_filter=None):
		"""
		Iterate over a remote database table hosted on the server. Rows are
		yielded as named tuples whose fields are the columns of the specified
		table.

		:param str table: The table name to retrieve.
		:return: A generator which yields rows of named tuples.
		:rtype: tuple
		"""
		page = 0
		results = self.call('db/table/view', table, page, query_filter=query_filter)
		if results is None:
			return
		results_length = len(results['rows'])
		row_cls = database_table_objects[table]
		while results:
			for row in results['rows']:
				yield row_cls(self, *row)
			page += 1
			if 'page_size' in results and 'total_rows' in results:
				if results['page_size'] * page >= results['total_rows']:
					break
			if len(results['rows']) < results_length:
				break
			results = self.call('db/table/view', table, page, query_filter=query_filter)

	def remote_table_row(self, table, row_id, cache=False, refresh=False):
		"""
		Get a row from the specified table by it's id, optionally caching it.

		:param str table: The table in which the row exists.
		:param row_id: The value of the row's id column.
		:param bool cache: Whether to use the cache for this row.
		:param bool refresh: If *cache* is True, get the current row value and store it.
		:return: The remote row as a named tuple of the specified table.
		:rtype: tuple
		"""
		if cache and refresh:
			row = self.cache_call_refresh('db/table/get', table, row_id)
		elif cache and not refresh:
			row = self.cache_call('db/table/get', table, row_id)
		else:
			row = self.call('db/table/get', table, row_id)
		if row is None:
			return None
		row_cls = database_table_objects[table]
		return row_cls(self, **row)

	def remote_table_row_set(self, table, row_id, attributes):
		keys, values = zip(*attributes.items())
		return self.call('db/table/set', table, row_id, keys, values)

	def geoip_lookup(self, ip):
		"""
		Look up the geographic location information for the specified IP
		address in the server's geoip database.

		:param ip: The IP address to lookup.
		:type ip: :py:class:`ipaddress.IPv4Address`, str
		:return: The geographic location information for the specified IP address.
		:rtype: :py:class:`~king_phisher.geoip.GeoLocation`
		"""
		result = self.cache_call('geoip/lookup', str(ip))
		if result:
			result = geoip.GeoLocation(ip, result=result)
		return result

	def geoip_lookup_multi(self, ips):
		"""
		Look up the geographic location information for the specified IP
		addresses in the server's geoip database. Because results are cached
		for optimal performance, IP addresses to be queried should be grouped
		and sorted in a way that is unlikely to change, i.e. by a timestamp.

		:param ips: The IP addresses to lookup.
		:type ips: list, set, tuple
		:return: The geographic location information for the specified IP address.
		:rtype: dict
		"""
		ips = [str(ip) for ip in ips]
		results = self.cache_call('geoip/lookup/multi', ips)
		for ip, data in results.items():
			results[ip] = geoip.GeoLocation(ip, result=data)
		return results

	def get_tag_model(self, tag_table, model=None):
		"""
		Load tag information from a remote table into a
		:py:class:`Gtk.ListStore` instance. Tables compatible with the tag
		interface must have id, name and description fields. If no *model* is
		provided a new one will be created, else the current model will be
		cleared.

		:param str tag_table: The name of the table to load tag information from.
		:param model: The model to place the information into.
		:type model: :py:class:`Gtk.ListStore`
		:return: The model with the loaded data from the server.
		:rtype: :py:class:`Gtk.ListStore`
		"""
		if tag_table not in _tag_tables:
			raise ValueError('tag_table is not a valid tag interface exposing table')
		tag_table = smoke_zephyr.utilities.parse_case_snake_to_camel(tag_table, upper_first=False)
		if model is None:
			model = Gtk.ListStore(str, str, str)
			# sort by the name column, ascending
			model.set_sort_column_id(1, Gtk.SortType.ASCENDING)
		else:
			model.clear()
		graphql_query = 'query getTags { db { ' + tag_table + ' { edges { node { id name description } } } } }'
		tags = self.graphql(graphql_query)['db'][tag_table]['edges']
		for tag in tags:
			tag = tag['node']
			model.append((tag['id'], tag['name'], tag['description']))
		return model

	def login(self, username, password, otp=None):
		"""
		Authenticate to the remote server. This is required before calling RPC
		methods which require an authenticated session.

		:param str username: The username to authenticate with.
		:param str password: The password to authenticate with.
		:param str otp: An optional one time password as a 6 digit string to provide if the account requires it.
		:return: The login result and an accompanying reason.
		:rtype: tuple
		"""
		login_result, login_reason, login_session = self.call('login', username, password, otp)
		if login_result:
			if self.headers is None:
				self.headers = {}
			self.headers['X-RPC-Auth'] = login_session
		return login_result, login_reason

	def ping(self):
		"""
		Call the ping RPC method on the remote server to ensure that it is
		responsive. On success this method will always return True, otherwise
		an exception will be thrown.

		:return: True
		:rtype: bool
		"""
		return self.call('ping')

def _magic_graphql(rpc, mode, line):
	if mode == 'file':
		line = os.path.expandvars(line)
		line = os.path.expanduser(line)
		if not os.access(line, os.R_OK):
			print('GraphQL Exception: invalid query file')
			return
		with open(line, 'r') as file_h:
			query = file_h.read()
	elif mode == 'query':
		query = line
	else:
		raise RuntimeError('unsupported magic mode: ' + mode)

	try:
		result = rpc.graphql(query)
	except errors.KingPhisherGraphQLQueryError as error:
		print('GraphQL Exception: ' + error.message)
		for message in error.errors:
			print(message.rstrip())
		return
	return result

def vte_child_routine(config):
	"""
	This is the method which is executed within the child process spawned
	by VTE. It expects additional values to be set in the *config*
	object so it can initialize a new :py:class:`.KingPhisherRPCClient`
	instance. It will then drop into an interpreter where the user may directly
	interact with the rpc object.

	:param str config: A JSON encoded client configuration.
	"""
	config = serializers.JSON.loads(config)
	try:
		import readline
		import rlcompleter  # pylint: disable=unused-variable
	except ImportError:
		has_readline = False
	else:
		has_readline = True

	try:
		import IPython.terminal.embed
	except ImportError:
		has_ipython = False
	else:
		has_ipython = True

	for plugins_directory in ('rpc_plugins', 'rpc-plugins'):
		plugins_directory = find.data_directory(plugins_directory)
		if not plugins_directory:
			continue
		sys.path.append(plugins_directory)

	headers = config['rpc_data'].pop('headers')
	rpc = KingPhisherRPCClient(**config['rpc_data'])
	if rpc.headers is None:
		rpc.headers = {}
	for name, value in headers.items():
		rpc.headers[str(name)] = str(value)
	user_data_path = config['user_data_path']

	print("Python {0} on {1}".format(sys.version, sys.platform))  # pylint: disable=superfluous-parens
	print("Campaign Name: '{0}' ID: {1}".format(config['campaign_name'], config['campaign_id']))  # pylint: disable=superfluous-parens
	print('The \'rpc\' object holds the connected KingPhisherRPCClient instance')
	console_vars = {
		'CAMPAIGN_NAME': config['campaign_name'],
		'CAMPAIGN_ID': config['campaign_id'],
		'os': os,
		'rpc': rpc,
		'sys': sys
	}

	if has_ipython:
		console = IPython.terminal.embed.InteractiveShellEmbed(ipython_dir=os.path.join(user_data_path, 'ipython'))
		console.register_magic_function(functools.partial(_magic_graphql, rpc, 'query'), 'line', 'graphql')
		console.register_magic_function(functools.partial(_magic_graphql, rpc, 'file'), 'line', 'graphql_file')
		console.mainloop(console_vars)
	else:
		if has_readline:
			readline.parse_and_bind('tab: complete')
		console = code.InteractiveConsole(console_vars)
		for var in tuple(console_vars.keys()):
			console.push("__builtins__['{0}'] = {0}".format(var))
		console.interact('')
	return
