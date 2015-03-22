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
import time
import urllib

from king_phisher.client import gui_utilities

from gi.repository import WebKit

if sys.version_info[0] < 3:
	import urlparse
	urllib.parse = urlparse
else:
	import urllib.parse

class WebPageCloner(object):
	"""
	This object is used to clone web pages. It will use the WebKit engine and
	hook signals to detect what remote resources that are loaded from the target
	URL. These resources are then written to disk.
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
		self.logger = logging.getLogger('WebPageScraper')
		self.cloned_resources = collections.OrderedDict()
		self.ignore_scheme = False

		self.webview = WebKit.WebView()
		self.webview.connect('navigation-policy-decision-requested', self.signal_navigation_requested)
		self.webview.connect('resource-load-finished', self.signal_resource_load_finished)
		self.webview.load_uri(target_url)

	def wait(self):
		"""
		Wait for the cloning operation to complete and return whether the
		operation was successful or not.

		:return: True if the operation was successful.
		:rtype: bool
		"""
		status = self.webview.get_property('load-status')
		while status != WebKit.LoadStatus.FAILED and status != WebKit.LoadStatus.FINISHED:
			gui_utilities.gtk_sync()
			time.sleep(0.25)
			status = self.webview.get_property('load-status')
		return status == WebKit.LoadStatus.FINISHED

	def signal_navigation_requested(self, webview, frame, request, navigation_action, policy_decision):
		resource_url_str = request.get_property('uri')
		self.logger.debug('received navigation policy decision request for uri: ' + resource_url_str)
		if resource_url_str == urllib.parse.urlunparse(self.target_url):
			return
		if len(self.cloned_resources) != 0:
			return
		self.target_url = urllib.parse.urlparse(resource_url_str)

	def signal_resource_load_finished(self, webview, frame, resource):
		resource_url_str = resource.get_property('uri')
		resource_url = urllib.parse.urlparse(resource_url_str)
		if not (resource_url.scheme == self.target_url.scheme and resource_url.netloc == self.target_url.netloc):
			self.logger.debug('loaded external resource: ' + resource_url_str)
			return
		self.logger.info('loaded target resource: ' + resource_url_str)

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

		data = resource.get_data()
		with open(resource_path, 'wb') as file_h:
			file_h.write(data.str)
		self.cloned_resources[resource_url.path] = resource.get_mime_type()
		self.logger.debug("wrote {0:,} bytes to {1}".format(data.len, resource_path))
