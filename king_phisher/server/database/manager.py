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

import collections
import contextlib
import datetime
import logging
import os
import re

from . import models
from king_phisher import archive
from king_phisher import errors
from king_phisher import find
from king_phisher import ipaddress
from king_phisher import serializers
from king_phisher import startup
from king_phisher.server import signals

import alembic.command
import alembic.config
import alembic.environment
import alembic.script
import smoke_zephyr.utilities
import sqlalchemy
import sqlalchemy.engine.url
import sqlalchemy.event
import sqlalchemy.exc
import sqlalchemy.ext.serializer
import sqlalchemy.orm
import sqlalchemy.pool

Session = sqlalchemy.orm.scoped_session(sqlalchemy.orm.sessionmaker())
logger = logging.getLogger('KingPhisher.Server.Database')
# map of signal names to sqlalchemy.orm.session.Session attributes
_flush_signal_map = (
	('db-session-deleted', 'deleted'),
	('db-session-inserted', 'new'),
	('db-session-updated', 'dirty')
)
_metadata_namespace = 'metadata'
_metadata_serializer = serializers.MsgPack

@sqlalchemy.event.listens_for(Session, 'after_flush')
def on_session_after_flush(session, flush_context):
	for signal, session_attribute in _flush_signal_map:
		objs = collections.defaultdict(list)
		for obj in getattr(session, session_attribute):
			objs[obj.__tablename__].append(obj)
		for table, targets in objs.items():
			signals.send_safe(signal, logger, table, targets=tuple(targets), session=session)

def _popen_psql(sql):
	if os.getuid():
		raise RuntimeError('_popen_psql can only be used as root due to su requirement')
	results = startup.run_process(['su', 'postgres', '-c', "psql -At -c \"{0}\"".format(sql)])
	if results.status != os.EX_OK:
		raise errors.KingPhisherDatabaseError("failed to execute postgresql query '{0}' via su and psql".format(sql))
	return results.stdout.split('\n')

def clear_database():
	"""
	Delete all data from all tables in the connected database. The database
	schema will remain unaffected.

	.. warning::
		This action can not be reversed and there is no confirmation before it
		takes place.
	"""
	engine = Session.connection().engine
	with contextlib.closing(engine.connect()) as connection:
		transaction = connection.begin()
		for table in reversed(models.metadata.sorted_tables):
			connection.execute(table.delete())
		transaction.commit()

def export_database(target_file):
	"""
	Export the contents of the database using SQLAlchemy's serialization. This
	creates an archive file containing all of the tables and their data. The
	resulting export can be imported into another supported database so long
	as the :py:data:`~king_phisher.server.database.models.SCHEMA_VERSION` is the
	same.

	:param str target_file: The file to write the export to.
	"""
	session = Session()
	kpdb = archive.ArchiveFile(target_file, 'w')
	kpdb.metadata['database-schema'] = models.SCHEMA_VERSION
	for table in models.metadata.sorted_tables:
		table_name = table.name
		model = models.database_table[table_name].model
		kpdb.add_data('tables/' + table_name, sqlalchemy.ext.serializer.dumps(session.query(model).all()))
	kpdb.close()

def import_database(target_file, clear=True):
	"""
	Import the contents of a serialized database from an archive previously
	created with the :py:func:`.export_database` function. The current
	:py:data:`~king_phisher.server.database.models.SCHEMA_VERSION` must be the
	same as the exported archive.

	.. warning::
		This will by default delete the contents of the current database in
		accordance with the *clear* parameter. If *clear* is not
		specified and objects in the database and import share an ID, they will
		be merged.

	:param str target_file: The database archive file to import from.
	:param bool clear: Whether or not to delete the contents of the
		existing database before importing the new data.
	"""
	kpdb = archive.ArchiveFile(target_file, 'r')
	schema_version = kpdb.metadata['database-schema']
	if schema_version != models.SCHEMA_VERSION:
		raise errors.KingPhisherDatabaseError("incompatible database schema versions ({0} vs {1})".format(schema_version, models.SCHEMA_VERSION))

	if clear:
		clear_database()
	session = Session()
	for table in models.metadata.sorted_tables:
		table_data = kpdb.get_data('tables/' + table.name)
		for row in sqlalchemy.ext.serializer.loads(table_data):
			session.merge(row)
	session.commit()
	kpdb.close()

