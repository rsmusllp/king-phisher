import contextlib
import os
import random
import shutil
import sqlite3
import string
import threading

import pam
from AdvancedHTTPServer import *

from king_phisher.server import database

__version__ = '0.0.1'

make_uid = lambda: ''.join(random.choice(string.ascii_letters + string.digits) for x in range(24))

class KingPhisherRequestHandler(AdvancedHTTPServerRequestHandler):
	def install_handlers(self):
		self.database = self.server.database
		self.database_lock = threading.Lock()
		self.config = self.server.config
		self.rpc_handler_map['/ping'] = self.rpc_ping
		self.rpc_handler_map['/campaign/list'] = self.rpc_campaign_list
		self.rpc_handler_map['/campaign/new'] = self.rpc_campaign_new
		self.rpc_handler_map['/campaign/message/new'] = self.rpc_campaign_message_new
		self.rpc_handler_map['/campaign/visits/view'] = self.rpc_campaign_visits_view
		self.rpc_handler_map['/message/get'] = self.rpc_message_get

	@contextlib.contextmanager
	def get_cursor(self):
		cursor = self.database.cursor()
		self.database_lock.acquire()
		yield cursor
		self.database.commit()
		self.database_lock.release()

	def do_GET(self, *args, **kwargs):
		self.server.throttle_semaphore.acquire()
		try:
			super(self.__class__, self).do_GET(*args, **kwargs)
		except:
			raise
		finally:
			self.server.throttle_semaphore.release()

	def do_POST(self, *args, **kwargs):
		self.server.throttle_semaphore.acquire()
		try:
			super(self.__class__, self).do_POST(*args, **kwargs)
		except:
			raise
		finally:
			self.server.throttle_semaphore.release()

	def do_RPC(self, *args, **kwargs):
		self.server.throttle_semaphore.acquire()
		try:
			super(self.__class__, self).do_RPC(*args, **kwargs)
		except:
			raise
		finally:
			self.server.throttle_semaphore.release()

	def custom_authentication(self, username, password):
		return pam.authenticate(username, password)

	def check_authorization(self):
		if self.command in ['GET', 'POST']:
			return True
		if self.client_address[0] != '127.0.0.1':
			return False
		return super(self.__class__, self).check_authorization()

	def respond_file(self, file_path, attachment = False, query = {}):
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

		get_query_parameter = lambda p: query.get(p, [None])[0]
		msg_id = get_query_parameter('id')
		if msg_id:
			try:
				self.handle_visit(query, msg_id)
			except Exception as err:
				# TODO: log execeptions here
				pass

		self.end_headers()
		shutil.copyfileobj(file_obj, self.wfile)
		file_obj.close()
		return

	def handle_visit(self, query, msg_id):
		with self.get_cursor() as cursor:
			cursor.execute('SELECT campaign_id FROM messages WHERE id = ?', (msg_id,))
			campaign_id = cursor.fetchone()
			if not campaign_id:
				return
			campaign_id = campaign_id[0]

		get_query_parameter = lambda p: query.get(p, [None])[0]
		kp_cookie_name = self.config.get('cookie_name', 'KPID')
		if not kp_cookie_name in self.cookies:
			visit_id = make_uid()
			cookie = "{0}={1}; Path=/; HttpOnly".format(kp_cookie_name, visit_id)
			self.send_header('Set-Cookie', cookie)
			with self.get_cursor() as cursor:
				client_ip = self.client_address[0]
				user_agent = (self.headers.getheader('user-agent') or '')
				cursor.execute('INSERT INTO visits (id, message_id, campaign_id, visitor_ip, visitor_details) VALUES (?, ?, ?, ?, ?)', (visit_id, msg_id, campaign_id, client_ip, user_agent))
		else:
			visit_id = self.cookies[kp_cookie_name].value
			with self.get_cursor() as cursor:
				cursor.execute('UPDATE visits SET visit_count = visit_count + 1, last_visit = CURRENT_TIMESTAMP WHERE id = ?', (visit_id,))

		username = (get_query_parameter('username') or get_query_parameter('user') or get_query_parameter('u'))
		if not username:
			return
		password = (get_query_parameter('password') or get_query_parameter('pass') or get_query_parameter('p'))
		password = (password or '')
		with self.get_cursor() as cursor:
			cursor.execute('INSERT INTO credentials (visit_id, username, password) VALUES (?, ?, ?)', (visit_id, username, password))

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

	def rpc_message_get(self, message_id):
		with self.get_cursor() as cursor:
			columns = ['campaign_id', 'target_email', 'sent']
			cursor.execute('SELECT ' + ', '.join(columns) + ' FROM messages WHERE id = ?', (message_id,))
			message = cursor.fetchone()
			if message:
				message = dict(zip(columns, message))
		return message

	def rpc_campaign_visits_view(self, campaign_id, page = 0):
		visits = []
		offset = 25 * page
		columns = ['id', 'message_id', 'visit_count', 'visitor_ip', 'visitor_details', 'first_visit', 'last_visit']
		with self.get_cursor() as cursor:
			for row in cursor.execute('SELECT ' + ', '.join(columns) + ' FROM visits WHERE campaign_id = ? LIMIT 25 OFFSET ?', (campaign_id, offset)):
				visit = dict(zip(columns, row))
				visits.append(visit)
		if not len(visits):
			return None
		return visits


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
