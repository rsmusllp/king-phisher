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
import collections
import datetime
import json
import logging
import os
import re
import shutil
import threading
import weakref

from king_phisher import errors
from king_phisher import find
from king_phisher import geoip
from king_phisher import ipaddress
from king_phisher import templates
from king_phisher import utilities
from king_phisher import xor
from king_phisher.server import aaa
from king_phisher.server import pages
from king_phisher.server import rest_api
from king_phisher.server import server_rpc
from king_phisher.server import signals
from king_phisher.server import web_sockets
from king_phisher.server.database import manager as db_manager
from king_phisher.server.database import models as db_models

import advancedhttpserver
import jinja2
import smoke_zephyr.job
import smoke_zephyr.utilities

class LoggerAdapter(logging.LoggerAdapter):
	def process(self, message, kwargs):
		message = "{0} {message}".format(self.extra['client_address'], message=message)
		return message, kwargs

class KingPhisherRequestHandler(advancedhttpserver.RequestHandler):
	_logger = logging.getLogger('KingPhisher.Server.RequestHandler')
	def __init__(self, request, client_address, server, **kwargs):
		self.logger = LoggerAdapter(
			self._logger,
			{'client_address': client_address[0]}
		)
		self.logger.debug("tid: 0x{0:x} running http request handler".format(threading.current_thread().ident))
		# this is for attribute documentation
		self.config = None
		"""A reference to the main server instance :py:attr:`.KingPhisherServer.config`."""
		self.path = None
		"""The resource path of the current HTTP request."""
		self.rpc_session = None
		self.semaphore_acquired = False
		super(KingPhisherRequestHandler, self).__init__(request, client_address, server, **kwargs)

	def on_init(self):
		self.config = self.server.config
		regex_prefix = '^'
		if self.config.get('server.vhost_directories'):
			regex_prefix += r'[\w\.\-]+\/'
			for path, handler in self.handler_map.items():
				if path.startswith(rest_api.REST_API_BASE):
					del self.handler_map[path]
					self.handler_map[regex_prefix + path] = handler
		self.handler_map[regex_prefix + 'kpdd$'] = self.handle_deaddrop_visit
		self.handler_map[regex_prefix + 'kp\\.js$'] = self.handle_javascript_hook
		self.web_socket_handler = self.server.ws_manager.dispatch

		tracking_image = self.config.get('server.tracking_image')
		tracking_image = tracking_image.replace('.', '\\.')
		self.handler_map[regex_prefix + tracking_image + '$'] = self.handle_email_opened
		signals.send_safe('request-received', self.logger, self)

	def end_headers(self, *args, **kwargs):
		if self.command != 'RPC':
			for header, value in self.server.headers.items():
				self.send_header(header, value)
		return super(KingPhisherRequestHandler, self).end_headers(*args, **kwargs)

	def issue_alert(self, campaign_id, table, count):
		"""
		Send a campaign alert for the specified table.

		:param int campaign_id: The campaign subscribers to send the alert to.
		:param str table: The type of event to use as the sender when it is forwarded.
		:param int count: The number associated with the event alert.
		"""
		session = db_manager.Session()
		campaign = db_manager.get_row_by_id(session, db_models.Campaign, campaign_id)
		now = datetime.datetime.utcnow()
		alert_subscriptions = tuple(subscription for subscription in campaign.alert_subscriptions if subscription.mute_timestamp is None or subscription.mute_timestamp > now)
		if not alert_subscriptions:
			self.server.logger.debug("no active alert subscriptions are present for campaign id: {0} ({1})".format(campaign.id, campaign.name))
			session.close()
			return
		if not signals.campaign_alert.receivers:
			self.server.logger.warning('users are subscribed to campaign alerts, and no signal handlers are connected')
			session.close()
			return
		if not signals.campaign_alert.has_receivers_for(table):
			self.server.logger.info('users are subscribed to campaign alerts, and no signal handlers are connected for sender: ' + table)
			session.close()
			return

		for subscription in alert_subscriptions:
			results = signals.send_safe('campaign-alert', self.server.logger, table, alert_subscription=subscription, count=count)
			if any((result for (_, result) in results)):
				continue
			self.server.logger.warning("user {0} is subscribed to campaign alerts, and no signal handlers succeeded to send an alert".format(subscription.user.id))
		session.close()
		return

	def adjust_path(self):
		"""Adjust the :py:attr:`~.KingPhisherRequestHandler.path` attribute based on multiple factors."""
		self.request_path = self.path.split('?', 1)[0]
		if not self.config.get('server.vhost_directories'):
			return
		if not self.vhost:
			raise errors.KingPhisherAbortRequestError()
		if self.vhost in ('localhost', '127.0.0.1') and self.client_address[0] != '127.0.0.1':
			raise errors.KingPhisherAbortRequestError()
		self.path = '/' + self.vhost + self.path

	def semaphore_acquire(self):
		if self.semaphore_acquired:
			raise RuntimeError('the request semaphore has already been acquired')
		self.server.throttle_semaphore.acquire()
		self.semaphore_acquired = True

	def semaphore_release(self):
		if not self.semaphore_acquired:
			raise RuntimeError('the request semaphore has not been acquired')
		self.server.throttle_semaphore.release()
		self.semaphore_acquired = False

	def _do_http_method(self, *args, **kwargs):
		# This method wraps all of the default do_* HTTP verb handlers to
		# provide error handling and (for non-RPC requests) path adjustments.
		# This also is also a high level location where the throttle semaphore
		# is managed which is acquired for all RPC requests. Non-RPC requests
		# can acquire it as necessary and *should* release it when they are
		# finished with it, however if they fail to do so or encounter an error
		# the semaphore will be released here as a fail safe.
		self.connection.settimeout(smoke_zephyr.utilities.parse_timespan('20s'))  # set a timeout as a fail safe
		if self.command == 'RPC':
			self.semaphore_acquire()
		else:
			self.adjust_path()

		http_method_handler = None
		try:
			signals.request_handle.send(self)
			http_method_handler = getattr(super(KingPhisherRequestHandler, self), 'do_' + self.command)
			http_method_handler(*args, **kwargs)
		except errors.KingPhisherAbortRequestError as error:
			if http_method_handler is None:
				self.logger.debug('http request aborted by a signal handler')
			else:
				self.logger.info('http request aborted')
			if not error.response_sent:
				self.respond_not_found()
		finally:
			if self.semaphore_acquired:
				if self.command != 'RPC':
					self.logger.warning('http request failed to cleanly release resources')
				self.semaphore_release()
		self.connection.settimeout(None)

	do_GET = _do_http_method
	do_HEAD = _do_http_method
	do_POST = _do_http_method
	do_RPC = _do_http_method

	def do_OPTIONS(self):
		available_methods = list(x[3:] for x in dir(self) if x.startswith('do_'))
		if 'RPC' in available_methods:
			if not len(self.rpc_handler_map) or not ipaddress.ip_address(self.client_address[0]).is_loopback:
				self.logger.debug('removed RPC method from Allow header in OPTIONS reply')
				available_methods.remove('RPC')
		self.send_response(200)
		self.send_header('Content-Length', 0)
		self.send_header('Allow', ', '.join(available_methods))
		self.end_headers()

	def get_query_creds(self, check_query=True):
		"""
		Get credentials that have been submitted in the request. For credentials
		to be returned at least a username must have been specified. The
		returned username will be None or a non-empty string. The returned
		password will be None if the parameter was not found or a string which
		maybe empty. This functions checks the query data for credentials first
		if *check_query* is True, and then checks the contents of an
		Authorization header.

		:param bool check_query: Whether or not to check the query data in addition to an Authorization header.
		:return: The submitted credentials.
		:rtype: tuple
		"""
		username = None
		password = ''

		for pname in ('username', 'user', 'u', 'login'):
			username = (self.get_query(pname) or self.get_query(pname.title()) or self.get_query(pname.upper()))
			if username:
				break
		if username:
			for pname in ('password', 'pass', 'p'):
				password = (self.get_query(pname) or self.get_query(pname.title()) or self.get_query(pname.upper()))
				if password:
					break
			return username, (password or '')

		basic_auth = self.headers.get('authorization')
		if basic_auth is None:
			return None, ''
		basic_auth = basic_auth.split()
		if len(basic_auth) == 2 and basic_auth[0] == 'Basic':
			try:
				basic_auth = base64.b64decode(basic_auth[1])
			except TypeError:
				return None, ''
			basic_auth = basic_auth.decode('utf-8')
			basic_auth = basic_auth.split(':', 1)
			if len(basic_auth) == 2 and len(basic_auth[0]):
				username, password = basic_auth
		return username, password

	def get_template_vars(self):
		template_vars = {
			'client': self.get_template_vars_client(),
			'request': {
				'command': self.command,
				'cookies': dict((c[0], c[1].value) for c in self.cookies.items()),
				'headers': dict(self.headers),
				'parameters': dict(zip(self.query_data.keys(), map(self.get_query, self.query_data.keys()))),
				'user_agent': self.headers.get('user-agent')
			},
			'server': {
				'hostname': self.vhost,
				'address': self.connection.getsockname()[0]
			}
		}
		template_vars.update(self.server.template_env.standard_variables)
		return template_vars

	def get_template_vars_client(self):
		"""
		Build a dictionary of variables for a client with an associated
		campaign.

		:return: The client specific template variables.
		:rtype: dict
		"""
		client_vars = {
			'address': self.get_client_ip()
		}
		if not self.message_id:
			return client_vars
		credential_count = 0
		expired_campaign = True
		visit_count = 0
		result = None
		session = db_manager.Session()
		if self.message_id == self.config.get('server.secret_id'):
			client_vars['company_name'] = 'Wonderland Inc.'
			client_vars['company'] = {'name': 'Wonderland Inc.'}
			result = ('aliddle@wonderland.com', 'Alice', 'Liddle', 0)
		elif self.message_id:
			message = db_manager.get_row_by_id(session, db_models.Message, self.message_id)
			if message:
				campaign = message.campaign
				client_vars['campaign'] = {
					'id': str(campaign.id),
					'name': campaign.name,
					'created': campaign.created,
					'expiration': campaign.expiration,
					'has_expired': campaign.has_expired,
					'message_count': session.query(db_models.Message).filter_by(campaign_id=campaign.id).count(),
					'visit_count': session.query(db_models.Visit).filter_by(campaign_id=campaign.id).count(),
					'credential_count': session.query(db_models.Credential).filter_by(campaign_id=campaign.id).count(),
				}
				if message.campaign.company:
					client_vars['company_name'] = message.campaign.company.name
					client_vars['company'] = {
						'name': campaign.company.name,
						'url_email': campaign.company.url_email,
						'url_main': campaign.company.url_main,
						'url_remote_access': campaign.company.url_remote_access
					}
				result = (message.target_email, message.first_name, message.last_name, message.trained)
			query = session.query(db_models.Credential)
			query = query.filter_by(message_id=self.message_id)
			credential_count = query.count()
			expired_campaign = message.campaign.has_expired
		if not result:
			session.close()
			return client_vars

		client_vars['email_address'] = result[0]
		client_vars['first_name'] = result[1]
		client_vars['last_name'] = result[2]
		client_vars['is_trained'] = result[3]
		client_vars['message_id'] = self.message_id

		if self.visit_id:
			visit = db_manager.get_row_by_id(session, db_models.Visit, self.visit_id)
			client_vars['visit_id'] = visit.id
			visit_count = visit.visit_count

		# increment some counters preemptively
		if not expired_campaign and self.get_query_creds()[0] is not None:
			credential_count += 1
		client_vars['credential_count'] = credential_count
		client_vars['visit_count'] = visit_count + (0 if expired_campaign else 1)

		session.close()
		return client_vars

	def check_authorization(self):
		# don't require authentication for non-RPC requests
		cmd = self.command
		if cmd == 'GET':
			# check if the GET request is to open a web socket
			if 'upgrade' not in self.headers:
				return True
		elif cmd != 'RPC':
			return True

		if not ipaddress.ip_address(self.client_address[0]).is_loopback:
			return False

		# the only two RPC methods that do not require authentication
		if self.path in ('/login', '/version'):
			return True
		self.rpc_session = self.server.session_manager.get(self.rpc_session_id)
		if not isinstance(self.rpc_session, aaa.AuthenticatedSession):
			return False
		return True

	@property
	def rpc_session_id(self):
		return self.headers.get(server_rpc.RPC_AUTH_HEADER, None)

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
		msg_id = self.get_query('id')
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
		The visit id that is associated with the current request's visitor. This
		is retrieved by looking for the King Phisher cookie. If no cookie is
		set, this value is None.
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

	def get_client_ip(self):
		"""
		Intelligently get the IP address of the HTTP client, optionally
		accounting for proxies that may be in use.

		:return: The clients IP address.
		:rtype: str
		"""
		address = self.client_address[0]
		header_name = self.config.get_if_exists('server.client_ip_header')                 # new style
		header_name = header_name or self.config.get_if_exists('server.client_ip_cookie')  # old style
		if not header_name:
			return address
		header_value = self.headers.get(header_name, '')
		if not header_value:
			return address
		header_value = header_value.split(',')[0]
		header_value = header_value.strip()
		if header_value.startswith('['):
			# header_value looks like an IPv6 address
			header_value = header_value.split(']:', 1)[0]
		else:
			# treat header_value as an IPv4 address
			header_value = header_value.split(':', 1)[0]
		if ipaddress.is_valid(header_value):
			address = header_value
		return address

	def send_response(self, code, message=None):
		super(KingPhisherRequestHandler, self).send_response(code, message)
		signals.send_safe('response-sent', self.logger, self, code=code, message=message)

	def respond_file(self, file_path, attachment=False, query=None):
		self._respond_file_check_id()
		file_path = os.path.abspath(file_path)
		mime_type = self.guess_mime_type(file_path)
		if attachment or (mime_type != 'text/html' and mime_type != 'text/plain'):
			self._respond_file_raw(file_path, attachment)
			return
		try:
			template = self.server.template_env.get_template(os.path.relpath(file_path, self.config.get('server.web_root')))
		except jinja2.exceptions.TemplateSyntaxError as error:
			self.server.logger.error("jinja2 syntax error in template {0}:{1} {2}".format(error.filename, error.lineno, error.message))
			raise errors.KingPhisherAbortRequestError()
		except jinja2.exceptions.TemplateError:
			raise errors.KingPhisherAbortRequestError()
		except UnicodeDecodeError as error:
			self.server.logger.error("unicode error {0} in template file: {1}:{2}-{3}".format(error.reason, file_path, error.start, error.end))
			raise errors.KingPhisherAbortRequestError()

		self.semaphore_acquire()
		template_data = b''
		headers = []
		template_vars = self.get_template_vars()
		try:
			template_module = template.make_module(template_vars)
		except (TypeError, jinja2.TemplateError) as error:
			self.semaphore_release()
			self.server.logger.error("jinja2 template {0} render failed: {1} {2}".format(template.filename, error.__class__.__name__, error.message))
			raise errors.KingPhisherAbortRequestError()

		require_basic_auth = getattr(template_module, 'require_basic_auth', False)
		require_basic_auth &= not all(self.get_query_creds(check_query=False))
		require_basic_auth &= self.message_id != self.config.get('server.secret_id')
		if require_basic_auth:
			mime_type = 'text/html'
			self.send_response(401)
			headers.append(('WWW-Authenticate', "Basic realm=\"{0}\"".format(getattr(template_module, 'basic_auth_realm', 'Authentication Required'))))
		else:
			try:
				template_data = template.render(template_vars)
			except (TypeError, jinja2.TemplateError) as error:
				self.semaphore_release()
				self.server.logger.error("jinja2 template {0} render failed: {1} {2}".format(template.filename, error.__class__.__name__, error.message))
				raise errors.KingPhisherAbortRequestError()
			self.send_response(200)
			headers.append(('Last-Modified', self.date_time_string(os.stat(template.filename).st_mtime)))
			template_data = template_data.encode('utf-8', 'ignore')

		if mime_type.startswith('text'):
			mime_type += '; charset=utf-8'
		self.send_header('Content-Type', mime_type)
		self.send_header('Content-Length', len(template_data))
		for header in headers:
			self.send_header(*header)

		try:
			self.handle_page_visit()
		except Exception as error:
			self.server.logger.error('handle_page_visit raised error: {0}.{1}'.format(error.__class__.__module__, error.__class__.__name__), exc_info=True)
		finally:
			self.semaphore_release()

		self.end_headers()
		self.wfile.write(template_data)
		return

	def _respond_file_raw(self, file_path, attachment):
		try:
			file_obj = open(file_path, 'rb')
		except IOError:
			raise errors.KingPhisherAbortRequestError()
		fs = os.fstat(file_obj.fileno())
		self.send_response(200)
		self.send_header('Content-Type', self.guess_mime_type(file_path))
		self.send_header('Content-Length', fs[6])
		if attachment:
			file_name = os.path.basename(file_path)
			self.send_header('Content-Disposition', 'attachment; filename=' + file_name)
		self.send_header('Last-Modified', self.date_time_string(fs.st_mtime))
		self.end_headers()
		shutil.copyfileobj(file_obj, self.wfile)
		file_obj.close()
		return

	def _respond_file_check_id(self):
		if re.match(r'^/\.well-known/acme-challenge/[a-zA-Z0-9\-_]{40,50}$', self.request_path):
			self.server.logger.info('received request for .well-known/acme-challenge')
			return
		if not self.config.get('server.require_id'):
			return

		self.semaphore_acquire()
		if self.message_id == self.config.get('server.secret_id'):
			self.semaphore_release()
			self.server.logger.debug('request received with the correct secret id')
			return
		# a valid campaign_id requires a valid message_id
		if not self.campaign_id:
			self.semaphore_release()
			self.server.logger.warning('denying request due to lack of a valid id')
			raise errors.KingPhisherAbortRequestError()

		session = db_manager.Session()
		campaign = db_manager.get_row_by_id(session, db_models.Campaign, self.campaign_id)
		query = session.query(db_models.LandingPage)
		query = query.filter_by(campaign_id=self.campaign_id, hostname=self.vhost)
		if query.count() == 0:
			session.close()
			self.semaphore_release()
			self.server.logger.warning('denying request with not found due to invalid hostname')
			raise errors.KingPhisherAbortRequestError()
		if campaign.has_expired:
			session.close()
			self.semaphore_release()
			self.server.logger.warning('denying request because the campaign has expired')
			raise errors.KingPhisherAbortRequestError()
		if campaign.reject_after_credentials and self.visit_id is None:
			query = session.query(db_models.Credential)
			query = query.filter_by(message_id=self.message_id)
			if query.count():
				session.close()
				self.semaphore_release()
				self.server.logger.warning('denying request because credentials were already harvested')
				raise errors.KingPhisherAbortRequestError()
		session.close()
		self.semaphore_release()
		return

	def respond_not_found(self):
		self.send_response(404, 'Not Found')
		self.send_header('Content-Type', 'text/html; charset=utf-8')
		file_path = find.data_file(os.path.join('pages', 'error_404.html'))
		if file_path:
			with open(file_path, 'rb') as file_h:
				message = file_h.read()
		else:
			message = b'Resource Not Found\n'
		self.send_header('Content-Length', len(message))
		self.end_headers()
		self.wfile.write(message)
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

		data = self.get_query('token')
		if not data:
			self.logger.warning('dead drop request received with no \'token\' parameter')
			return
		try:
			data = base64.b64decode(data)
		except (binascii.Error, TypeError):
			self.logger.error('dead drop request received with invalid \'token\' data')
			return
		data = xor.xor_decode(data)
		try:
			data = json.loads(data)
		except ValueError:
			self.logger.error('dead drop request received with invalid \'token\' data')
			return

		self.semaphore_acquire()
		session = db_manager.Session()
		deployment = db_manager.get_row_by_id(session, db_models.DeaddropDeployment, data.get('deaddrop_id'))
		if not deployment:
			session.close()
			self.semaphore_release()
			self.logger.error('dead drop request received for an unknown campaign')
			return
		if deployment.campaign.has_expired:
			session.close()
			self.semaphore_release()
			self.logger.info('dead drop request received for an expired campaign')
			return

		local_username = data.get('local_username')
		local_hostname = data.get('local_hostname')
		if local_username is None or local_hostname is None:
			session.close()
			self.semaphore_release()
			self.logger.error('dead drop request received with missing data')
			return
		local_ip_addresses = data.get('local_ip_addresses')
		if isinstance(local_ip_addresses, (list, tuple)):
			local_ip_addresses = ' '.join(local_ip_addresses)

		query = session.query(db_models.DeaddropConnection)
		query = query.filter_by(deployment_id=deployment.id, local_username=local_username, local_hostname=local_hostname)
		connection = query.first()
		if connection:
			connection.visit_count += 1
			new_connection = False
		else:
			connection = db_models.DeaddropConnection(campaign_id=deployment.campaign_id, deployment_id=deployment.id)
			connection.visitor_ip = self.get_client_ip()
			connection.local_username = local_username
			connection.local_hostname = local_hostname
			connection.local_ip_addresses = local_ip_addresses
			session.add(connection)
			new_connection = True
		session.commit()

		query = session.query(db_models.DeaddropConnection)
		query = query.filter_by(campaign_id=deployment.campaign_id)
		visit_count = query.count()
		session.close()
		self.semaphore_release()
		if new_connection and visit_count > 0 and ((visit_count in [1, 3, 5]) or ((visit_count % 10) == 0)):
			self.server.job_manager.job_run(self.issue_alert, (deployment.campaign_id, 'deaddrop_connections', visit_count))
		return

	def handle_email_opened(self, query):
		# image size: 43 Bytes
		img_data = '47494638396101000100800100000000ffffff21f90401000001002c00000000'
		img_data += '010001000002024c01003b'
		img_data = binascii.a2b_hex(img_data)
		self.send_response(200)
		self.send_header('Content-Type', 'image/gif')
		self.send_header('Content-Length', str(len(img_data)))
		self.end_headers()
		self.wfile.write(img_data)

		msg_id = self.get_query('id')
		if not msg_id:
			return
		self.semaphore_acquire()
		session = db_manager.Session()
		query = session.query(db_models.Message)
		query = query.filter_by(id=msg_id, opened=None)
		message = query.first()
		if message and not message.campaign.has_expired:
			message.opened = db_models.current_timestamp()
			message.opener_ip = self.get_client_ip()
			message.opener_user_agent = self.headers.get('user-agent', None)
			session.commit()
		session.close()
		signals.send_safe('email-opened', self.logger, self)
		self.semaphore_release()

	def handle_javascript_hook(self, query):
		kp_hook_js = find.data_file('javascript_hook.js')
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
		self.send_header('Content-Length', len(javascript))
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
		client_ip = self.get_client_ip()

		session = db_manager.Session()
		campaign = db_manager.get_row_by_id(session, db_models.Campaign, self.campaign_id)
		if campaign.has_expired:
			self.logger.info("ignoring page visit for expired campaign id: {0} from IP address: {1}".format(self.campaign_id, client_ip))
			session.close()
			return
		self.logger.info("handling a page visit for campaign id: {0} from IP address: {1}".format(self.campaign_id, client_ip))
		message = db_manager.get_row_by_id(session, db_models.Message, self.message_id)

		if message.opened is None and self.config.get('server.set_message_opened_on_visit'):
			message.opened = db_models.current_timestamp()
			message.opener_ip = self.get_client_ip()
			message.opener_user_agent = self.headers.get('user-agent', None)

		set_new_visit = True
		visit_id = None
		if self.visit_id:
			visit_id = self.visit_id
			set_new_visit = False
			query = session.query(db_models.LandingPage)
			query = query.filter_by(campaign_id=self.campaign_id, hostname=self.vhost, page=self.request_path[1:])
			if query.count():
				visit = db_manager.get_row_by_id(session, db_models.Visit, self.visit_id)
				if visit.message_id == self.message_id:
					visit.visit_count += 1
					visit.last_visit = db_models.current_timestamp()
				else:
					set_new_visit = True
					visit_id = None

		if visit_id is None:
			visit_id = utilities.make_visit_uid()

		if set_new_visit:
			kp_cookie_name = self.config.get('server.cookie_name')
			cookie = "{0}={1}; Path=/; HttpOnly".format(kp_cookie_name, visit_id)
			self.send_header('Set-Cookie', cookie)
			visit = db_models.Visit(id=visit_id, campaign_id=self.campaign_id, message_id=self.message_id)
			visit.visitor_ip = client_ip
			visit.visitor_details = self.headers.get('user-agent', '')
			session.add(visit)
			visit_count = len(campaign.visits)
			if visit_count > 0 and ((visit_count in (1, 10, 25)) or ((visit_count % 50) == 0)):
				self.server.job_manager.job_run(self.issue_alert, (self.campaign_id, 'visits', visit_count))
			signals.send_safe('visit-received', self.logger, self)

		if visit_id is None:
			self.logger.error('the visit id has not been set')
			raise RuntimeError('the visit id has not been set')
		self._handle_page_visit_creds(session, visit_id)
		trained = self.get_query('trained')
		if isinstance(trained, str) and trained.lower() in ['1', 'true', 'yes']:
			message.trained = True
		session.commit()
		session.close()

	def _handle_page_visit_creds(self, session, visit_id):
		username, password = self.get_query_creds()
		if username is None:
			return
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
			self.server.job_manager.job_run(self.issue_alert, (self.campaign_id, 'credentials', cred_count))
		signals.send_safe('credentials-received', self.logger, self, username=username, password=password)

