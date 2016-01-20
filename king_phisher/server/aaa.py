#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  king_phisher/server/authenticator.py
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

import base64
import grp
import hashlib
import json
import logging
import os
import pwd
import random
import select
import string
import threading
import time

from king_phisher import errors
from king_phisher import its
from king_phisher import utilities
from king_phisher.server.database import manager as db_manager
from king_phisher.server.database import models as db_models
from king_phisher.third_party import pam

import smoke_zephyr.utilities

__all__ = ('AuthenticatedSessionManager', 'ForkedAuthenticator')

def get_groups_for_user(username):
	"""
	Get the groups that a user is a member of.

	:param str username: The user to lookup group membership for.
	:rtype: set
	:return: The names of the groups that the user is a member of.
	"""
	groups = set(g.gr_name for g in grp.getgrall() if username in g.gr_mem)
	groups.add(grp.getgrgid(pwd.getpwnam(username).pw_gid).gr_name)
	return groups

class AuthenticatedSession(object):
	"""A container to store information associated with an authenticated session."""
	__slots__ = ('user', 'created', 'last_seen')
	def __init__(self, user):
		"""
		:param user: The unique identifier for the authenticated user.
		"""
		self.user = user
		self.created = time.time()
		self.last_seen = self.created

	def __repr__(self):
		return "<{0} user={1} >".format(self.__class__.__name__, self.user)

	@classmethod
	def from_db_authenticated_session(cls, stored_session):
		utilities.assert_arg_type(stored_session, db_models.AuthenticatedSession)
		session = cls(stored_session.user_id)
		session.created = stored_session.created
		session.last_seen = stored_session.last_seen
		return session

class AuthenticatedSessionManager(object):
	"""A container for managing authenticated sessions."""
	def __init__(self, timeout='30m'):
		"""
		:param timeout: The length of time in seconds for which sessions are valid.
		:type timeout: int, str
		"""
		self.logger = logging.getLogger('KingPhisher.Server.SessionManager')
		timeout = smoke_zephyr.utilities.parse_timespan(timeout)
		self.session_timeout = timeout
		self._sessions = {}
		self._lock = threading.Lock()

		# get valid sessions from the database
		expired = 0
		session = db_manager.Session()
		for stored_session in session.query(db_models.AuthenticatedSession):
			if stored_session.last_seen < time.time() - self.session_timeout:
				expired += 1
				continue
			auth_session = AuthenticatedSession.from_db_authenticated_session(stored_session)
			self._sessions[stored_session.id] = auth_session
		session.query(db_models.AuthenticatedSession).delete()
		session.commit()
		self.logger.info("restored {0:,} valid sessions and skipped {1:,} expired sessions from the database".format(len(self._sessions), expired))

	def __len__(self):
		return len(self._sessions)

	def __repr__(self):
		return "<{0} sessions={1} session_timeout={2} >".format(self.__class__.__name__, len(self._sessions), self.session_timeout)

	def clean(self):
		"""Remove sessions which have expired."""
		should_lock = not self._lock.locked()
		if should_lock:
			self._lock.acquire()
		oldest = time.time() - self.session_timeout
		remove = []
		for session_id, session in self._sessions.items():
			if session.last_seen < oldest:
				remove.append(session_id)
		for session_id in remove:
			del self._sessions[session_id]
		if should_lock:
			self._lock.release()
		return

	def put(self, user):
		"""
		Create and store a new :py:class:`.AuthenticatedSession` object for the
		specified user id. Any previously existing sessions for the specified
		user are removed from the manager.

		:return: The unique identifier for this session.
		:rtype: str
		"""
		new_session = AuthenticatedSession(user)
		new_session_id = base64.b64encode(os.urandom(50))
		if its.py_v3:
			new_session_id = new_session_id.decode('utf-8')

		with self._lock:
			self.clean()
			# limit users to one valid session
			remove = []
			for old_session_id, old_session in self._sessions.items():
				if old_session.user == user:
					remove.append(old_session_id)
			for old_session_id in remove:
				del self._sessions[old_session_id]
			if remove:
				self.logger.info("invalidated {0:,} previously existing session for user {1}".format(len(remove), user))
			while new_session_id in self._sessions:
				new_session_id = base64.b64encode(os.urandom(50))
			self._sessions[new_session_id] = new_session
		return new_session_id

	def get(self, session_id, update_timestamp=True):
		"""
		Look up an :py:class:`.AuthenticatedSession` instance from it's unique
		identifier and optionally update the last seen timestamp. If the session
		is not found or has expired, None will be returned.

		:param str session_id: The unique identifier of the session to retrieve.
		:param bool update_timestamp: Whether or not to update the last seen timestamp for the session.
		:return: The session if it exists and is active.
		:rtype: :py:class:`.AuthenticatedSession`
		"""
		if session_id is None:
			return None
		with self._lock:
			session = self._sessions.get(session_id)
			if session is None:
				return None
			if session.last_seen < time.time() - self.session_timeout:
				del self._sessions[session_id]
				return None
			if update_timestamp:
				session.last_seen = time.time()
		return session

	def remove(self, session_id):
		"""
		Remove the specified session from the manager.

		:param str session_id: The unique identifier for the session to remove.
		"""
		with self._lock:
			del self._sessions[session_id]

	def stop(self):
		self.clean()
		if not self._sessions:
			self.logger.info('no sessions to store in the database')
			return
		session = db_manager.Session()
		for session_id, auth_session in self._sessions.items():
			session.add(db_models.AuthenticatedSession(
				id=session_id,
				created=auth_session.created,
				last_seen=auth_session.last_seen,
				user_id=auth_session.user
			))
		session.commit()
		session.close()
		if len(self._sessions) == 1:
			self.logger.info('1 session was stored in the database')
		else:
			self.logger.info("{0:,} sessions were stored in the database".format(len(self._sessions)))