def get_metadata(key, session=None):
	"""
	Store a piece of metadata regarding the King Phisher database.

	:param str key: The name of the data.
	:param value: The value to store.
	:type value: int, str
	:param session: The session to use to store the value.
	"""
	if not isinstance(key, str):
		raise TypeError('key must be a str instance')
	close_session = session is None
	session = (session or Session())
	obj = session.query(models.StorageData).filter_by(namespace=_metadata_namespace, key=key).first()
	if obj is None:
		raise KeyError(key)
	value = obj.value
	if value is not None:
		value = _metadata_serializer.loads(value)
	if close_session:
		session.commit()
		session.close()
	return value

def get_row_by_id(session, table, row_id):
	"""
	Retrieve a database row from the specified table by it's unique id.

	:param session: The database session to use for the query.
	:type session: `.Session`
	:param table: The table object or the name of the database table where the row resides.
	:param row_id: The id of the row to retrieve.
	:return: The object representing the specified row or None if it does not exist.
	"""
	if not issubclass(table, models.Base):
		table = models.database_tables[table].model
	query = session.query(table)
	query = query.filter_by(id=row_id)
	result = query.first()
	return result

def get_schema_version(engine):
	results = None
	# try the new style storage
	try:
		results = engine.execute(
			sqlalchemy.text("SELECT value FROM storage_data WHERE namespace = :namespace AND key = 'schema_version'"),
			namespace=_metadata_namespace
		).fetchone()
	except sqlalchemy.exc.DatabaseError:
		pass
	if results:
		return _metadata_serializer.loads(results[0])

	# try the old style storage
	try:
		results = engine.execute(sqlalchemy.text("SELECT value_type, value FROM meta_data WHERE id = 'schema_version'")).fetchone()
	except sqlalchemy.exc.DatabaseError:
		pass
	if results:
		value_type, value = results
		if value_type != 'int':
			raise TypeError('the value is not of type: int')
		return int(value)
	return models.SCHEMA_VERSION

def set_metadata(key, value, session=None):
	"""
	Store a piece of metadata regarding the King Phisher database.

	:param str key: The name of the data.
	:param value: The value to store.
	:type value: int, str
	:param session: The session to use to store the value.
	"""
	if not isinstance(key, str):
		raise TypeError('key must be a str instance')
	close_session = session is None
	session = (session or Session())
	if value is not None:
		value = _metadata_serializer.dumps(value)
	obj = session.query(models.StorageData).filter_by(namespace=_metadata_namespace, key=key).first()
	if obj is None:
		obj = models.StorageData(namespace=_metadata_namespace, key=key)
	elif obj.value != value:
		obj.value = value
		obj.modified = datetime.datetime.utcnow()
	obj.value = value
	session.add(obj)
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

def init_alembic(engine, schema_version):
	"""
	Creates the alembic_version table and sets the value of the table according
	to the specified schema version.

	:param engine: The engine used to connect to the database.
	:type engine: :py:class:`sqlalchemy.engine.Engine`
	:param int schema_version: The MetaData schema_version to set the alembic version to.
	"""
	pattern = re.compile(r'[a-f0-9]{10,16}_schema_v\d+\.py')
	alembic_revision = None
	alembic_directory = find.data_directory('alembic')
	if not alembic_directory:
		raise errors.KingPhisherDatabaseError('cannot find the alembic data directory')
	alembic_versions_files = os.listdir(os.path.join(alembic_directory, 'versions'))
	for file in alembic_versions_files:
		if not pattern.match(file):
			continue
		if not file.endswith('_schema_v' + str(schema_version) + '.py'):
			continue
		alembic_revision = file.split('_', 1)[0]
		break
	if not alembic_revision:
		raise errors.KingPhisherDatabaseError("cannot find current alembic version for schema version {0}".format(schema_version))

	alembic_metadata = sqlalchemy.MetaData(engine)
	alembic_table = sqlalchemy.Table(
		'alembic_version',
		alembic_metadata,
		sqlalchemy.Column(
			'version_num',
			sqlalchemy.String,
			primary_key=True,
			nullable=False
		)
	)
	alembic_metadata.create_all()
	alembic_version_entry = alembic_table.insert().values(version_num=alembic_revision)
	engine.connect().execute(alembic_version_entry)
	logger.info("alembic_version table initialized to {0}".format(alembic_revision))

