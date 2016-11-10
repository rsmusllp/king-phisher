#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  tools/debug_smtp_server.py
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
# pylint: disable=superfluous-parens

import argparse
import logging
import os
import sys

sys.path.insert(1, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import king_phisher.color as color
import king_phisher.smtp_server as smtp_server
import king_phisher.utilities as utilities

def main():
	parser = argparse.ArgumentParser(description='King Phisher SMTP Debug Server', conflict_handler='resolve')
	utilities.argp_add_args(parser)
	parser.add_argument('-f', '--foreground', dest='foreground', action='store_true', default=False, help='run in foreground (do not fork)')
	parser.add_argument('-a', '--address', dest='address', default='127.0.0.1', help='address to listen on')
	parser.add_argument('-p', '--port', dest='port', type=int, default=2525, help='port to listen on')
	arguments = parser.parse_args()
	del parser

	utilities.configure_stream_logger(arguments.loglvl, arguments.logger)

	if (not arguments.foreground) and os.fork():
		return

	bind_address = (arguments.address, arguments.port)
	server = smtp_server.BaseSMTPServer(bind_address)
	color.print_status("smtp server listening on {0}:{1}".format(bind_address[0], bind_address[1]))
	try:
		server.serve_forever()
	except KeyboardInterrupt:
		color.print_status('keyboard interrupt caught, now exiting')

if __name__ == '__main__':
	main()