class CachedPassword(object):
	"""
	A cached in-memory password. Cleartext passwords are salted with data
	generated at runtime and hashed before being stored for future comparisons.
	"""
	__slots__ = ('pw_hash', 'time')
	salt = ''.join(random.choice(string.ascii_letters + string.digits + string.punctuation) for _ in range(random.randint(6, 10)))
	hash_algorithm = 'sha512'
	iterations = 5000
	def __init__(self, pw_hash):
		"""
		:param bytes pw_hash: The salted hash of the password to cache.
		"""
		self.pw_hash = pw_hash
		self.time = time.time()

	def __eq__(self, other):
		if isinstance(other, str):
			other = self.__class__.new_from_password(other)
		if isinstance(other, self.__class__):
			return self.pw_hash == other.pw_hash
		return False

	@classmethod
	def new_from_password(cls, password):
		"""
		Create a new instance from a plaintext password.

		:param str password: The password to cache in memory.
		"""
		password = (cls.salt + password).encode('utf-8')
		pw_hash = hashlib.new(cls.hash_algorithm, password).digest()
		for _ in range(cls.iterations - 1):
			pw_hash = hashlib.new(cls.hash_algorithm, pw_hash).digest()
		return cls(pw_hash)

class ForkedAuthenticator(object):
	"""
	This provides authentication services to the King Phisher server
	through PAM. It is initialized while the server is running as root
	and forks into the background before the privileges are dropped. It
	continues to run as root and forwards requests through a pipe to PAM.
	The pipes use JSON to encoded the request data as a string before
	sending it and using a newline character as the terminator.
	"""
	def __init__(self, cache_timeout='10m', required_group=None):
		"""
		:param cache_timeout: The life time of cached credentials in seconds.
		:type cache_timeout: int, str
		:param str required_group: A group that if specified, users must be a member of to be authenticated.
		"""
		self.logger = logging.getLogger('KingPhisher.Server.Authenticator')
		self.cache_timeout = smoke_zephyr.utilities.parse_timespan(cache_timeout)
		"""The timeout of the credential cache in seconds."""
		self.required_group = required_group
		if self.required_group and not self.required_group in [g.gr_name for g in grp.getgrall()]:
			self.logger.error('the specified group for authentication was not found')
		self.parent_rfile, self.child_wfile = os.pipe()
		self.child_rfile, self.parent_wfile = os.pipe()
		self.child_pid = os.fork()
		"""The PID of the forked child."""
		if not self.child_pid:
			self.rfile = self.child_rfile
			self.wfile = self.child_wfile
		else:
			self.rfile = self.parent_rfile
			self.wfile = self.parent_wfile
		self._lock = threading.Lock()
		self.rfile = os.fdopen(self.rfile, 'r', 1)
		self.wfile = os.fdopen(self.wfile, 'w', 1)
		if not self.child_pid:
			self.child_routine()
			self.rfile.close()
			self.wfile.close()
			logging.shutdown()
			os._exit(os.EX_OK)
		self.cache = {}
		"""The credential cache dictionary. Keys are usernames and values are tuples of password hashes and ages."""
		return

	def send(self, request):
		"""
		Encode and send a request through the pipe to the opposite end.

		:param dict request: A request.
		"""
		self.wfile.write(json.dumps(request) + '\n')

	def recv(self, timeout=None):
		"""
		Receive a request and decode it.

		:param int timeout: The amount of time in seconds to wait for a response to be received.
		:return: The decoded request.
		:rtype: dict
		"""
		if timeout is not None:
			ready, _, _ = select.select([self.rfile], [], [], timeout)
			if not ready:
				raise errors.KingPhisherTimeoutError('a response was not received within the timeout')
		try:
			request = self.rfile.readline()[:-1]
			return json.loads(request)
		except KeyboardInterrupt:
			return {}

	def child_routine(self):
		"""
		The main routine that is executed by the child after the object forks.
		This loop does not exit unless a stop request is made.
		"""
		service = 'login'
		if os.path.isfile('/etc/pam.d/sshd'):
			service = 'sshd'
		while True:
			request = self.recv()
			if not 'action' in request:
				continue
			action = request['action']
			if action == 'stop':
				break
			elif action != 'authenticate':
				continue
			username = str(request['username'])
			password = str(request['password'])
			result = {}
			result['result'] = pam.authenticate(username, password, service=service)
			if result['result']:
				if self.required_group:
					result['result'] = False
					try:
						assert self.required_group in get_groups_for_user(username)
					except AssertionError:
						self.logger.warning("authentication failed for user: {0} reason: lack of group membership".format(username))
					except KeyError:
						self.logger.error("encountered a KeyError while looking up group member ship for user: {0}".format(username))
					else:
						result['result'] = True
			else:
				self.logger.warning("authentication failed for user: {0} reason: bad username or password".format(username))
			self.send(result)

	def authenticate(self, username, password):
		"""
		Check if a username and password are valid. If they are, the password
		will be salted, hashed with SHA-512 and stored so the next call with the
		same values will not require sending a request to the forked child.

		:param str username: The username to check.
		:param str password: The password to check.
		:return: Whether the credentials are valid or not.
		:rtype: bool
		"""
		cached_password = self.cache.get(username)
		if cached_password is not None and cached_password.time + self.cache_timeout >= time.time():
			return cached_password == password
		request = {
			'action': 'authenticate',
			'username': username,
			'password': password
		}
		self._lock.acquire()
		self.send(request)
		try:
			result = self.recv(timeout=30)
		except errors.KingPhisherTimeoutError as error:
			self.logger.error(error.message)
			self._lock.release()
			return False
		if result['result']:
			self.logger.info("user {0} has successfully authenticated".format(username))
			self.cache[username] = CachedPassword.new_from_password(password)
		self._lock.release()
		return result['result']

	def stop(self):
		"""
		Send a stop request to the child process and wait for it to exit.
		"""
		if not os.path.exists("/proc/{0}".format(self.child_pid)):
			return
		request = {}
		request['action'] = 'stop'
		with self._lock:
			self.send(request)
			os.waitpid(self.child_pid, 0)
		self.rfile.close()
		self.wfile.close()
