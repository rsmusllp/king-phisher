#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  king_phisher/client/rpcclient.py
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
#  * Neither the name of the  nor the names of its
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

from AdvancedHTTPServer import AdvancedHTTPServerRPCError, AdvancedHTTPServerRPCClientCached

class KingPhisherRPCClient(AdvancedHTTPServerRPCClientCached):
	def __init__(self, *args, **kwargs):
		super(KingPhisherRPCClient, self).__init__(*args, **kwargs)
		self.set_serializer('binary/json+zlib')

	def remote_table(self, table, *args):
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

	def remote_row(self, table, row_id):
		table_method = table + '/get'
		return self.call(table_method, row_id)
