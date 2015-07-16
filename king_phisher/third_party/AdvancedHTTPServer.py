#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  AdvancedHTTPServer.py
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
#  pylint: disable=too-many-lines

#  Homepage: https://github.com/zeroSteiner/AdvancedHTTPServer
#  Author:   Spencer McIntyre (zeroSteiner)

# Config file example
FILE_CONFIG = """
[server]
ip = 0.0.0.0
port = 8080
web_root = /var/www/html
list_directories = True
# Set an ssl_cert to enable SSL
# ssl_cert = /path/to/cert.pem
"""

# The AdvancedHTTPServer systemd service unit file
# Quick how to:
#   1. Copy this file to /etc/systemd/system/pyhttpd.service
#   2. Edit the run parameters appropriately in the ExecStart option
#   3. Set configuration settings in /etc/pyhttpd.conf
#   4. Run "systemctl daemon-reload"
FILE_SYSTEMD_SERVICE_UNIT = """
[Unit]
Description=Python Advanced HTTP Server
After=network.target

[Service]
Type=simple
ExecStart=/sbin/runuser -l nobody -c "/usr/bin/python -m AdvancedHTTPServer -c /etc/pyhttpd.conf"
ExecStop=/bin/kill -INT $MAINPID

[Install]
WantedBy=multi-user.target
"""

__version__ = '1.1.0'
__all__ = [
	'AdvancedHTTPServer',
	'AdvancedHTTPServerRegisterPath',
	'AdvancedHTTPServerRequestHandler',
	'AdvancedHTTPServerRPCClient',
	'AdvancedHTTPServerRPCClientCached',
	'AdvancedHTTPServerRPCError',
	'AdvancedHTTPServerTestCase',
	'build_server_from_argparser',
	'build_server_from_config'
]

import base64
import binascii
import datetime
import hashlib
import hmac
import io
import json
import logging
import logging.handlers
import mimetypes
import os
import posixpath
import random
import re
import shutil
import socket
import sqlite3
import ssl
import string
import sys
import threading
import time
import traceback
import unittest
import urllib
import zlib

if sys.version_info[0] < 3:
	import BaseHTTPServer
	import cgi as html
	import Cookie
	import httplib
	import SocketServer as socketserver
	import urlparse
	http = type('http', (), {'client': httplib, 'cookies': Cookie, 'server': BaseHTTPServer})
	urllib.parse = urlparse
	urllib.parse.quote = urllib.quote
	urllib.parse.unquote = urllib.unquote
	from ConfigParser import ConfigParser
else:
	import html
	import http.client
	import http.cookies
	import http.server
	import socketserver
	import urllib.parse
	from configparser import ConfigParser

GLOBAL_HANDLER_MAP = {}

def _serialize_ext_dump(obj):
	if obj.__class__ == datetime.date:
		return 'datetime.date', obj.isoformat()
	elif obj.__class__ == datetime.datetime:
		return 'datetime.datetime', obj.isoformat()
	elif obj.__class__ == datetime.time:
		return 'datetime.time', obj.isoformat()
	raise TypeError('Unknown type: ' + repr(obj))

def _serialize_ext_load(obj_type, obj_value, default):
	if obj_type == 'datetime.date':
		return datetime.datetime.strptime(obj_value, '%Y-%m-%d').date()
	elif obj_type == 'datetime.datetime':
		return datetime.datetime.strptime(obj_value, '%Y-%m-%dT%H:%M:%S' + ('.%f' if '.' in obj_value else ''))
	elif obj_type == 'datetime.time':
		return datetime.datetime.strptime(obj_value, '%H:%M:%S' + ('.%f' if '.' in obj_value else '')).time()
	return default

def _json_default(obj):
	obj_type, obj_value = _serialize_ext_dump(obj)
	return {'__complex_type__': obj_type, 'value': obj_value}

def _json_object_hook(obj):
	return _serialize_ext_load(obj.get('__complex_type__'), obj.get('value'), obj)

SERIALIZER_DRIVERS = {}
"""Dictionary of available drivers for serialization."""
SERIALIZER_DRIVERS['application/json'] = {'loads': lambda d, e: json.loads(d, object_hook=_json_object_hook), 'dumps': lambda d: json.dumps(d, default=_json_default)}

try:
	import msgpack
except ImportError:
	has_msgpack = False
else:
	has_msgpack = True
	_MSGPACK_EXT_TYPES = {10: 'datetime.datetime', 11: 'datetime.date', 12: 'datetime.time'}
	def _msgpack_default(obj):
		obj_type, obj_value = _serialize_ext_dump(obj)
		obj_type = next(i[0] for i in _MSGPACK_EXT_TYPES.items() if i[1] == obj_type)
		if sys.version_info[0] == 3:
			obj_value = obj_value.encode('utf-8')
		return msgpack.ExtType(obj_type, obj_value)

	def _msgpack_ext_hook(code, obj_value):
		default = msgpack.ExtType(code, obj_value)
		if sys.version_info[0] == 3:
			obj_value = obj_value.decode('utf-8')
		obj_type = _MSGPACK_EXT_TYPES.get(code)
		return _serialize_ext_load(obj_type, obj_value, default)
	SERIALIZER_DRIVERS['binary/message-pack'] = {'loads': lambda d, e: msgpack.loads(d, encoding=e, ext_hook=_msgpack_ext_hook), 'dumps': lambda d: msgpack.dumps(d, default=_msgpack_default)}

if hasattr(logging, 'NullHandler'):
	logging.getLogger('AdvancedHTTPServer').addHandler(logging.NullHandler())

def random_string(size):
	"""
	Generate a random string of *size* length consisting of both letters
	and numbers. This function is not meant for cryptographic purposes
	and should not be used to generate security tokens.

	:param int size: The length of the string to return.
	:return: A string consisting of random characters.
	:rtype: str
	"""
	return ''.join(random.choice(string.ascii_letters + string.digits) for x in range(size))

def resolve_ssl_protocol_version(version=None):
	"""
	Look up an SSL protocol version by name. If *version* is not specified, then
	the strongest protocol available will be returned.

	:param str version: The name of the version to look up.
	:return: A protocol constant from the :py:mod:`ssl` module.
	:rtype: int
	"""
	if version is None:
		protocol_preference = ('TLSv1_2', 'TLSv1_1', 'TLSv1', 'SSLv3', 'SSLv23', 'SSLv2')
		for protocol in protocol_preference:
			if hasattr(ssl, 'PROTOCOL_' + protocol):
				return getattr(ssl, 'PROTOCOL_' + protocol)
		raise RuntimeError('could not find a suitable ssl PROTOCOL_ version constant')
	elif isinstance(version, str):
		if not hasattr(ssl, 'PROTOCOL_' + version):
			raise ValueError('invalid ssl protocol version: ' + version)
		return getattr(ssl, 'PROTOCOL_' + version)
	raise TypeError("ssl_version() argument 1 must be str, not {0}".format(type(version).__name__))

