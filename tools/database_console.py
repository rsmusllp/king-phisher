#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  tools/database_console.py
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

import argparse
import code
import os
import pprint
import sys

sys.path.insert(1, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import king_phisher.constants as constants
import king_phisher.utilities as utilities
import king_phisher.server.database.manager as manager
import king_phisher.server.database.models as models

import yaml

history_file = os.path.expanduser('~/.config/king-phisher/database_console.his')

try:
	import readline
except ImportError:
	has_readline = False
else:
	has_readline = True
	import rlcompleter
	readline.parse_and_bind('tab: complete')
	if os.path.isfile(history_file):
		readline.read_history_file(history_file)

def main():
	parser = argparse.ArgumentParser(description='King Phisher Interactive Database Console', conflict_handler='resolve')
	utilities.argp_add_args(parser)
	config_group = parser.add_mutually_exclusive_group(required=True)
	config_group.add_argument('-c', '--config', dest='server_config', type=argparse.FileType('r'), help='the server configuration file')
	config_group.add_argument('-u', '--url', dest='database_url', help='the database connection url')
	arguments = parser.parse_args()

	utilities.configure_stream_logger(arguments.loglvl, arguments.logger)

	if arguments.database_url:
		database_connection_url = arguments.database_url
	elif arguments.server_config:
		server_config = yaml.load(arguments.server_config)
		database_connection_url = server_config['server']['database']
	else:
		raise RuntimeError('no database connection was specified')

	engine = manager.init_database(database_connection_url)
	session = manager.Session()
	console = code.InteractiveConsole(dict(
		engine=engine,
		manager=manager,
		models=models,
		pprint=pprint.pprint,
		session=session
	))
	console.interact('starting interactive database console')

	if os.path.isdir(os.path.dirname(history_file)):
		readline.write_history_file(history_file)

if __name__ == '__main__':
	sys.exit(main())
