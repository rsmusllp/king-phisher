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

import logging
import ssl
import threading

from king_phisher import json_ex
from king_phisher import utilities
from king_phisher.client import client_rpc

from gi.repository import GObject
import websocket

if isinstance(GObject.GObject, utilities.Mock):
	_GObject_GObject = type('GObject.GObject', (object,), {'__module__': ''})
else:
	_GObject_GObject = GObject.GObject

class ServerEventsSubscriber(_GObject_GObject):
	"""
	An object which provides functionality to subscribe to events that are
	published by the remote King Phisher server instance. This object manages
	the subscriptions and forwards the events allowing consumers to connect
	to the available GObject signals.
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
	logger = logging.getLogger('KingPhisher.Client.ServerEventsSubscriber')
	def __init__(self, rpc):
		"""
		:param rpc: The client's connected RPC instance.
		:py:class:`.KingPhisherRPCClient`
		"""
		super(ServerEventsSubscriber, self).__init__()
		self._encoding = 'utf-8'
		self.rpc = rpc
		self._connect_event = threading.Event()
		self._worker_thread = None
		self._ws_connect()

	def _on_close(self, _):
		self._connect_event.clear()

	def _on_message(self, _, message):
		if isinstance(message, bytes):
			message.decode(self._encoding)
		try:
			message = json_ex.loads(message, strict=True)
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
			on_message=self._on_message,
			on_open=self._on_open
		)
		self._worker_thread = threading.Thread(target=self.ws.run_forever, kwargs={'sslopt': {'cert_reqs': ssl.CERT_NONE}})
		self._worker_thread.start()
		self._connect_event.wait()

	def is_subscribed(self, event_id, event_type):
		"""
		Check if the client is currently subscribed to the remote event.

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
		"""
		self.ws.close()
		self._worker_thread.join()

	def subscribe(self, event_id, event_types=None, attributes=None):
		"""
		Subscribe to an event published by the server.

		:param str event_id: The identifier of the event to subscribe to.
		:param list event_types: A list of sub-types for the corresponding event.
		:param list attributes: A list of attributes of the event object to be sent to the client.
		"""
		return self.rpc('events/subscribe', event_id, event_types=event_types, attributes=attributes)

	def unsubscribe(self, event_id, event_types=None, attributes=None):
		"""
		Unsubscribe from an event published by the server that the client
		previously subscribed to.

		:param str event_id: The identifier of the event to subscribe to.
		:param list event_types: A list of sub-types for the corresponding event.
		:param list attributes: A list of attributes of the event object to be sent to the client.
		"""
		return self.rpc('events/unsubscribe', event_id, event_types=event_types, attributes=attributes)