class KingPhisherServer(advancedhttpserver.AdvancedHTTPServer):
	"""
	The main HTTP and RPC server for King Phisher.
	"""
	def __init__(self, config, plugin_manager, handler_klass, *args, **kwargs):
		"""
		:param config: Configuration to retrieve settings from.
		:type config: :py:class:`smoke_zephyr.configuration.Configuration`
		"""
		# additional mime types to be treated as html because they're probably cloned pages
		handler_klass.extensions_map.update({
			'': 'text/html',
			'.asp': 'text/html',
			'.aspx': 'text/html',
			'.cfm': 'text/html',
			'.cgi': 'text/html',
			'.do': 'text/html',
			'.jsp': 'text/html',
			'.nsf': 'text/html',
			'.php': 'text/html',
			'.srf': 'text/html'
		})
		super(KingPhisherServer, self).__init__(handler_klass, *args, **kwargs)
		self.logger = logging.getLogger('KingPhisher.Server')
		self.config = config
		"""A :py:class:`~smoke_zephyr.configuration.Configuration` instance used as the main King Phisher server configuration."""
		self.headers = collections.OrderedDict()
		"""A :py:class:`~collections.OrderedDict` containing additional headers specified from the server configuration to include in responses."""
		self.plugin_manager = plugin_manager
		self.serve_files = True
		self.serve_files_root = config.get('server.web_root')
		self.serve_files_list_directories = False
		self.serve_robots_txt = True
		self.database_engine = db_manager.init_database(config.get('server.database'), extra_init=True)

		self.throttle_semaphore = threading.BoundedSemaphore()
		self.session_manager = aaa.AuthenticatedSessionManager(
			timeout=config.get_if_exists('server.authentication.cache_timeout', '30m')
		)
		self.forked_authenticator = aaa.ForkedAuthenticator(
			cache_timeout=config.get_if_exists('server.authentication.cache_timeout', '10m'),
			required_group=config.get_if_exists('server.authentication.group'),
			pam_service=config.get_if_exists('server.authentication.pam_service', 'sshd')
		)
		self.job_manager = smoke_zephyr.job.JobManager(logger_name='KingPhisher.Server.JobManager')
		"""A :py:class:`~smoke_zephyr.job.JobManager` instance for scheduling tasks."""
		self.job_manager.start()
		loader = jinja2.FileSystemLoader(config.get('server.web_root'))
		global_vars = {}
		if config.has_section('server.page_variables'):
			global_vars = config.get('server.page_variables')
		global_vars.update(pages.EXPORTED_FUNCTIONS)
		self.template_env = templates.TemplateEnvironmentBase(loader=loader, global_vars=global_vars)
		self.ws_manager = web_sockets.WebSocketsManager(config, self.job_manager)

		for http_server in self.sub_servers:
			http_server.config = config
			http_server.plugin_manager = plugin_manager
			http_server.throttle_semaphore = self.throttle_semaphore
			http_server.session_manager = self.session_manager
			http_server.forked_authenticator = self.forked_authenticator
			http_server.job_manager = self.job_manager
			http_server.template_env = self.template_env
			http_server.kp_shutdown = self.shutdown
			http_server.ws_manager = self.ws_manager
			http_server.headers = self.headers

		if not config.has_option('server.secret_id'):
			config.set('server.secret_id', rest_api.generate_token())
		if not config.get_if_exists('server.rest_api.token'):
			config.set('server.rest_api.token', rest_api.generate_token())
		if config.get('server.rest_api.enabled'):
			self.logger.info('rest api initialized with token: ' + config.get('server.rest_api.token'))

		self.__geoip_db = geoip.init_database(config.get('server.geoip.database'))
		self.__is_shutdown = threading.Event()
		self.__is_shutdown.clear()
		self.__shutdown_lock = threading.Lock()
		plugin_manager.server = weakref.proxy(self)

		headers = self.config.get_if_exists('server.headers', [])
		for header in headers:
			if ': ' not in header:
				self.logger.warning("header '{0}' is invalid and will not be included".format(header))
				continue
			header, value = header.split(': ', 1)
			header = header.strip()
			self.headers[header] = value
		self.logger.info("including {0} custom http headers".format(len(self.headers)))

	def shutdown(self, *args, **kwargs):
		"""
		Request that the server perform any cleanup necessary and then shut
		down. This will wait for the server to stop before it returns.
		"""
		with self.__shutdown_lock:
			if self.__is_shutdown.is_set():
				return
			self.logger.warning('processing shutdown request')
			super(KingPhisherServer, self).shutdown(*args, **kwargs)
			self.ws_manager.stop()
			self.job_manager.stop()
			self.session_manager.stop()
			self.forked_authenticator.stop()
			self.logger.debug('stopped the forked authenticator process')
			self.__geoip_db.close()
			self.__is_shutdown.set()
