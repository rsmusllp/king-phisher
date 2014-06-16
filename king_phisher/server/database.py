#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  king_phisher/server/database.py
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

import argparse
import contextlib
import os
import random
import sqlite3
import string
import threading

SCHEMA_VERSION = 1
"""The schema version of the database, used for compatibility checks."""
DATABASE_TABLES = {
	'users':                ['id', 'phone_carrier', 'phone_number'],
	'alert_subscriptions':  ['id', 'campaign_id', 'user_id'],
	'campaigns':            ['id', 'name', 'creator', 'created', 'reject_after_credentials'],
	'landing_pages':        ['id', 'campaign_id', 'hostname', 'page'],
	'messages':             ['id', 'campaign_id', 'target_email', 'company_name', 'first_name', 'last_name', 'opened', 'sent', 'trained'],
	'visits':               ['id', 'campaign_id', 'message_id', 'visit_count', 'visitor_ip', 'visitor_details', 'first_visit', 'last_visit'],
	'credentials':          ['id', 'campaign_id', 'message_id', 'visit_id', 'username', 'password', 'submitted'],
	'deaddrop_deployments': ['id', 'campaign_id', 'destination'],
	'deaddrop_connections': ['id', 'campaign_id', 'deployment_id', 'visit_count', 'visitor_ip', 'local_username', 'local_hostname', 'local_ip_addresses', 'first_visit', 'last_visit'],
	'meta_data':            ['id', 'value_type', 'value']
}
"""A dictionary which contains all the database tables and their columns."""

class KingPhisherDatabase(object):
	"""
	This is a thread-safe direct connection to the King Phisher SQLite3
	database.
	"""
	_type_map = {'int': int, 'long': long, 'str': str}
	def __init__(self, database_file):
		"""
		:param str database_file: The SQLite3 database to use.
		"""
		self._db = sqlite3.connect(database_file, check_same_thread=False)
		self._lock = threading.RLock()

	def commit(self):
		"""Commit changes to the database file."""
		return self._db.commit()

	def cursor(self):
		"""Get the database cursor for executing queries."""
		return self._db.cursor()

	@contextlib.contextmanager
	def get_cursor(self):
		"""
		A context manager that yields the *cursor* object and
		allows queries to be executed while the thread lock is held.
		"""
		self._lock.acquire()
		cursor = self._db.cursor()
		yield cursor
		self._db.commit()
		self._lock.release()

	def get_meta_data(self, key):
		"""
		Retreive the value from the database meta_data table. The value
		will be the same as the type when it was set.

		:param str key: The name of the value to retrieve.
		:return: The meta data value.
		"""
		with self.get_cursor() as cursor:
			cursor.execute('SELECT value_type, value FROM meta_data WHERE id = ?', (key,))
			result = cursor.fetchone()
		if not result:
			raise ValueError('unknown data key: ' + key)
		value_type, value = result
		return self._type_map[value_type](value)

	def set_meta_data(self, key, value):
		"""
		Store a piece of metadata regarding the King Phisher database.

		:param str key: The name of the data.
		:param value: The value to store.
		:type value: int, str
		"""
		value_type = type(value).__name__
		if not value_type in self._type_map.keys():
			raise ValueError('incompatible data type:' + value_type)
		with self.get_cursor() as cursor:
			cursor.execute('INSERT OR REPLACE INTO meta_data (id, value_type, value) VALUES (?, ?, ?)', (key, value_type, str(value)))
		return

	@property
	def schema_version(self):
		"""The schema version of the current database."""
		return self.get_meta_data('schema_version')

def get_tables_with_column_id(column_id):
	"""
	Get all tables which contain a column named *column_id*.

	:param str column_id: The column name to get all the tables of.
	:return: The list of matching tables.
	:rtype: list
	"""
	return map(lambda x: x[0], filter(lambda x: column_id in x[1], DATABASE_TABLES.items()))

