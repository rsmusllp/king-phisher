#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  tests/templates.py
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

import unittest

from king_phisher.templates import *
from king_phisher.utilities import random_string

class TemplatesTests(unittest.TestCase):
	def test_global_variables(self):
		# prepend an alphabetic character so the result is a valid identifier
		test_key = 'a' + random_string(10)
		test_value = random_string(20)
		global_vars = {test_key: test_value}
		env = BaseTemplateEnvironment(global_vars=global_vars)
		test_string = test_string = '<html>{{ ' + test_key + ' }}</html>'
		template = env.from_string(test_string)
		result = template.render()
		self.assertTrue(test_value in result)
		self.assertFalse(test_key in result)

	def test_strings_are_not_escaped(self):
		env = BaseTemplateEnvironment()
		test_string = '<html>{{ link }}</html>'
		link = '<a href="http://kingphisher.com/">Click Me</a>'
		template = env.from_string(test_string)
		result = template.render(link=link)
		self.assertTrue(link in result)

if __name__ == '__main__':
	unittest.main()
