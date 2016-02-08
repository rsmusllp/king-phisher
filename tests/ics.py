#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  tests/ics.py
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

import datetime
import os
import unittest

from king_phisher import testing
from king_phisher import ics

import icalendar
import smoke_zephyr.utilities

class ICSTests(testing.KingPhisherTestCase):
	def assertParsedTimezoneOffsetDetailsMatch(self, tz_name, expected):
		env_var = ics.get_tz_posix_env_var(tz_name)
		details = ics.parse_tz_posix_env_var(env_var)
		self.assertIsNotNone(details)
		self.assertEqual(details, expected, msg='offset details differ from what was expected')

	def test_parse_tz_posix_env_var_america_new_york(self):
		expected = ics.TimezoneOffsetDetails(
			offset=datetime.timedelta(-1, 68400),
			offset_dst=datetime.timedelta(-1, 64800),
			dst_start=icalendar.vRecur({
				'BYMONTH': '3',
				'FREQ': 'YEARLY',
				'INTERVAL': 1,
				'BYDAY': '2SU'
			}),
			dst_end=icalendar.vRecur({
				'BYMONTH': '11',
				'FREQ': 'YEARLY',
				'INTERVAL': 1,
				'BYDAY': '1SU'
			})
		)
		self.assertParsedTimezoneOffsetDetailsMatch('America/New_York', expected)

	def test_parse_tz_posix_env_var_australia_melbourne(self):
		expected = ics.TimezoneOffsetDetails(
			offset=datetime.timedelta(0, 36000),
			offset_dst=datetime.timedelta(0, 32400),
			dst_start=icalendar.vRecur({
				'BYMONTH': '10',
				'FREQ': 'YEARLY',
				'INTERVAL': 1,
				'BYDAY': '1SU'
			}),
			dst_end=icalendar.vRecur({
				'BYMONTH': '4',
				'FREQ': 'YEARLY',
				'INTERVAL': 1,
				'BYDAY': '1SU'
			})
		)
		self.assertParsedTimezoneOffsetDetailsMatch('Australia/Melbourne', expected)

	def test_posix_tz_var_extraction(self):
		for path in smoke_zephyr.utilities.FileWalker(ics.zoneinfo_path, absolute_path=True, skip_dirs=True):
			tz_name = os.path.relpath(path, ics.zoneinfo_path)
			# blacklist of timezones to ignore
			if tz_name.split(os.sep, 1)[-1] == 'Factory':
				continue

			with open(path, 'rb') as file_h:
				# only version 2 TZ files have the variable defined
				if file_h.read(5) != b'TZif2':
					continue
			env_var = ics.get_tz_posix_env_var(tz_name)
			self.assertIsInstance(env_var, str)
			if not env_var:
				continue
			details = ics.parse_tz_posix_env_var(env_var)
			self.assertIsInstance(details, ics.TimezoneOffsetDetails, msg="failed to parse environment variable: '{0}' for zone: '{1}'".format(env_var, tz_name))

	def test_posix_tz_data_directory_exists(self):
		self.assertTrue(os.path.isdir(ics.zoneinfo_path), msg='the timezone data files are not present')

if __name__ == '__main__':
	unittest.main()
