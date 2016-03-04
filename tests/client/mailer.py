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

from king_phisher import testing
from king_phisher.client.mailer import *
from king_phisher.templates import MessageTemplateEnvironment
from king_phisher.utilities import random_string

class ClientMailerTests(testing.KingPhisherTestCase):
	def setUp(self):
		self.config = {
			'mailer.webserver_url': 'http://king-phisher.local/foobar',
			'server_config': {
				'server.secret_id': random_string(24),
				'server.tracking_image': "{0}.gif".format(random_string(32))
			}
		}
		self.image_cid_regex = r'img_[a-z0-9]{8}' + re.escape(os.path.splitext(testing.TEST_MESSAGE_TEMPLATE_INLINE_IMAGE)[-1])

	def test_mailer_guess_smtp_server_address(self):
		random_host = random_string(7) + '.' + random_string(7) + '.' + random_string(3)
		self.assertIsNone(guess_smtp_server_address('localhost'))
		self.assertIsNone(guess_smtp_server_address('127.0.0.1'))
		self.assertIsNone(guess_smtp_server_address('::1'))
		self.assertIsNone(guess_smtp_server_address('localhost', 'localhost'))
		self.assertIsNone(guess_smtp_server_address('localhost', random_host))

		self.assertEqual(str(guess_smtp_server_address('10.0.0.1')), '10.0.0.1')
		self.assertEqual(str(guess_smtp_server_address('10.0.0.1', random_host)), '10.0.0.1')
		self.assertEqual(str(guess_smtp_server_address('127.0.0.1', '10.0.0.1')), '10.0.0.1')
		self.assertEqual(str(guess_smtp_server_address('::1', '10.0.0.1')), '10.0.0.1')
		self.assertEqual(str(guess_smtp_server_address('localhost', '10.0.0.1')), '10.0.0.1')
		self.assertEqual(str(guess_smtp_server_address('10.0.0.1', 'localhost')), '10.0.0.1')
		self.assertEqual(str(guess_smtp_server_address('10.0.0.1', '10.0.0.2')), '10.0.0.1')

	def test_mailer_message_format(self):
		secret_id = re.escape(self.config['server_config']['server.secret_id'])
		tracking_image = re.escape(self.config['server_config']['server.tracking_image'])

		formatted_msg = render_message_template(testing.TEST_MESSAGE_TEMPLATE, self.config)
		regexp = r"""(<a href="https?://king-phisher.local/foobar\?id={0}">)""".format(secret_id)
		self.assertRegex(formatted_msg, regexp, msg='The web server URL was not inserted correctly')
		regexp = r"""(<img src="https?://king-phisher.local/{0}\?id={1}" style="display:none" />)""".format(tracking_image, secret_id)
		self.assertRegex(formatted_msg, regexp, msg='The tracking image tag was not inserted correctly')

	def test_client_template_environment_mode_analyze(self):
		tenv = MessageTemplateEnvironment()
		self.assertTrue(hasattr(tenv, 'attachment_images'))
		self.assertIsInstance(tenv.attachment_images, dict)
		self.assertEqual(len(tenv.attachment_images), 0)

		tenv.set_mode(MessageTemplateEnvironment.MODE_ANALYZE)
		template = tenv.from_string(testing.TEST_MESSAGE_TEMPLATE)
		template.render(dict(client=dict(), url=dict()))
		msg = 'The analysis mode failed to identify the inline image'
		self.assertIn(testing.TEST_MESSAGE_TEMPLATE_INLINE_IMAGE, tenv.attachment_images, msg=msg)
		cid_value = tenv.attachment_images[testing.TEST_MESSAGE_TEMPLATE_INLINE_IMAGE]
		self.assertRegex(cid_value, self.image_cid_regex)

	def test_client_template_environment_mode_preview(self):
		tenv = MessageTemplateEnvironment()
		tenv.set_mode(MessageTemplateEnvironment.MODE_PREVIEW)
		self.assertTrue('inline_image' in tenv.globals)
		inline_image = tenv.globals['inline_image']
		img_tag_result = inline_image(testing.TEST_MESSAGE_TEMPLATE_INLINE_IMAGE)
		img_tag_test = "<img src=\"file://{0}\">".format(testing.TEST_MESSAGE_TEMPLATE_INLINE_IMAGE)
		msg = 'The preview mode failed to properly format the img HTML tag'
		self.assertEqual(img_tag_result, img_tag_test, msg=msg)

	def test_client_template_environment_mode_send(self):
		tenv = MessageTemplateEnvironment()
		tenv.set_mode(MessageTemplateEnvironment.MODE_SEND)
		self.assertTrue('inline_image' in tenv.globals)
		inline_image = tenv.globals['inline_image']
		img_tag_result = inline_image(testing.TEST_MESSAGE_TEMPLATE_INLINE_IMAGE)
		img_tag_test = r'<img src="cid:'
		img_tag_test += self.image_cid_regex
		img_tag_test += r'">'
		msg = 'The send mode failed to properly format the img HTML tag'
		self.assertRegex(img_tag_result, img_tag_test, msg=msg)

if __name__ == '__main__':
	unittest.main()
