#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  tests/server/graphql.py
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

from king_phisher import its
from king_phisher import version
from king_phisher.server import aaa
from king_phisher.server.database import manager as db_manager
from king_phisher.server.database import models as db_models
from king_phisher.server.graphql import schema
from king_phisher.testing import KingPhisherTestCase

graphql_schema = schema.Schema()

class ServerGraphQLTests(KingPhisherTestCase):
	def test_query_plugins(self):
		result = graphql_schema.execute("{ plugins { edges { node { name } } } }")
		self.assertIn('plugins', result.data)
		plugins = result.data['plugins']['edges']
		self.assertIsInstance(plugins, list)
		self.assertEqual(len(plugins), 0)

	def test_query_version(self):
		result = graphql_schema.execute("{ version }")
		self.assertEquals(result.data['version'], version.version)

class ServerGraphQLDatabaseTests(ServerGraphQLTests):
	def setUp(self):
		try:
			db_manager.init_database('sqlite://')
		except Exception as error:
			self.fail("failed to initialize the database (error: {0})".format(error.__class__.__name__))
		alice = db_models.User(name='alice', otp_secret='secret')
		calie = db_models.User(name='calie', otp_secret='secret')
		self._session = db_manager.Session()
		self._session.add(alice)
		self._session.add(calie)
		self._session.commit()
		self.users = {'alice': alice, 'calie': calie}

	def tearDown(self):
		self._session.close()

	def test_query_auth_middleware_no_session(self):
		session = db_manager.Session()
		result = graphql_schema.execute(
			"{ db { users { edges { node { id otpSecret } } } } }",
			context_value={'session': session}
		)
		users = result.data['db']['users']['edges']
		self.assertEquals(len(users), 2)
		self.assertEquals(users[0]['node']['otpSecret'], 'secret')
		self.assertEquals(users[1]['node']['otpSecret'], 'secret')

	def test_query_auth_middleware_session(self):
		session = db_manager.Session()
		db_user = self.users['alice']
		rpc_session = aaa.AuthenticatedSession(db_user)
		result = graphql_schema.execute(
			"{ db { users { edges { node { id name otpSecret } } } } }",
			context_value={'rpc_session': rpc_session, 'session': session}
		)
		users = result.data['db']['users']['edges']
		self.assertEquals(len(users), 2)
		self.assertEquals(users[0]['node']['id'], str(db_user.id))
		self.assertEquals(users[0]['node']['name'], db_user.name)
		self.assertEquals(users[0]['node']['otpSecret'], 'secret')
		self.assertIsNone(users[1]['node']['otpSecret'])

	def test_query_get_node(self):
		session = db_manager.Session()
		result = graphql_schema.execute(
			"{ db { users(first: 1) { total edges { cursor node { id } } } } }",
			context_value={'session': session}
		)
		users = result.data['db']['users']
		self.assertEquals(users['total'], 2)
		self.assertIn('edges', users)
		self.assertEqual(len(users['edges']), 1)
		edge = users['edges'][0]
		self.assertIn('cursor', edge)
		self.assertIsInstance(edge['cursor'], (unicode if its.py_v2 else str))
		self.assertIn('node', edge)
		self.assertIsInstance(edge['node'], dict)

	def test_query_get_total(self):
		session = db_manager.Session()
		result = graphql_schema.execute(
			"{ db { users { total } } }",
			context_value={'session': session}
		)
		self.assertEquals(result.data['db']['users']['total'], 2)

	def test_query_get_pageinfo(self):
		session = db_manager.Session()
		result = graphql_schema.execute(
			"{ db { users(first: 1) { total pageInfo { hasNextPage } } } }",
			context_value={'session': session}
		)
		users = result.data['db']['users']
		self.assertEquals(users['total'], 2)
		self.assertIn('pageInfo', users)
		self.assertTrue(users['pageInfo'].get('hasNextPage', False))
