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
#  * Neither the name of the  nor the names of its
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

import select
import SocketServer
import threading

import paramiko

__all__ = ['SSHTCPForwarder']

class ForwardServer(SocketServer.ThreadingTCPServer):
	daemon_threads = True
	allow_reuse_address = True
	def __init__(self, remote_server, ssh_transport, *args, **kwargs):
		self.remote_server = remote_server
		self.ssh_transport = ssh_transport
		SocketServer.ThreadingTCPServer.__init__(self, *args, **kwargs)

class ForwardHandler(SocketServer.BaseRequestHandler):
	def __init__(self, *args, **kwargs):
		self.server = args[2]
		self.chain_host = self.server.remote_server[0]
		self.chain_port = self.server.remote_server[1]
		self.ssh_transport = self.server.ssh_transport
		SocketServer.BaseRequestHandler.__init__(self, *args, **kwargs)

	def handle(self):
		try:
			chan = self.ssh_transport.open_channel('direct-tcpip', (self.chain_host, self.chain_port), self.request.getpeername())
		except Exception as err:
			return
		if chan is None:
			return
		while True:
			r, w, x = select.select([self.request, chan], [], [])
			if self.request in r:
				data = self.request.recv(1024)
				if len(data) == 0:
					break
				chan.send(data)
			if chan in r:
				data = chan.recv(1024)
				if len(data) == 0:
					break
				self.request.send(data)

		peername = self.request.getpeername()
		chan.close()
		self.request.close()

class SSHTCPForwarder(threading.Thread):
	def __init__(self, server, username, password, local_port, remote_server):
		super(SSHTCPForwarder, self).__init__()
		self.local_port = local_port
		self.server = server
		self.remote_server = remote_server
		client = paramiko.SSHClient()
		client.load_system_host_keys()
		client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
		client.connect(server[0], server[1], username = username, look_for_keys = True, key_filename = None, password = password)
		self.client = client

	def run(self):
		transport = self.client.get_transport()
		self.server = ForwardServer(self.remote_server, transport, ('', self.local_port), ForwardHandler)
		self.server.serve_forever()

	def stop(self):
		if isinstance(self.server, ForwardServer):
			self.server.shutdown()
			self.join()
		self.client.close()
