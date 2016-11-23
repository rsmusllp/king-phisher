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

import collections
import unittest

from king_phisher import testing
from king_phisher.client import server_events

class FakeServerEventSubscriber(server_events.ServerEventSubscriber):
	def __init__(self, *args, **kwargs):
		super(FakeServerEventSubscriber, self).__init__(*args, **kwargs)
		self.reinit_test_tables()

	def reinit_test_tables(self):
		self.subscribed = collections.defaultdict(lambda: collections.defaultdict(set))
		self.unsubscribed = collections.defaultdict(lambda: collections.defaultdict(set))

	def _subscribe(self, event_id, event_types, attributes):
		table = self.subscribed[event_id]
		table['event_types'] = set(event_types)
		table['attributes'] = set(attributes)

	def _unsubscribe(self, event_id, event_types, attributes):
		table = self.unsubscribed[event_id]
		table['event_types'] = set(event_types)
		table['attributes'] = set(attributes)

	def _ws_connect(self, *args, **kwargs):
		pass

class ServerEventSubscriberTests(testing.KingPhisherTestCase):
	def test_reference_counting(self):
		subscriber = FakeServerEventSubscriber(rpc=None)
		event_id = 'db-visits'
		event_types = ('deleted', 'inserted', 'updated')
		attributes = ('id', 'campaign_id')

		subscriber.reinit_test_tables()
		subscriber.subscribe(event_id, event_types, attributes)
		self.assertIn(event_id, subscriber.subscribed)
		table = subscriber.subscribed[event_id]
		self.assertSetEqual(table['event_types'], set(event_types))
		self.assertSetEqual(table['attributes'], set(attributes))

		subscriber.reinit_test_tables()
		subscriber.subscribe(event_id, (event_types[0],), (attributes[0],))
		self.assertNotIn(event_id, subscriber.subscribed)
		table = subscriber.subscribed[event_id]
		self.assertSetEqual(table['event_types'], set())
		self.assertSetEqual(table['attributes'], set())

		subscriber.reinit_test_tables()
		subscriber.unsubscribe(event_id, event_types, attributes)
		self.assertIn(event_id, subscriber.unsubscribed)
		table = subscriber.unsubscribed[event_id]
		self.assertSetEqual(table['event_types'], set(event_types[1:]))
		self.assertSetEqual(table['attributes'], set(attributes[1:]))

		subscriber.reinit_test_tables()
		subscriber.unsubscribe(event_id, (event_types[0],), (attributes[0],))
		self.assertIn(event_id, subscriber.unsubscribed)
		table = subscriber.unsubscribed[event_id]
		self.assertSetEqual(table['event_types'], set((event_types[0],)))
		self.assertSetEqual(table['attributes'], set((attributes[0],)))

if __name__ == '__main__':
	unittest.main()