def create_database(database_file):
	"""
	Initialize a new King Phisher database, creating all the necessary
	tables and setting the initial schema version number.

	:param str database_file: The path to the database file to initialize.
	:return: The initialized database.
	:rtype: :py:class:`.KingPhisherDatabase`
	"""
	if database_file != ':memory:' and os.path.exists(database_file):
		os.unlink(database_file)
	db = KingPhisherDatabase(database_file)
	cursor = db.cursor()
	cursor.execute("""
	CREATE TABLE users (
		id TEXT PRIMARY KEY UNIQUE NOT NULL,
		phone_carrier TEXT,
		phone_number TEXT
	)
	""")
	cursor.execute("""
	CREATE TABLE alert_subscriptions (
		id INTEGER PRIMARY KEY AUTOINCREMENT,
		user_id TEXT NOT NULL,
		campaign_id INTEGER
	)
	""")
	cursor.execute("""
	CREATE TABLE campaigns (
		id INTEGER PRIMARY KEY AUTOINCREMENT,
		name TEXT UNIQUE NOT NULL,
		creator TEXT NOT NULL,
		created TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
		reject_after_credentials BOOLEAN DEFAULT 0
	)
	""")
	cursor.execute("""
	CREATE TABLE landing_pages (
		id INTEGER PRIMARY KEY AUTOINCREMENT,
		campaign_id INTEGER NOT NULL,
		hostname TEXT NOT NULL,
		page TEXT NOT NULL
	)
	""")
	cursor.execute("""
	CREATE TABLE messages (
		id TEXT PRIMARY KEY UNIQUE NOT NULL,
		campaign_id INTEGER NOT NULL,
		target_email TEXT,
		company_name TEXT,
		first_name TEXT,
		last_name TEXT,
		opened TIMESTAMP DEFAULT NULL,
		sent TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
		trained BOOLEAN DEFAULT 0
	)
	""")
	cursor.execute("""
	CREATE TABLE visits (
		id TEXT PRIMARY KEY UNIQUE NOT NULL,
		message_id TEXT NOT NULL,
		campaign_id INTEGER NOT NULL,
		visit_count INTEGER DEFAULT 1,
		visitor_ip TEXT,
		visitor_details TEXT,
		first_visit TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
		last_visit TIMESTAMP DEFAULT CURRENT_TIMESTAMP
	)
	""")
	cursor.execute("""
	CREATE TABLE credentials (
		id INTEGER PRIMARY KEY AUTOINCREMENT,
		visit_id TEXT NOT NULL,
		message_id TEXT NOT NULL,
		campaign_id INTEGER NOT NULL,
		username TEXT,
		password TEXT,
		submitted TIMESTAMP DEFAULT CURRENT_TIMESTAMP
	)
	""")
	cursor.execute("""
	CREATE TABLE deaddrop_deployments (
		id TEXT PRIMARY KEY UNIQUE NOT NULL,
		campaign_id INTEGER NOT NULL,
		destination TEXT
	)
	""")
	cursor.execute("""
	CREATE TABLE deaddrop_connections (
		id INTEGER PRIMARY KEY AUTOINCREMENT,
		deployment_id TEXT NOT NULL,
		campaign_id INTEGER NOT NULL,
		visit_count INTEGER DEFAULT 1,
		visitor_ip TEXT,
		local_username TEXT,
		local_hostname TEXT,
		local_ip_addresses TEXT,
		first_visit TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
		last_visit TIMESTAMP DEFAULT CURRENT_TIMESTAMP
	)
	""")
	cursor.execute("""
	CREATE TABLE meta_data (
		id TEXT PRIMARY KEY UNIQUE NOT NULL,
		value_type TEXT DEFAULT str,
		value TEXT
	)
	""")
	db.commit()
	db.set_meta_data('schema_version', SCHEMA_VERSION)
	return db

def main():
	parser = argparse.ArgumentParser(description='King Phisher Server Database Utility', conflict_handler='resolve')
	parser.add_argument('database_file', help='database file to use')
	arguments = parser.parse_args()

	database_file = arguments.database_file
	create_database(database_file)
	print('Created new database file: ' + database_file)

if __name__ == '__main__':
	main()
