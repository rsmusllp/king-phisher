#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  tests/sms.py
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

import platform
import sys
import unittest

from king_phisher import plugins
from king_phisher import testing
from king_phisher import version

class PluginRequirementsTests(testing.KingPhisherTestCase):
	def _test_requirement(self, requirement, case_true, case_false):
		requirements = plugins.Requirements([(requirement, case_true)])
		self.assertTrue(requirements.is_compatible)

		requirements = plugins.Requirements([(requirement, case_false)])
		self.assertFalse(requirements.is_compatible)

	def test_empty_requirements(self):
		requirements = plugins.Requirements({})
		self.assertTrue(requirements.is_compatible, 'no requirements means compatible')

	def test_req_minimum_python_version(self):
		version_info = sys.version_info
		self._test_requirement(
			'minimum-python-version',
			"{0}.{1}".format(version_info.major, version_info.minor),
			"{0}.{1}".format(version_info.major, version_info.minor + 1)
		)

	def test_req_minimum_version(self):
		version_info = version.version_info
		self._test_requirement(
			'minimum-version',
			version.distutils_version,
			"{0}.{1}".format(version_info.major, version_info.minor + 1)
		)

	def test_req_platforms(self):
		self._test_requirement(
			'platforms',
			[],
			['Foobar']
		)
		self._test_requirement(
			'platforms',
			[platform.system().lower()],
			['Foobar']
		)

if __name__ == '__main__':
	unittest.main()
