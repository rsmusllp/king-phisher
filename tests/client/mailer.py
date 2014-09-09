#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  tests/client/mailer.py
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

import re
import unittest

from king_phisher.client.mailer import *
from tests.testing import random_string

TEST_MESSAGE = """
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
	{{ tracking_dot_image_tag }}
</body>
</html>
"""

class ClientMailerTests(unittest.TestCase):
	def setUp(self):
		self.config = {
			'mailer.webserver_url': 'http://king-phisher.local/foobar',
			'server_config': {
				'server.secret_id': random_string(24),
				'server.tracking_image': "{0}.gif".format(random_string(32))
			}
		}

	def test_mailer_message_format(self):
		secret_id = re.escape(self.config['server_config']['server.secret_id'])
		tracking_image = re.escape(self.config['server_config']['server.tracking_image'])

		formatted_msg = format_message(TEST_MESSAGE, self.config)
		regexp = """(<a href=['"]https?://king-phisher.local/foobar\?id={0}['"]>)""".format(secret_id)
		self.assertRegexpMatches(formatted_msg, regexp, msg='The web server URL was not inserted correctly')
		regexp = """(<img src=['"]https?://king-phisher.local/{0}\?id={1}['"] style=['"]display:none['"] />)""".format(tracking_image, secret_id)
		self.assertRegexpMatches(formatted_msg, regexp, msg='The tracking image tag was not inserted correctly')

if __name__ == '__main__':
	unittest.main()
