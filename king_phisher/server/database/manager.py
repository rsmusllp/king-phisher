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
import os

from . import models
from king_phisher import errors
from king_phisher import find


import alembic.command
import alembic.config
import alembic.environment
import alembic.script
import sqlalchemy
import sqlalchemy.engine.url
import sqlalchemy.orm
import sqlalchemy.pool

Session = sqlalchemy.orm.scoped_session(sqlalchemy.orm.sessionmaker())
logger = logging.getLogger('KingPhisher.Server.database')
_meta_data_type_map = {'int': int, 'long': long, 'str': str}

def get_meta_data(key, session=None):
	"""
	Retreive the value from the database's metadata storage.

	:param str key: The name of the value to retrieve.
	:param session: The session to use to retrieve the value.
	:return: The meta data value.
	"""
	close_session = session == None
	session = (session or Session())
	result = get_row_by_id(session, models.MetaData, key)
	if close_session:
		session.close()
	if result == None:
		return None
	return _meta_data_type_map[result.value_type](result.value)

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

def set_meta_data(key, value, session=None):
	"""
	Store a piece of metadata regarding the King Phisher database.

	:param str key: The name of the data.
	:param value: The value to store.
	:type value: int, str
	:param session: The session to use to store the value.
	"""
	value_type = type(value).__name__
	if not value_type in _meta_data_type_map:
		raise ValueError('incompatible data type:' + value_type)
	close_session = session == None
	session = (session or Session())
	result = get_row_by_id(session, models.MetaData, key)
	if result:
		session.delete(result)
	md = models.MetaData(id=key)
	md.value_type = value_type
	md.value = str(value)
	session.add(md)
	if close_session:
		session.commit()
		session.close()
	return

def normalize_connection_url(connection_url):
	"""
	Normalize a connection url by performing any conversions necessary for it to
	be used with the database API.

	:param str connection_url: The connection url to normalize.
	:return: The normalized connection url.
	:rtype: str
	"""
	if connection_url == ':memory:':
		connection_url = 'sqlite://'
	elif os.path.isfile(connection_url) or os.path.isdir(os.path.dirname(connection_url)):
		connection_url = 'sqlite:///' + os.path.abspath(connection_url)
	return connection_url

def init_database(connection_url):
	"""
	Create and initialize the database engine. This must be done before the
	session object can be used. This will also attempt to perform any updates to
	the database schema if the backend support such operations.

	:param str connection_url: The url for the database connection.
	:return: The initialized database engine.
	"""
	connection_url = normalize_connection_url(connection_url)
	connection_url = sqlalchemy.engine.url.make_url(connection_url)
	if connection_url.drivername == 'sqlite':
		engine = sqlalchemy.create_engine(connection_url, connect_args={'check_same_thread': False}, poolclass=sqlalchemy.pool.StaticPool)
		sqlalchemy.event.listens_for(engine, 'begin')(lambda conn: conn.execute('BEGIN'))
	elif connection_url.drivername == 'postgresql':
		engine = sqlalchemy.create_engine(connection_url)
	else:
		raise errors.KingPhisherDatabaseError('only sqlite and postgresql database drivers are supported')
	Session.remove()
	Session.configure(bind=engine)
	models.Base.metadata.create_all(engine)

	session = Session()
	set_meta_data('database_driver', connection_url.drivername, session=session)
	schema_version = (get_meta_data('schema_version', session=session) or models.SCHEMA_VERSION)
	session.commit()
	session.close()

	if schema_version > models.SCHEMA_VERSION:
		raise errors.KingPhisherDatabaseError('the database schema is for a newer version, automatic downgrades are not supported')
	elif schema_version < models.SCHEMA_VERSION:
		alembic_config_file = find.find_data_file('alembic.ini')
		if not alembic_config_file:
			raise errors.KingPhisherDatabaseError('cannot find the alembic.ini configuration file')
		alembic_directory = find.find_data_directory('alembic')
		if not alembic_directory:
			raise errors.KingPhisherDatabaseError('cannot find the alembic data directory')

		config = alembic.config.Config(alembic_config_file)
		config.config_file_name = alembic_config_file
		config.set_main_option('script_location', alembic_directory)
		config.set_main_option('skip_logger_config', 'True')
		config.set_main_option('sqlalchemy.url', str(connection_url))

		logger.info("automatically updating the database schema to version {0}".format(models.SCHEMA_VERSION))
		try:
			alembic.command.upgrade(config, 'head')
		except Exception as error:
			logger.critical("database schema upgrade failed with exception: {0}.{1} {2}".format(error.__class__.__module__, error.__class__.__name__, getattr(error, 'message', '')).rstrip())
			raise errors.KingPhisherDatabaseError('failed to upgrade to the latest database schema')
	set_meta_data('schema_version', models.SCHEMA_VERSION)

	logger.debug("connected to {0} database: {1}".format(connection_url.drivername, connection_url.database))
	return engine
