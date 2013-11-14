import os
import sqlite3

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
		username TEXT,
		password TEXT,
		submitted TIMESTAMP DEFAULT CURRENT_TIMESTAMP
	)
	""")
	db.commit()
	return db

def main():
	import sys
	if len(sys.argv) < 2:
		print('Usage: database.py [NEW DATABASE FILE]')
		return
	database_file = sys.argv[1]
	create_database(database_file)
	print('Created new database file: ' + database_file)

if __name__ == '__main__':
	main()
