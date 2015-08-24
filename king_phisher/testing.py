#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  king_phisher/testing.py
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

import functools
import os
import sys
import threading
import time
import urllib
import unittest

from king_phisher import find
from king_phisher.client import client_rpc
from king_phisher.server import rest_api
from king_phisher.server.server import *

import smoke_zephyr.configuration
import smoke_zephyr.utilities

if sys.version_info[0] < 3:
	import httplib
	http = type('http', (), {'client': httplib})
	import urlparse
	urllib.parse = urlparse
	urllib.parse.urlencode = urllib.urlencode
else:
	import http.client
	import urllib.parse

__all__ = [
	'TEST_MESSAGE_TEMPLATE',
	'TEST_MESSAGE_TEMPLATE_INLINE_IMAGE',
	'KingPhisherTestCase',
	'KingPhisherServerTestCase'
]

TEST_MESSAGE_TEMPLATE_INLINE_IMAGE = '/path/to/fake/image.png'
"""A string with the path to a file used as an inline image in the :py:data:`.TEST_MESSAGE_TEMPLATE`."""

TEST_MESSAGE_TEMPLATE = """
<html>
<body>
	Hello {{ client.first_name }} {{ client.last_name }},<br />
	<br />
	Lorem ipsum dolor sit amet, inani assueverit duo ei. Exerci eruditi nominavi
	ei eum, vim erant recusabo ex, nostro vocibus minimum no his. Omnesque
	officiis his eu, sensibus consequat per cu. Id modo vidit quo, an has
	detracto intellegat deseruisse. Vis ut novum solet complectitur, ei mucius
	tacimates sit.
	<br />
	Duo veniam epicuri cotidieque an, usu vivendum adolescens ei, eu ius soluta
	minimum voluptua. Eu duo numquam nominavi deterruisset. No pro dico nibh
	luptatum. Ex eos iriure invenire disputando, sint mutat delenit mei ex.
	Mundi similique persequeris vim no, usu at natum philosophia.
	<a href="{{ url.webserver }}">{{ client.company_name }} HR Enroll</a><br />
	<br />
	{{ inline_image('""" + TEST_MESSAGE_TEMPLATE_INLINE_IMAGE + """') }}
	{{ tracking_dot_image_tag }}
</body>
</html>
"""
"""A string representing a message template that can be used for testing."""

def skip_if_offline(test_method):
	"""
	A decorator to skip running tests when the KING_PHISHER_TEST_OFFLINE
	environment variable is set. This allows unit tests which require a internet
	connection to be skipped when network connectivity is known to be inactive.
	"""
	@functools.wraps(test_method)
	def decorated(self, *args, **kwargs):
		if os.environ.get('KING_PHISHER_TEST_OFFLINE'):
			self.skipTest('due to running in offline mode')
		return test_method(self, *args, **kwargs)
	return decorated

def skip_on_travis(test_method):
	"""
	A decorator to skip running a test when executing in the travis-ci environment.
	"""
	@functools.wraps(test_method)
	def decorated(self, *args, **kwargs):
		if os.environ.get('TRAVIS'):
			self.skipTest('due to running in travis-ci environment')
		return test_method(self, *args, **kwargs)
	return decorated

class KingPhisherRequestHandlerTest(KingPhisherRequestHandler):
	def install_handlers(self):
		super(KingPhisherRequestHandlerTest, self).install_handlers()
		self.rpc_handler_map['^/login$'] = self.rpc_test_login

	def rpc_test_login(self, username, password, otp=None):
		return True, 'success', self.server.session_manager.put(username)

class KingPhisherTestCase(smoke_zephyr.utilities.TestCase):
	"""
	This class provides additional functionality over the built in
	:py:class:`unittest.TestCase` object, including better compatibility for
	methods across Python 2.x and Python 3.x.
	"""
	pass

