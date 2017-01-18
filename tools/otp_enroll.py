#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  tools/otp_enroll.py
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
import os
import sys

sys.path.insert(1, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import king_phisher.color as color
import king_phisher.utilities as utilities
import king_phisher.server.database.manager as manager
import king_phisher.server.database.models as models

import pyotp
import yaml

try:
	import qrcode
except ImportError:
	has_qrcode = False
else:
	has_qrcode = True

PARSER_EPILOG = """
If --otp is set then it must be a valid base32 encoded secret otherwise a random
one will be used. Also note that unless the --force flag is specified, the user
that is selected to be managed must already exist within the database, i.e. they
should have logged in at least once before.
"""
PARSER_EPILOG = PARSER_EPILOG.replace('\n', ' ')
PARSER_EPILOG = PARSER_EPILOG.strip()

def main():
	parser = argparse.ArgumentParser(description='King Phisher TOTP Enrollment Utility', conflict_handler='resolve')
	utilities.argp_add_args(parser)
	config_group = parser.add_mutually_exclusive_group(required=True)
	config_group.add_argument('-c', '--config', dest='server_config', type=argparse.FileType('r'), help='the server configuration file')
	config_group.add_argument('-u', '--url', dest='database_url', help='the database connection url')
	parser.add_argument('--force', dest='force', action='store_true', default=False, help='create the user if necessary')
	parser.add_argument('--otp', dest='otp_secret', help='a specific otp secret')
	if has_qrcode:
		parser.add_argument('--qrcode', dest='qrcode_filename', help='generate a qrcode image file')
	parser.add_argument('user', help='the user to mange')
	parser.add_argument('action', choices=('remove', 'set', 'show'), help='the action to preform')
	parser.epilog = PARSER_EPILOG
	arguments = parser.parse_args()

	utilities.configure_stream_logger(arguments.logger, arguments.loglvl)

	if arguments.database_url:
		database_connection_url = arguments.database_url
	elif arguments.server_config:
		server_config = yaml.load(arguments.server_config)
		database_connection_url = server_config['server']['database']
	else:
		raise RuntimeError('no database connection was specified')

	manager.init_database(database_connection_url)
	session = manager.Session()
	user = session.query(models.User).filter_by(id=arguments.user).first()
	if not user:
		if not arguments.force:
			color.print_error("invalid user id: {0}".format(arguments.user))
			return
		user = models.User(id=arguments.user)
		session.add(user)
		color.print_status('the specified user was created')

	for case in utilities.switch(arguments.action):
		if case('remove'):
			user.otp_secret = None
			break
		if case('set'):
			if user.otp_secret:
				color.print_error("the specified user already has an otp secret set")
				return
			if arguments.otp_secret:
				new_otp = arguments.otp_secret
			else:
				new_otp = pyotp.random_base32()
			if len(new_otp) != 16:
				color.print_error("invalid otp secret length, must be 16")
				return
			user.otp_secret = new_otp
			break

	if user.otp_secret:
		color.print_status("user: {0} otp: {1}".format(user.id, user.otp_secret))
		totp = pyotp.TOTP(user.otp_secret)
		uri = totp.provisioning_uri(user.id + '@king-phisher') + '&issuer=King%20Phisher'
		color.print_status("provisioning uri: {0}".format(uri))
		if has_qrcode and arguments.qrcode_filename:
			img = qrcode.make(uri)
			img.save(arguments.qrcode_filename)
			color.print_status("wrote qrcode image to: " + arguments.qrcode_filename)
	else:
		color.print_status("user: {0} otp: N/A".format(user.id))
	session.commit()

if __name__ == '__main__':
	sys.exit(main())
