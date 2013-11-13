import os
import sqlite3

def create_database(database_file):
	if database_file != ':memory:' and os.path.exists(database_file):
		os.unlink(database_file)
	db = sqlite3.connect(database_file, check_same_thread = False)
	cursor = db.cursor()
	cursor.execute('''CREATE TABLE campaigns (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE NOT NULL, created TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
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
