#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
#  tools/certbot_wrapper.py
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
import datetime
import logging
import os
import socket
import subprocess
import sys

sys.path.insert(1, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import king_phisher.color as color
import king_phisher.serializers as serializers
import king_phisher.utilities as utilities
import king_phisher.server.letsencrypt as letsencrypt
import king_phisher.server.configuration as configuration

import advancedhttpserver
import smoke_zephyr.utilities

LETS_ENCRYPT_LIVE_PATH = '/etc/letsencrypt/live'
PARSER_DESCRIPTION = """\
King Phisher Certbot Wrapper Utility

This tool facilitates issuing certificates with the certbot Let's Encrypt client
utility while the King Phisher server is running.
"""
PARSER_EPILOG = """\
Example usage (issuing a certificate for "test.king-phisher.com"):
  # standard configuration output
  sudo ./certbot_wrapper.py ../server_config.yml test.king-phisher.com
  
  # use json configuration output (for use with the config file's include
  # directive) and then restart the service
  sudo ./certbot_wrapper.py \\
    --json-output ../configs/ssl_hosts.json \\
    --restart-service \\
    ../server_config.yml test.king-phisher.com
"""

def main():
	parser = argparse.ArgumentParser(
		conflict_handler='resolve',
		description=PARSER_DESCRIPTION,
		epilog=PARSER_EPILOG,
		formatter_class=argparse.RawTextHelpFormatter
	)
	utilities.argp_add_args(parser)
	parser.add_argument('--certbot', dest='certbot_bin', help='the path to the certbot binary to use')
	parser.add_argument('--json-output', dest='json_file', help='update a json formatted file with the details')
	parser.add_argument('--restart-service', action='store_true', default=False, help='attempt to restart the king-phisher service')
	parser.add_argument('server_config', help='the server configuration file')
	parser.add_argument('hostnames', nargs='+', help='the host names to request certificates for')
	parser.epilog = PARSER_EPILOG
	arguments = parser.parse_args()

	server_config = configuration.ex_load_config(arguments.server_config).get('server')
	web_root = server_config['web_root']

	if os.getuid():
		color.print_error('this tool must be run as root')
		return os.EX_NOPERM

	certbot_bin = arguments.certbot_bin or smoke_zephyr.utilities.which('certbot')
	if certbot_bin is None:
		color.print_error('could not identify the path to the certbot binary, make sure that it is')
		color.print_error('installed and see: https://certbot.eff.org/ for more details')
		return os.EX_UNAVAILABLE
	if not os.access(certbot_bin, os.R_OK | os.X_OK):
		color.print_error('found insufficient permissions on the certbot binary')
		return os.EX_NOPERM

	logger = logging.getLogger('KingPhisher.Tool.CLI.CertbotWrapper')
	logger.info('using certbot binary at: ' + certbot_bin)

	logger.debug('getting server binding information')
	if server_config.get('addresses'):
		address = server_config['addresses'][0]
	else:
		address = server_config['address']
		address['ssl'] = bool(server_config.get('ssl_cert'))

	logger.debug("checking that the king phisher server is running on: {host}:{port} (ssl={ssl})".format(**address))
	try:
		rpc = advancedhttpserver.RPCClient((address['host'], address['port']), use_ssl=address['ssl'])
		version = rpc('version')
	except (advancedhttpserver.RPCError, socket.error):
		logger.error('received an rpc error while checking the version', exc_info=True)
		color.print_error('failed to verify that the king phisher server is running')
		return os.EX_UNAVAILABLE
	logger.info('connected to server version: ' + version['version'])

	vhost_directories = server_config['vhost_directories']
	if len(arguments.hostnames) > 1 and not vhost_directories:
		color.print_error('vhost_directories must be true to specify multiple hostnames')
		return os.EX_CONFIG

	for hostname in arguments.hostnames:
		if vhost_directories:
			directory = os.path.join(web_root, hostname)
		else:
			directory = web_root
			if os.path.split(os.path.abspath(directory))[-1] != hostname:
				color.print_error('when the vhost_directories option is not set, the web_root option')
				color.print_error('must be: ' + os.path.join(web_root, hostname))
				return os.EX_CONFIG
		if not os.path.exists(directory):
			os.mkdir(directory, mode=0o775)
			logger.info('created directory for host at: ' + directory)

		status = letsencrypt.certbot_issue(directory, hostname, bin_path=certbot_bin)
		if status:
			color.print_error('certbot exited with exit status: ' + str(status))
			break
		color.print_good('certbot exited with a successful status code')
		timestamp = datetime.datetime.utcnow().isoformat() + '+00:00'
		if not os.path.isdir(os.path.join(LETS_ENCRYPT_LIVE_PATH, hostname)):
			logger.warning('failed to find the new hostname in: ' + LETS_ENCRYPT_LIVE_PATH)
			continue

		details = {
			'created': timestamp,
			'host': hostname,
			'ssl_cert': os.path.join(LETS_ENCRYPT_LIVE_PATH, hostname, 'fullchain.pem'),
			'ssl_key': os.path.join(LETS_ENCRYPT_LIVE_PATH, hostname, 'privkey.pem')
		}

		if arguments.json_file:
			existing_data = []
			if os.path.isfile(arguments.json_file):
				with open(arguments.json_file, 'r') as file_h:
					existing_data = serializers.JSON.load(file_h)
				if not isinstance(existing_data, list):
					color.print_status('the existing json data must be a list to add the new data')
			existing_data.append(details)
			with open(arguments.json_file, 'w') as file_h:
				serializers.JSON.dump(existing_data, file_h)
		else:
			color.print_status('copy the following lines into the server configuration file under')
			color.print_status('the \'ssl_hosts:\' section to use the certificates with king phisher')
			print('    # created: ' + details['created'])
			print('    - host: ' + details['host'])
			print('      ssl_cert: ' + details['ssl_cert'])
			print('      ssl_key: ' + details['ssl_key'])

	if arguments.hostnames and arguments.json_file and arguments.restart_service:
		systemctl_bin = smoke_zephyr.utilities.which('systemctl')
		if systemctl_bin is None:
			color.print_error('could not restart the king-phisher service (could not find systemctl)')
			return os.EX_OK
		proc_h = subprocess.Popen([systemctl_bin, 'restart', 'king-phisher'], shell=False)
		if proc_h.wait() != 0:
			color.print_error('failed to restart the king-phisher service via systemctl')
			return os.EX_SOFTWARE
		color.print_status('restarted the king-phisher service via systemctl')
	return os.EX_OK

if __name__ == '__main__':
	sys.exit(main())
