#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  king_phisher/server/signals.py
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

import inspect
import logging

from king_phisher import utilities

import blinker

def safe_send(signal, logger, *args, **kwargs):
	"""
	Send a signal and catch any exception which may be raised during it's
	emission. Details regarding the error that occurs (including a stack trace)
	are logged to the specified *logger*. This is suitable for allowing signals
	to be emitted in critical code paths without interrupting the emitter.

	:param str signal: The name of the signal to send safely.
	:param logger: The logger to use for logging exceptions.
	:type logger: :py:class:`logging.Logger`
	:param args: The arguments to be forwarded to the signal as it is sent.
	:param kwargs: The key word arguments to be forward to the signal as it is sent.
	"""
	utilities.assert_arg_type(signal, str, 1)
	utilities.assert_arg_type(logger, logging.Logger, 2)
	try:
		blinker.signal(signal).send(*args, **kwargs)
	except Exception:
		calling_frame = inspect.stack()[1]
		logger.error("an error occurred while emitting signal '{0}' from {1}:{2}".format(signal, calling_frame[1], calling_frame[2]), exc_info=True)
	return

# database signals
db_initialized = blinker.signal(
	'db-initialized',
	"""
	Emitted after a connection has been made and the database has been fully
	initialized. At this point, it is safe to operate on the database.

	:param connection_url: The connection string for the database that has been initialized.
	:type connection_url: :py:class:`sqlalchemy.engine.url.URL`
	"""
)

db_session_deleted = blinker.signal(
	'db-session-deleted',
	"""
	Emitted after one or more rows have been deleted on a SQLAlchemy session. At
	this point, references are valid but objects can not be modified. See
	:py:meth:`sqlalchemy.orm.events.SessionEvents.after_flush` for more details.

	:param str table: The name of the table for which the target objects belong.
	:param tuple targets: The objects that have been deleted with the session.
	:param session: The SQLAlchemy session with which the *targets* are associated.
	:type session: :py:class:`sqlalchemy.orm.session.Session`
	"""
)

db_session_inserted = blinker.signal(
	'db-session-inserted',
	"""
	Emitted after one or more rows have been inserted in a SQLAlchemy session.
	At this point, references are valid but objects can not be modified. See
	:py:meth:`sqlalchemy.orm.events.SessionEvents.after_flush` for more details.

	:param str table: The name of the table for which the target objects belong.
	:param tuple targets: The objects that have been inserted with the session.
	:param session: The SQLAlchemy session with which the *targets* are associated.
	:type session: :py:class:`sqlalchemy.orm.session.Session`
	"""
)

db_session_updated = blinker.signal(
	'db-session-updated',
	"""
	Emitted after one or more rows have been updated in a SQLAlchemy session.
	At this point, references are valid but objects can not be modified. See
	:py:meth:`sqlalchemy.orm.events.SessionEvents.after_flush` for more details.

	:param str table: The name of the table for which the target objects belong.
	:param tuple targets: The objects that have been updated with the session.
	:param session: The SQLAlchemy session with which the *targets* are associated.
	:type session: :py:class:`sqlalchemy.orm.session.Session`
	"""
)

db_table_delete = blinker.signal(
	'db-table-delete',
	"""
	Emitted before a row inheriting from
	:py:class:`~king_phisher.server.server.database.models.Base` is deleted from
	the database table. To only subscribe to delete events for a specific table,
	specify the table's name as the *sender* parameter when calling
	:py:meth:`blinker.base.Signal.connect`.
	See :py:meth:`sqlalchemy.orm.events.MapperEvents.before_delete` for more
	details.

	:param str table: The name of the table for which the target object belongs.
	:param mapper: The Mapper object which is the target of the event.
	:type mapper: :py:class:`sqlalchemy.orm.mapper.Mapper`
	:param connection: The SQLAlchemy connection object which is being used to emit the SQL statements for the instance.
	:type connection: :py:class:`sqlalchemy.engine.Connection`
	:param target: The target object instance.
	"""
)

