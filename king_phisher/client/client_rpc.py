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
import logging
import os
import sys

from king_phisher import find
from king_phisher import geoip
from king_phisher import json_ex
from king_phisher import utilities
from king_phisher.third_party import AdvancedHTTPServer

try:
	import msgpack  # pylint: disable=unused-import
	has_msgpack = True
	"""Whether the :py:mod:`msgpack` module is available or not."""
except ImportError:
	has_msgpack = False

database_table_objects = utilities.FreezableDict()
_tag_mixin_fields = ('id', 'name', 'description')

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
	__table__ = None
	__xref_attr__ = None
	__slots__ = ()
	def __init__(self, rpc, *args, **kwargs):
		if not isinstance(rpc, KingPhisherRPCClient):
			raise ValueError('rpc is not a KingPhisherRPCClient instance')
		self.__rpc__ = rpc
		slots = self.__slots__[1:]
		if args:
			if not len(args) == len(slots):
				raise RuntimeError('all arguments must be specified')
			kwargs = dict(zip(self.__slots__[1:], args))
		elif kwargs:
			if not len(kwargs) == len(kwargs):
				raise RuntimeError('all key word arguments must be specified')
		else:
			raise RuntimeError('all arguments must be specified in either args or kwargs')
		for key, value in kwargs.items():
			setattr(self, key, value)

	def __getattr__(self, item):
		if hasattr(self, item + '_id'):
			row_id = getattr(self, item + '_id', None)
			for table, table_cls in database_table_objects.items():
				if table_cls.__xref_attr__ == item:
					return self.__rpc__.remote_table_row(table, row_id, cache=True)
		raise AttributeError("object has no attribute '{0}'".format(item))

	def _asdict(self):
		return dict(zip(self.__slots__[1:], (getattr(self, prop) for prop in self.__slots__[1:])))

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
	__slots__ = _tag_mixin_fields

class Company(RemoteRow):
	__table__ = 'companies'
	__xref_attr__ = 'company'
	__slots__ = ('id', 'name', 'description', 'industry_id', 'url_main', 'url_email', 'url_remote_access')

class CompanyDepartment(RemoteRow):
	__table__ = 'company_departments'
	__xref_attr__ = 'company_department'
	__slots__ = _tag_mixin_fields

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
	__slots__ = _tag_mixin_fields

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

class KingPhisherRPCClient(AdvancedHTTPServer.AdvancedHTTPServerRPCClientCached):
	"""
	The main RPC object for communicating with the King Phisher Server
	over RPC.
	"""
	def __init__(self, *args, **kwargs):
		self.logger = logging.getLogger('KingPhisher.Client.RPC')
		super(KingPhisherRPCClient, self).__init__(*args, **kwargs)
		if has_msgpack:
			serializer = 'binary/message-pack'
		else:
			serializer = 'binary/json'
		self.set_serializer(serializer)

	def __repr__(self):
		return "<{0} '{1}@{2}:{3}{4}'>".format(self.__class__.__name__, self.username, self.host, self.port, self.uri_base)

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

	def login(self, username, password, otp=None):
		login_result, login_reason, login_session = self.call('login', username, password, otp)
		if login_result:
			if self.headers is None:
				self.headers = {}
			self.headers['X-RPC-Auth'] = login_session
		return login_result, login_reason

def vte_child_routine(config):
	"""
	This is the method which is executed within the child process spawned
	by VTE. It expects additional values to be set in the *config*
	object so it can initialize a new :py:class:`.KingPhisherRPCClient`
	instance. It will then drop into an interpreter where the user may directly
	interact with the rpc object.

	:param str config: A JSON encoded client configuration.
	"""
	config = json_ex.loads(config)
	try:
		import readline
		import rlcompleter  # pylint: disable=unused-variable
	except ImportError:
		pass
	else:
		readline.parse_and_bind('tab: complete')
	for plugins_directory in ('rpc_plugins', 'rpc-plugins'):
		plugins_directory = find.find_data_directory(plugins_directory)
		if not plugins_directory:
			continue
		sys.path.append(plugins_directory)

	headers = config['rpc_data'].pop('headers')
	rpc = KingPhisherRPCClient(**config['rpc_data'])
	if rpc.headers is None:
		rpc.headers = {}
	for name, value in headers.items():
		rpc.headers[str(name)] = str(value)

	banner = "Python {0} on {1}".format(sys.version, sys.platform)
	print(banner)  # pylint: disable=superfluous-parens
	information = "Campaign Name: '{0}' ID: {1}".format(config['campaign_name'], config['campaign_id'])
	print(information)  # pylint: disable=superfluous-parens
	console_vars = {
		'CAMPAIGN_NAME': config['campaign_name'],
		'CAMPAIGN_ID': config['campaign_id'],
		'os': os,
		'rpc': rpc,
		'sys': sys
	}
	export_to_builtins = ['CAMPAIGN_NAME', 'CAMPAIGN_ID', 'rpc']
	console = code.InteractiveConsole(console_vars)
	for var in export_to_builtins:
		console.push("__builtins__['{0}'] = {0}".format(var))
	console.interact('The \'rpc\' object holds the connected KingPhisherRPCClient instance')
	return
