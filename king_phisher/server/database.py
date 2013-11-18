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
#  * Neither the name of the  nor the names of its
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
import os
import random
import sqlite3
import string

__version__ = '0.0.1'
make_uid = lambda s: ''.join(random.choice(string.ascii_letters + string.digits) for x in range(24))

def create_database(database_file):
	if database_file != ':memory:' and os.path.exists(database_file):
		os.unlink(database_file)
	db = sqlite3.connect(database_file, check_same_thread = False)
	cursor = db.cursor()
	cursor.execute("""
	CREATE TABLE campaigns (
		id INTEGER PRIMARY KEY AUTOINCREMENT,
		name TEXT UNIQUE NOT NULL,
		created TIMESTAMP DEFAULT CURRENT_TIMESTAMP
	)
	""")
	cursor.execute("""
	CREATE TABLE messages (
		id TEXT PRIMARY KEY UNIQUE NOT NULL,
		campaign_id INTEGER NOT NULL,
		target_email TEXT,
		sent TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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
	db.commit()
	return db

def create_stress_test_database(database_file, count):
	db = create_database(database_file)
	cursor = db.cursor()
	campaign_name = 'Stress Test'
	cursor.execute('INSERT INTO campaigns (name) VALUES (?)', (campaign_name,))
	cursor.execute('SELECT id FROM campaigns WHERE name = ?', (campaign_name,))
	campaign_id = cursor.fetchone()[0]

	for a in xrange(0, count, 10):
		msg_id = make_uid(16)

		message = (msg_id, campaign_id, make_uid(8)+'@devnull.com')
		cursor.execute('INSERT INTO messages (id, campaign_id, target_email) VALUES (?, ?, ?)', message)

		visit = (make_uid(24), msg_id, campaign_id, '127.0.0.1', ('A' * 64))
		cursor.execute('INSERT INTO visits (id, message_id, campaign_id, visitor_ip, visitor_details) VALUES (?, ?, ?, ?, ?)', visit)

		visit = (make_uid(24), msg_id, campaign_id, '127.0.0.1', ('B' * 64))
		cursor.execute('INSERT INTO visits (id, message_id, campaign_id, visitor_ip, visitor_details) VALUES (?, ?, ?, ?, ?)', visit)
		db.commit()

def action_create_database(arguments):
	database_file = arguments.database_file
	create_database(database_file)
	print('Created new database file: ' + database_file)

def action_create_stress_test_database(arguments):
	database_file = arguments.database_file
	create_stress_test_database(database_file, arguments.count)
	print('Created new database file: ' + database_file)

def main():
	parser = argparse.ArgumentParser(description = 'King Phisher Server Database Utility', conflict_handler = 'resolve')
	parser.add_argument('-v', '--version', action = 'version', version = parser.prog + ' Version: ' + __version__)
	parser.add_argument('database_file', help = 'database file to use')
	subparsers = parser.add_subparsers(help = 'action')

	parser_create = subparsers.add_parser('create', help = 'create a new database')
	parser_create.set_defaults(handler = action_create_database)

	parser_stress = subparsers.add_parser('stress_test', help = 'create a database for stress testing')
	parser_stress.add_argument('-c', '--count', dest = 'count', default = 5000, type = int, help = 'the number of message entries to create')
	parser_stress.set_defaults(handler = action_create_stress_test_database)
	arguments = parser.parse_args()

	arguments.handler(arguments)

if __name__ == '__main__':
	main()
