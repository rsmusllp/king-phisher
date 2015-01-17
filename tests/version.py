#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  tests/version.py
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

import json
import re
import urllib2
import unittest

from king_phisher import testing
from king_phisher.version import *

class VersionTests(testing.KingPhisherTestCase):
	def test_version_info(self):
		if version_label:
			self.assertIn(version_label, ('alpha', 'beta'), msg='the version label is invalid')
		version_regex = r'^\d+\.\d+\.\d+(-(alpha|beta))?$'
		self.assertRegexMatches(version, version_regex, msg='the version format is invalid')
		version_regex = r'^\d+\.\d+\.\d+((a|b)\d)?$'
		self.assertRegexMatches(distutils_version, version_regex, msg='the distutils version format is invalid')

	@testing.skip_on_travis
	def test_github_releases(self):
		url_h = urllib2.urlopen('https://api.github.com/repos/securestate/king-phisher/releases')
		releases = json.load(url_h)
		url_h.close()
		releases = filter(lambda release: not release['draft'], releases)
		for release in releases:
			tag_name_regex = r'v\d+\.\d+\.\d+'
			tag_name = release['tag_name']
			self.assertRegexMatches(tag_name, tag_name_regex, msg='the release tag name is invalid')
			name = "{0}: Version {1}".format(tag_name, tag_name[1:])
			self.assertEqual(name, release['name'], msg='the release name is invalid')

if __name__ == '__main__':
	unittest.main()
