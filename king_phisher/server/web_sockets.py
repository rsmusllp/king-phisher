#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  king_phisher/server/web_sockets.py
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
import functools
import logging
import threading

from king_phisher import ipaddress
from king_phisher import its
from king_phisher import json_ex
from king_phisher import utilities
from king_phisher.server import signals
from king_phisher.server.database import models as db_models

import advancedhttpserver

if its.py_v2:
	import Queue as queue
else:
	import queue

Event = collections.namedtuple('Event', ('event_id', 'event_type', 'sources'))
EventSubscription = collections.namedtuple('EventSubscription', ('attributes', 'event_types'))

class EventSocket(advancedhttpserver.WebSocketHandler):
	"""
	A socket through which server events are published to subscribers.
	"""
	logger = logging.getLogger('KingPhisher.Server.WebSocket.EventPublisher')
	def __init__(self, handler, manager):
		handler.server.throttle_semaphore.release()
		self._subscriptions = {}
		self.rpc_session = handler.rpc_session
		if self.rpc_session.event_socket is not None:
			self.rpc_session.event_socket.close()
		self.rpc_session.event_socket = self
		manager.append(self)
		super(EventSocket, self).__init__(handler)

	def is_subscribed(self, event_id, event_type):
		if event_id not in self._subscriptions:
			return False
		return event_type in self._subscriptions[event_id].event_types

	def on_closed(self):
		self.handler.server.throttle_semaphore.acquire()
		return

	def publish(self, event):
		subscription = self._subscriptions.get(event.event_id)
		if subscription is None:
			return
		if event.event_type not in subscription.event_types:
			return
		summaries = []
		for source in event.sources:
			if isinstance(source, db_models.Base) and not source.session_has_permissions('r', self.rpc_session):
				continue
			summary = dict((attribute, getattr(source, attribute, None)) for attribute in subscription.attributes)
			summaries.append(summary)
		if not summaries:
			return

		msg = {
			'event': {
				'id': event.event_id,
				'type': event.event_type,
				'objects': summaries
			}
		}
		self.logger.debug("publishing event {0} (type: {1}) with {2} objects".format(event.event_id, event.event_type, len(summaries)))
		self.send_message_text(json_ex.dumps(msg, pretty=False))

	def subscribe(self, event_id, event_types=None, attributes=None):
		utilities.assert_arg_type(event_id, str, arg_pos=1)
		utilities.assert_arg_type(event_types, (type(None), list, set, tuple), arg_pos=2)
		utilities.assert_arg_type(event_types, (type(None), list, set, tuple), arg_pos=3)

		subscription = self._subscriptions.get(event_id)
		if subscription is None:
			subscription = EventSubscription(attributes=set(), event_types=set())
		if event_types is not None:
			subscription.event_types.update(event_types)
		if attributes is not None:
			subscription.attributes.update(attributes)
		self._subscriptions[event_id] = subscription

	def unsubscribe(self, event_id, event_types=None, attributes=None):
		utilities.assert_arg_type(event_id, str, arg_pos=1)
		utilities.assert_arg_type(event_types, (type(None), list, set, tuple), arg_pos=2)
		utilities.assert_arg_type(event_types, (type(None), list, set, tuple), arg_pos=3)

		subscription = self._subscriptions.get(event_id)
		if subscription is None:
			return
		if event_types is not None:
			for event_type in event_types:
				subscription.event_types.discard(event_type)
		if attributes is not None:
			for attribute in attributes:
				subscription.attributes.discard(attribute)
		if not subscription.event_types and not subscription.attributes:
			del self._subscriptions[event_id]

class WebSocketsManager(object):
	"""
	An object used to manage connected web sockets.
	"""
	logger = logging.getLogger('KingPhisher.Server.WebSocketManager')
	def __init__(self, job_manager):
		"""
		:param job_manager: A job manager instance that can be used to schedule tasks.
		:type job_manager: :py:class:`smoke_zephyr.job.JobManager`
		"""
		self.web_sockets = []
		self.job_manager = job_manager
		self._ping_job = job_manager.job_add(self.ping_all, seconds=20)
		self._work_queue = queue.Queue()
		self._worker_thread = threading.Thread(target=self._worker_routine)
		self._worker_thread.start()
		signals.db_session_deleted.connect(self._sig_db_deleted)
		signals.db_session_inserted.connect(self._sig_db_inserted)
		signals.db_session_updated.connect(self._sig_db_updated)

	def _sig_db(self, event_type, table_name, targets):
		event = Event(
			event_id='db-' + table_name,
			event_type=event_type,
			sources=targets
		)
		self._work_queue.put((self._worker_publish_event, (event,)))

	def _sig_db_deleted(self, table_name, targets, session):
		self._sig_db('deleted', table_name, targets)

	def _sig_db_inserted(self, table_name, targets, session):
		self._sig_db('inserted', table_name, targets)

	def _sig_db_updated(self, table_name, targets, session):
		self._sig_db('updated', table_name, targets)

	def _worker_publish_event(self, event):
		for web_socket in self.web_sockets:
			if not isinstance(web_socket, EventSocket):
				continue
			web_socket.publish(event)

	def _worker_routine(self):
		while True:
			job = self._work_queue.get()
			if job is None:
				break
			func, args = job
			try:
				func(*args)
			except Exception:
				self.logger.error('web socket manager worker thread encountered an exception while processing a job', exc_info=True)

	def __iter__(self):
		for web_socket in self.web_sockets:
			yield web_socket

	def __len__(self):
		return len(self.web_sockets)

	def append(self, web_socket):
		"""
		Add a connected web socket to the manager.
		:param web_socket: The connected web socket.
		:type web_socket: :py:class:`advancedhttpserver.WebSocketHandler`
		"""
		utilities.assert_arg_type(web_socket, advancedhttpserver.WebSocketHandler)
		self.web_sockets.append(web_socket)

	def dispatch(self, handler):
		"""
		A method that is suitable for use as a
		:py:attr:`~advancedhttpserver.RequestHandler.web_socket_handler`.

		:param handler: The current request handler instance.
		:type handler: :py:class:`~king_phisher.server.server.KingPhisherRequestHandler`
		"""
		if not ipaddress.ip_address(handler.client_address[0]).is_loopback:
			return
		if handler.path == '/_/ws/events/json':
			EventSocket(handler, self)
			return
		handler.respond_not_found()
		return

	def ping_all(self):
		"""
		Ping all of the connected web sockets to ensure they stay alive. This
		method is automatically executed periodically through a job added when
		the manager is initialized.
		"""
		disconnected = collections.deque()
		for web_socket in self.web_sockets:
			if web_socket.connected:
				try:
					web_socket.ping()
				except:
					self.logger.info('error occurred while pinging the web socket, closing it')
					web_socket.close()
				else:
					continue
			disconnected.append(web_socket)
		for web_socket in disconnected:
			self.web_sockets.remove(web_socket)

	def pop(self, index=None):
		"""
		Remove a connected web socket from those that are currently being
		managed.

		:param int index: An optional index of the web socket to remove.
		:return: The removed web socket.
		:rtype: :py:class:`advancedhttpserver.WebSocketHandler`
		"""
		return self.web_sockets.pop(index)

	def stop(self):
		"""
		Shutdown the manager and clean up the resources it has allocated.
		"""
		self.job_manager.job_delete(self._ping_job)
		for web_socket in self.web_sockets:
			if web_socket.connected:
				web_socket.close()
		self.web_sockets = []

		self._work_queue.put(None)
		self._worker_thread.join()
