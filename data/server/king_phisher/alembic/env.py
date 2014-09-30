from __future__ import with_statement
from alembic import context
from sqlalchemy import create_engine, pool
from logging.config import fileConfig

import os
import sys
kp_path = os.path.dirname(os.path.abspath(__file__))
kp_path = os.path.normpath(os.path.join(kp_path, '..', '..', '..', '..'))
sys.path.insert(1, kp_path)

from king_phisher.server.database import manager
from king_phisher.server.database import models

import yaml

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if not config.get_main_option('skip_logger_config'):
	fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
# from myapp import mymodel
# target_metadata = mymodel.Base.metadata
target_metadata = models.Base.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.

database_connection_url = config.get_main_option('sqlalchemy.url')
if not database_connection_url:
	# consume the x arguments provided on the command line
	x_arguments = context.get_x_argument(as_dictionary=True)
	if 'config' in x_arguments:
		server_config = yaml.load(open(x_arguments['config']))
		database_connection_url = server_config['server']['database']
	elif 'database' in x_arguments:
		database_connection_url = x_arguments['database']
	else:
		print('[-] the database connection string has not been specified, either')
		print('[-] \'config\' or \'database\' must be specified via the -x option')
		print('[-] for example:')
		print('    -x database=driver://user:pass@localhost/dbname')
		print('    -x config=/path/to/server/config/file')
		os._exit(os.EX_USAGE)
	database_connection_url = manager.normalize_connection_url(database_connection_url)

def run_migrations_offline():
	"""Run migrations in 'offline' mode.

	This configures the context with just a URL
	and not an Engine, though an Engine is acceptable
	here as well.  By skipping the Engine creation
	we don't even need a DBAPI to be available.

	Calls to context.execute() here emit the given string to the
	script output.

	"""
	context.configure(url=database_connection_url, target_metadata=target_metadata)

	with context.begin_transaction():
		context.run_migrations()


def run_migrations_online():
	"""Run migrations in 'online' mode.

	In this scenario we need to create an Engine
	and associate a connection with the context.

	"""
	engine = create_engine(
		database_connection_url,
		poolclass=pool.NullPool)

	connection = engine.connect()
	context.configure(
		connection=connection,
		target_metadata=target_metadata
	)

	try:
		with context.begin_transaction():
			context.run_migrations()
	finally:
		connection.close()

if context.is_offline_mode():
	run_migrations_offline()
else:
	run_migrations_online()