class KingPhisherServerTestCase(unittest.TestCase):
	"""
	This class can be inherited to automatically set up a King Phisher server
	instance configured in a way to be suitable for testing purposes.
	"""
	def setUp(self):
		find.data_path_append('data/server')
		web_root = os.path.join(os.getcwd(), 'data', 'server', 'king_phisher')
		config = smoke_zephyr.configuration.Configuration(find.find_data_file('server_config.yml'))
		config.set('server.address.port', 0)
		config.set('server.database', 'sqlite://')
		config.set('server.geoip.database', os.environ.get('KING_PHISHER_TEST_GEOIP_DB', './GeoLite2-City.mmdb'))
		config.set('server.web_root', web_root)
		config.set('server.rest_api.enabled', True)
		config.set('server.rest_api.token', rest_api.generate_token())
		self.config = config
		self.server = build_king_phisher_server(config, HandlerClass=KingPhisherRequestHandlerTest)
		config.set('server.address.port', self.server.http_server.server_port)
		self.assertIsInstance(self.server, KingPhisherServer)
		self.server_thread = threading.Thread(target=self.server.serve_forever)
		self.server_thread.daemon = True
		self.server_thread.start()
		self.assertTrue(self.server_thread.is_alive())
		self.shutdown_requested = False
		self.rpc = client_rpc.KingPhisherRPCClient(('localhost', self.config.get('server.address.port')))
		self.rpc.login(username='unittest', password='unittest')

	def assertHTTPStatus(self, http_response, status):
		"""
		Check an HTTP response to ensure that the correct HTTP status code is
		specified.

		:param http_response: The response object to check.
		:type http_response: :py:class:`httplib.HTTPResponse`
		:param int status: The status to check for.
		"""
		self.assertIsInstance(http_response, http.client.HTTPResponse)
		error_message = "HTTP Response received status {0} when {1} was expected".format(http_response.status, status)
		self.assertEqual(http_response.status, status, msg=error_message)

	def http_request(self, resource, method='GET', include_id=True, body=None, headers=None):
		"""
		Make an HTTP request to the specified resource on the test server.

		:param str resource: The resource to send the request to.
		:param str method: The HTTP method to use for the request.
		:param bool include_id: Whether to include the the id parameter.
		:param body: The data to include in the body of the request.
		:type body: dict, str
		:param dict headers: The headers to include in the request.
		:return: The servers HTTP response.
		:rtype: :py:class:`httplib.HTTPResponse`
		"""
		if include_id:
			if isinstance(include_id, str):
				id_value = include_id
			else:
				id_value = self.config.get('server.secret_id')
			resource += "{0}id={1}".format('&' if '?' in resource else '?', id_value)
		conn = http.client.HTTPConnection('localhost', self.config.get('server.address.port'))
		request_kwargs = {}
		if isinstance(body, dict):
			body = urllib.parse.urlencode(body)
		if body:
			request_kwargs['body'] = body
		if headers:
			request_kwargs['headers'] = headers
		conn.request(method, resource, **request_kwargs)
		time.sleep(0.025)
		response = conn.getresponse()
		conn.close()
		return response

	def web_root_files(self, limit=None, include_templates=True):
		"""
		A generator object that yields valid files which are contained in the
		web root of the test server instance. This can be used to find resources
		which the server should process as files. The function will fail if
		no files can be found in the web root.

		:param int limit: A limit to the number of files to return.
		:param bool include_templates: Whether or not to include files that might be templates.
		"""
		limit = (limit or float('inf'))
		philes_yielded = 0
		web_root = self.config.get('server.web_root')
		self.assertTrue(os.path.isdir(web_root), msg='The test web root does not exist')
		philes = (phile for phile in os.listdir(web_root) if os.path.isfile(os.path.join(web_root, phile)))
		for phile in philes:
			if not include_templates and os.path.splitext(phile)[1] in ('.txt', '.html'):
				continue
			if philes_yielded < limit:
				yield phile
				philes_yielded += 1
		self.assertGreater(philes_yielded, 0, msg='No files were found in the web root')

	def tearDown(self):
		if not self.shutdown_requested:
			self.assertTrue(self.server_thread.is_alive())
		self.server.shutdown()
		self.server_thread.join(10.0)
		self.assertFalse(self.server_thread.is_alive())
		del self.server