def build_server_from_argparser(description=None, ServerClass=None, HandlerClass=None):
	"""
	Build a server from command line arguments. If a ServerClass or
	HandlerClass is specified, then the object must inherit from the
	corresponding AdvancedHTTPServer base class.

	:param str description: Description string to be passed to the argument parser.
	:param ServerClass: Alternative server class to use.
	:type ServerClass: :py:class:`.AdvancedHTTPServer`
	:param HandlerClass: Alternative handler class to use.
	:type HandlerClass: :py:class:`.AdvancedHTTPServerRequestHandler`
	:return: A configured server instance.
	:rtype: :py:class:`.AdvancedHTTPServer`
	"""
	import argparse

	def _argp_dir_type(arg):
		if not os.path.isdir(arg):
			raise argparse.ArgumentTypeError("{0} is not a valid directory".format(repr(arg)))
		return arg

	def _argp_port_type(arg):
		if not arg.isdigit():
			raise argparse.ArgumentTypeError("{0} is not a valid port".format(repr(arg)))
		arg = int(arg)
		if arg < 0 or arg > 65535:
			raise argparse.ArgumentTypeError("{0} is not a valid port".format(repr(arg)))
		return arg

	description = (description or 'HTTP Server')
	ServerClass = (ServerClass or AdvancedHTTPServer)
	HandlerClass = (HandlerClass or AdvancedHTTPServerRequestHandler)

	parser = argparse.ArgumentParser(conflict_handler='resolve', description=description, fromfile_prefix_chars='@')
	parser.epilog = 'When a config file is specified with --config the --ip, --port and --web-root options are all ignored.'
	parser.add_argument('-w', '--web-root', dest='web_root', action='store', default='.', type=_argp_dir_type, help='path to the web root directory')
	parser.add_argument('-p', '--port', dest='port', action='store', default=8080, type=_argp_port_type, help='port to serve on')
	parser.add_argument('-i', '--ip', dest='ip', action='store', default='0.0.0.0', help='the ip address to serve on')
	parser.add_argument('--password', dest='password', action='store', default=None, help='password to use for basic authentication')
	parser.add_argument('--log-file', dest='log_file', action='store', default=None, help='log information to a file')
	parser.add_argument('-c', '--conf', dest='config', action='store', default=None, type=argparse.FileType('r'), help='read settings from a config file')
	parser.add_argument('-v', '--version', action='version', version=parser.prog + ' Version: ' + __version__)
	parser.add_argument('-L', '--log', dest='loglvl', action='store', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'], default='INFO', help='set the logging level')
	arguments = parser.parse_args()

	logging.getLogger('').setLevel(logging.DEBUG)
	console_log_handler = logging.StreamHandler()
	console_log_handler.setLevel(getattr(logging, arguments.loglvl))
	console_log_handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)-8s %(message)s"))
	logging.getLogger('').addHandler(console_log_handler)

	if arguments.log_file:
		main_file_handler = logging.handlers.RotatingFileHandler(arguments.log_file, maxBytes=262144, backupCount=5)
		main_file_handler.setLevel(logging.DEBUG)
		main_file_handler.setFormatter(logging.Formatter("%(asctime)s %(name)-30s %(levelname)-10s %(message)s"))
		logging.getLogger('').setLevel(logging.DEBUG)
		logging.getLogger('').addHandler(main_file_handler)

	if arguments.config:
		config = ConfigParser()
		config.readfp(arguments.config)
		server = build_server_from_config(config, 'server', ServerClass=ServerClass, HandlerClass=HandlerClass)
	else:
		server = ServerClass(HandlerClass, address=(arguments.ip, arguments.port))
		server.serve_files_root = arguments.web_root

	if arguments.password:
		server.auth_add_creds('', arguments.password)
	return server

def build_server_from_config(config, section_name, ServerClass=None, HandlerClass=None):
	"""
	Build a server from a provided :py:class:`configparser.ConfigParser`
	instance. If a ServerClass or HandlerClass is specified, then the
	object must inherit from the corresponding AdvancedHTTPServer base
	class.

	:param config: Configuration to retrieve settings from.
	:type config: :py:class:`configparser.ConfigParser`
	:param str section_name: The section name of the configuration to use.
	:param ServerClass: Alternative server class to use.
	:type ServerClass: :py:class:`.AdvancedHTTPServer`
	:param HandlerClass: Alternative handler class to use.
	:type HandlerClass: :py:class:`.AdvancedHTTPServerRequestHandler`
	:return: A configured server instance.
	:rtype: :py:class:`.AdvancedHTTPServer`
	"""
	ServerClass = (ServerClass or AdvancedHTTPServer)
	HandlerClass = (HandlerClass or AdvancedHTTPServerRequestHandler)
	port = config.getint(section_name, 'port')
	web_root = None
	if config.has_option(section_name, 'web_root'):
		web_root = config.get(section_name, 'web_root')

	if config.has_option(section_name, 'ip'):
		ip = config.get(section_name, 'ip')
	else:
		ip = '0.0.0.0'
	ssl_certfile = None
	if config.has_option(section_name, 'ssl_cert'):
		ssl_certfile = config.get(section_name, 'ssl_cert')
	ssl_keyfile = None
	if config.has_option(section_name, 'ssl_key'):
		ssl_keyfile = config.get(section_name, 'ssl_key')
	server = ServerClass(HandlerClass, address=(ip, port), ssl_certfile=ssl_certfile, ssl_keyfile=ssl_keyfile)

	if config.has_option(section_name, 'password_type'):
		password_type = config.get(section_name, 'password_type')
	else:
		password_type = 'md5'
	if config.has_option(section_name, 'password'):
		password = config.get(section_name, 'password')
		if config.has_option(section_name, 'username'):
			username = config.get(section_name, 'username')
		else:
			username = ''
		server.auth_add_creds(username, password, pwtype=password_type)
	cred_idx = 0
	while config.has_option(section_name, 'password' + str(cred_idx)):
		password = config.get(section_name, 'password' + str(cred_idx))
		if not config.has_option(section_name, 'username' + str(cred_idx)):
			break
		username = config.get(section_name, 'username' + str(cred_idx))
		server.auth_add_creds(username, password, pwtype=password_type)
		cred_idx += 1

	if web_root is None:
		server.serve_files = False
	else:
		server.serve_files = True
		server.serve_files_root = web_root
		if config.has_option(section_name, 'list_directories'):
			server.serve_files_list_directories = config.getboolean(section_name, 'list_directories')
	return server

class AdvancedHTTPServerRegisterPath(object):
	"""
	Register a path and handler with the global handler map. This can be
	used as a decorator. If no handler is specified then the path and
	function will be registered with all :py:class:`.AdvancedHTTPServerRequestHandler`
	instances.

	.. code-block:: python

	  @AdvancedHTTPServerRegisterPath('^test$')
	  def handle_test(handler, query):
	      pass
	"""
	def __init__(self, path, handler=None, is_rpc=False):
		"""
		:param str path: The path regex to register the function to.
		:param str handler: A specific :py:class:`.AdvancedHTTPServerRequestHandler` class to register the handler with.
		:param bool is_rpc: Whether the handler is an RPC handler or not.
		"""
		self.path = path
		self.is_rpc = is_rpc
		if handler is None or isinstance(handler, str):
			self.handler = handler
		elif hasattr(handler, '__name__'):
			self.handler = handler.__name__
		elif hasattr(handler, '__class__'):
			self.handler = handler.__class__.__name__
		else:
			raise ValueError('unknown handler: ' + repr(handler))

	def __call__(self, function):
		handler_map = GLOBAL_HANDLER_MAP.get(self.handler, {})
		handler_map[self.path] = (function, self.is_rpc)
		GLOBAL_HANDLER_MAP[self.handler] = handler_map
		return function

