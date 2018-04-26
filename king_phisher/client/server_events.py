#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  king_phisher/client/server_events.py
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
import itertools
import logging
import ssl
import threading

from king_phisher import its
from king_phisher import serializers
from king_phisher import utilities
from king_phisher.client import client_rpc

from gi.repository import GLib
from gi.repository import GObject
import websocket

if its.mocked:
	_GObject_GObject = type('GObject.GObject', (object,), {'__module__': ''})
else:
	_GObject_GObject = GObject.GObject

_SubscriptionStub = collections.namedtuple('_SubscriptionStub', ('event_type', 'attribute'))

def event_type_filter(event_types, is_method=False):
	"""
	A decorator to filter a signal handler by the specified event types. Using
	this will ensure that the decorated function is only called for the
	specified event types and not others which may have been subscribed to
	elsewhere in the application.

	:param event_types: A single event type as a string or a list of event type strings.
	:type event_types: list, str
	:param bool is_method: Whether or not the function being decorated is a class method.
	"""
	utilities.assert_arg_type(event_types, (list, set, str, tuple))
	if isinstance(event_types, str):
		event_types = (event_types,)

	def decorator(function):
		@functools.wraps(function)
		def wrapper(*args):
			if is_method:
				_, _, event_type, _ = args
			else:
				_, event_type, _ = args
			if event_type in event_types:
				function(*args)
			return
		return wrapper
	return decorator

