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

try:
	import msgpack
	has_msgpack = True
except ImportError:
	has_msgpack = False

class KingPhisherRPCClient(AdvancedHTTPServerRPCClientCached):
	def __init__(self, *args, **kwargs):
		super(KingPhisherRPCClient, self).__init__(*args, **kwargs)
		if has_msgpack:
			serializer = 'binary/message-pack'
		else:
			serializer = 'binary/json'
		self.set_serializer(serializer)

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

	def remote_table_row(self, table, row_id, cache = False, refresh = False):
		table_method = table + '/get'
		if cache and refresh:
			result = self.cache_call_refresh(table_method, row_id)
		elif cache and not refresh:
			result = self.cache_call(table_method, row_id)
		else:
			result = self.call(table_method, row_id)
		return result

def main():
	import argparse
	import code
	import getpass
	import logging

	import utilities

	try:
		import readline
	except ImportError:
		print('[-] Module readline not available.')
	else:
		import rlcompleter
		readline.parse_and_bind('tab: complete')

	parser = argparse.ArgumentParser(description = 'King Phisher RPC Client', conflict_handler = 'resolve')
	parser.add_argument('-u', '--username', dest = 'username', help = 'user to authenticate as')
	parser.add_argument('-p', '--password', dest = 'password', help = argparse.SUPPRESS)
	parser.add_argument('server', action = 'store', help = 'server to connect to')
	parser.add_argument('-L', '--log', dest = 'loglvl', action = 'store', choices = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'], default = 'CRITICAL', help = 'set the logging level')
	arguments = parser.parse_args()

	logging.getLogger('').setLevel(logging.DEBUG)
	console_log_handler = logging.StreamHandler()
	console_log_handler.setLevel(getattr(logging, arguments.loglvl))
	console_log_handler.setFormatter(logging.Formatter("%(levelname)-8s %(message)s"))
	logging.getLogger('').addHandler(console_log_handler)
	server = utilities.server_parse(arguments.server, 80)
	username = (arguments.username or getpass.getuser())
	if arguments.password:
		password = arguments.password
	else:
		password = getpass.getpass("Password For {0}@{1}: ".format(username, server[0]))
	del arguments, parser
	rpc = KingPhisherRPCClient(server, username = username, password = password)
	console = code.InteractiveConsole({'rpc':rpc, 'server':server})
	console.interact('The \'rpc\' object holds the connected KingPhisherRPCClient instance')
	return

if __name__ == '__main__':
	main()