db_table_insert = blinker.signal(
	'db-table-insert',
	"""
	Emitted before a row inheriting from
	:py:class:`~king_phisher.server.server.database.models.Base` is inserted
	into the database table. To only subscribe to insert events for a specific
	table, specify the table's name as the *sender* parameter when calling
	:py:meth:`blinker.base.Signal.connect`.
	See :py:meth:`sqlalchemy.orm.events.MapperEvents.before_insert` for more
	details.

	:param str table: The name of the table for which the target object belongs.
	:param mapper: The Mapper object which is the target of the event.
	:type mapper: :py:class:`sqlalchemy.orm.mapper.Mapper`
	:param connection: The SQLAlchemy connection object which is being used to emit the SQL statements for the instance.
	:type connection: :py:class:`sqlalchemy.engine.Connection`
	:param target: The target object instance.
	"""
)

db_table_update = blinker.signal(
	'db-table-update',
	"""
	Emitted before a row inheriting from
	:py:class:`~king_phisher.server.server.database.models.Base` is updated in
	the database table. To only subscribe to update events for a specific table,
	specify the table's name as the *sender* parameter when calling
	:py:meth:`blinker.base.Signal.connect`.
	See :py:meth:`sqlalchemy.orm.events.MapperEvents.before_update` for more
	details.

	:param str table: The name of the table for which the target object belongs.
	:param mapper: The Mapper object which is the target of the event.
	:type mapper: :py:class:`sqlalchemy.orm.mapper.Mapper`
	:param connection: The SQLAlchemy connection object which is being used to emit the SQL statements for the instance.
	:type connection: :py:class:`sqlalchemy.engine.Connection`
	:param target: The target object instance.
	"""
)

# request handler signals
request_received = blinker.signal(
	'request-received',
	"""
	Sent when a new HTTP request has been received and is about to be processed.

	:param request_handler: The handler for the received request.
	"""
)

credentials_received = blinker.signal(
	'credentials-received',
	"""
	Sent when a new pair of credentials have been submitted.

	:param request_handler: The handler for the received request.
	:param str username: The username of the credentials that were submitted.
	:param str password: The password of the credentials that were submitted.
	"""
)

rpc_method_call = blinker.signal(
	'rpc-method-call',
	"""
	Sent when a new RPC request has been received and it's corresponding method
	is about to be called.

	:param str method: The RPC method which is about to be executed.
	:param request_handler: The handler for the received request.
	:param tuple args: The arguments that are to be passed to the method.
	:param dict kwargs: The key word arguments that are to be passed to the method.
	"""
)

rpc_method_called = blinker.signal(
	'rpc-method-called',
	"""
	Sent after an RPC request has been received and it's corresponding method
	has been called.

	:param str method: The RPC method which has been executed.
	:param request_handler: The handler for the received request.
	:param tuple args: The arguments that were passed to the method.
	:param dict kwargs: The key word arguments that were passed to the method.
	:param retval: The value returned from the RPC method invocation.
	"""
)

rpc_user_logged_in = blinker.signal(
	'rpc-user-logged-in',
	"""
	Sent when a new RPC user has successfully logged in and created a new
	authenticated session.

	:param request_handler: The handler for the received request.
	:param str session: The session ID of the newly logged in user.
	:param str name: The username of the newly logged in user.
	"""
)

rpc_user_logged_out = blinker.signal(
	'rpc-user-logged-out',
	"""
	Sent when an authenticated RPC user has successfully logged out and
	terminated their authenticated session.

	:param request_handler: The handler for the received request.
	:param str session: The session ID of the user who has logged out.
	:param str name: The username of the user who has logged out.
	"""
)

visit_received = blinker.signal(
	'visit-received',
	"""
	Sent when a new visit is received on a landing page. This is only emitted
	when a new visit entry is added to the database.

	:param request_handler: The handler for the received request.
	"""
)

# server signals
server_initialized = blinker.signal(
	'server-initialized',
	"""
	Sent when a new instance of
	:py:class:`~king_phisher.server.server.KingPhisherServer` is initialized.

	:param server: The newly initialized server instance.
	"""
)
