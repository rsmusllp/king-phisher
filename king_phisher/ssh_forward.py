#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  king_phisher/ssh_forward.py
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

import binascii
import hashlib
import io
import logging
import os
import select
import socket
import sys
import threading
import time

from king_phisher import errors

import paramiko

if sys.version_info[0] < 3:
	import SocketServer as socketserver
else:
	import socketserver

__all__ = ('KingPhisherSSHKeyError', 'SSHTCPForwarder',)

class KingPhisherSSHKeyError(errors.KingPhisherError):
	"""
	An exception that is thrown when there is a problem resolving a users SSH
	key file. The *message* attribute is formatted to be displayed to the user
	via a dialog.
	"""
	pass

class ForwardServer(socketserver.ThreadingTCPServer):
	daemon_threads = True
	allow_reuse_address = True
	def __init__(self, remote_server, ssh_transport, *args, **kwargs):
		self.remote_server = remote_server
		self.ssh_transport = ssh_transport
		socketserver.ThreadingTCPServer.__init__(self, *args, **kwargs)

class ForwardHandler(socketserver.BaseRequestHandler):
	def __init__(self, *args, **kwargs):
		self.server = args[2]
		self.chain_host = self.server.remote_server[0]
		self.chain_port = self.server.remote_server[1]
		self.ssh_transport = self.server.ssh_transport
		socketserver.BaseRequestHandler.__init__(self, *args, **kwargs)

	def handle(self):
		try:
			channel = self.ssh_transport.open_channel('direct-tcpip', (self.chain_host, self.chain_port), self.request.getpeername())
		except paramiko.ChannelException:
			channel = None
		if channel is None:
			return
		try:
			self._handle(channel)
		except socket.error:
			pass
		channel.close()
		self.request.close()

	def _handle(self, channel):
		while True:
			read_ready, _, _ = select.select([self.request, channel], [], [])
			if self.request in read_ready:
				data = self.request.recv(1024)
				if len(data) == 0:
					break
				channel.send(data)
			if channel in read_ready:
				data = channel.recv(1024)
				if len(data) == 0:
					break
				self.request.send(data)

