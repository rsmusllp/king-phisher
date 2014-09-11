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

import os
import re
import unittest

from king_phisher.client.mailer import *
from king_phisher.client.mailer import ClientTemplateEnvironment
from king_phisher.testing import TEST_MESSAGE_TEMPLATE, TEST_MESSAGE_TEMPLATE_INLINE_IMAGE
from king_phisher.utilities import random_string

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

		formatted_msg = format_message(TEST_MESSAGE_TEMPLATE, self.config)
		regexp = """(<a href="https?://king-phisher.local/foobar\?id={0}">)""".format(secret_id)
		self.assertRegexpMatches(formatted_msg, regexp, msg='The web server URL was not inserted correctly')
		regexp = """(<img src="https?://king-phisher.local/{0}\?id={1}" style="display:none" />)""".format(tracking_image, secret_id)
		self.assertRegexpMatches(formatted_msg, regexp, msg='The tracking image tag was not inserted correctly')

	def test_client_template_environment_mode_analyze(self):
		tenv = ClientTemplateEnvironment()
		self.assertTrue(hasattr(tenv, 'attachment_images'))
		self.assertIsInstance(tenv.attachment_images, list)
		self.assertEqual(len(tenv.attachment_images), 0)

		tenv.set_mode(ClientTemplateEnvironment.MODE_ANALYZE)
		template = tenv.from_string(TEST_MESSAGE_TEMPLATE)
		template.render(dict(client=dict(), url=dict()))
		msg = 'The analysis mode failed to identify the inline image'
		self.assertListEqual(tenv.attachment_images, [TEST_MESSAGE_TEMPLATE_INLINE_IMAGE], msg=msg)

	def test_client_template_environment_mode_preview(self):
		tenv = ClientTemplateEnvironment()
		tenv.set_mode(ClientTemplateEnvironment.MODE_PREVIEW)
		self.assertTrue('inline_image' in tenv.globals)
		inline_image = tenv.globals['inline_image']
		img_tag_result = inline_image(TEST_MESSAGE_TEMPLATE_INLINE_IMAGE)
		img_tag_test = "<img src=\"file://{0}\">".format(TEST_MESSAGE_TEMPLATE_INLINE_IMAGE)
		msg = 'The preview mode failed to properly format the img HTML tag'
		self.assertEqual(img_tag_result, img_tag_test, msg=msg)

	def test_client_template_environment_mode_send(self):
		tenv = ClientTemplateEnvironment()
		tenv.set_mode(ClientTemplateEnvironment.MODE_SEND)
		self.assertTrue('inline_image' in tenv.globals)
		inline_image = tenv.globals['inline_image']
		img_tag_result = inline_image(TEST_MESSAGE_TEMPLATE_INLINE_IMAGE)
		img_tag_test = "<img src=\"cid:{0}\">".format(os.path.basename(TEST_MESSAGE_TEMPLATE_INLINE_IMAGE))
		msg = 'The send mode failed to properly format the img HTML tag'
		self.assertEqual(img_tag_result, img_tag_test, msg=msg)

if __name__ == '__main__':
	unittest.main()
