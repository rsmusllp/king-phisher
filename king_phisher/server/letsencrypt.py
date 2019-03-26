#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  king_phisher/letsencrypt.py
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
import os
import re

from king_phisher import startup
from king_phisher.server.database import storage as db_storage

logger = logging.getLogger('KingPhisher.LetsEncrypt')

LETS_ENCRYPT_DEFAULT_DATA_PATH = '/etc/letsencrypt'
"""The default path at which Let's Encrypt data is stored."""

_HOSTNAME_DIRECTORY_REGEX = re.compile(r'^(?P<hostname>[a-z0-9][a-z0-9-]*(\.[a-z0-9-]+)*\.[a-z]+)(-(?P<index>\d+))?$', re.IGNORECASE)

sni_hostnames = db_storage.KeyValueStorage(namespace='server.ssl.sni.hostnames')

def _check_files(*file_paths):
	return all(os.path.isfile(file_path) and os.access(file_path, os.R_OK) for file_path in file_paths)

def _get_files(directory, hostname):
	if os.path.isdir(os.path.join(directory, hostname)):
		directory = os.path.join(directory, hostname)
	else:
		# certbot will append digits to the end of a directory to avoid naming conflicts, so find the highest index
		index_str = None
		for subdirectory in os.listdir(directory):
			match = _HOSTNAME_DIRECTORY_REGEX.match(subdirectory)
			if match is None or match.group('hostname') != hostname or not match.group('index'):
				continue
			if index_str is None or int(match.group('index')) > int(index_str):
				index_str = match.group('index')
		if index_str is None:
			return None, None
		directory = os.path.join(directory, hostname + '-' + index_str)

	cert_path = os.path.join(directory, 'fullchain.pem')
	if not _check_files(cert_path):
		cert_path = None
	key_path = os.path.join(directory, 'privkey.pem')
	if not _check_files(key_path):
		key_path = None
	return cert_path, key_path

def _run_certbot(args, bin_path=None):
	bin_path = bin_path or startup.which('certbot')
	if bin_path is None:
		return RuntimeError('certbot could not be found')
	args = (bin_path,) + tuple(args)
	return startup.run_process(args)

def certbot_issue(webroot, hostname, bin_path=None, unified_directory=None):
	"""
	Issue a certificate using Let's Encrypt's ``certbot`` utility. This function
	wraps the ``certbot`` binary and configures the parameters as appropriate.
	By default, the resulting certificate will be placed under
	:py:data:`.LETS_ENCRYPT_DEFAULT_DATA_PATH`, however if *unified_directory*
	is used then it will be under ``$unified_directory/etc``.

	:param str webroot: The webroot to use while requesting the certificate.
	:param str hostname: The hostname of the certificate to request.
	:param str bin_path: The optional path to the ``certbot`` binary. If not
		specified, then it will be searched for utilizing
		:py:func:`~king_phisher.startup.which`.
	:param str unified_directory: A single directory under which all the Let's
		Encrypt data should be stored. This is useful when not running the
		utility as root.
	:return: The exit status of the ``certbot`` utility.
	:rtype: int
	"""
	args = ['certonly']
	if unified_directory:
		args.extend(['--config-dir', os.path.join(unified_directory, 'etc')])
		args.extend(['--logs-dir', os.path.join(unified_directory, 'log')])
		args.extend(['--work-dir', os.path.join(unified_directory, 'lib')])
	args.extend(['--webroot', '--webroot-path', webroot, '-d', hostname])
	proc = _run_certbot(args, bin_path=bin_path)
	return proc.status

def get_files(unified_directory, hostname):
	"""
	Given the *unified_directory*, find and return the certificate and key files
	for the specified *hostname*. The paths to the files will be returned if
	exist, are files and are readable. If either path fails to meet these
	conditions, ``None`` will be returned in it's place.

	:param str unified_directory: The path to the unified directory as used by the :py:func:`.certbot_issue`.
	:param str hostname: The hostname to retrieve files for.
	:return: A tuple containing the certfile and keyfile.
	:rtype: tuple
	"""
	unified_directory = os.path.abspath(unified_directory)
	directory = os.path.join(unified_directory, 'etc', 'live')
	if not os.path.isdir(directory):
		return None, None
	sni_config = sni_hostnames.get(hostname)
	if sni_config and _check_files(sni_config['certfile'], sni_config['keyfile']):
		return sni_config['certfile'], sni_config['keyfile']
	return _get_files(directory, hostname)

def get_sni_hostnames(unified_directory):
	"""
	Return a list of hostnames for which the necessary files are available for.
	This function first checks the the files configured in the database, then
	enumerates the *unified_directory* to add additional entries.

	:param str unified_directory: The path to the unified directory as used by the :py:func:`.certbot_issue`.
	:return: The hostnames that are available.
	:rtype: list
	"""
	directory = os.path.join(unified_directory, 'etc', 'live')
	if not os.path.isdir(directory):
		return None
	hostnames = []
	for hostname, sni_config in sni_hostnames.items():
		if not _check_files(sni_config['certfile'], sni_config['keyfile']):
			continue
		hostnames.append(hostname)

	for subdirectory in os.listdir(directory):
		match = _HOSTNAME_DIRECTORY_REGEX.match(subdirectory)
		if match is None:
			continue
		hostname = match.group('hostname')
		if hostname in hostnames:
			continue
		if not all(get_files(directory, match.group('hostname'))):
			continue
		hostnames.append(hostname)
	return sorted(hostnames)