class AdvancedHTTPServerRPCError(Exception):
	"""
	This class represents an RPC error either local or remote. Any errors
	in routines executed on the server will raise this error.
	"""
	def __init__(self, message, status, remote_exception=None):
		super(AdvancedHTTPServerRPCError, self).__init__()
		self.message = message
		self.status = status
		self.remote_exception = remote_exception

	def __repr__(self):
		return "{0}(message='{1}', status={2}, remote_exception={3})".format(self.__class__.__name__, self.message, self.status, self.is_remote_exception)

	def __str__(self):
		if self.is_remote_exception:
			return 'a remote exception occurred'
		return "the server responded with {0} '{1}'".format(self.status, self.message)

	@property
	def is_remote_exception(self):
		"""
		This is true if the represented error resulted from an exception on the
		remote server.

		:type: bool
		"""
		return bool(self.remote_exception is not None)

class AdvancedHTTPServerRPCClient(object):
	"""
	This object facilitates communication with remote RPC methods as
	provided by a :py:class:`.AdvancedHTTPServerRequestHandler` instance.
	Once created this object can be called directly, doing so is the same
	as using the call method.

	This object uses locks internally to be thread safe. Only one thread
	can execute a function at a time.
	"""
	def __init__(self, address, use_ssl=False, username=None, password=None, uri_base='/', hmac_key=None):
		"""
		:param tuple address: The address of the server to conenct to as (host, port).
		:param bool use_ssl: Whether to connect with SSL or not.
		:param str username: The username to authenticate with.
		:param str password: The password to authenticate with.
		:param str uri_base: An optional prefix for all methods.
		:param str hmac_key: An HMAC key to use for request authentication.
		"""
		self.host = str(address[0])
		self.port = int(address[1])
		if not hasattr(self, 'logger'):
			self.logger = logging.getLogger('AdvancedHTTPServer.RPCClient')

		self.use_ssl = bool(use_ssl)
		self.uri_base = str(uri_base)
		self.username = (None if username is None else str(username))
		self.password = (None if password is None else str(password))
		if isinstance(hmac_key, str):
			hmac_key = hmac_key.encode('UTF-8')
		self.hmac_key = hmac_key
		self.lock = threading.Lock()
		self.set_serializer('application/json')
		self.reconnect()

	def __reduce__(self):
		address = (self.host, self.port)
		return (self.__class__, (address, self.use_ssl, self.username, self.password, self.uri_base, self.hmac_key))

	def set_serializer(self, serializer_name, compression=None):
		"""
		Configure the serializer to use for communication with the server.
		The serializer specified must be valid and in the
		:py:data:`.SERIALIZER_DRIVERS` map.

		:param str serializer_name: The name of the serializer to use.
		:param str compression: The name of a compression library to use.
		"""
		self.serializer = AdvancedHTTPServerSerializer(serializer_name, charset='UTF-8', compression=compression)
		self.logger.debug('using serializer: ' + serializer_name)

	def __call__(self, *args, **kwargs):
		return self.call(*args, **kwargs)

	def encode(self, data):
		"""Encode data with the configured serializer."""
		return self.serializer.dumps(data)

	def decode(self, data):
		"""Decode data with the configured serializer."""
		return self.serializer.loads(data)

	def reconnect(self):
		"""Reconnect to the remote server."""
		self.lock.acquire()
		if self.use_ssl:
			self.client = http.client.HTTPSConnection(self.host, self.port)
		else:
			self.client = http.client.HTTPConnection(self.host, self.port)
		self.lock.release()

	def call(self, method, *args, **kwargs):
		"""
		Issue a call to the remote end point to execute the specified
		procedure.

		:param str method: The name of the remote procedure to execute.
		:return: The return value from the remote function.
		"""
		options = self.encode(dict(args=args, kwargs=kwargs))

		headers = {}
		headers['Content-Type'] = self.serializer.content_type
		headers['Content-Length'] = str(len(options))

		if self.hmac_key is not None:
			hmac_calculator = hmac.new(self.hmac_key, digestmod=hashlib.sha1)
			hmac_calculator.update(options)
			headers['X-RPC-HMAC'] = hmac_calculator.hexdigest()

		if self.username is not None and self.password is not None:
			headers['Authorization'] = 'Basic ' + base64.b64encode((self.username + ':' + self.password).encode('UTF-8')).decode('UTF-8')

		method = os.path.join(self.uri_base, method)
		self.logger.debug('calling RPC method: ' + method[1:])
		with self.lock:
			self.client.request('RPC', method, options, headers)
			resp = self.client.getresponse()
		if resp.status != 200:
			raise AdvancedHTTPServerRPCError(resp.reason, resp.status)

		resp_data = resp.read()
		if self.hmac_key is not None:
			hmac_digest = resp.getheader('X-RPC-HMAC')
			if not isinstance(hmac_digest, str):
				raise AdvancedHTTPServerRPCError('hmac validation error', resp.status)
			hmac_digest = hmac_digest.lower()
			hmac_calculator = hmac.new(self.hmac_key, digestmod=hashlib.sha1)
			hmac_calculator.update(resp_data)
			if hmac_digest != hmac_calculator.hexdigest():
				raise AdvancedHTTPServerRPCError('hmac validation error', resp.status)
		resp_data = self.decode(resp_data)
		if not ('exception_occurred' in resp_data and 'result' in resp_data):
			raise AdvancedHTTPServerRPCError('missing response information', resp.status)
		if resp_data['exception_occurred']:
			raise AdvancedHTTPServerRPCError('remote method incured an exception', resp.status, remote_exception=resp_data['exception'])
		return resp_data['result']

class AdvancedHTTPServerRPCClientCached(AdvancedHTTPServerRPCClient):
	"""
	This object builds upon :py:class:`.AdvancedHTTPServerRPCClient` and
	provides additional methods for cacheing results in memory.
	"""
	def __init__(self, *args, **kwargs):
		cache_db = kwargs.pop('cache_db', ':memory:')
		super(AdvancedHTTPServerRPCClientCached, self).__init__(*args, **kwargs)
		self.cache_db = sqlite3.connect(cache_db, check_same_thread=False)
		cursor = self.cache_db.cursor()
		cursor.execute('CREATE TABLE IF NOT EXISTS cache (method TEXT NOT NULL, options_hash BLOB NOT NULL, return_value BLOB NOT NULL)')
		self.cache_db.commit()
		self.cache_lock = threading.Lock()

	def cache_call(self, method, *options):
		"""
		Call a remote method and store the result locally. Subsequent
		calls to the same method with the same arguments will return the
		cached result without invoking the remote procedure. Cached results are
		kept indefinitely and must be manually refreshed with a call to
		:py:meth:`.cache_call_refresh`.

		:param str method: The name of the remote procedure to execute.
		:return: The return value from the remote function.
		"""
		options_hash = self.encode(options)
		if len(options_hash) > 20:
			options_hash = hashlib.new('sha1', options_hash).digest()
		options_hash = sqlite3.Binary(options_hash)

		with self.cache_lock:
			cursor = self.cache_db.cursor()
			cursor.execute('SELECT return_value FROM cache WHERE method = ? AND options_hash = ?', (method, options_hash))
			return_value = cursor.fetchone()
		if return_value:
			return_value = bytes(return_value[0])
			return self.decode(return_value)
		return_value = self.call(method, *options)
		store_return_value = sqlite3.Binary(self.encode(return_value))
		with self.cache_lock:
			cursor = self.cache_db.cursor()
			cursor.execute('INSERT INTO cache (method, options_hash, return_value) VALUES (?, ?, ?)', (method, options_hash, store_return_value))
			self.cache_db.commit()
		return return_value

	def cache_call_refresh(self, method, *options):
		"""
		Call a remote method and update the local cache with the result
		if it already existed.

		:param str method: The name of the remote procedure to execute.
		:return: The return value from the remote function.
		"""
		options_hash = self.encode(options)
		if len(options_hash) > 20:
			options_hash = hashlib.new('sha1', options).digest()
		options_hash = sqlite3.Binary(options_hash)

		with self.cache_lock:
			cursor = self.cache_db.cursor()
			cursor.execute('DELETE FROM cache WHERE method = ? AND options_hash = ?', (method, options_hash))
		return_value = self.call(method, *options)
		store_return_value = sqlite3.Binary(self.encode(return_value))
		with self.cache_lock:
			cursor = self.cache_db.cursor()
			cursor.execute('INSERT INTO cache (method, options_hash, return_value) VALUES (?, ?, ?)', (method, options_hash, store_return_value))
			self.cache_db.commit()
		return return_value

	def cache_clear(self):
		"""Purge the local store of all cached function information."""
		with self.cache_lock:
			cursor = self.cache_db.cursor()
			cursor.execute('DELETE FROM cache')
			self.cache_db.commit()
		self.logger.info('the RPC cache has been purged')
		return

