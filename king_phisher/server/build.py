#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  king_phisher/server/build.py
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
import socket

from king_phisher import errors
from king_phisher.server import rest_api
from king_phisher.server import signals
from king_phisher.server.server import KingPhisherRequestHandler, KingPhisherServer

logger = logging.getLogger('KingPhisher.Server.build')

def get_bind_addresses(config):
	"""
	Retrieve the addresses on which the server should bind to. Each of these
	addresses should be an IP address, port and optionally enable SSL. The
	returned list will contain tuples for each address found in the
	configuration. These tuples will be in the (host, port, use_ssl) format that
	is compatible with AdvancedHTTPServer.

	:param config: Configuration to retrieve settings from.
	:type config: :py:class:`smoke_zephyr.configuration.Configuration`
	:return: The specified addresses to bind to.
	:rtype: list
	"""
	addresses = []
	# pull the legacy lone address
	if config.has_option('server.address'):
		host = config.get_if_exists('server.address.host', '0.0.0.0')
		port = config.get('server.address.port')
		if not isinstance(port, int) and (0 <= port <= 0xffff):
			logger.critical("can not bind to invalid port: {0!r}".format(port))
			raise errors.KingPhisherError("invalid port configuration for address '{0}'".format(host))
		addresses.append((host, port, config.has_option('server.ssl_cert')))

	# pull the new-style list of addresses
	if not isinstance(config.get_if_exists('server.addresses', []), list):
		logger.critical('the server.addresses configuration is invalid, it must be a list of entries')
		raise errors.KingPhisherError('invalid server.addresses configuration')
	for entry, address in enumerate(config.get_if_exists('server.addresses', [])):
		host = address.get('host', '0.0.0.0')
		port = address['port']
		if not (isinstance(port, int) and (0 <= port <= 0xffff)):
			logger.critical("setting server.addresses[{0}] invalid port specified".format(entry))
			raise errors.KingPhisherError("invalid port configuration for address #{0}".format(entry + 1))
		addresses.append((host, port, address.get('ssl', False)))

	for host, port, use_ssl in addresses:
		if port in (443, 8443) and not use_ssl:
			logger.warning("running on port {0} without ssl, specify server.ssl_cert to enable ssl".format(port))
		elif port in (80, 8080) and use_ssl:
			logger.warning("running on port {0} with ssl, remove server.ssl_cert to disable ssl".format(port))
	return addresses

def get_ssl_hostnames(config):
	"""
	Retrieve the SSL hosts that are specified within the configuration. This
	also ensures that the settings appear to be valid by ensuring that the
	necessary files are defined and readable.

	:param config: Configuration to retrieve settings from.
	:type config: :py:class:`smoke_zephyr.configuration.Configuration`
	:return: The specified SSH hosts.
	:rtype: list
	"""
	ssl_hostnames = []
	for entry, ssl_host in enumerate(config.get_if_exists('server.ssl_hosts', [])):
		hostname = ssl_host.get('host')
		if hostname is None:
			logger.critical("setting server.ssl_hosts[{0}] host not specified".format(entry))
			raise errors.KingPhisherError("invalid ssl host configuration #{0}, host must be specified".format(entry + 1))
		ssl_certfile = ssl_host.get('ssl_cert')
		if ssl_certfile is None:
			logger.critical("setting server.ssl_hosts[{0}] cert file not specified".format(entry))
			raise errors.KingPhisherError("invalid ssl host configuration #{0}, missing cert file".format(entry + 1))
		if not os.access(ssl_certfile, os.R_OK):
			logger.critical("setting server.ssl_hosts[{0}] file '{1}' not found".format(entry, ssl_certfile))
			raise errors.KingPhisherError("invalid ssl host configuration #{0}, missing cert file".format(entry + 1))
		ssl_keyfile = ssl_host.get('ssl_key')
		if ssl_keyfile is not None and not os.access(ssl_keyfile, os.R_OK):
			logger.critical("setting server.ssl_hosts[{0}] file '{1}' not found".format(entry, ssl_keyfile))
			raise errors.KingPhisherError("invalid ssl host configuration #{0}, missing key file".format(entry + 1))
		ssl_hostnames.append((hostname, ssl_certfile, ssl_keyfile))
	return ssl_hostnames

def server_from_config(config, handler_klass=None, plugin_manager=None):
	"""
	Build a server from a provided configuration instance. If *handler_klass* is
	specified, then the object must inherit from the corresponding
	KingPhisherServer base class.

	:param config: Configuration to retrieve settings from.
	:type config: :py:class:`smoke_zephyr.configuration.Configuration`
	:param handler_klass: Alternative handler class to use.
	:type handler_klass: :py:class:`.KingPhisherRequestHandler`
	:param plugin_manager: The server's plugin manager instance.
	:type plugin_manager: :py:class:`~king_phisher.server.plugins.ServerPluginManager`
	:return: A configured server instance.
	:rtype: :py:class:`.KingPhisherServer`
	"""
	handler_klass = (handler_klass or KingPhisherRequestHandler)
	# set config defaults
	if not config.has_option('server.secret_id'):
		config.set('server.secret_id', rest_api.generate_token())
	addresses = get_bind_addresses(config)

	if not len(addresses):
		raise errors.KingPhisherError('at least one address to listen on must be specified')

	ssl_certfile = None
	ssl_keyfile = None
	if config.has_option('server.ssl_cert'):
		ssl_certfile = config.get('server.ssl_cert')
		if not os.access(ssl_certfile, os.R_OK):
			logger.critical("setting server.ssl_cert file '{0}' not found".format(ssl_certfile))
			raise errors.KingPhisherError('invalid ssl configuration, missing file')
		logger.info("using default ssl cert file '{0}'".format(ssl_certfile))
		if config.has_option('server.ssl_key'):
			ssl_keyfile = config.get('server.ssl_key')
			if not os.access(ssl_keyfile, os.R_OK):
				logger.critical("setting server.ssl_key file '{0}' not found".format(ssl_keyfile))
				raise errors.KingPhisherError('invalid ssl configuration, missing file')

	if any([address[2] for address in addresses]) and ssl_certfile is None:
		raise errors.KingPhisherError('an ssl certificate must be specified when ssl is enabled')
	if ssl_certfile is None:
		ssl_hostnames = []
	else:
		ssl_hostnames = get_ssl_hostnames(config)

	try:
		server = KingPhisherServer(config, plugin_manager, handler_klass, addresses=addresses, ssl_certfile=ssl_certfile, ssl_keyfile=ssl_keyfile)
	except socket.error as error:
		error_number, error_message = error.args
		if error_number == 98:
			logger.critical('failed to bind server to address (socket error #98)')
		raise errors.KingPhisherError("socket error #{0} ({1})".format((error_number or 'NOT-SET'), error_message))
	if config.has_option('server.server_header'):
		server.server_version = config.get('server.server_header')
	for hostname, ssl_certfile, ssl_keyfile in ssl_hostnames:
		logger.info("adding configuration for ssl hostname: {0} with cert: {1}".format(hostname, ssl_certfile))
		server.add_sni_cert(hostname, ssl_certfile=ssl_certfile, ssl_keyfile=ssl_keyfile)

	if not config.get_if_exists('server.rest_api.token'):
		config.set('server.rest_api.token', rest_api.generate_token())
	if config.get('server.rest_api.enabled'):
		logger.info('rest api initialized with token: ' + config.get('server.rest_api.token'))

	signals.server_initialized.send(server)
	return server
