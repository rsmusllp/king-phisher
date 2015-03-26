#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  webkit_scrape.py
#
#  Copyright 2015 Spencer McIntyre <zeroSteiner@gmail.com>
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

import collections
import logging
import os
import sys
import urllib

from king_phisher.client import gui_utilities

from gi.repository import WebKit2

if sys.version_info[0] < 3:
	import urlparse
	urllib.parse = urlparse
else:
	import urllib.parse

ClonedResourceDetails = collections.namedtuple('ClonedResourceDetails', ['mime_type', 'size'])

class WebPageCloner(object):
	"""
	This object is used to clone web pages. It will use the WebKit2GTK+ engine
	and hook signals to detect what remote resources that are loaded from the
	target URL. These resources are then written to disk.
	"""
	def __init__(self, target_url, dest_dir):
		"""
		:param str target_url: The URL of the target web page to clone.
		:param str dest_dir: The path of a directory to write the resources to.
		"""
		self.target_url = urllib.parse.urlparse(target_url)
		dest_dir = os.path.abspath(dest_dir)
		if not os.path.exists(dest_dir):
			os.mkdir(dest_dir)
		self.dest_dir = dest_dir
		self.logger = logging.getLogger('KingPhisher.Client.WebPageScraper')
		self.cloned_resources = collections.OrderedDict()
		self.load_started = False
		self.load_failed_event = None

		self.webview = WebKit2.WebView()
		web_context = self.webview.get_context()
		web_context.set_cache_model(WebKit2.CacheModel.DOCUMENT_VIEWER)
		self.webview.connect('decide-policy', self.signal_decide_policy)
		self.webview.connect('load-changed', self.signal_load_changed)
		self.webview.connect('load-failed', self.signal_load_failed)
		self.webview.connect('resource-load-started', self.signal_resource_load_started)
		self.webview.load_uri(target_url)

	def resource_is_on_target(self, resource):
		"""
		Test whether the resource is on the target system. This tries to match
		the hostname, scheme and port number of the resource's URI against the
		target URI.

		:return: Whether the resource is on the target or not.
		:rtype: bool
		"""
		resource_url = urllib.parse.urlparse(resource.get_property('uri'))
		if resource_url.netloc != self.target_url.netloc:
			return False
		if resource_url.scheme != self.target_url.scheme:
			return False
		rport = resource_url.port or (443 if resource_url.scheme == 'https' else 80)
		tport = self.target_url.port or (443 if self.target_url.scheme == 'https' else 80)
		if rport != tport:
			return False
		return True

	def copy_resource_data(self, resource, data):
		"""
		Copy the data from a loaded resource to a local file.

		:param resource: The resource whos data is being copied.
		:type resource: :py:class:`WebKit2.WebResource`
		:param data: The raw data of the represented resource.
		:type data: bytes, str
		"""
		resource_url_str = resource.get_property('uri')
		resource_url = urllib.parse.urlparse(resource_url_str)
		resource_path = os.path.split(resource_url.path)[0].lstrip('/')
		directory = self.dest_dir
		for part in resource_path.split('/'):
			directory = os.path.join(directory, part)
			if not os.path.exists(directory):
				os.mkdir(directory)

		resource_path = resource_url.path
		if resource_path.endswith('/'):
			resource_path += 'index.html'
		resource_path = resource_path.lstrip('/')
		resource_path = os.path.join(self.dest_dir, resource_path)
		with open(resource_path, 'wb') as file_h:
			file_h.write(data)

		mime_type = None
		response = resource.get_response()
		if response:
			mime_type = response.get_mime_type()
		crd = ClonedResourceDetails(mime_type, len(data))
		self.cloned_resources[resource_url.path] = crd
		self.logger.debug("wrote {0:,} bytes to {1}".format(crd.size, resource_path))

	def stop_cloning(self):
		"""Stop the current cloning operation if it is running."""
		if self.webview.get_property('is-loading'):
			self.webview.stop_loading()

	@property
	def load_failed(self):
		return self.load_failed_event != None

	@property
	def target_url_str(self):
		return urllib.parse.urlunparse(self.target_url)

	def wait(self):
		"""
		Wait for the cloning operation to complete and return whether the
		operation was successful or not.

		:return: True if the operation was successful.
		:rtype: bool
		"""
		while not self.load_started:
			gui_utilities.gtk_sync()
		while self.webview.get_property('is-loading'):
			gui_utilities.gtk_sync()
		return not self.load_failed

	def signal_decide_policy(self, webview, decision, decision_type):
		self.logger.debug("received policy decision request of type: {0}".format(decision_type.value_name))
		if decision_type != WebKit2.PolicyDecisionType.NAVIGATION_ACTION:
			return
		new_target_url_str = decision.get_request().get_uri()
		new_target_url = urllib.parse.urlparse(new_target_url_str)
		if new_target_url_str == self.target_url_str:
			return
		# don't allow offsite redirects
		if new_target_url.netloc != self.target_url.netloc:
			return
		self.target_url = new_target_url
		self.logger.info("updated the target url to: {0}".format(new_target_url_str))

	def cb_get_data_finish(self, resource, task):
		data = resource.get_data_finish(task)
		if not resource.get_response():
			return
		resource_url_str = resource.get_property('uri')
		if not self.resource_is_on_target(resource):
			self.logger.debug('loaded external resource: ' + resource_url_str)
			return
		self.logger.info('loaded on target resource: ' + resource_url_str)
		self.copy_resource_data(resource, data)

	def signal_load_changed(self, webview, load_event):
		self.logger.debug("load status changed to: {0}".format(load_event.value_name))
		if load_event == WebKit2.LoadEvent.STARTED:
			self.load_started = True

	def signal_load_failed(self, webview, event, uri, error):
		self.logger.warning("load failed on event: {0} for uri: {1}".format(event.value_name, uri))
		self.load_failed_event = event

	def signal_resource_load_started(self, webveiw, resource, request):
		resource.connect('finished', self.signal_resource_load_finished)

	def signal_resource_load_finished(self, resource):
		resource.get_data(callback=self.cb_get_data_finish)