class AdvancedHTTPServerNonThreaded(http.server.HTTPServer, object):
	"""
	This class is used internally by :py:class:`.AdvancedHTTPServer` and
	is not intended for use by other classes or functions.
	"""
	def __init__(self, *args, **kwargs):
		if not hasattr(self, 'logger'):
			self.logger = logging.getLogger('AdvancedHTTPServer')
		self.allow_reuse_address = True
		self.using_ssl = False
		self.serve_files = False
		self.serve_files_root = os.getcwd()
		self.serve_files_list_directories = True # irrelevant if serve_files == False
		self.serve_robots_txt = True
		self.rpc_hmac_key = None
		self.basic_auth = None
		self.robots_txt = b'User-agent: *\nDisallow: /\n'
		self.server_version = 'HTTPServer/' + __version__
		super(AdvancedHTTPServerNonThreaded, self).__init__(*args, **kwargs)

	def finish_request(self, *args, **kwargs):
		try:
			super(AdvancedHTTPServerNonThreaded, self).finish_request(*args, **kwargs)
		except IOError:
			self.logger.warning('IOError encountered in finish_request')

	def server_bind(self, *args, **kwargs):
		self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
		super(AdvancedHTTPServerNonThreaded, self).server_bind(*args, **kwargs)

	def shutdown(self, *args, **kwargs):
		super(AdvancedHTTPServerNonThreaded, self).shutdown(*args, **kwargs)
		try:
			self.socket.shutdown(socket.SHUT_RDWR)
		except socket.error:
			pass
		self.socket.close()

class AdvancedHTTPServerThreaded(socketserver.ThreadingMixIn, AdvancedHTTPServerNonThreaded):
	"""
	This class is used internally by :py:class:`.AdvancedHTTPServer` and
	is not intended for use by other classes or functions.
	"""
	pass

