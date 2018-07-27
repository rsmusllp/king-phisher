#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  king_phisher/smtp_server.py
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

import asyncore
import logging
import smtpd

class BaseSMTPServer(smtpd.SMTPServer, object):
	"""
	An SMTP server useful for debugging. Messages handled by this server
	are not forwarded anywhere.
	"""
	def __init__(self, localaddr, remoteaddr=None):
		"""
		:param tuple localaddr: The local address to bind to.
		:param tuple remoteaddr: The remote address to use as an upstream SMTP relayer.
		"""
		self.logger = logging.getLogger('KingPhisher.SMTPD')
		super(BaseSMTPServer, self).__init__(localaddr, remoteaddr)
		self.logger.info("smtp server listening on {0}:{1}".format(localaddr[0], localaddr[1]))

	def process_message(self, peer, mailfrom, rcpttos, data, **kwargs):
		self.logger.info("received message from {0} ({1}) to {2}".format(mailfrom, peer[0], ', '.join(rcpttos)))

	def serve_forever(self):
		"""
		Process requests until :py:meth:`BaseSMTPServer.shutdown` is called.
		"""
		asyncore.loop()

	def shutdown(self):
		raise NotImplementedError()
