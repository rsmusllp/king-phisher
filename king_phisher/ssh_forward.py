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
		client.set_missing_host_key_policy(paramiko.WarningPolicy())
		client.connect(server[0], server[1], username=username, look_for_keys=True, key_filename= None, password=password)
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
