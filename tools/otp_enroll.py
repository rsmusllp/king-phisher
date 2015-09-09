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

from king_phisher import color
from king_phisher import utilities
from king_phisher.server.database import manager
from king_phisher.server.database import models

import pyotp
import yaml

def main():
	parser = argparse.ArgumentParser(description='King Phisher TOTP Enrollment Utility', conflict_handler='resolve')
	utilities.argp_add_args(parser)
	config_group = parser.add_mutually_exclusive_group(required=True)
	config_group.add_argument('-c', '--config', dest='server_config', type=argparse.FileType('r'), help='the server configuration file')
	config_group.add_argument('-u', '--url', dest='database_url', help='the database connection url')
	parser.add_argument('--otp', dest='otp_secret', help='a specific otp secret')
	parser.add_argument('user', help='the user to mange')
	parser.add_argument('action', choices=('remove', 'set', 'show'), help='the action to preform')
	parser.epilog = 'If --otp is set then it must be a valid base32 encoded secret otherwise a random one will be used.'
	arguments = parser.parse_args()

	utilities.configure_stream_logger(arguments.loglvl, arguments.logger)

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
		color.print_error("invalid user id: {0}".format(arguments.user))
		return

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
	else:
		color.print_status("user: {0} otp: N/A".format(user.id))
	session.commit()

if __name__ == '__main__':
	sys.exit(main())
