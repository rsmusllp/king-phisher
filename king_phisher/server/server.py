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
from king_phisher import serializers
from king_phisher import templates
from king_phisher import utilities
from king_phisher import xor
from king_phisher.server import aaa
from king_phisher.server import letsencrypt
from king_phisher.server import rest_api
from king_phisher.server import server_rpc
from king_phisher.server import signals
from king_phisher.server import template_extras
from king_phisher.server import web_sockets
from king_phisher.server.database import manager as db_manager
from king_phisher.server.database import models as db_models
from king_phisher.server.database import validation as db_validation

import advancedhttpserver
import blinker
import jinja2
import smoke_zephyr.job
import smoke_zephyr.utilities

def _send_safe_campaign_alerts(campaign, signal_name, sender, **kwargs):
	alert_subscriptions = tuple(subscription for subscription in campaign.alert_subscriptions if not subscription.has_expired)
	logger = logging.getLogger('KingPhisher.Server.CampaignAlerts')
	logger.debug("dispatching campaign alerts for '{0}' (sender: {1!r}) to {2:,} active subscriptions".format(signal_name, sender, len(alert_subscriptions)))
	if not alert_subscriptions:
		return
	signal = blinker.signal(signal_name)
	if not signal.receivers:
		logger.warning("users are subscribed to '{0}', and no signal handlers are connected".format(signal_name))
		return
	if not signal.has_receivers_for(sender):
		logger.info("users are subscribed to '{0}', and no signal handlers are connected for sender: {1}".format(signal_name, sender))
		return
	for subscription in alert_subscriptions:
		results = signals.send_safe(signal_name, logger, sender, alert_subscription=subscription, **kwargs)
		if any((result for (_, result) in results)):
			continue
		logger.warning("user {0} is subscribed to '{1}', and no signal handlers succeeded to send an alert".format(subscription.user.name, signal_name))