class AdvancedHTTPServerRequestHandler(http.server.BaseHTTPRequestHandler, object):
	"""
	This is the primary http request handler class of the
	AdvancedHTTPServer framework. Custom request handlers must inherit
	from this object to be compatible. Instances of this class are created
	automatically. This class will handle standard HTTP GET, HEAD, OPTIONS,
	and POST requests. Callback functions called handlers can be registered
	to resource paths using regular expressions in the *handler_map*
	attribute for GET HEAD and POST requests and *rpc_handler_map* for RPC
	requests. Non-RPC handler functions that are not class methods of
	the request handler instance will be passed the instance of the
	request handler as the first argument.
	"""
	if not mimetypes.inited:
		mimetypes.init() # try to read system mime.types
	extensions_map = mimetypes.types_map.copy()
	extensions_map.update({
		'': 'application/octet-stream', # Default
		'.py': 'text/plain',
		'.rb': 'text/plain',
		'.c':  'text/plain',
		'.h':  'text/plain',
	})

	def __init__(self, *args, **kwargs):
		self.cookies = None
		self.path = None
		self.wfile = None
		self.handler_map = {}
		"""The dict object which maps regular expressions of resources to the functions which should handle them."""
		self.rpc_handler_map = {}
		"""The dict object which maps regular expressions of RPC functions to their handlers."""
		self.server = args[2]
		self.headers_active = False
		"""Whether or not the request is in the sending headers phase."""
		for map_name in (None, self.__class__.__name__):
			handler_map = GLOBAL_HANDLER_MAP.get(map_name, {})
			for path, function_info in handler_map.items():
				function, function_is_rpc = function_info
				if function_is_rpc:
					self.rpc_handler_map[path] = function
				else:
					self.handler_map[path] = function
		self.install_handlers()

		self.basic_auth_user = None
		"""The name of the user if the current request is using basic authentication."""
		self.query_data = None
		"""The parameter data that has been passed to the server parsed as a dict."""
		self.raw_query_data = None
		"""The raw data that was parsed into the :py:attr:`.query_data` attribute."""
		super(AdvancedHTTPServerRequestHandler, self).__init__(*args, **kwargs)

	def version_string(self):
		return self.server.server_version

	def install_handlers(self):
		"""
		This method is meant to be over ridden by custom classes. It is
		called as part of the __init__ method and provides an opportunity
		for the handler maps to be populated with entries.
		"""
		pass # over ride me

	def respond_file(self, file_path, attachment=False, query=None):
		"""
		Respond to the client by serving a file, either directly or as
		an attachment.

		:param str file_path: The path to the file to serve, this does not need to be in the web root.
		:param bool attachment: Whether to serve the file as a download by setting the Content-Disposition header.
		"""
		del query
		file_path = os.path.abspath(file_path)
		try:
			file_obj = open(file_path, 'rb')
		except IOError:
			self.respond_not_found()
			return None
		self.send_response(200)
		self.send_header('Content-Type', self.guess_mime_type(file_path))
		fs = os.fstat(file_obj.fileno())
		self.send_header('Content-Length', str(fs[6]))
		if attachment:
			file_name = os.path.basename(file_path)
			self.send_header('Content-Disposition', 'attachment; filename=' + file_name)
		self.send_header('Last-Modified', self.date_time_string(fs.st_mtime))
		self.end_headers()
		shutil.copyfileobj(file_obj, self.wfile)
		file_obj.close()
		return

	def respond_list_directory(self, dir_path, query=None):
		"""
		Respond to the client with an HTML page listing the contents of
		the specified directory.

		:param str dir_path: The path of the directory to list the contents of.
		"""
		del query
		try:
			dir_contents = os.listdir(dir_path)
		except os.error:
			self.respond_not_found()
			return None
		if os.path.normpath(dir_path) != self.server.serve_files_root:
			dir_contents.append('..')
		dir_contents.sort(key=lambda a: a.lower())
		displaypath = html.escape(urllib.parse.unquote(self.path), quote=True)

		f = io.BytesIO()
		encoding = sys.getfilesystemencoding()
		f.write(b'<!DOCTYPE html PUBLIC "-//W3C//DTD HTML 3.2 Final//EN">\n')
		f.write(b'<html>\n<title>Directory listing for ' + displaypath.encode(encoding) + b'</title>\n')
		f.write(b'<body>\n<h2>Directory listing for ' + displaypath.encode(encoding) + b'</h2>\n')
		f.write(b'<hr>\n<ul>\n')
		for name in dir_contents:
			fullname = os.path.join(dir_path, name)
			displayname = linkname = name
			# Append / for directories or @ for symbolic links
			if os.path.isdir(fullname):
				displayname = name + "/"
				linkname = name + "/"
			if os.path.islink(fullname):
				displayname = name + "@"
				# Note: a link to a directory displays with @ and links with /
			f.write(('<li><a href="' + urllib.parse.quote(linkname) + '">' + html.escape(displayname, quote=True) + '</a>\n').encode(encoding))
		f.write(b'</ul>\n<hr>\n</body>\n</html>\n')
		length = f.tell()
		f.seek(0)

		self.send_response(200)
		self.send_header('Content-Type', 'text/html; charset=' + encoding)
		self.send_header('Content-Length', str(length))
		self.end_headers()
		shutil.copyfileobj(f, self.wfile)
		f.close()
		return

	def respond_not_found(self):
		"""Respond to the client with a default 404 message."""
		self.send_response(404)
		self.send_header('Content-Type', 'text/html')
		self.end_headers()
		self.wfile.write(b'Resource Not Found\n')
		return

	def respond_redirect(self, location='/'):
		"""
		Respond to the client with a 301 message and redirect them with
		a Location header.

		:param str location: The new location to redirect the client to.
		"""
		self.send_response(301)
		self.send_header('Location', location)
		self.end_headers()
		return

	def respond_server_error(self, status=None, status_line=None, message=None):
		"""
		Handle an internal server error, logging a traceback if executed
		within an exception handler.

		:param int status: The status code to respond to the client with.
		:param str status_line: The status message to respond to the client with.
		:param str message: The body of the response that is sent to the client.
		"""
		(ex_type, ex_value, ex_traceback) = sys.exc_info()
		if ex_type:
			(ex_file_name, ex_line, _, _) = traceback.extract_tb(ex_traceback)[-1]
			line_info = "{0}:{1}".format(ex_file_name, ex_line)
			log_msg = "encountered {0} in {1}".format(repr(ex_value), line_info)
			self.server.logger.error(log_msg)
		status = (status or 500)
		status_line = (status_line or http.client.responses.get(status, 'Internal Server Error')).strip()
		self.send_response(status, status_line)
		message = (message or status_line)
		if isinstance(message, (str, bytes)):
			self.send_header('Content-Length', len(message))
			self.end_headers()
			if isinstance(message, str):
				self.wfile.write(message.encode(sys.getdefaultencoding()))
			else:
				self.wfile.write(message)
		elif hasattr(message, 'fileno'):
			fs = os.fstat(message.fileno())
			self.send_header('Content-Length', str(fs[6]))
			self.end_headers()
			shutil.copyfileobj(message, self.wfile)
		else:
			self.end_headers()
		return

	def respond_unauthorized(self, request_authentication=False):
		"""
		Respond to the client that the request is unauthorized.

		:param bool request_authentication: Whether to request basic authentication information by sending a WWW-Authenticate header.
		"""
		self.send_response(401)
		if request_authentication:
			self.send_header('WWW-Authenticate', 'Basic realm="' + self.server_version + '"')
		self.send_header('Content-Type', 'text/html')
		self.end_headers()
		self.wfile.write(b'Unauthorized\n')
		return

	def dispatch_handler(self, query=None):
		"""
		Dispatch functions based on the established handler_map. It is
		generally not necessary to override this function and doing so
		will prevent any handlers from being executed. This function is
		executed automatically when requests of either GET, HEAD, or POST
		are received.

		:param dict query: Parsed query parameters from the corresponding request.
		"""
		query = (query or {})
		# normalize the path
		# abandon query parameters
		self.path = self.path.split('?', 1)[0]
		self.path = self.path.split('#', 1)[0]
		original_path = urllib.parse.unquote(self.path)
		self.path = posixpath.normpath(original_path)
		words = self.path.split('/')
		words = filter(None, words)
		tmp_path = ''
		for word in words:
			_, word = os.path.splitdrive(word)
			_, word = os.path.split(word)
			if word in (os.curdir, os.pardir):
				continue
			tmp_path = os.path.join(tmp_path, word)
		self.path = tmp_path

		if self.path == 'robots.txt' and self.server.serve_robots_txt:
			self.send_response(200)
			self.send_header('Content-Type', 'text/plain')
			self.end_headers()
			self.wfile.write(self.server.robots_txt)
			return

		self.cookies = http.cookies.SimpleCookie(self.headers.get('cookie', ''))
		for (path_regex, handler) in self.handler_map.items():
			if re.match(path_regex, self.path):
				try:
					if hasattr(self, handler.__name__) and (handler == getattr(self, handler.__name__).__func__ or handler == getattr(self, handler.__name__)):
						getattr(self, handler.__name__)(query)
					else:
						handler(self, query)
				except Exception:
					self.respond_server_error()
				return

		if not self.server.serve_files:
			self.respond_not_found()
			return

		file_path = self.server.serve_files_root
		file_path = os.path.join(file_path, tmp_path)
		if os.path.isfile(file_path) and os.access(file_path, os.R_OK):
			self.respond_file(file_path, query=query)
			return
		elif os.path.isdir(file_path) and os.access(file_path, os.R_OK):
			if not original_path.endswith('/'):
				# redirect browser, doing what apache does
				destination = self.path + '/'
				if self.command == 'GET':
					destination += '?' + urllib.urlencode(self.query_data, True)
				self.respond_redirect(destination)
				return
			for index in ['index.html', 'index.htm']:
				index = os.path.join(file_path, index)
				if os.path.isfile(index) and os.access(index, os.R_OK):
					self.respond_file(index, query=query)
					return
			if self.server.serve_files_list_directories:
				self.respond_list_directory(file_path, query=query)
				return
		self.respond_not_found()
		return

	def send_response(self, *args, **kwargs):
		super(AdvancedHTTPServerRequestHandler, self).send_response(*args, **kwargs)
		self.headers_active = True

	def end_headers(self):
		super(AdvancedHTTPServerRequestHandler, self).end_headers()
		self.headers_active = False
		if self.command == 'HEAD':
			self.wfile.close() # pylint: disable=access-member-before-definition
			self.wfile = open(os.devnull, 'wb')

	def guess_mime_type(self, path):
		"""
		Guess an appropriate MIME type based on the extension of the
		provided path.

		:param str path: The of the file to analyze.
		:return: The guessed MIME type of the default if non are found.
		:rtype: str
		"""
		_, ext = posixpath.splitext(path)
		if ext in self.extensions_map:
			return self.extensions_map[ext]
		ext = ext.lower()
		if ext in self.extensions_map:
			return self.extensions_map[ext]
		else:
			return self.extensions_map['']

	def stock_handler_respond_unauthorized(self, query):
		"""This method provides a handler suitable to be used in the handler_map."""
		del query
		self.respond_unauthorized()
		return

	def stock_handler_respond_not_found(self, query):
		"""This method provides a handler suitable to be used in the handler_map."""
		del query
		self.respond_not_found()
		return

	def check_authorization(self):
		"""
		Check for the presence of a basic auth Authorization header and
		if the credentials contained within in are valid.

		:return: Whether or not the credentials are valid.
		:rtype: bool
		"""
		try:
			if self.server.basic_auth is None:
				return True
			auth_info = self.headers.get('Authorization')
			if not auth_info:
				return False
			auth_info = auth_info.split()
			if len(auth_info) != 2 or auth_info[0] != 'Basic':
				return False
			auth_info = base64.b64decode(auth_info[1]).decode(sys.getdefaultencoding())
			username = auth_info.split(':')[0]
			password = ':'.join(auth_info.split(':')[1:])
			password_bytes = password.encode(sys.getdefaultencoding())
			if hasattr(self, 'custom_authentication'):
				if self.custom_authentication(username, password):
					self.basic_auth_user = username
					return True
				return False
			if not username in self.server.basic_auth:
				self.server.logger.warning('received invalid username: ' + username)
				return False
			password_data = self.server.basic_auth[username]

			if password_data['type'] == 'plain':
				if password == password_data['value']:
					self.basic_auth_user = username
					return True
			elif hashlib.new(password_data['type'], password_bytes).digest() == password_data['value']:
				self.basic_auth_user = username
				return True
			self.server.logger.warning('received invalid password from user: ' + username)
		except Exception:
			pass
		return False

	def cookie_get(self, name):
		"""
		Check for a cookie value by name.

		:param str name: Name of the cookie value to retreive.
		:return: Returns the cookie value if it's set or None if it's not found.
		"""
		if not hasattr(self, 'cookies'):
			return None
		if self.cookies.get(name):
			return self.cookies.get(name).value
		return None

	def cookie_set(self, name, value):
		"""
		Set the value of a client cookie. This can only be called while
		headers can be sent.

		:param str name: The name of the cookie value to set.
		:param str value: The value of the cookie to set.
		"""
		if not self.headers_active:
			raise RuntimeError('headers have already been ended')
		cookie = "{0}={1}; Path=/; HttpOnly".format(name, value)
		self.send_header('Set-Cookie', cookie)

	def do_GET(self):
		if not self.check_authorization():
			self.respond_unauthorized(request_authentication=True)
			return
		uri = urllib.parse.urlparse(self.path)
		self.path = uri.path
		self.query_data = urllib.parse.parse_qs(uri.query)

		self.dispatch_handler(self.query_data)
		return
	do_HEAD = do_GET

	def do_POST(self):
		if not self.check_authorization():
			self.respond_unauthorized(request_authentication=True)
			return
		content_length = int(self.headers.get('content-length', 0))
		data = self.rfile.read(content_length)
		self.raw_query_data = data
		content_type = self.headers.get('content-type', '')
		content_type = content_type.split(';', 1)[0]
		self.query_data = {}
		try:
			if not isinstance(data, str):
				data = data.decode(self.get_content_type_charset())
			if content_type.startswith('application/json'):
				data = json.loads(data)
				if isinstance(data, dict):
					self.query_data = dict([(i[0], [i[1]]) for i in data.items()])
			else:
				self.query_data = urllib.parse.parse_qs(data, keep_blank_values=1)
		except Exception:
			self.respond_server_error(400)
		else:
			self.dispatch_handler(self.query_data)
		return

	def do_OPTIONS(self):
		available_methods = list(x[3:] for x in dir(self) if x.startswith('do_'))
		if 'RPC' in available_methods and len(self.rpc_handler_map) == 0:
			available_methods.remove('RPC')
		self.send_response(200)
		self.send_header('Allow', ', '.join(available_methods))
		self.end_headers()

	def do_RPC(self):
		if not self.check_authorization():
			self.respond_unauthorized(request_authentication=True)
			return

		data_length = self.headers.get('content-length')
		if data_length is None:
			self.send_error(411)
			return

		content_type = self.headers.get('content-type')
		if content_type is None:
			self.send_error(400, 'Missing Header: Content-Type')
			return

		try:
			data_length = int(self.headers.get('content-length'))
			data = self.rfile.read(data_length)
		except Exception:
			self.send_error(400, 'Invalid Data')
			return

		if self.server.rpc_hmac_key is not None:
			hmac_digest = self.headers.get('X-RPC-HMAC')
			if not isinstance(hmac_digest, str):
				self.respond_unauthorized(request_authentication=True)
				return
			hmac_digest = hmac_digest.lower()
			hmac_calculator = hmac.new(self.server.rpc_hmac_key, digestmod=hashlib.sha1)
			hmac_calculator.update(data)
			if hmac_digest != hmac_calculator.hexdigest():
				self.server.logger.warning('failed to validate HMAC digest')
				self.respond_unauthorized(request_authentication=True)
				return

		try:
			serializer = AdvancedHTTPServerSerializer.from_content_type(content_type)
		except ValueError:
			self.send_error(400, 'Invalid Content-Type')
			return

		try:
			data = serializer.loads(data)
		except Exception:
			self.server.logger.warning('serializer failed to load data')
			self.send_error(400, 'Invalid Data')
			return

		if isinstance(data, (list, tuple)):
			meth_args = data
			meth_kwargs = {}
		elif isinstance(data, dict):
			meth_args = data.get('args', ())
			meth_kwargs = data.get('kwargs', {})
		else:
			self.server.logger.warning('received data does not match the calling convention')
			self.send_error(400, 'Invalid Data')
			return

		rpc_handler = None
		for (path_regex, handler) in self.rpc_handler_map.items():
			if re.match(path_regex, self.path):
				rpc_handler = handler
				break
		if not rpc_handler:
			self.respond_server_error(501)
			return

		self.server.logger.info('running RPC method: ' + self.path)
		response = {'result': None, 'exception_occurred': False}
		try:
			response['result'] = rpc_handler(*meth_args, **meth_kwargs)
		except Exception as error:
			response['exception_occurred'] = True
			exc_name = "{0}.{1}".format(error.__class__.__module__, error.__class__.__name__)
			response['exception'] = dict(name=exc_name, message=getattr(error, 'message', None))
			self.server.logger.error('error: ' + exc_name + ' occurred while calling RPC method: ' + self.path)

		try:
			response = serializer.dumps(response)
		except Exception:
			self.respond_server_error(message='Failed To Pack Response')
			return

		self.send_response(200)
		self.send_header('Content-Type', serializer.content_type)
		if self.server.rpc_hmac_key is not None:
			hmac_calculator = hmac.new(self.server.rpc_hmac_key, digestmod=hashlib.sha1)
			hmac_calculator.update(response)
			self.send_header('X-RPC-HMAC', hmac_calculator.hexdigest())
		self.end_headers()

		self.wfile.write(response)
		return

	def log_error(self, format, *args):
		self.server.logger.warning(self.address_string() + ' ' + format % args)

	def log_message(self, format, *args):
		self.server.logger.info(self.address_string() + ' ' + format % args)

	def get_query(self, name, default=None):
		"""
		Get a value from the query data that was sent to the server.

		:param str name: The name of the query value to retrieve.
		:return: The value if it exists, otherwise *default* will be returned.
		:rtype: str
		"""
		return self.query_data.get(name, [default])[0]

	def get_content_type_charset(self, default='UTF-8'):
		"""
		Inspect the Content-Type header to retrieve the charset that the client
		has specified.

		:param str default: The default charset to return if none exists.
		:return: The charset of the request.
		:rtype: str
		"""
		encoding = default
		header = self.headers.get('Content-Type', '')
		idx = header.find('charset=')
		if idx > 0:
			encoding = (header[idx + 8:].split(' ', 1)[0] or encoding)
		return encoding