class SSHTCPForwarder(threading.Thread):
	"""
	Open an SSH connection and forward TCP traffic through it to a remote host.
	A private key for authentication can be specified as a string either by it's
	OpenSSH fingerprint, as a file (prefixed with "file:"), or a raw key string
	(prefixed with "key:"). If no *missing_host_key_policy* is specified,
	:py:class:`paramiko.client.AutoAddPolicy` will be used to accept all host
	keys.

	.. note::
		This is a :py:class:`threading.Thread` object and needs to be started
		with a call to :py:meth:`~threading.Thread.start` after it is initialized.
	"""
	def __init__(self, server, username, password, remote_server, local_port=0, private_key=None, missing_host_key_policy=None):
		"""
		:param tuple server: The SSH server to connect to.
		:param str username: The username to authenticate with.
		:param str password: The password to authenticate with.
		:param tuple remote_server: The remote server to connect to through the specified SSH server.
		:param int local_port: The local port to forward, if not set a random one will be used.
		:param str private_key: An RSA key to prefer for authentication.
		:param missing_host_key_policy: The policy to use for missing host keys.
		"""
		super(SSHTCPForwarder, self).__init__()
		self.logger = logging.getLogger('KingPhisher.' + self.__class__.__name__)
		self.server = (server[0], int(server[1]))
		self.remote_server = (remote_server[0], int(remote_server[1]))
		client = paramiko.SSHClient()
		if missing_host_key_policy is None:
			missing_host_key_policy = paramiko.AutoAddPolicy()
		elif isinstance(missing_host_key_policy, paramiko.RejectPolicy):
			self.logger.info('reject policy in place, loading system host keys')
			client.load_system_host_keys()
		client.set_missing_host_key_policy(missing_host_key_policy)
		self.client = client
		self.username = username
		self.__connected = False

		# an issue seems to exist in paramiko when multiple keys are present through the ssh-agent
		agent_keys = paramiko.Agent().get_keys()

		if not self.__connected and private_key:
			private_key = self.__resolve_private_key(private_key, agent_keys)
			if private_key:
				self.logger.debug('attempting ssh authentication with user specified key')
				self.__try_connect(look_for_keys=False, pkey=private_key)
			else:
				self.logger.warning('failed to identify the user specified key for ssh authentication')

		if not self.__connected and len(agent_keys) == 1:
			self.__try_connect(look_for_keys=False, pkey=agent_keys[0])

		if not self.__connected:
			self.__try_connect(password=password, look_for_keys=True, raise_error=True)

		transport = self.client.get_transport()
		self._forward_server = ForwardServer(self.remote_server, transport, ('127.0.0.1', local_port), ForwardHandler)

	def __repr__(self):
		return "<{0} ({1}) >".format(self.__class__.__name__, str(self))

	def __str__(self):
		local_server = "{0}:{1}".format(*self.local_server)
		remote_server = "{0}:{1}".format(*self.remote_server)
		server = "{0}:{1}".format(*self.server)
		return "{0} to {1} via {2}".format(local_server, remote_server, server)

	def __resolve_private_key(self, private_key, agent_keys):
		private_key = private_key.strip()
		pkey_type = private_key.split(':', 1)[0].lower()
		if pkey_type in ('file', 'key'):
			if pkey_type == 'file':
				file_path = os.path.expandvars(private_key[5:])
				if not os.access(file_path, os.R_OK):
					self.logger.warning("the user specified ssh key file '{0}' can not be opened".format(file_path))
					raise KingPhisherSSHKeyError('The SSH key file can not be opened.')
				self.logger.debug('loading the user specified ssh key file: ' + file_path)
				file_h = open(file_path, 'r')
				first_line = file_h.readline()
				file_h.seek(0, os.SEEK_SET)
			else:
				self.logger.debug('loading the user specified ssh key string from memory')
				key_str = private_key[4:]
				file_h = io.StringIO(key_str)
				first_line = key_str.split('\n', 1)[0]

			if 'BEGIN DSA PRIVATE KEY' in first_line:
				KeyKlass = paramiko.DSSKey
			elif 'BEGIN RSA PRIVATE KEY' in first_line:
				KeyKlass = paramiko.RSAKey
			else:
				file_h.close()
				self.logger.warning('the user specified ssh key does not appear to be a valid dsa or rsa private key')
				raise KingPhisherSSHKeyError('The SSH key file is not a DSA or RSA private key.')
			try:
				private_key = KeyKlass.from_private_key(file_h)
			except paramiko.PasswordRequiredException:
				self.logger.warning('the user specified ssh key is encrypted and requires a password')
				raise
			finally:
				file_h.close()
			return private_key
		# if the key has whitespace, discard anything after the first occurrence
		private_key = private_key.split(' ', 1)[0]

		# if it's not one of the above, treat it like it's a fingerprint
		if pkey_type == 'sha256':
			# OpenSSH 6.8 started to use sha256 & base64 for keys
			algorithm = pkey_type
			private_key = private_key[7:]
			private_key = binascii.a2b_base64(private_key + '=')
		else:
			algorithm = 'md5'
			private_key = private_key.replace(':', '')
			private_key = binascii.a2b_hex(private_key)
		private_key = tuple(key for key in agent_keys if hashlib.new(algorithm, key.blob).digest() == private_key)
		if not private_key:
			self.logger.warning('the user specified ssh key could not be loaded from the ssh agent')
			raise KingPhisherSSHKeyError('The SSH key could not be loaded from the SSH agent.')
		return private_key[0]

	def __try_connect(self, *args, **kwargs):
		raise_error = kwargs.pop('raise_error', False)
		try:
			self.client.connect(self.server[0], self.server[1], username=self.username, allow_agent=False, timeout=12.0, *args, **kwargs)
		except paramiko.PasswordRequiredException:
			raise
		except paramiko.AuthenticationException as error:
			if raise_error:
				raise error
			return False
		self.__connected = True
		return True

	@property
	def local_server(self):
		"""
		A tuple representing the local address of the listening service which is
		forwarding traffic to the specified remote host.
		"""
		return self._forward_server.server_address

	def run(self):
		self.logger.debug("ssh port forwarding running in tid: 0x{0:x}".format(threading.current_thread().ident))
		self._forward_server.serve_forever()

	def start(self):
		super(SSHTCPForwarder, self).start()
		time.sleep(0.5)
		self.logger.info("started ssh port forwarding to the remote server ({0})".format(str(self)))

	def stop(self):
		if isinstance(self._forward_server, ForwardServer):
			self._forward_server.shutdown()
			self.join()
		self.client.close()
		self.logger.info("stopped ssh port forwarding to the remote server ({0})".format(str(self)))
