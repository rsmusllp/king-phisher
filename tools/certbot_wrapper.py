#!/usr/bin/env python
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
import logging
import os
import socket
import subprocess
import sys

sys.path.insert(1, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import king_phisher.color as color
import king_phisher.utilities as utilities

import advancedhttpserver
import smoke_zephyr.utilities
import yaml

LETS_ENCRYPT_LIVE_PATH = '/etc/letsencrypt/live'
PARSER_EPILOG = """
This tool facilitates issuing certificates with the certbot utility while the
King Phisher server is running.
"""
PARSER_EPILOG = PARSER_EPILOG.replace('\n', ' ')
PARSER_EPILOG = PARSER_EPILOG.strip()

def main():
	parser = argparse.ArgumentParser(description='King Phisher Certbot Wrapper Utility', conflict_handler='resolve')
	utilities.argp_add_args(parser)
	parser.add_argument('--certbot', dest='certbot_bin', help='the path to the certbot binary to use')
	parser.add_argument('server_config', type=argparse.FileType('r'), help='the server configuration file')
	parser.add_argument('hostnames', nargs='+', help='the host names to request certificates for')
	parser.epilog = PARSER_EPILOG
	arguments = parser.parse_args()

	server_config = yaml.load(arguments.server_config)
	web_root = server_config['server']['web_root']

	if os.getuid():
		color.print_error('this tool must be ran as root')
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
	if server_config['server'].get('addresses'):
		address = server_config['server']['addresses'][0]
	else:
		address = server_config['server']['address']
		address['ssl'] = bool(server_config['server'].get('ssl_cert'))

	logger.debug("checking that the king phisher server is running on: {host}:{port} (ssl={ssl})".format(**address))
	try:
		rpc = advancedhttpserver.RPCClient((address['host'], address['port']), use_ssl=address['ssl'])
		version = rpc('version')
	except (advancedhttpserver.RPCError, socket.error):
		logger.error('received an rpc error while checking the version', exc_info=True)
		color.print_error('failed to verify that the king phisher server is running')
		return os.EX_UNAVAILABLE
	logger.info('connected to server version: ' + version['version'])

	vhost_directories = server_config['server']['vhost_directories']
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

		certbot_args = (certbot_bin, 'certonly', '--webroot', '-w', directory, '-d', hostname)
		logger.info('running certbot command: ' + ' '.join(certbot_args))
		proc_h = subprocess.Popen(certbot_args, shell=False)
		status = proc_h.wait()
		if status != os.EX_OK:
			color.print_error('certbot exited with exit status: ' + str(status))
			break
		color.print_good('certbot exited with successful status code')
		if not os.path.isdir(os.path.join(LETS_ENCRYPT_LIVE_PATH, hostname)):
			logger.warning('failed to find the new hostname in: ' + LETS_ENCRYPT_LIVE_PATH)
			continue
		color.print_status('copy the following lines into the server configuration file under')
		color.print_status('the \'ssl_hosts:\' section to use the certificates with king phisher')
		print("    - host: {0}".format(hostname))
		print("      ssl_cert: /etc/letsencrypt/live/{0}/fullchain.pem".format(hostname))
		print("      ssl_key: /etc/letsencrypt/live/{0}/privkey.pem".format(hostname))

if __name__ == '__main__':
	sys.exit(main())
