#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  tests/pipfile.py
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
import os
import unittest

from king_phisher import testing

class PipfileLockTests(testing.KingPhisherTestCase):
	pipfile_lock_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'Pipfile.lock'))
	def test_blacklisted_packages_are_not_present(self):
		with open(self.pipfile_lock_path, 'r') as file_h:
			pipfile_lock = json.load(file_h)
		meta = pipfile_lock.get('_meta', {})
		self.assertEqual(meta.get('pipfile-spec'), 6, msg="incompatible specification version, this test must be reviewed")
		packages = pipfile_lock.get('default', {})
		self.assertIsNotEmpty(packages)
		# a list of packages to blacklist from the default group
		blacklisted_package_names = (
			'alabaster',
			'sphinx',
			'sphinx-rtd-theme',
			'sphinxcontrib-websupport'
		)
		for package_name in blacklisted_package_names:
			message = "blacklisted package '{}' found in the Pipfile.lock default group".format(package_name)
			self.assertNotIn(package_name, packages, msg=message)

if __name__ == '__main__':
	unittest.main()
