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
import logging
import queue
import threading
import weakref

from king_phisher import ipaddress
from king_phisher import serializers
from king_phisher import utilities
from king_phisher.server import signals
from king_phisher.server.database import models as db_models

import advancedhttpserver

EventSubscription = collections.namedtuple('EventSubscription', ('attributes', 'event_types'))

class Event(object):
	"""
	An object representing an event which occurred on the server in a way that
	is ready to be published to client subscribers.
	"""
	__slots__ = ('event_id', 'event_type', 'sources')
	def __init__(self, event_id, event_type, sources):
		self.event_id = event_id
		"""The unique string identifier of this event."""
		self.event_type = event_type
		"""The unique string identifier of the type of this event."""
		self.sources = sources
		"""The source objects which are associated with this event."""

class EventSocket(advancedhttpserver.WebSocketHandler):
	"""
	A socket through which server events are published to subscribers. This
	socket will automatically add and remove itself from the manager that is
	initialized with.
	"""
	logger = logging.getLogger('KingPhisher.Server.WebSocket.EventPublisher')
	def __init__(self, handler, manager):
		"""
		:param handler: The request handler that should be used by this socket.
		:type handler: :py:class:`advancedhttpserver.RequestHandler`
		:param manager: The manager that this event socket should register with.
		:type manager: :py:class:`.WebSocketsManager`
		"""
		handler.connection.settimeout(None)
		self._subscriptions = {}
		self.rpc_session = handler.rpc_session
		if self.rpc_session.event_socket is not None:
			self.rpc_session.event_socket.close()
		self.rpc_session.event_socket = self
		manager.add(self)
		self._manager_ref = weakref.ref(manager)
		super(EventSocket, self).__init__(handler)

	def is_subscribed(self, event_id, event_type):
		"""
		Check if the client is currently subscribed to the specified server event.

		:param str event_id: The identifier of the event to subscribe to.
		:param str event_type: A sub-type for the corresponding event.
		:return: Whether or not the client is subscribed to the event.
		:rtype: bool
		"""
		if event_id not in self._subscriptions:
			return False
		return event_type in self._subscriptions[event_id].event_types

	def on_closed(self):
		manager = self._manager_ref()
		if manager is not None:
			manager.remove(self)
		return

	def publish(self, event):
		"""
		Publish the event by sending the relevant information to the client.
		If the client has not requested to receive the information through a
		subscription, then no data will be sent.

		:param event: The object representing the data to be published.
		:type event: :py:class:`.Event`
		"""
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
		self.send_message_text(serializers.JSON.dumps(msg, pretty=False))

	def subscribe(self, event_id, event_types=None, attributes=None):
		"""
		Subscribe the client to the specified event published by the server.
		When the event is published the specified *attributes* of it and it's
		corresponding id and type information will be sent to the client.

		:param str event_id: The identifier of the event to subscribe to.
		:param list event_types: A list of sub-types for the corresponding event.
		:param list attributes: A list of attributes of the event object to be sent to the client.
		"""
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
		"""
		Unsubscribe from an event published by the server that the client
		previously subscribed to.

		:param str event_id: The identifier of the event to subscribe to.
		:param list event_types: A list of sub-types for the corresponding event.
		:param list attributes: A list of attributes of the event object to be sent to the client.
		"""
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
	def __init__(self, config, job_manager):
		"""
		:param config: Configuration to retrieve settings from.
		:type config: :py:class:`smoke_zephyr.configuration.Configuration`
		:param job_manager: A job manager instance that can be used to schedule tasks.
		:type job_manager: :py:class:`smoke_zephyr.job.JobManager`
		"""
		self.config = config
		self.web_sockets = []
		self.job_manager = job_manager
		self._ping_job = job_manager.job_add(self.ping_all, seconds=30)
		self._work_queue = queue.Queue()
		self._worker_thread = threading.Thread(target=self._worker_routine)
		self._worker_thread.start()
		signals.db_session_deleted.connect(self._sig_db_deleted)
		signals.db_session_inserted.connect(self._sig_db_inserted)
		signals.db_session_updated.connect(self._sig_db_updated)

	def _sig_db(self, event_id, event_type, targets):
		event = Event(
			event_id='db-' + event_id.replace('_', '-'),
			event_type=event_type,
			sources=targets
		)
		self._work_queue.put((self._worker_publish_event, (event,)))

	def _sig_db_deleted(self, event_id, targets, session=None):
		return self._sig_db(event_id, 'deleted', targets)

	def _sig_db_inserted(self, event_id, targets, session=None):
		return self._sig_db(event_id, 'inserted', targets)

	def _sig_db_updated(self, event_id, targets, session=None):
		return self._sig_db(event_id, 'updated', targets)

	def _worker_publish_event(self, event):
		for web_socket in self.web_sockets:
			if not isinstance(web_socket, EventSocket):
				continue
			web_socket.publish(event)

	def _worker_routine(self):
		self.logger.debug("web socket manager worker running in tid: 0x{0:x}".format(threading.current_thread().ident))
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

	def add(self, web_socket):
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
		prefix = '/'
		if self.config.get('server.vhost_directories'):
			prefix += handler.vhost + '/'
		request_path = handler.path
		if request_path.startswith(prefix):
			request_path = request_path[len(prefix):]
			if request_path == '_/ws/events/json':
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
				except Exception:
					self.logger.error('error occurred while pinging the web socket, closing it', exc_info=True)
					web_socket.close()
				else:
					continue
			disconnected.append(web_socket)
		for web_socket in disconnected:
			self.logger.debug('closing a disconnected web socket')
			self.web_sockets.remove(web_socket)

	def remove(self, web_socket):
		"""
		Remove a connected web socket from those that are currently being
		managed. If the web socket is not currently being managed, no changes
		are made.

		:param web_socket: The connected web socket.
		:type web_socket: :py:class:`advancedhttpserver.WebSocketHandler`
		"""
		if web_socket in self.web_sockets:
			self.web_sockets.remove(web_socket)

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
