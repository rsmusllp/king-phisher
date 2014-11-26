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

import logging

from king_phisher.third_party.AdvancedHTTPServer import AdvancedHTTPServerRPCError, AdvancedHTTPServerRPCClientCached

try:
	import msgpack
	has_msgpack = True
	"""Whether the :py:mod:`msgpack` module is available or not."""
except ImportError:
	has_msgpack = False

class KingPhisherRPCClient(AdvancedHTTPServerRPCClientCached):
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
		Get a remote table from the server by calling the correct RPC
		method.

		:param str table: The table name to retrieve.
		:return: A generator which yields rows in dictionaries.
		"""
		table_method = table + '/view'
		page = 0
		args = list(args)
		args.append(page)
		results = self.call(table_method, *args)
		results_length = len(results or '')
		while results:
			columns = results['columns']
			for row in results['rows']:
				yield dict(zip(columns, row))
			if len(results) < results_length:
				break
			args[-1] += 1
			results = self.call(table_method, *args)

	def remote_table_row(self, table, row_id, cache=False, refresh=False):
		"""
		Get a specific row by it's id, optionally cacheing it.

		:param str table: The table in which the row exists.
		:param row_id: The value of the row's id column.
		:param bool cache: Whether to use the cache for this row.
		:param bool refresh: If *cache* is True, get the current row value and store it.
		:return: The remote row.
		"""
		table_method = table + '/get'
		if cache and refresh:
			result = self.cache_call_refresh(table_method, row_id)
		elif cache and not refresh:
			result = self.cache_call(table_method, row_id)
		else:
			result = self.call(table_method, row_id)
		return result