class AdvancedHTTPServerSerializer(object):
	"""
	This class represents a serilizer object for use with the RPC system.
	"""
	def __init__(self, name, charset='UTF-8', compression=None):
		"""
		:param str name: The name of the serializer to use.
		:param str charset: The name of the encoding to use.
		:param str compression: The compression library to use.
		"""
		if not name in SERIALIZER_DRIVERS:
			raise ValueError("unknown serializer '{0}'".format(name))
		self.name = name
		self._charset = charset
		self._compression = compression
		self.content_type = "{0}; charset={1}".format(self.name, self._charset)
		if self._compression:
			self.content_type += '; compression=' + self._compression

	@classmethod
	def from_content_type(cls, content_type):
		"""
		Build a serializer object from a MIME Content-Type string.

		:param str content_type: The Content-Type string to parse.
		:return: A new serializer instance.
		:rtype: :py:class:`.AdvancedHTTPServerSerializer`
		"""
		name = content_type
		options = {}
		if ';' in content_type:
			name, options_str = content_type.split(';', 1)
			for part in options_str.split(';'):
				part = part.strip()
				if '=' in part:
					key, value = part.split('=')
				else:
					key, value = (part, None)
				options[key] = value
		# old style compatibility
		if name.endswith('+zlib'):
			options['compression'] = 'zlib'
			name = name[:-5]
		return cls(name, charset=options.get('charset', 'UTF-8'), compression=options.get('compression'))

	def dumps(self, data):
		"""
		Serialize a python data type for transmission or storage.

		:param data: The python object to serialize.
		:return: The serialized representation of the object.
		:rtype: bytes
		"""
		data = SERIALIZER_DRIVERS[self.name]['dumps'](data)
		if sys.version_info[0] == 3 and isinstance(data, str):
			data = data.encode(self._charset)
		if self._compression == 'zlib':
			data = zlib.compress(data)
		assert isinstance(data, bytes)
		return data

	def loads(self, data):
		"""
		Deserialize the data into it's original python object.

		:param bytes data: The serialized object to load.
		:return: The original python object.
		"""
		if not isinstance(data, bytes):
			raise TypeError("loads() argument 1 must be bytes, not {0}".format(type(data).__name__))
		if self._compression == 'zlib':
			data = zlib.decompress(data)
		if sys.version_info[0] == 3 and self.name.startswith('application/'):
			data = data.decode(self._charset)
		data = SERIALIZER_DRIVERS[self.name]['loads'](data, (self._charset if sys.version_info[0] == 3 else None))
		if isinstance(data, list):
			data = tuple(data)
		return data