def init_database(connection_url, extra_init=False):
	"""
	Create and initialize the database engine. This must be done before the
	session object can be used. This will also attempt to perform any updates to
	the database schema if the backend supports such operations.

	:param str connection_url: The url for the database connection.
	:param bool extra_init: Run optional extra dbms-specific initialization logic.
	:return: The initialized database engine.
	"""
	connection_url = normalize_connection_url(connection_url)
	connection_url = sqlalchemy.engine.url.make_url(connection_url)
	logger.info("initializing database connection with driver {0}".format(connection_url.drivername))
	if connection_url.drivername == 'sqlite':
		engine = sqlalchemy.create_engine(connection_url, connect_args={'check_same_thread': False}, poolclass=sqlalchemy.pool.StaticPool)
		sqlalchemy.event.listens_for(engine, 'begin')(lambda conn: conn.execute('BEGIN'))
	elif connection_url.drivername == 'postgresql':
		if extra_init:
			init_database_postgresql(connection_url)
		engine = sqlalchemy.create_engine(connection_url, connect_args={'client_encoding': 'utf8'})
	else:
		raise errors.KingPhisherDatabaseError('only sqlite and postgresql database drivers are supported')

	try:
		Session.remove()
		Session.configure(bind=engine)
		inspector = sqlalchemy.inspect(engine)
	except sqlalchemy.exc.OperationalError as error:
		logger.debug('encountered a sqlalchemy OperationalError while initializing the database', exc_info=True)
		if error.args:
			match = re.match(r'\(psycopg2\.OperationalError\) FATAL:\s+password authentication failed for user \"(?P<username>\w+)\"$', error.args[0])
			if match:
				raise errors.KingPhisherDatabaseAuthenticationError('database initialization failed', username=match.group('username')) from None
		raise errors.KingPhisherDatabaseError('database initialization failed') from error

	if 'campaigns' not in inspector.get_table_names():
		logger.debug('campaigns table not found, creating all new tables')
		try:
			models.Base.metadata.create_all(engine)
		except sqlalchemy.exc.SQLAlchemyError as error:
			error_lines = (line.strip() for line in error.message.split('\n'))
			raise errors.KingPhisherDatabaseError('SQLAlchemyError: ' + ' '.join(error_lines).strip())

	schema_version = get_schema_version(engine)
	logger.debug("current database schema version: {0} ({1})".format(schema_version, ('latest' if schema_version == models.SCHEMA_VERSION else 'obsolete')))
	if 'alembic_version' not in inspector.get_table_names():
		logger.debug('alembic version table not found, attempting to create and set version')
		init_alembic(engine, schema_version)

	if schema_version > models.SCHEMA_VERSION:
		raise errors.KingPhisherDatabaseError('the database schema is for a newer version, automatic downgrades are not supported')
	elif schema_version < models.SCHEMA_VERSION:
		alembic_config_file = find.data_file('alembic.ini')
		if not alembic_config_file:
			raise errors.KingPhisherDatabaseError('cannot find the alembic.ini configuration file')
		alembic_directory = find.data_directory('alembic')
		if not alembic_directory:
			raise errors.KingPhisherDatabaseError('cannot find the alembic data directory')

		config = alembic.config.Config(alembic_config_file)
		config.config_file_name = alembic_config_file
		config.set_main_option('script_location', alembic_directory)
		config.set_main_option('skip_logger_config', 'True')
		config.set_main_option('sqlalchemy.url', str(connection_url))

		logger.warning("automatically updating the database schema from version {0} to {1}".format(schema_version, models.SCHEMA_VERSION))
		try:
			alembic.command.upgrade(config, 'head')
		except Exception as error:
			logger.critical("database schema upgrade failed with exception: {0}.{1} {2}".format(error.__class__.__module__, error.__class__.__name__, getattr(error, 'message', '')).rstrip(), exc_info=True)
			raise errors.KingPhisherDatabaseError('failed to upgrade to the latest database schema')
		logger.info("successfully updated the database schema from version {0} to {1}".format(schema_version, models.SCHEMA_VERSION))
		# reset it because it may have been altered by alembic
		Session.remove()
		Session.configure(bind=engine)
	set_metadata('database_driver', connection_url.drivername)
	set_metadata('last_started', datetime.datetime.utcnow())
	set_metadata('schema_version', models.SCHEMA_VERSION)

	logger.debug("connected to {0} database: {1}".format(connection_url.drivername, connection_url.database))
	signals.db_initialized.send(connection_url)
	return engine

