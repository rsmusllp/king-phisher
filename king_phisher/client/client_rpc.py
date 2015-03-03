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
import getpass
import json
import logging
import os
import sys

from king_phisher import find
from king_phisher import geoip
from king_phisher.third_party import AdvancedHTTPServer
try:
	import msgpack # pylint: disable=unused-import
	has_msgpack = True
	"""Whether the :py:mod:`msgpack` module is available or not."""
except ImportError:
	has_msgpack = False

AlertSubscription = collections.namedtuple('AlertSubscription', ('id', 'user_id', 'campaign_id'))
Campaign = collections.namedtuple('Campaign', ('id', 'name', 'user_id', 'created', 'reject_after_credentials'))
Credential = collections.namedtuple('Credential', ('id', 'visit_id', 'message_id', 'campaign_id', 'username', 'password', 'submitted'))
DeaddropConnection = collections.namedtuple('DeaddropConnection', ('id', 'deployment_id', 'campaign_id', 'visit_count', 'visitor_ip', 'local_username', 'local_hostname', 'local_ip_addresses', 'first_visit', 'last_visit'))
DeaddropDeployment = collections.namedtuple('DeaddropDeployment', ('id', 'campaign_id', 'destination'))
LandingPage = collections.namedtuple('LandingPage', ('id', 'campaign_id', 'hostname', 'page'))
Message = collections.namedtuple('Message', ('id', 'campaign_id', 'target_email', 'company_name', 'first_name', 'last_name', 'opened', 'sent', 'trained'))
MetaData = collections.namedtuple('MetaData', ('id', 'value_type', 'value'))
User = collections.namedtuple('User', ('id', 'phone_carrier', 'phone_number'))
Visit = collections.namedtuple('Visit', ('id', 'message_id', 'campaign_id', 'visit_count', 'visitor_ip', 'visitor_details', 'first_visit', 'last_visit'))

_table_row_classes = {
	'alert_subscriptions': AlertSubscription,
	'campaigns': Campaign,
	'credentials': Credential,
	'deaddrop_connections': DeaddropConnection,
	'deaddrop_deployments': DeaddropDeployment,
	'landing_pages': LandingPage,
	'messages': Message,
	'meta_data': MetaData,
	'users': User,
	'visits': Visit
}

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

	def remote_table(self, table, *args):
		"""
		Iterate over a remote database table hosted on the server. Rows are
		yielded as named tuples whose fields are the columns of the specified
		table.

		:param str table: The table name to retrieve.
		:return: A generator which yields rows of named tuples.
		:rtype: tuple
		"""
		table_method = table + '/view'
		table = table.rsplit('/', 1)[-1]
		page = 0
		args = list(args)
		args.append(page)
		results = self.call(table_method, *args)
		results_length = len(results or '')
		row_cls = _table_row_classes[table]
		while results:
			for row in results['rows']:
				yield row_cls(*row)
			if len(results) < results_length:
				break
			args[-1] += 1
			results = self.call(table_method, *args)

	def remote_table_row(self, table, row_id, cache=False, refresh=False):
		"""
		Get a row from the specified table by it's id, optionally cacheing it.

		:param str table: The table in which the row exists.
		:param row_id: The value of the row's id column.
		:param bool cache: Whether to use the cache for this row.
		:param bool refresh: If *cache* is True, get the current row value and store it.
		:return: The remote row as a named tuple of the specified table.
		:rtype: tuple
		"""
		table_method = table + '/get'
		if cache and refresh:
			row = self.cache_call_refresh(table_method, row_id)
		elif cache and not refresh:
			row = self.cache_call(table_method, row_id)
		else:
			row = self.call(table_method, row_id)
		row_cls = _table_row_classes[table]
		return row_cls(**row)

	def geoip_lookup(self, ip):
		"""
		Look up the geographic location information for the specified IP
		address in the server's geoip database.

		:param ip: The IP address to lookup.
		:return: The geographic location information for the specified IP address.
		:rtype: :py:class:`~king_phisher.geoip.GeoLocation`
		"""
		result = self.cache_call('geoip/lookup', ip)
		return geoip.GeoLocation(ip, result=result)

def vte_child_routine(config):
	"""
	This is the method which is executed within the child process spawned
	by VTE. It expects additional values to be set in the *config*
	object so it can initialize a new :py:class:`.KingPhisherRPCClient`
	instance. It will then drop into an interpreter where the user may directly
	interact with the rpc object.

	:param str config: A JSON encoded client configuration.
	"""
	config = json.loads(config)
	try:
		import readline
		import rlcompleter # pylint: disable=unused-variable
	except ImportError:
		pass
	else:
		readline.parse_and_bind('tab: complete')
	plugins_directory = find.find_data_directory('plugins')
	if plugins_directory:
		sys.path.append(plugins_directory)

	rpc = KingPhisherRPCClient(**config['rpc_data'])
	logged_in = False
	for _ in range(0, 3):
		rpc.password = getpass.getpass("{0}@{1}'s password: ".format(rpc.username, rpc.host))
		try:
			logged_in = rpc('ping')
		except AdvancedHTTPServer.AdvancedHTTPServerRPCError:
			print('Permission denied, please try again.') # pylint: disable=C0325
			continue
		else:
			break
	if not logged_in:
		return

	banner = "Python {0} on {1}".format(sys.version, sys.platform)
	print(banner) # pylint: disable=C0325
	information = "Campaign Name: '{0}'  ID: {1}".format(config['campaign_name'], config['campaign_id'])
	print(information) # pylint: disable=C0325
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