class AdvancedHTTPServer(object):
	"""
	This is the primary server class for the AdvancedHTTPServer framework.
	Custom servers must inherit from this object to be compatible. When
	no *address* parameter is specified the address '0.0.0.0' is used and
	the port is guessed based on if the server is run as root or not and
	SSL is used.
	"""
	def __init__(self, RequestHandler, address=None, use_threads=True, ssl_certfile=None, ssl_keyfile=None, ssl_version=None):
		"""
		:param RequestHandler: The request handler class to use.
		:type RequestHandler: :py:class:`.AdvancedHTTPServerRequestHandler`
		:param tuple address: The address to bind to in the format (host, port).
		:param bool use_threads: Whether to enable the use of a threaded handler.
		:param str ssl_certfile: An SSL certificate file to use, setting this enables SSL.
		:param str ssl_keyfile: An SSL certificate file to use.
		:param ssl_version: The SSL protocol version to use.
		"""
		self.use_ssl = bool(ssl_certfile)
		if address is None:
			if self.use_ssl:
				if os.getuid():
					address = ('0.0.0.0', 8443)
				else:
					address = ('0.0.0.0', 443)
			else:
				if os.getuid():
					address = ('0.0.0.0', 8080)
				else:
					address = ('0.0.0.0', 80)
		self.address = address
		self.ssl_certfile = ssl_certfile
		self.ssl_keyfile = ssl_keyfile
		if not hasattr(self, 'logger'):
			self.logger = logging.getLogger('AdvancedHTTPServer')
		self.server_started = False

		if use_threads:
			self.http_server = AdvancedHTTPServerThreaded(address, RequestHandler)
		else:
			self.http_server = AdvancedHTTPServerNonThreaded(address, RequestHandler)
		self.logger.info('listening on ' + address[0] + ':' + str(address[1]))

		if self.use_ssl:
			if ssl_version is None or isinstance(ssl_version, str):
				ssl_version = resolve_ssl_protocol_version(ssl_version)
			self.http_server.socket = ssl.wrap_socket(self.http_server.socket, keyfile=ssl_keyfile, certfile=ssl_certfile, server_side=True, ssl_version=ssl_version)
			self.http_server.using_ssl = True
			self.logger.info(address[0] + ':' + str(address[1]) + ' - ssl has been enabled')

		if hasattr(RequestHandler, 'custom_authentication'):
			self.logger.debug(address[0] + ':' + str(address[1]) + ' - a custom authentication function is being used')
			self.auth_set(True)

	def serve_forever(self, fork=False):
		"""
		Start handling requests. This method must be called and does not
		return unless the :py:meth:`.shutdown` method is called from
		another thread.

		:param bool fork: Whether to fork or not before serving content.
		"""
		if fork:
			if not hasattr(os, 'fork'):
				raise OSError('os.fork is not available')
			child_pid = os.fork()
			if child_pid != 0:
				self.logger.info(self.address[0] + ':' + str(self.address[1]) + ' - forked child process: ' + str(child_pid))
				return child_pid
		self.server_started = True
		self.http_server.serve_forever()
		return 0

	def shutdown(self):
		"""Shutdown the server and stop responding to requests."""
		if self.server_started:
			self.http_server.shutdown()

	@property
	def serve_files(self):
		"""
		Whether to enable serving files or not.

		:type: bool
		"""
		return self.http_server.serve_files

	@serve_files.setter
	def serve_files(self, value):
		value = bool(value)
		if self.http_server.serve_files == value:
			return
		self.http_server.serve_files = value
		if value:
			self.logger.info(self.address[0] + ':' + str(self.address[1]) + ' - serving files has been enabled')
		else:
			self.logger.info(self.address[0] + ':' + str(self.address[1]) + ' - serving files has been disabled')

	@property
	def serve_files_root(self):
		"""
		The web root to use when serving files.

		:type: str
		"""
		return self.http_server.serve_files_root

	@serve_files_root.setter
	def serve_files_root(self, value):
		self.http_server.serve_files_root = os.path.abspath(value)

	@property
	def serve_files_list_directories(self):
		"""
		Whether to list the contents of directories. This is only honored
		when :py:attr:`.serve_files` is True.

		:type: bool
		"""
		return self.http_server.serve_files_list_directories

	@serve_files_list_directories.setter
	def serve_files_list_directories(self, value):
		self.http_server.serve_files_list_directories = bool(value)

	@property
	def serve_robots_txt(self):
		"""
		Whether to serve a default robots.txt file which denies everything.

		:type: bool
		"""
		return self.http_server.serve_robots_txt

	@serve_robots_txt.setter
	def serve_robots_txt(self, value):
		self.http_server.serve_robots_txt = bool(value)

	@property
	def rpc_hmac_key(self):
		"""
		An HMAC key to be used for authenticating RPC requests.

		:type: str
		"""
		return self.http_server.rpc_hmac_key

	@rpc_hmac_key.setter
	def rpc_hmac_key(self, value):
		if not value:
			self.http_server.rpc_hmac_key = None
			return
		self.http_server.rpc_hmac_key = value.encode('UTF-8')

	@property
	def server_version(self):
		"""
		The server version to be sent to clients in headers.

		:type: str
		"""
		return self.http_server.server_version

	@server_version.setter
	def server_version(self, value):
		self.http_server.server_version = str(value)

	def auth_set(self, status):
		"""
		Enable or disable requring authentication on all incoming requests.

		:param bool status: Whether to enable or disable requiring authentication.
		"""
		if not bool(status):
			self.http_server.basic_auth = None
			self.logger.info(self.address[0] + ':' + str(self.address[1]) + ' - basic authentication has been disabled')
		else:
			self.http_server.basic_auth = {}
			self.logger.info(self.address[0] + ':' + str(self.address[1]) + ' - basic authentication has been enabled')

	def auth_delete_creds(self, username=None):
		"""
		Delete the credentials for a specific username if specified or all
		stored credentials.

		:param str username: The username of the credentials to delete.
		"""
		if not username:
			self.http_server.basic_auth = {}
			self.logger.info(self.address[0] + ':' + str(self.address[1]) + ' - basic authentication database has been cleared of all entries')
			return
		del self.http_server.basic_auth[username]

	def auth_add_creds(self, username, password, pwtype='plain'):
		"""
		Add a valid set of credentials to be accepted for authentication.
		Calling this function will automatically enable requiring
		authentication. Passwords can be provided in either plaintext or
		as a hash by specifying the hash type in the *pwtype* argument.

		:param str username: The username of the credentials to be added.
		:param password: The password data of the credentials to be added.
		:type password: bytes, str
		:param str pwtype: The type of the *password* data, (plain, md5, sha1, etc.).
		"""
		if not isinstance(password, (bytes, str)):
			raise TypeError("auth_add_creds() argument 2 must be bytes or str, not {0}".format(type(password).__name__))
		pwtype = pwtype.lower()
		if not pwtype in ('plain', 'md5', 'sha1', 'sha256', 'sha384', 'sha512'):
			raise ValueError('invalid password type, must be \'plain\', or supported by hashlib')
		if self.http_server.basic_auth is None:
			self.http_server.basic_auth = {}
			self.logger.info(self.address[0] + ':' + str(self.address[1]) + ' - basic authentication has been enabled')
		if pwtype != 'plain':
			algorithms_available = getattr(hashlib, 'algorithms_available', ()) or getattr(hashlib, 'algorithms', ())
			if not pwtype in algorithms_available:
				raise ValueError('hashlib does not support the desired algorithm')
			# only md5 and sha1 hex for backwards compatibility
			if pwtype == 'md5' and len(password) == 32:
				password = binascii.unhexlify(password)
			elif pwtype == 'sha1' and len(password) == 40:
				password = binascii.unhexlify(password)
			if not isinstance(password, bytes):
				password = password.encode('UTF-8')
			if len(hashlib.new(pwtype, b'foobar').digest()) != len(password):
				raise ValueError('the length of the password hash does not match the type specified')
		self.http_server.basic_auth[username] = {'value': password, 'type': pwtype}