class KingPhisherRequestHandler(advancedhttpserver.RequestHandler):
	_logger = logging.getLogger('KingPhisher.Server.RequestHandler')
	def __init__(self, request, client_address, server, **kwargs):
		self.logger = utilities.PrefixLoggerAdapter("{0}:{1}".format(client_address[0], client_address[1]), self._logger, {})
		self.logger.debug("tid: 0x{0:x} running http request handler".format(threading.current_thread().ident))
		# this is for attribute documentation
		self.config = None
		"""A reference to the main server instance :py:attr:`.KingPhisherServer.config`."""
		self.path = None
		"""The resource path of the current HTTP request."""
		self.rpc_session = None
		self.rpc_session_id = None
		self.semaphore_acquired = False
		self._session = None
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
		campaign = db_manager.get_row_by_id(self._session, db_models.Campaign, campaign_id)
		_send_safe_campaign_alerts(campaign, 'campaign-alert', table, count=count)
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
		self.rpc_session_id = self.headers.get(server_rpc.RPC_AUTH_HEADER, None)
		# delete cached properties so they are handled per request instead of connection.
		for cache_prop in ('_campaign_id', '_message_id', '_visit_id'):
			if hasattr(self, cache_prop):
				delattr(self, cache_prop)
		self.adjust_path()
		self._session = db_manager.Session()

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
				self.logger.warning('http request failed to cleanly release resources')
				self.semaphore_release()
			self._session.close()
		self.connection.settimeout(None)

	def _do_rpc_method(self, *args, **kwargs):
		self.connection.settimeout(smoke_zephyr.utilities.parse_timespan('20s'))  # set a timeout as a fail safe
		self.rpc_session_id = self.headers.get(server_rpc.RPC_AUTH_HEADER, None)
		self.semaphore_acquire()

		http_method_handler = None
		try:
			signals.request_handle.send(self)
			http_method_handler = getattr(super(KingPhisherRequestHandler, self), 'do_RPC')
			http_method_handler(*args, **kwargs)
		except errors.KingPhisherAbortRequestError as error:
			if http_method_handler is None:
				self.logger.debug('rpc request aborted by a signal handler')
			else:
				self.logger.info('rpc request aborted')
			if not error.response_sent:
				self.respond_not_found()
		finally:
			self.semaphore_release()
		self.connection.settimeout(None)

	do_GET = _do_http_method
	do_HEAD = _do_http_method
	do_POST = _do_http_method
	do_RPC = _do_rpc_method

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
		:rtype: :py:class:`~king_phisher.server.database.validation.CredentialCollection`
		"""
		username = None
		password = ''
		mfa_token = None

		if check_query:
			for pname in ('username', 'user', 'u', 'login'):
				username = (self.get_query(pname) or self.get_query(pname.title()) or self.get_query(pname.upper()))
				if username:
					break
			if username:
				for pname in ('password', 'pass', 'p'):
					password = (self.get_query(pname) or self.get_query(pname.title()) or self.get_query(pname.upper()))
					if password:
						break
				for pname in ('mfa', 'mfa-token', 'otp', 'otp-token', 'token'):
					mfa_token = (self.get_query(pname) or self.get_query(pname.title()) or self.get_query(pname.upper()))
					if mfa_token:
						break
				return db_validation.CredentialCollection(username, (password or ''), mfa_token)

		basic_auth = self.headers.get('authorization')
		if basic_auth:
			basic_auth = basic_auth.split()
			if len(basic_auth) == 2 and basic_auth[0] == 'Basic':
				try:
					basic_auth = base64.b64decode(basic_auth[1])
				except TypeError:
					return db_validation.CredentialCollection(None, '', None)
				basic_auth = basic_auth.decode('utf-8')
				basic_auth = basic_auth.split(':', 1)
				if len(basic_auth) == 2 and len(basic_auth[0]):
					username, password = basic_auth
		return db_validation.CredentialCollection(username, password, mfa_token)

	def _get_db_creds(self, query_creds):
		query = self._session.query(db_models.Credential)
		query = query.filter_by(message_id=self.message_id, **query_creds._asdict())
		return query.first()

	def get_template_vars(self):
		request_vars = {
			'command': self.command,
			'cookies': dict((c[0], c[1].value) for c in self.cookies.items()),
			'headers': dict(self.headers),
			'parameters': dict(zip(self.query_data.keys(), map(self.get_query, self.query_data.keys()))),
			'user_agent': self.headers.get('user-agent')
		}
		creds = self.get_query_creds()
		creds = None if creds.username is None else self._get_db_creds(creds)
		if creds is not None:
			request_vars['credentials'] = creds.to_dict()
		template_vars = {
			'client': self.get_template_vars_client(),
			'request': request_vars,
			'server': {
				'hostname': self.vhost,
				'address': self.connection.getsockname()[0],
				'port': self.connection.getsockname()[1]
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
		if self.message_id == self.config.get('server.secret_id'):
			client_vars['company_name'] = 'Wonderland Inc.'
			client_vars['company'] = {'name': 'Wonderland Inc.'}
			result = ('aliddle@wonderland.com', 'Alice', 'Liddle', 0)
		elif self.message_id:
			message = db_manager.get_row_by_id(self._session, db_models.Message, self.message_id)
			if message:
				campaign = message.campaign.to_dict()
				campaign['message_count'] = self._session.query(db_models.Message).filter_by(campaign_id=message.campaign.id).count()
				campaign['visit_count'] = self._session.query(db_models.Visit).filter_by(campaign_id=message.campaign.id).count()
				campaign['credential_count'] = self._session.query(db_models.Credential).filter_by(campaign_id=message.campaign.id).count()
				client_vars['campaign'] = campaign
				if message.campaign.company:
					client_vars['company_name'] = message.campaign.company.name
					client_vars['company'] = message.campaign.company.to_dict()
				result = (message.target_email, message.first_name, message.last_name, message.trained)
			query = self._session.query(db_models.Credential)
			query = query.filter_by(message_id=self.message_id)
			credential_count = query.count()
			expired_campaign = message.campaign.has_expired
		if not result:
			return client_vars

		client_vars['email_address'] = result[0]
		client_vars['first_name'] = result[1]
		client_vars['last_name'] = result[2]
		client_vars['is_trained'] = result[3]
		client_vars['message_id'] = self.message_id

		if self.visit_id:
			visit = db_manager.get_row_by_id(self._session, db_models.Visit, self.visit_id)
			client_vars['visit_id'] = visit.id
			visit_count = visit.count

		client_vars['credential_count'] = credential_count
		client_vars['visit_count'] = visit_count + (0 if expired_campaign else 1)
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
			self.logger.warning("request authorization failed (RPC session id is {0})".format('None' if self.rpc_session_id is None else 'invalid'))
			return False
		return True

	def _set_ids(self):
		"""
		Handle lazy resolution of the ``*_id`` properties necessary to track
		information.
		"""
		self._visit_id = None
		kp_cookie_name = self.config.get('server.cookie_name')
		if kp_cookie_name in self.cookies:
			value = self.cookies[kp_cookie_name].value
			if db_manager.get_row_by_id(self._session, db_models.Visit, value):
				self._visit_id = value

		self._message_id = None
		msg_id = self.get_query('id')
		if msg_id == self.config.get('server.secret_id'):
			self._message_id = msg_id
		elif msg_id and db_manager.get_row_by_id(self._session, db_models.Message, msg_id):
			self._message_id = msg_id
		elif self._visit_id:
			visit = db_manager.get_row_by_id(self._session, db_models.Visit, self._visit_id)
			self._message_id = visit.message_id

		self._campaign_id = None
		if self._message_id and self._message_id != self.config.get('server.secret_id'):
			message = db_manager.get_row_by_id(self._session, db_models.Message, self._message_id)
			if message:
				self._campaign_id = message.campaign_id

	@property
	def campaign_id(self):
		"""
		The campaign id that is associated with the current request's visitor.
		This is retrieved by looking up the
		:py:attr:`~.KingPhisherRequestHandler.message_id` value in the database.
		If no campaign is associated, this value is None.
		"""
		if not hasattr(self, '_campaign_id'):
			self.logger.warning('using lazy resolution for the request campaign id')
			self._set_ids()
		return self._campaign_id

	@property
	def message_id(self):
		"""
		The message id that is associated with the current request's visitor.
		This is retrieved by looking at an 'id' parameter in the query and then
		by checking the :py:attr:`~.KingPhisherRequestHandler.visit_id` value in
		the database. If no message id is associated, this value is None. The
		resulting value will be either a confirmed valid value, or the value of
		the configurations server.secret_id for testing purposes.
		"""
		if not hasattr(self, '_message_id'):
			self.logger.warning('using lazy resolution for the request message id')
			self._set_ids()
		return self._message_id

	@property
	def visit_id(self):
		"""
		The visit id that is associated with the current request's visitor. This
		is retrieved by looking for the King Phisher cookie. If no cookie is
		set, this value is None.
		"""
		if not hasattr(self, '_visit_id'):
			self.logger.warning('using lazy resolution for the request visit id')
			self._set_ids()
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
		self.semaphore_acquire()
		try:
			self._set_ids()
			self._respond_file_check_id()
		finally:
			self.semaphore_release()

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
		headers = collections.deque()
		try:
			headers.extend(self.handle_page_visit() or [])
		except Exception as error:
			self.server.logger.error('handle_page_visit raised error: {0}.{1}'.format(error.__class__.__module__, error.__class__.__name__), exc_info=True)

		template_vars = self.get_template_vars()
		try:
			template_module = template.make_module(template_vars)
		except (TypeError, jinja2.TemplateError) as error:
			self.semaphore_release()
			self.server.logger.error("jinja2 template {0} render failed: {1} {2}".format(template.filename, error.__class__.__name__, getattr(error, 'message', '')))
			raise errors.KingPhisherAbortRequestError()

		query_creds = self.get_query_creds(check_query=False)
		require_basic_auth = getattr(template_module, 'require_basic_auth', False)
		require_basic_auth &= not (query_creds.username and query_creds.password)
		require_basic_auth &= self.message_id != self.config.get('server.secret_id')
		template_data = b''
		if require_basic_auth:
			mime_type = 'text/html'
			self.send_response(401)
			headers.append(('WWW-Authenticate', "Basic realm=\"{0}\"".format(getattr(template_module, 'basic_auth_realm', 'Authentication Required'))))
		else:
			self.send_response(200)
			headers.append(('Last-Modified', self.date_time_string(os.stat(template.filename).st_mtime)))
			template_data = str(template_module).encode('utf-8', 'ignore')

		if mime_type.startswith('text'):
			mime_type += '; charset=utf-8'
		headers.extendleft([('Content-Type', mime_type), ('Content-Length', len(template_data))])
		for header in headers:
			self.send_header(*header)

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
		headers = collections.deque([('Content-Type', self.guess_mime_type(file_path)), ('Content-Length', fs[6])])

		if attachment:
			file_name = os.path.basename(file_path)
			headers.append(('Content-Disposition', 'attachment; filename=' + file_name))
		headers.append(('Last-Modified', self.date_time_string(fs.st_mtime)))
		self.semaphore_acquire()
		try:
			headers.extend(self.handle_page_visit() or [])
		except Exception as error:
			self.server.logger.error('handle_page_visit raised error: {0}.{1}'.format(error.__class__.__module__, error.__class__.__name__), exc_info=True)
		finally:
			self.semaphore_release()

		self.send_response(200)
		for header in headers:
			self.send_header(*header)
		self.end_headers()
		shutil.copyfileobj(file_obj, self.wfile)
		file_obj.close()
		return

	def _respond_file_check_id(self):
		if re.match(r'^[._]metadata\.(json|yaml|yml)$', os.path.basename(self.request_path)):
			self.server.logger.warning('received request for template metadata file')
			raise errors.KingPhisherAbortRequestError()
		if re.match(r'^/\.well-known/acme-challenge/[a-zA-Z0-9\-_]{40,50}$', self.request_path):
			self.server.logger.info('received request for .well-known/acme-challenge')
			return
		if not self.config.get('server.require_id'):
			return

		if self.message_id == self.config.get('server.secret_id'):
			self.server.logger.debug('request received with the correct secret id')
			return
		# a valid campaign_id requires a valid message_id
		if not self.campaign_id:
			self.server.logger.warning('denying request due to lack of a valid id')
			raise errors.KingPhisherAbortRequestError()

		campaign = db_manager.get_row_by_id(self._session, db_models.Campaign, self.campaign_id)
		query = self._session.query(db_models.LandingPage)
		query = query.filter_by(campaign_id=self.campaign_id, hostname=self.vhost)
		if query.count() == 0:
			self.server.logger.warning('denying request with not found due to invalid hostname')
			raise errors.KingPhisherAbortRequestError()
		if campaign.has_expired:
			self.server.logger.warning('denying request because the campaign has expired')
			raise errors.KingPhisherAbortRequestError()
		if campaign.max_credentials is not None and self.visit_id is None:
			query = self._session.query(db_models.Credential)
			query = query.filter_by(message_id=self.message_id)
			if query.count() >= campaign.max_credentials:
				self.server.logger.warning('denying request because the maximum number of credentials have already been harvested')
				raise errors.KingPhisherAbortRequestError()
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
		deployment = db_manager.get_row_by_id(self._session, db_models.DeaddropDeployment, data.get('deaddrop_id'))
		if not deployment:
			self.semaphore_release()
			self.logger.error('dead drop request received for an unknown campaign')
			return
		if deployment.campaign.has_expired:
			self.semaphore_release()
			self.logger.info('dead drop request received for an expired campaign')
			return

		local_username = data.get('local_username')
		local_hostname = data.get('local_hostname')
		if local_username is None or local_hostname is None:
			self.semaphore_release()
			self.logger.error('dead drop request received with missing data')
			return
		local_ip_addresses = data.get('local_ip_addresses')
		if isinstance(local_ip_addresses, (list, tuple)):
			local_ip_addresses = ' '.join(local_ip_addresses)

		query = self._session.query(db_models.DeaddropConnection)
		query = query.filter_by(deployment_id=deployment.id, local_username=local_username, local_hostname=local_hostname)
		connection = query.first()
		if connection:
			connection.count += 1
			connection.last_seen = db_models.current_timestamp()
			new_connection = False
		else:
			connection = db_models.DeaddropConnection(campaign_id=deployment.campaign_id, deployment_id=deployment.id)
			connection.ip = self.get_client_ip()
			connection.local_username = local_username
			connection.local_hostname = local_hostname
			connection.local_ip_addresses = local_ip_addresses
			self._session.add(connection)
			new_connection = True
		self._session.commit()

		query = self._session.query(db_models.DeaddropConnection)
		query = query.filter_by(campaign_id=deployment.campaign_id)
		visit_count = query.count()
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
		query = self._session.query(db_models.Message)
		query = query.filter_by(id=msg_id, opened=None)
		message = query.first()
		if message and not message.campaign.has_expired:
			message.opened = db_models.current_timestamp()
			message.opener_ip = self.get_client_ip()
			message.opener_user_agent = self.headers.get('user-agent', None)
			self._session.commit()
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
		self.send_header('Content-Length', len(javascript))
		self.send_header('Pragma', 'no-cache')
		self.send_header('Cache-Control', 'no-cache')
		self.send_header('Expires', '0')
		self.send_header('Access-Control-Allow-Origin', '*')
		self.send_header('Access-Control-Allow-Methods', 'POST, GET')
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
		headers = []

		campaign = db_manager.get_row_by_id(self._session, db_models.Campaign, self.campaign_id)
		if campaign.has_expired:
			self.logger.info("ignoring page visit for expired campaign id: {0} from IP address: {1}".format(self.campaign_id, client_ip))
			return
		self.logger.info("handling a page visit for campaign id: {0} from IP address: {1}".format(self.campaign_id, client_ip))
		message = db_manager.get_row_by_id(self._session, db_models.Message, self.message_id)

		if message.opened is None and self.config.get('server.set_message_opened_on_visit'):
			message.opened = db_models.current_timestamp()
			message.opener_ip = self.get_client_ip()
			message.opener_user_agent = self.headers.get('user-agent', None)

		query = self._session.query(db_models.LandingPage)
		query = query.filter_by(campaign_id=self.campaign_id, hostname=self.vhost, page=self.request_path[1:])
		landing_page = query.first()

		set_new_visit = True
		visit_id = None
		if self.visit_id:
			visit_id = self.visit_id
			set_new_visit = False
			if landing_page:
				visit = db_manager.get_row_by_id(self._session, db_models.Visit, self.visit_id)
				if visit.message_id == self.message_id:
					visit.count += 1
					visit.last_seen = db_models.current_timestamp()
					self._session.commit()
				else:
					set_new_visit = True
					visit_id = None

		if visit_id is None:
			visit_id = utilities.make_visit_uid()

		if landing_page and set_new_visit:
			kp_cookie_name = self.config.get('server.cookie_name')
			cookie = "{0}={1}; Path=/; HttpOnly".format(kp_cookie_name, visit_id)
			headers.append(('Set-Cookie', cookie))
			visit = db_models.Visit(id=visit_id, campaign_id=self.campaign_id, message_id=self.message_id)
			visit.ip = client_ip
			visit.first_landing_page_id = landing_page.id
			visit.user_agent = self.headers.get('user-agent', '')
			self._session.add(visit)
			self._session.commit()
			self.logger.debug("visit id: {0} created for message id: {1}".format(visit_id, self.message_id))
			visit_count = len(campaign.visits)
			if visit_count > 0 and ((visit_count in (1, 10, 25)) or ((visit_count % 50) == 0)):
				self.server.job_manager.job_run(self.issue_alert, (self.campaign_id, 'visits', visit_count))
			signals.send_safe('visit-received', self.logger, self)

		self._handle_page_visit_creds(campaign, visit_id)
		trained = self.get_query('trained')
		if isinstance(trained, str) and trained.lower() in ['1', 'true', 'yes']:
			message.trained = True
			self._session.commit()
		return headers

	def _handle_page_visit_creds(self, campaign, visit_id):
		query_creds = self.get_query_creds()
		if query_creds.username is None:
			return
		cred_count = 0
		cred = self._get_db_creds(query_creds)
		if cred is None:
			cred = db_models.Credential(
				campaign_id=campaign.id,
				message_id=self.message_id,
				visit_id=visit_id,
				**query_creds._asdict()
			)
			cred.regex_validated = db_validation.validate_credential(cred, campaign)
			self._session.add(cred)
			self._session.commit()
			self.logger.debug("credential id: {0} created for message id: {1}".format(cred.id, cred.message_id))
			campaign = db_manager.get_row_by_id(self._session, db_models.Campaign, self.campaign_id)
			cred_count = len(campaign.credentials)
		if cred_count > 0 and ((cred_count in [1, 5, 10]) or ((cred_count % 25) == 0)):
			self.server.job_manager.job_run(self.issue_alert, (self.campaign_id, 'credentials', cred_count))
		signals.send_safe('credentials-received', self.logger, self, username=query_creds.username, password=query_creds.password)

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
			timeout=config.get_if_exists('server.authentication.session_timeout', '30m')
		)
		self.forked_authenticator = aaa.ForkedAuthenticator(
			cache_timeout=config.get_if_exists('server.authentication.cache_timeout', '10m'),
			required_group=config.get_if_exists('server.authentication.group'),
			pam_service=config.get_if_exists('server.authentication.pam_service', 'sshd')
		)
		self.job_manager = smoke_zephyr.job.JobManager(logger_name='KingPhisher.Server.JobManager')
		"""A :py:class:`~smoke_zephyr.job.JobManager` instance for scheduling tasks."""
		self.job_manager.start()
		maintenance_interval = 900  # 15 minutes
		self._maintenance_job = self.job_manager.job_add(self._maintenance, parameters=(maintenance_interval,), seconds=maintenance_interval)

		loader = jinja2.FileSystemLoader(config.get('server.web_root'))
		global_vars = {}
		if config.has_section('server.page_variables'):
			global_vars = config.get('server.page_variables')
		global_vars.update(template_extras.functions)
		self.template_env = templates.TemplateEnvironmentBase(loader=loader, global_vars=global_vars)
		self.ws_manager = web_sockets.WebSocketsManager(config, self.job_manager)

		self.tables_api = {}
		self._init_tables_api()

		for http_server in self.sub_servers:
			http_server.add_sni_cert = self.add_sni_cert
			http_server.config = config
			http_server.forked_authenticator = self.forked_authenticator
			http_server.get_sni_certs = lambda: self.sni_certs
			http_server.headers = self.headers
			http_server.job_manager = self.job_manager
			http_server.kp_shutdown = self.shutdown
			http_server.plugin_manager = plugin_manager
			http_server.remove_sni_cert = self.remove_sni_cert
			http_server.session_manager = self.session_manager
			http_server.tables_api = self.tables_api
			http_server.template_env = self.template_env
			http_server.throttle_semaphore = self.throttle_semaphore
			http_server.ws_manager = self.ws_manager

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

	def _init_tables_api(self):
		# initialize the tables api dataset, this is to effectively pin the schema exposed allowing new columns to be
		# added without breaking rpc compatibility
		file_path = find.data_file('table-api.json')
		if file_path is None:
			raise errors.KingPhisherResourceError('missing the table-api.json data file')
		with open(file_path, 'r') as file_h:
			tables_api_data = serializers.JSON.load(file_h)
		if tables_api_data['schema'] > db_models.SCHEMA_VERSION:
			raise errors.KingPhisherInputValidationError('the table-api.json data file\'s schema version is incompatible')
		for table_name, columns in tables_api_data['tables'].items():
			model = db_models.database_tables[table_name].model
			self.tables_api[table_name] = db_models.MetaTable(
				column_names=columns,
				model=model,
				name=table_name,
				table=model.__table__
			)
		self.logger.debug("initialized the table api dataset (schema version: {0})".format(tables_api_data['schema']))

	def _maintenance(self, interval):
		"""
		Execute periodic maintenance related tasks.

		:param int interval: The interval of time (in seconds) at which this method is being executed.
		"""
		self.logger.debug('running periodic maintenance tasks')
		now = db_models.current_timestamp()
		session = db_manager.Session()
		campaigns = session.query(db_models.Campaign).filter(
			db_models.Campaign.expiration != None
		).filter(
			db_models.Campaign.expiration < now
		).filter(
			db_models.Campaign.expiration >= now - datetime.timedelta(seconds=interval)
		)
		for campaign in campaigns:
			signals.send_safe('campaign-expired', self.logger, campaign)
			_send_safe_campaign_alerts(campaign, 'campaign-alert-expired', campaign)
		session.close()

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

	def add_sni_cert(self, hostname, ssl_certfile=None, ssl_keyfile=None, ssl_version=None):
		try:
			result = super(KingPhisherServer, self).add_sni_cert(hostname, ssl_certfile=ssl_certfile, ssl_keyfile=ssl_keyfile, ssl_version=ssl_version)
		except Exception as error:
			letsencrypt.set_sni_hostname(hostname, ssl_certfile, ssl_keyfile, enabled=False)
			raise error
		letsencrypt.set_sni_hostname(hostname, ssl_certfile, ssl_keyfile, enabled=True)
		return result

	def remove_sni_cert(self, hostname):
		for sni_cert in self.sni_certs:
			if sni_cert.hostname == hostname:
				break
		else:
			raise ValueError('the specified hostname does not have an sni certificate configuration')
		result = super(KingPhisherServer, self).remove_sni_cert(hostname)
		letsencrypt.set_sni_hostname(hostname, sni_cert.certfile, sni_cert.keyfile, enabled=False)
		return result
