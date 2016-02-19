#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  king_phisher/client/web_cloner.py
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

import codecs
import collections
import logging
import os
import re
import string
import sys
import urllib

from king_phisher.client import gui_utilities

import requests

if sys.version_info[0] < 3:
	import urlparse
	urllib.parse = urlparse
else:
	import urllib.parse

try:
	from gi.repository import WebKit2
	has_webkit2 = True
except ImportError:
	has_webkit2 = False

class ClonedResourceDetails(collections.namedtuple('ClonedResourceDetails', ('resource', 'mime_type', 'size', 'file_name'))):
	"""
	A named tuple which contains details regard a resource that has been cloned.

	.. py:attribute:: resource

		The web resource that has been cloned.

	.. py:attribute:: mime_type

		The MIME type that was provided by the server for the cloned resource.

	.. py:attribute:: size

		The size of the original resource that was provided by the server.

	.. py:attribute:: file_name

		The path to the file which the resource was written to.
	"""
	pass

class WebPageCloner(object):
	"""
	This object is used to clone web pages. It will use the WebKit2GTK+ engine
	and hook signals to detect what remote resources that are loaded from the
	target URL. These resources are then written to disk. Resources that have
	a MIME type of text/html have the King Phisher server javascript file
	patched in..
	"""
	def __init__(self, target_url, dest_dir):
		"""
		:param str target_url: The URL of the target web page to clone.
		:param str dest_dir: The path of a directory to write the resources to.
		"""
		if not has_webkit2:
			raise RuntimeError('cloning requires WebKit2GTK+')
		self.target_url = urllib.parse.urlparse(target_url)
		dest_dir = os.path.abspath(dest_dir)
		if not os.path.exists(dest_dir):
			os.mkdir(dest_dir)
		self.dest_dir = os.path.abspath(os.path.normpath(dest_dir))
		self.logger = logging.getLogger('KingPhisher.Client.WebPageScraper')
		self.cloned_resources = collections.OrderedDict()
		"""A :py:class:`collections.OrderedDict` instance of :py:class:`.ClonedResourceDetails` keyed by the web resource they describe."""
		self.load_started = False
		self.load_failed_event = None
		self.__web_resources = []

		self.webview = WebKit2.WebView()
		web_context = self.webview.get_context()
		web_context.set_cache_model(WebKit2.CacheModel.DOCUMENT_VIEWER)
		web_context.set_tls_errors_policy(WebKit2.TLSErrorsPolicy.IGNORE)
		self.webview.connect('decide-policy', self.signal_decide_policy)
		self.webview.connect('load-changed', self.signal_load_changed)
		self.webview.connect('load-failed', self.signal_load_failed)
		self.webview.connect('resource-load-started', self.signal_resource_load_started)
		self.webview.load_uri(self.target_url_str)

	def _webkit_empty_resource_bug_workaround(self, url, expected_len):
		"""
		This works around an issue in WebKit2GTK+ that will hopefully be
		resolved eventually. Sometimes the resource data that is returned is
		an empty string so attempt to re-request it with Python.
		"""
		try:
			response = requests.get(url, timeout=10)
		except requests.exceptions.RequestException:
			self.logger.warning('failed to request the empty resource with python')
			return ''
		if response.status_code < 200 or response.status_code > 299:
			self.logger.warning("requested the empty resource with python, but received status: {0} ({1})".format(response.status_code, response.reason))
			return ''
		data = response.content
		if len(data) != expected_len:
			self.logger.warning('requested the empty resource with python, but the length appears invalid')
		return data

	@property
	def load_failed(self):
		return self.load_failed_event != None

	@property
	def target_url_str(self):
		return urllib.parse.urlunparse(self.target_url)

	def copy_resource_data(self, resource, data):
		"""
		Copy the data from a loaded resource to a local file.

		:param resource: The resource whose data is being copied.
		:type resource: :py:class:`WebKit2.WebResource`
		:param data: The raw data of the represented resource.
		:type data: bytes, str
		"""
		resource_url_str = resource.get_property('uri')
		resource_url = urllib.parse.urlparse(resource_url_str)
		resource_path = os.path.split(resource_url.path)[0].lstrip('/')
		resource_path = urllib.parse.unquote(resource_path)
		directory = self.dest_dir
		for part in resource_path.split('/'):
			directory = os.path.join(directory, part)
			if not os.path.exists(directory):
				os.mkdir(directory)

		mime_type = None
		charset = 'utf-8'
		response = resource.get_response()
		if response:
			mime_type = response.get_http_headers().get('content-type')
			if ';' in mime_type:
				mime_type, charset = mime_type.split(';', 1)
				charset = charset.strip()
				if charset.startswith('charset='):
					charset = charset[8:].strip()

		resource_path = urllib.parse.unquote(resource_url.path)
		if resource_path.endswith('/'):
			resource_path += 'index.html'
		resource_path = resource_path.lstrip('/')
		resource_path = os.path.join(self.dest_dir, resource_path)
		if mime_type == 'text/html':
			try:
				codec = codecs.lookup(charset)
			except LookupError as error:
				self.logger.warning('failed to decode data from web response, ' + error.args[0])
			else:
				data = codec.decode(data)[0]
				data = self.patch_html(data)
				data = codec.encode(data)[0]
		with open(resource_path, 'wb') as file_h:
			file_h.write(data)

		crd = ClonedResourceDetails(urllib.parse.unquote(resource_url.path), mime_type, len(data), resource_path)
		self.cloned_resources[resource_url.path] = crd
		self.logger.debug("wrote {0:,} bytes to {1}".format(crd.size, resource_path))

	def patch_html(self, data):
		"""
		Patch the HTML data to include the King Phisher javascript resource.
		The script tag is inserted just before the closing head tag. If no head
		tag is present, the data is left unmodified.

		:param str data: The HTML data to patch.
		:return: The patched HTML data.
		:rtype: str
		"""
		match = re.search(r'</head>', data, flags=re.IGNORECASE)
		if not match:
			return data
		end_head = match.start(0)
		patched = ''
		patched += data[:end_head]
		patched += '<script src="/kp.js" type="text/javascript"></script>'
		ws_cursor = end_head - 1
		while ws_cursor > 0 and data[ws_cursor] in string.whitespace:
			ws_cursor -= 1
		patched += data[ws_cursor + 1:end_head]
		patched += data[end_head:]
		return patched

	def resource_is_on_target(self, resource):
		"""
		Test whether the resource is on the target system. This tries to match
		the hostname, scheme and port number of the resource's URI against the
		target URI.

		:return: Whether the resource is on the target or not.
		:rtype: bool
		"""
		resource_url = urllib.parse.urlparse(resource.get_property('uri'))
		if resource_url.netloc.lower() != self.target_url.netloc.lower():
			return False
		if resource_url.scheme.lower() != self.target_url.scheme.lower():
			return False
		rport = resource_url.port or (443 if resource_url.scheme == 'https' else 80)
		tport = self.target_url.port or (443 if self.target_url.scheme == 'https' else 80)
		if rport != tport:
			return False
		return True

	def stop_cloning(self):
		"""Stop the current cloning operation if it is running."""
		if self.webview.get_property('is-loading'):
			self.webview.stop_loading()

	def wait(self):
		"""
		Wait for the cloning operation to complete and return whether the
		operation was successful or not.

		:return: True if the operation was successful.
		:rtype: bool
		"""
		while not self.load_started:
			gui_utilities.gtk_sync()
		while self.webview.get_property('is-loading') or len(self.__web_resources):
			gui_utilities.gtk_sync()
		self.webview.destroy()
		return not self.load_failed

	def cb_get_data_finish(self, resource, task):
		data = resource.get_data_finish(task)
		for _ in range(1):
			response = resource.get_response()
			if not response:
				break
			resource_url_str = resource.get_property('uri')
			if not self.resource_is_on_target(resource):
				self.logger.debug('loaded external resource: ' + resource_url_str)
				break
			if len(data) == 0:
				self.logger.warning('loaded empty on target resource: ' + resource_url_str)
				data = self._webkit_empty_resource_bug_workaround(resource_url_str, response.get_content_length())
			else:
				self.logger.info('loaded on target resource: ' + resource_url_str)
			if len(data):
				self.copy_resource_data(resource, data)
		self.__web_resources.remove(resource)

	def signal_decide_policy(self, webview, decision, decision_type):
		self.logger.debug("received policy decision request of type: {0}".format(decision_type.value_name))
		if decision_type != WebKit2.PolicyDecisionType.NAVIGATION_ACTION:
			return
		new_target_url_str = decision.get_request().get_uri()
		new_target_url = urllib.parse.urlparse(new_target_url_str)
		if new_target_url_str == self.target_url_str:
			return
		# don't allow offsite redirects
		if new_target_url.netloc.lower() != self.target_url.netloc.lower():
			return
		self.target_url = new_target_url
		self.logger.info("updated the target url to: {0}".format(new_target_url_str))

	def signal_load_changed(self, webview, load_event):
		self.logger.debug("load status changed to: {0}".format(load_event.value_name))
		if load_event == WebKit2.LoadEvent.STARTED:
			self.load_started = True

	def signal_load_failed(self, webview, event, uri, error):
		self.logger.warning("load failed on event: {0} for uri: {1}".format(event.value_name, uri))
		self.load_failed_event = event

	def signal_resource_load_started(self, webveiw, resource, request):
		self.__web_resources.append(resource)
		resource.connect('failed', self.signal_resource_load_failed)
		resource.connect('finished', self.signal_resource_load_finished)

	def signal_resource_load_finished(self, resource):
		resource.get_data(callback=self.cb_get_data_finish)

	def signal_resource_load_failed(self, resource, error):
		self.logger.warning('failed to load resource: ' + resource.get_uri())
