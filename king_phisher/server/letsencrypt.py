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

import collections
import logging
import os
import re

from king_phisher import startup
from king_phisher.server.database import storage as db_storage

logger = logging.getLogger('KingPhisher.LetsEncrypt')

LETS_ENCRYPT_DEFAULT_DATA_PATH = '/etc/letsencrypt'
"""The default path at which Let's Encrypt data is stored."""

_HOSTNAME_DIRECTORY_REGEX = re.compile(r'^(?P<hostname>[a-z0-9][a-z0-9-]*(\.[a-z0-9-]+)*\.[a-z]+)(-(?P<index>\d+))?$', re.IGNORECASE)

_sni_hostnames = db_storage.KeyValueStorage(namespace='server.ssl.sni.hostnames', order_by='key')

SNIHostnameConfiguration = collections.namedtuple('SNIHostnameConfiguration', ('certfile', 'keyfile', 'enabled'))
"""
The information for a certificate used by the server's SSL Server Name Indicator
(SNI) extension.

.. py:attribute:: certfile

	The path to the SSL certificate file on disk to use for the hostname.

.. py:attribute:: keyfile

	The path to the SSL key file on disk to use for the hostname.

.. py:attribute:: enabled

	Whether or not this configuration is set to be loaded by the server.
"""

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

def _sync_hostnames(unified_directory):
	directory = os.path.join(unified_directory, 'etc', 'live')
	if not os.path.isdir(directory):
		return
	for subdirectory in os.listdir(directory):
		match = _HOSTNAME_DIRECTORY_REGEX.match(subdirectory)
		if match is None:
			continue
		hostname = match.group('hostname')
		if hostname in _sni_hostnames:
			continue
		certfile, keyfile = _get_files(directory, match.group('hostname'))
		if not (certfile and keyfile):
			continue
		set_sni_hostname(hostname, certfile, keyfile)

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

def get_sni_hostname_config(hostname, config=None):
	"""
	Search for and return the SNI configuration for the specified *hostname*.
	This method will first check to see if the entry exists in the database
	before searching the Let's Encrypt data directory (if ``data_path`` is
	present in the server configuration). If no configuration data is found, or
	the data file paths appear invalid, ``None`` is returned.

	:param str hostname: The hostname to retrieve the configuration for.
	:param config: Configuration to retrieve settings from.
	:type config: :py:class:`smoke_zephyr.configuration.Configuration`
	:return: The SNI configuration for the hostname if it was found.
	:rtype: :py:class:`.SNIHostnameConfiguration`
	"""
	unified_directory = config.get_if_exists('server.letsencrypt.data_path') if config else None
	if unified_directory:
		_sync_hostnames(unified_directory)

	sni_config = _sni_hostnames.get(hostname)
	if not sni_config:
		return None
	if not _check_files(sni_config['certfile'], sni_config['keyfile']):
		return None
	return SNIHostnameConfiguration(**sni_config)

def get_sni_hostnames(config=None, check_files=True):
	"""
	Retrieve all the hostnames for which a valid SNI configuration can be
	retrieved. These are the hostnames for which SNI can be enabled. If
	*check_files* is enabled, the data files will be checked to ensure that they
	exist and are readable, else the configuration will be omitted.

	:param config: Configuration to retrieve settings from.
	:type config: :py:class:`smoke_zephyr.configuration.Configuration`
	:param bool check_files: Whether or not to check the referenced data files.
	:return: A dictionary, keyed by hostnames with values of :py:class:`.SNIHostnameConfiguration` instances.
	:rtype: dict
	"""
	unified_directory = config.get_if_exists('server.letsencrypt.data_path') if config else None
	if unified_directory:
		_sync_hostnames(unified_directory)
	hostnames = collections.OrderedDict()
	for hostname, sni_config in _sni_hostnames.items():
		if check_files and not _check_files(sni_config['certfile'], sni_config['keyfile']):
			continue
		hostnames[hostname] = SNIHostnameConfiguration(**sni_config)
	return hostnames

def set_sni_hostname(hostname, certfile, keyfile, enabled=False):
	"""
	Set the SNI configuration for the specified *hostname*. This information can
	then later be retrieved with either :py:func:`get_sni_hostname_config` or
	:py:func:`get_sni_hostnames`.

	:param str hostname: The hostname associated with the configuration data.
	:param str certfile: The path to the certificate file on disk.
	:param str keyfile: The path to the key file on disk.
	:param bool enabled: Whether or not this SNI configuration is loaded in the server.
	"""
	_sni_hostnames[hostname] = {'certfile': os.path.abspath(certfile), 'keyfile': os.path.abspath(keyfile), 'enabled': enabled}