class AdvancedHTTPServerTestCase(unittest.TestCase):
	"""
	A base class for unit tests with AdvancedHTTPServer derived classes.
	"""
	server_class = AdvancedHTTPServer
	"""The :py:class:`.AdvancedHTTPServer` class to use as the server, this can be overridden by subclasses."""
	handler_class = AdvancedHTTPServerRequestHandler
	"""The :py:class:`.AdvancedHTTPServerRequestHandler` class to use as the request handler, this can be overridden by subclasses."""
	config_section = 'server'
	"""The name of the :py:class:`configparser.ConfigParser` section that the server is using."""
	def __init__(self, *args, **kwargs):
		super(AdvancedHTTPServerTestCase, self).__init__(*args, **kwargs)
		config = ConfigParser()
		config.add_section(self.config_section)
		config.set(self.config_section, 'ip', '127.0.0.1')
		config.set(self.config_section, 'port', str(random.randint(30000, 50000)))
		self.config = config
		"""
		The :py:class:`configparser.ConfigParser` object used by the server.
		It has the ip and port options configured in the section named in
		the :py:attr:`.config_section` attribute.
		"""
		self.test_resource = "/{0}".format(random_string(40))
		"""
		A resource which has a handler set to it which will respond with
		a 200 status code and the message 'Hello World!'
		"""
		if hasattr(self, 'assertRegexpMatches') and not hasattr(self, 'assertRegexMatches'):
			self.assertRegexMatches = self.assertRegexpMatches
		if hasattr(self, 'assertRaisesRegexp') and not hasattr(self, 'assertRaisesRegex'):
			self.assertRaisesRegex = self.assertRaisesRegexp

	def setUp(self):
		AdvancedHTTPServerRegisterPath("^{0}$".format(self.test_resource[1:]), self.handler_class.__name__)(self._test_resource_handler)
		self.server = build_server_from_config(self.config, self.config_section, self.server_class, self.handler_class)
		self.assertTrue(isinstance(self.server, AdvancedHTTPServer))
		self.server_thread = threading.Thread(target=self.server.serve_forever)
		self.server_thread.daemon = True
		self.server_thread.start()
		self.assertTrue(self.server_thread.is_alive())
		self.shutdown_requested = False
		self.server_address = (self.config.get(self.config_section, 'ip'), self.config.getint(self.config_section, 'port'))
		self.http_connection = http.client.HTTPConnection(self.server_address[0], self.server_address[1])

	def _test_resource_handler(self, handler, query):
		del query
		handler.send_response(200)
		handler.end_headers()
		message = b'Hello World!\r\n\r\n'
		handler.send_response(200)
		handler.send_header('Content-Length', len(message))
		handler.end_headers()
		handler.wfile.write(message)
		return

	def assertHTTPStatus(self, http_response, status):
		"""
		Check an HTTP response object and ensure the status is correct.

		:param http_response: The response object to check.
		:type http_response: :py:class:`http.client.HTTPResponse`
		:param int status: The status code to expect for *http_response*.
		"""
		self.assertTrue(isinstance(http_response, http.client.HTTPResponse))
		error_message = "HTTP Response received status {0} when {1} was expected".format(http_response.status, status)
		self.assertEqual(http_response.status, status, msg=error_message)

	def http_request(self, resource, method='GET', headers=None):
		"""
		Make an HTTP request to the test server and return the response.

		:param str resource: The resource to issue the request to.
		:param str method: The HTTP verb to use (GET, HEAD, POST etc.).
		:param dict headers: The HTTP headers to provide in the request.
		:return: The HTTP response object.
		:rtype: :py:class:`http.client.HTTPResponse`
		"""
		headers = (headers or {})
		self.http_connection.request(method, resource, headers=headers)
		time.sleep(0.025)
		response = self.http_connection.getresponse()
		return response

	def tearDown(self):
		if not self.shutdown_requested:
			self.assertTrue(self.server_thread.is_alive())
		self.http_connection.close()
		self.server.shutdown()
		self.server_thread.join(5.0)
		self.assertFalse(self.server_thread.is_alive())
		del self.server

def main():
	try:
		server = build_server_from_argparser()
	except ImportError:
		server = AdvancedHTTPServer(AdvancedHTTPServerRequestHandler)
		server.serve_files_root = '.'

	server.serve_files_root = (server.serve_files_root or '.')
	server.serve_files = True
	try:
		server.serve_forever()
	except KeyboardInterrupt:
		pass
	server.shutdown()
	logging.shutdown()
	return 0

if __name__ == '__main__':
	main()
