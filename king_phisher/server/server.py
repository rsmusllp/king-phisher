import contextlib
import random
import sqlite3
import string

import pam
from AdvancedHTTPServer import *

from king_phisher.server import database

__version__ = '0.0.1'

make_uid = lambda: ''.join(random.choice(string.ascii_letters + string.digits) for x in range(24))

class KingPhisherRequestHandler(AdvancedHTTPServerRequestHandler):
	def install_handlers(self):
		if not self.server.database:
			return
		self.database = self.server.database
		self.rpc_handler_map['/ping'] = self.rpc_ping
		self.rpc_handler_map['/campaign/list'] = self.rpc_campaign_list
		self.rpc_handler_map['/campaign/new'] = self.rpc_campaign_new

		self.rpc_handler_map['/campaign/message/new'] = self.rpc_campaign_message_new

	@contextlib.contextmanager
	def get_cursor(self):
		cursor = self.database.cursor()
		yield cursor
		self.database.commit()

	def custom_authentication(self, username, password):
		return pam.authenticate(username, password)

	def check_authorization(self):
		if self.command in ['GET', 'POST']:
			return True
		if self.client_address[0] != '127.0.0.1':
			return False
		return super(self.__class__, self).check_authorization()

	def rpc_ping(self):
		return True

	def rpc_campaign_list(self):
		with self.get_cursor() as cursor:
			cursor.execute('SELECT id, name FROM campaigns')
			campaigns = cursor.fetchall()
		return dict(campaigns)

	def rpc_campaign_new(self, name):
		with self.get_cursor() as cursor:
			cursor.execute('INSERT INTO campaigns (name) VALUES (?)', (name,))
			cursor.execute('SELECT id FROM campaigns WHERE name = ?', (name,))
			campaign_id = cursor.fetchone()[0]
		return campaign_id

	def rpc_campaign_message_new(self, campaign_id, email_id, email_target):
		with self.get_cursor() as cursor:
			cursor.execute('INSERT INTO messages (id, campaign_id, target_email) VALUES (?, ?, ?)', (email_id, campaign_id, email_target))
		return

class KingPhisherServer(AdvancedHTTPServer):
	def __init__(self, *args, **kwargs):
		super(KingPhisherServer, self).__init__(*args, **kwargs)
		self.database = None

	def load_database(self, database_file):
		if database_file == ':memory:':
			db = database.create_database(database_file)
		else:
			db = sqlite3.connect(database_file, check_same_thread = False)
		self.database = db
		self.http_server.database = db