class ServerEventSubscriber(_GObject_GObject):
	"""
	An object which provides functionality to subscribe to events that are
	published by the remote King Phisher server instance. This object manages
	the subscriptions and forwards the events allowing consumers to connect
	to the available GObject signals.

	.. note::
		Both the :py:meth:`.ServerEventSubscriber.subscribe` and
		:py:meth:`.ServerEventSubscriber.unsubscribe` methods of
		this object internally implement reference counting for the server
		events. This makes it possible for multiple subscriptions to be created
		and deleted without interfering with each other.

	The socket is opened automatically when this object is initialized and will
	automatically attempt to reconnect if the connection is closed if the
	:py:attr:`.reconnect` attribute is true. After initializing this object,
	check the :py:attr:`.is_connected` attribute to ensure that it is properly
	connected to the server.
	"""
	__gsignals__ = {
		'db-alert-subscriptions': (GObject.SIGNAL_RUN_FIRST, None, (str, object)),
		'db-campaigns': (GObject.SIGNAL_RUN_FIRST, None, (str, object)),
		'db-campaign-types': (GObject.SIGNAL_RUN_FIRST, None, (str, object)),
		'db-companies': (GObject.SIGNAL_RUN_FIRST, None, (str, object)),
		'db-company-departments': (GObject.SIGNAL_RUN_FIRST, None, (str, object)),
		'db-credentials': (GObject.SIGNAL_RUN_FIRST, None, (str, object)),
		'db-deaddrop-connections': (GObject.SIGNAL_RUN_FIRST, None, (str, object)),
		'db-deaddrop-deployments': (GObject.SIGNAL_RUN_FIRST, None, (str, object)),
		'db-industries': (GObject.SIGNAL_RUN_FIRST, None, (str, object)),
		'db-landing-pages': (GObject.SIGNAL_RUN_FIRST, None, (str, object)),
		'db-messages': (GObject.SIGNAL_RUN_FIRST, None, (str, object)),
		'db-users': (GObject.SIGNAL_RUN_FIRST, None, (str, object)),
		'db-visits': (GObject.SIGNAL_RUN_FIRST, None, (str, object))
	}
	logger = logging.getLogger('KingPhisher.Client.ServerEventSubscriber')
	def __init__(self, rpc):
		"""
		:param rpc: The client's connected RPC instance.
		:type rpc: :py:class:`.KingPhisherRPCClient`
		"""
		super(ServerEventSubscriber, self).__init__()
		self._encoding = 'utf-8'
		self.__is_shutdown = threading.Event()
		self.__is_shutdown.clear()
		self._reconnect_event_id = None
		self.reconnect = True
		"""Whether or not the socket should attempt to reconnect itself when it has been closed."""
		self.rpc = rpc
		self._connect_event = threading.Event()
		self._subscriptions = collections.defaultdict(lambda: collections.defaultdict(int))
		self._worker_thread = None
		self.logger.info('connecting to the server event socket')
		self._ws_connect()

	def _on_close(self, _):
		if self._worker_thread is None:  # the socket was never successfully opened
			return
		getattr(self.logger, 'warning' if self.reconnect else 'info')('the server event socket has been closed')
		self._connect_event.clear()
		if self.__is_shutdown.is_set():
			return
		if self._worker_thread != threading.current_thread():
			return
		self._worker_thread = None
		if not self.reconnect:
			return
		self._reconnect_event_id = GLib.timeout_add_seconds(30, self._ws_reconnect)

	def _on_error(self, _, exception):
		self.logger.error('encountered a web socket exception', exc_info=True)

	def _on_message(self, _, message):
		if isinstance(message, bytes):
			message.decode(self._encoding)
		try:
			message = serializers.JSON.loads(message, strict=True)
		except ValueError:
			self.logger.warning('received invalid data from the server event publisher (invalid JSON)')
			return
		event = message.get('event')
		if event is None:
			self.logger.warning('received invalid data from the server event publisher (no event data)')
			return
		event_id = event.get('id')
		event_type = event.get('type')
		objects = event.get('objects')
		if not all((event_id, event_type, objects)):
			self.logger.warning('received invalid data from the server event publisher (missing event data)')
			return

		# db-<table name> events are the only ones that are valid right now
		if not event_id.startswith('db-'):
			self.logger.warning('received invalid data from the server event publisher (invalid event type)')
			return
		event_id = 'db-' + event_id[3:].replace('_', '-')
		klass = client_rpc.database_table_objects.get(event_id[3:])
		if klass is None:
			self.logger.warning('received invalid data from the server event publisher (invalid event type)')
			return
		new_objects = []
		for obj in objects:
			new_objects.append(klass(self.rpc, **obj))
		self.emit(event_id, event_type, new_objects)

	def _on_open(self, _):
		self._connect_event.set()

	def _ws_connect(self):
		self._connect_event.clear()
		self.ws = websocket.WebSocketApp(
			"ws{0}://{1}:{2}/_/ws/events/json".format('s' if self.rpc.use_ssl else '', self.rpc.host, self.rpc.port),
			header=self.rpc.headers,
			on_close=self._on_close,
			on_error=self._on_error,
			on_message=self._on_message,
			on_open=self._on_open
		)
		new_thread = threading.Thread(target=self.ws.run_forever, kwargs={'sslopt': {'cert_reqs': ssl.CERT_NONE}})
		new_thread.daemon = True
		new_thread.start()
		if not self._connect_event.wait(10):
			self.logger.error('failed to connect to the server event socket')
			return False
		self._worker_thread = new_thread
		self.logger.debug('successfully connected to the server event socket')

		for event_id, subscription_table in self._subscriptions.items():
			event_types = set(sub.event_type for sub in subscription_table)
			attributes = set(sub.attribute for sub in subscription_table)
			self._subscribe(event_id, event_types, attributes)
		return True

	def _ws_reconnect(self):
		self.logger.info('attempting to reconnect to the server event socket')
		return not self._ws_connect()

	@property
	def is_connected(self):
		"""True if the event socket is connected to the server."""
		return self._connect_event.is_set()

	def is_subscribed(self, event_id, event_type):
		"""
		Check if the client is currently subscribed to the specified server event.

		:param str event_id: The identifier of the event to subscribe to.
		:param str event_type: A sub-type for the corresponding event.
		:return: Whether or not the client is subscribed to the event.
		:rtype: bool
		"""
		return self.rpc('events/is_subscribed', event_id, event_type)

	def shutdown(self):
		"""
		Disconnect the event socket from the remote server. After the object is
		shutdown, remove events will no longer be published.

		:param int timeout: An optional timeout for how long to wait on the worker thread.
		"""
		self.__is_shutdown.set()
		self.logger.debug('shutting down the server event socket')
		worker = self._worker_thread
		if worker:
			worker.join()
			self._worker_thread = None

	def _subscribe(self, event_id, event_types, attributes):
		# same as subscribe but without reference counting
		return self.rpc('events/subscribe', event_id, event_types=list(event_types), attributes=list(attributes))

	def subscribe(self, event_id, event_types, attributes):
		"""
		Subscribe the client to the specified event published by the server.
		When the event is published the specified *attributes* of it and it's
		corresponding id and type information will be sent to the client.

		:param str event_id: The identifier of the event to subscribe to.
		:param list event_types: A list of sub-types for the corresponding event.
		:param list attributes: A list of attributes of the event object to be sent to the client.
		"""
		utilities.assert_arg_type(event_id, str, arg_pos=1)
		utilities.assert_arg_type(event_types, (list, set, tuple), arg_pos=2)
		utilities.assert_arg_type(event_types, (list, set, tuple), arg_pos=3)

		new_event_types = set(event_types)
		new_attributes = set(attributes)
		subscription_table = self._subscriptions[event_id]
		for subscription in itertools.product(event_types, attributes):
			subscription = _SubscriptionStub(*subscription)
			subscription_table[subscription] += 1
			if subscription_table[subscription] > 1:
				new_event_types.discard(subscription.event_type)
				new_attributes.discard(subscription.attribute)
		if new_event_types or new_attributes:
			self._subscribe(event_id, event_types, attributes)

	def _unsubscribe(self, event_id, event_types, attributes):
		# same as unsubscribe but without reference counting
		return self.rpc('events/unsubscribe', event_id, event_types=list(event_types), attributes=list(attributes))

	def unsubscribe(self, event_id, event_types, attributes):
		"""
		Unsubscribe from an event published by the server that the client
		previously subscribed to.

		:param str event_id: The identifier of the event to subscribe to.
		:param list event_types: A list of sub-types for the corresponding event.
		:param list attributes: A list of attributes of the event object to be sent to the client.
		"""
		utilities.assert_arg_type(event_id, str, arg_pos=1)
		utilities.assert_arg_type(event_types, (list, set, tuple), arg_pos=2)
		utilities.assert_arg_type(event_types, (list, set, tuple), arg_pos=3)

		event_types = set(event_types)
		attributes = set(attributes)
		freeable_subsriptions = collections.deque()
		subscription_table = self._subscriptions[event_id]
		for subscription in itertools.product(event_types, attributes):
			subscription = _SubscriptionStub(*subscription)
			subscription_table[subscription] -= 1
			if subscription_table[subscription] < 1:
				freeable_subsriptions.append(subscription)
		for subscription in freeable_subsriptions:
			del subscription_table[subscription]
		# to do, delete the subscription table from _subscriptions if it's empty
		remaining_event_types = [sub.event_type for sub in subscription_table]
		remaining_attributes = [sub.attribute for sub in subscription_table]
		freeable_event_types = [sub.event_type for sub in freeable_subsriptions if not sub.event_type in remaining_event_types]
		freeable_attributes = [sub.attribute for sub in freeable_subsriptions if not sub.attribute in remaining_attributes]

		if freeable_event_types or freeable_attributes:
			self._unsubscribe(event_id, freeable_event_types, freeable_attributes)
