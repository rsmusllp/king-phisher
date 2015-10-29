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
import select
import socket
import sys
import threading
import time

import paramiko

if sys.version_info[0] < 3:
	import SocketServer as socketserver
else:
	import socketserver

__all__ = ('SSHTCPForwarder',)

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
			chan = self.ssh_transport.open_channel('direct-tcpip', (self.chain_host, self.chain_port), self.request.getpeername())
		except paramiko.ChannelException:
			chan = None
		if chan is None:
			return
		while True:
			read_ready, _, _ = select.select([self.request, chan], [], [])
			if self.request in read_ready:
				data = self.request.recv(1024)
				if len(data) == 0:
					break
				chan.send(data)
			if chan in read_ready:
				data = chan.recv(1024)
				if len(data) == 0:
					break
				self.request.send(data)

		chan.close()
		self.request.close()

class SSHTCPForwarder(threading.Thread):
	"""
	Open an SSH connection and forward TCP traffic through it. This is
	a :py:class:`threading.Thread` object and needs to be started after
	it is initialized.
	"""
	def __init__(self, server, username, password, remote_server, local_port=0, preferred_private_key=None):
		"""
		:param tuple server: The server to connect to.
		:param str username: The username to authenticate with.
		:param str password: The password to authenticate with.
		:param tuple remote_server: The remote server to connect to through the SSH server.
		:param int local_port: The local port to forward, if not set a random one will be used.
		:param str preferred_private_key: An RSA key to prefer for authentication.
		"""
		super(SSHTCPForwarder, self).__init__()
		self.server = (server[0], int(server[1]))
		self.remote_server = (remote_server[0], int(remote_server[1]))
		client = paramiko.SSHClient()
		client.load_system_host_keys()
		client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
		self.client = client
		self.username = username
		self.__connected = False

		# an issue seems to exist in paramiko when multiple keys are present through the ssh-agent
		ssh_agent = paramiko.Agent()
		ssh_keys = ssh_agent.get_keys()
		if len(ssh_keys) == 1:
			self.__try_connect(look_for_keys=False, pkey=ssh_keys[0])

		if not self.__connected and preferred_private_key:
			preferred_private_key = preferred_private_key.strip()
			preferred_private_key = preferred_private_key.replace(':', '')
			preferred_private_key = preferred_private_key.lower()
			preferred_private_key = tuple(key for key in ssh_keys if binascii.b2a_hex(key.get_fingerprint()).lower() == preferred_private_key)
			if len(preferred_private_key) == 1:
				self.__try_connect(look_for_keys=False, pkey=preferred_private_key[0])

		if not self.__connected:
			self.__try_connect(password=password, look_for_keys=True, raise_error=True)

		transport = self.client.get_transport()
		self._forward_server = ForwardServer(self.remote_server, transport, ('127.0.0.1', local_port), ForwardHandler)

	def __repr__(self):
		return "<{0} {1} >".format(str(self))

	def __str__(self):
		local_server = "{0}:{1}".format(*self.local_server)
		remote_server = "{0}:{1}".format(*self.remote_server)
		server = "{0}:{1}".format(*self.server)
		return "{0} -> {1} via {2}".format(local_server, remote_server, server)

	def __try_connect(self, *args, **kwargs):
		raise_error = False
		if 'raise_error' in kwargs:
			raise_error = kwargs['raise_error']
			del kwargs['raise_error']
		try:
			self.client.connect(self.server[0], self.server[1], username=self.username, allow_agent=False, timeout=12.0, *args, **kwargs)
		except (paramiko.SSHException, socket.timeout) as error:
			if raise_error:
				raise error
			return False
		self.__connected = True
		return True

	@property
	def local_server(self):
		return self._forward_server.server_address

	def run(self):
		self._forward_server.serve_forever()

	def start(self):
		super(SSHTCPForwarder, self).start()
		time.sleep(0.5)

	def stop(self):
		if isinstance(self._forward_server, ForwardServer):
			self._forward_server.shutdown()
			self.join()
		self.client.close()
