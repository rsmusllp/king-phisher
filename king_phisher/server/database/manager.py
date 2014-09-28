#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  king_phisher/server/database/manager.py
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

from . import models

import sqlalchemy
import sqlalchemy.engine.url
import sqlalchemy.orm
import sqlalchemy.pool

Session = sqlalchemy.orm.scoped_session(sqlalchemy.orm.sessionmaker())
logger = logging.getLogger('KingPhisher.Server.database')

def get_row_by_id(session, table, row_id):
	"""
	Retrieve a database row fron the specified table by it's unique id.

	:param session: The database session to use for the query.
	:type session: `.Session`
	:param table: The table object or the name of the database table where the row resides.
	:param row_id: The id of the row to retrieve.
	:return: The object representing the specified row or None if it does not exist.
	"""
	if not issubclass(table, models.Base):
		table = models.DATABASE_TABLE_OBJECTS[table]
	query = session.query(table)
	query = query.filter_by(id=row_id)
	result = query.first()
	return result

def init_database(connection_url):
	"""
	Create and initialize the database engine. This must be done before the
	session object can be used.

	:param str connection_url: The url for the database connection.
	:return: The initialized database engine.
	"""
	connection_url = sqlalchemy.engine.url.make_url(connection_url)
	if connection_url.drivername == 'sqlite':
		engine = sqlalchemy.create_engine(connection_url, connect_args={'check_same_thread': False}, poolclass=sqlalchemy.pool.StaticPool)
	elif connection_url.drivername == 'postgresql':
		engine = sqlalchemy.create_engine(connection_url)
	else:
		raise ValueError('only sqlite and postgresql database drivers are supported')
	logger.debug("connected to {0} database: {1}".format(connection_url.drivername, connection_url.database))
	Session.configure(bind=engine)
	models.Base.metadata.create_all(engine)
	return engine
