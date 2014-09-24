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

import sqlalchemy
import sqlalchemy.engine.url
import sqlalchemy.orm
import sqlalchemy.pool

__all__ = [
	'DATABASE_TABLES',
	'Session',
	'get_tables_with_column_id',
	'initialize_database'
]

DATABASE_TABLES = {}
Session = sqlalchemy.orm.scoped_session(sqlalchemy.orm.sessionmaker())
logger = logging.getLogger('KingPhisher.Server.database')

def register_table(table):
	columns = tuple(map(lambda c: c.name, table.__table__.columns))
	DATABASE_TABLES[table.__tablename__] = columns
	return table

from . import models

def get_tables_with_column_id(column_id):
	"""
	Get all tables which contain a column named *column_id*.

	:param str column_id: The column name to get all the tables of.
	:return: The list of matching tables.
	:rtype: list
	"""
	return map(lambda x: x[0], filter(lambda x: column_id in x[1], DATABASE_TABLES.items()))

def init_database(connection_url):
	connection_url = sqlalchemy.engine.url.make_url(connection_url)
	if connection_url.drivername == 'sqlite':
		engine = sqlalchemy.create_engine(connection_url, connect_args={'check_same_thread': False}, poolclass=sqlalchemy.pool.StaticPool)
	elif connection_url.drivername == 'postgresql':
		engine = sqlalchemy.create_engine(connection_url)
	else:
		raise ValueError('only sqlite and postgresql database drivers are supported')
	logger.debug("connected to database: {0} using driver: {1}".format(connection_url.database, connection_url.drivername))
	Session.configure(bind=engine)
	models.Base.metadata.create_all(engine)
	return engine
