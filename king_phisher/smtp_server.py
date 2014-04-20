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
import smtpd
import logging
import time

from king_phisher import utilities

import dns.resolver

__version__ = '0.1.0'

class KingPhisherSMTPServer(smtpd.PureProxy, object):
	def __init__(self, localaddr, remoteaddr, debugging = False):
		self.debugging = debugging
		self.logger = logging.getLogger('KingPhisher.SMTPD')
		super(KingPhisherSMTPServer, self).__init__(localaddr, remoteaddr)
		self.logger.info("open relay listening on {0}:{1}".format(localaddr[0], localaddr[1]))
		if self.debugging:
			self.logger.warning('debugging mode is enabled, all messages will be dropped')

	@utilities.cache('6h')
	def get_smtp_servers(self, domain_name):
		try:
			smtp_servers = dns.resolver.query(domain_name, 'MX')
		except dns.resolver.NoAnswer:
			smtp_servers = ()
		else:
			smtp_servers = tuple(map(lambda r: str(r.exchange).rstrip('.'), smtp_servers))
		return smtp_servers

	def process_message(self, peer, mailfrom, rcpttos, data):
		self.logger.info("received message from {0} ({1}) to {2}".format(mailfrom, peer[0], ', '.join(rcpttos)))
		if self.debugging:
			return
		super(KingPhisherSMTPServer, self).process_message(peer, mailfrom, rcpttos, data)

	def serve_forever(self):
		asyncore.loop()