def init_database_postgresql(connection_url):
	"""
	Perform additional initialization checks and operations for a PostgreSQL
	database. If the database is hosted locally this will ensure that the
	service is currently running and start it if it is not. Additionally if the
	specified database or user do not exist, they will be created.

	:param connection_url: The url for the PostgreSQL database connection.
	:type connection_url: :py:class:`sqlalchemy.engine.url.URL`
	:return: The initialized database engine.
	"""
	if not ipaddress.is_loopback(connection_url.host):
		return

	is_sanitary = lambda s: re.match(r'^[a-zA-Z0-9_]+$', s) is not None

	systemctl_bin = smoke_zephyr.utilities.which('systemctl')
	if systemctl_bin is None:
		logger.info('postgresql service status check failed (could not find systemctl)')
	else:
		postgresql_setup = smoke_zephyr.utilities.which('postgresql-setup')
		if postgresql_setup is None:
			logger.debug('postgresql-setup was not found')
		else:
			logger.debug('using postgresql-setup to ensure that the database is initialized')
			startup.run_process([postgresql_setup, '--initdb'])
		results = startup.run_process([systemctl_bin, 'status', 'postgresql.service'])
		# wait for the process to return and check if it's running (status 0)
		if results.status == os.EX_OK:
			logger.debug('postgresql service is already running via systemctl')
		else:
			logger.info('postgresql service is not running, starting it now via systemctl')
			results = startup.run_process([systemctl_bin, 'start', 'postgresql'])
			if results.status != os.EX_OK:
				logger.error('failed to start the postgresql service via systemctl')
				raise errors.KingPhisherDatabaseError('postgresql service failed to start via systemctl')
			logger.debug('postgresql service successfully started via systemctl')

	rows = _popen_psql('SELECT usename FROM pg_user')
	if connection_url.username not in rows:
		logger.info('the specified postgresql user does not exist, adding it now')
		if not is_sanitary(connection_url.username):
			raise errors.KingPhisherInputValidationError('will not create the postgresql user (username contains bad characters)')
		if not is_sanitary(connection_url.password):
			raise errors.KingPhisherInputValidationError('will not create the postgresql user (password contains bad characters)')
		rows = _popen_psql("CREATE USER {url.username} WITH PASSWORD '{url.password}'".format(url=connection_url))
		if rows != ['CREATE ROLE']:
			logger.error('failed to create the postgresql user')
			raise errors.KingPhisherDatabaseError('failed to create the postgresql user')
		logger.debug('the specified postgresql user was successfully created')

	rows = _popen_psql('SELECT datname FROM pg_database')
	if connection_url.database not in rows:
		logger.info('the specified postgresql database does not exist, adding it now')
		if not is_sanitary(connection_url.database):
			raise errors.KingPhisherInputValidationError('will not create the postgresql database (name contains bad characters)')
		rows = _popen_psql("CREATE DATABASE {url.database} OWNER {url.username}".format(url=connection_url))
		if rows != ['CREATE DATABASE']:
			logger.error('failed to create the postgresql database')
			raise errors.KingPhisherDatabaseError('failed to create the postgresql database')
		logger.debug('the specified postgresql database was successfully created')
