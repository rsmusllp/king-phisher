import sqlite3

from AdvancedHTTPServer import *

__version__ = '0.0.1'

class KingPhisherRequestHandler(AdvancedHTTPServerRequestHandler):
	def install_handlers(self):
		if not self.server.database:
			return
		self.rpc_handler_map['/ping'] = self.rpc_ping

	def check_authorization(self):
		if self.command in ['GET', 'POST']:
			return True
		return super(self.__class__, self).check_authorization()

	def rpc_ping(self):
		return True

class KingPhisherServer(AdvancedHTTPServer):
	def __init__(self, *args, **kwargs):
		super(KingPhisherServer, self).__init__(*args, **kwargs)
		self.database = None

	def load_database(self, database):
		database = sqlite3.connect(database)
		self.http_server.database = database
		self.database = database
		self.load_accounts()

	def load_accounts(self):
		cursor = self.database.cursor()
		# clears the authentication database
		self.auth_delete_creds()
		for username, password in cursor.execute('SELECT username, password FROM accounts'):
			self.auth_add_creds(username, password, pwtype = 'sha1')
