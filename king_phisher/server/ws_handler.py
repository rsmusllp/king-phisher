#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  king_phisher/server/ws_handler.py
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

import collections
import logging

from king_phisher import ipaddress
from king_phisher import json_ex
from king_phisher.server import signals

import advancedhttpserver

def dispatcher(_, handler):
	if not ipaddress.ip_address(handler.client_address[0]).is_loopback:
		return False
	if handler.path == '/_/ws/events/json':
		return EventPublisher(handler)
	handler.respond_not_found()
	return

class EventPublisher(advancedhttpserver.WebSocketHandler):
	logger = logging.getLogger('KingPhisher.Server.EventPublisher')
	def __init__(self, handler):
		handler.server.throttle_semaphore.release()
		self.event_subscriptions = collections.defaultdict(set)
		# signal subscriptions
		signals.db_session_deleted.connect(self.sig_db_deleted)
		signals.db_session_inserted.connect(self.sig_db_inserted)
		signals.db_session_updated.connect(self.sig_db_updated)
		super(EventPublisher, self).__init__(handler)

	def on_closed(self):
		self.handler.server.throttle_semaphore.acquire()
		return

	def on_message_text(self, message):
		try:
			message = json_ex.loads(message)
		except ValueError:
			self.logger.error('received a message with invalid json data (serializer loads error)')
			return
		if not isinstance(message, dict):
			self.logger.error('received a message with invalid json data (message type error)')
			return
		action = message.get('action')
		if not isinstance(action, str):
			self.logger.error("received a message with invalid action: {0!r}".format(action))
			return
		action_handler = getattr(self, 'action_' + action, None)
		if action_handler is None:
			self.logger.error('received a message with unknown action: ' + action)
			return
		self.logger.debug('received a message with action: ' + action)
		args = message.get('args', [])
		if not isinstance(args, (list, tuple)):
			self.logger.error('received a message with invalid arguments')
			return
		try:
			action_handler(*args)
		except Exception:
			self.logger.error('an error occurred while handling action: ' + action)

	def _iter_subscription_items(self, items):
		for key, value in items.items():
			if not isinstance(key, str):
				continue
			if isinstance(value, (int, str, bool)):
				yield key, value
				continue
			if not isinstance(value, (list, tuple)):
				self.logger.warning("can not process subscription item {0!r} for {1}".format(value, key))
			for subvalue in value:
				yield key, subvalue

	def action_subscribe(self, items):
		for key, value in self._iter_subscription_items(items):
			self.event_subscriptions[key].add(value)

	def action_unsubscribe(self, items):
		for key, value in self._iter_subscription_items(items):
			self.event_subscriptions[key].discard(value)

	def send_db_event(self, event_type, sender, targets, session):
		for target in targets:
			if not target.session_has_read_access(self.handler.rpc_session):
				continue
			print(repr((event_type, sender, targets, session)))

	def sig_db_deleted(self, sender, targets, session):
		self.send_db_event('deleted', sender, targets, session)

	def sig_db_inserted(self, sender, targets, session):
		self.send_db_event('inserted', sender, targets, session)

	def sig_db_updated(self, sender, targets, session):
		self.send_db_event('updated', sender, targets, session)
