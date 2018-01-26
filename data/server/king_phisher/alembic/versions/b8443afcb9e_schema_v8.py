"""Schema v8

Revision ID: b8443afcb9e
Revises: b76eab0a059
Create Date: 2017-12-28

"""

# revision identifiers, used by Alembic.
revision = 'b8443afcb9e'
down_revision = 'b76eab0a059'

import os
import sys
sys.path.insert(1, os.path.abspath(os.path.join(os.path.dirname(__file__), *['..'] * 5)))

from alembic import op
from king_phisher.server.database import manager as db_manager
from king_phisher.server.database import schema_migration as db_schema_migration
import sqlalchemy

alert_subscriptions_type = sqlalchemy.Enum('email', 'sms', name='alert_subscription_type')

user_id_tables = ('alert_subscriptions', 'authenticated_sessions', 'campaigns')

def upgrade():
	op.alter_column('alert_subscriptions', 'mute_timestamp', new_column_name='expiration')
	op.drop_column('alert_subscriptions', 'type')
	alert_subscriptions_type.drop(op.get_bind(), checkfirst=True)

	op.drop_column('authenticated_sessions', 'created')
	op.add_column('authenticated_sessions', sqlalchemy.Column('created', sqlalchemy.DateTime, nullable=False))
	op.drop_column('authenticated_sessions', 'last_seen')
	op.add_column('authenticated_sessions', sqlalchemy.Column('last_seen', sqlalchemy.DateTime, nullable=False))

	op.add_column('campaigns', sqlalchemy.Column('max_credentials', sqlalchemy.Integer()))
	op.execute('UPDATE campaigns SET max_credentials = CASE WHEN (reject_after_credentials) THEN 1 ELSE NULL END')
	op.drop_column('campaigns', 'reject_after_credentials')

	db_schema_migration.rename_columns('deaddrop_connections', (
		('first_visit', 'first_seen'),
		('last_visit', 'last_seen'),
		('visit_count', 'count'),
		('visitor_ip', 'ip')
	))

	op.add_column('messages', sqlalchemy.Column('delivery_details', sqlalchemy.String))
	op.add_column('messages', sqlalchemy.Column('delivery_status', sqlalchemy.String))
	op.add_column('messages', sqlalchemy.Column('reported', sqlalchemy.DateTime))
	op.add_column('messages', sqlalchemy.Column('testing', sqlalchemy.Boolean))
	op.execute('UPDATE messages SET testing=FALSE')
	op.alter_column('messages', 'testing', server_default=False)
	op.alter_column('messages', 'testing', nullable=False)

	op.drop_table('meta_data')

	op.add_column('storage_data', sqlalchemy.Column('modified', sqlalchemy.DateTime))

	op.add_column('users', sqlalchemy.Column('name', sqlalchemy.String, unique=True))
	db_connection = op.get_bind()
	usernames = tuple(row[0] for row in db_connection.execute('SELECT id FROM users'))
	usernames = dict(zip(sorted(usernames), range(1, len(usernames) + 1)))
	def db_execute(query_string, **kwargs):
		db_connection.execute(sqlalchemy.text(query_string), **kwargs)
	with db_connection.begin() as transaction:
		for table in user_id_tables:
			db_execute('ALTER TABLE ' + table + ' DROP CONSTRAINT ' + table + '_user_id_fkey')
		for old_user_id, new_user_id in usernames.items():
			new_user_id = str(new_user_id)
			db_execute(
				"""\
					INSERT INTO users (id, name, phone_carrier, phone_number, email_address, otp_secret)\
					SELECT :new_user_id, name, phone_carrier, phone_number, email_address, otp_secret\
					FROM users WHERE id = :old_user_id\
				""",
				new_user_id=new_user_id,
				old_user_id=old_user_id
			)
			db_execute(
				'UPDATE users SET name = :old_user_id WHERE id = :new_user_id',
				new_user_id=new_user_id,
				old_user_id=old_user_id
			)
			for table in user_id_tables:
				db_execute(
					'UPDATE ' + table + ' SET user_id = :new_user_id WHERE user_id = :old_user_id',
					new_user_id=new_user_id,
					old_user_id=old_user_id
				)
		for old_user_id in usernames.keys():
			db_execute('DELETE FROM users WHERE id = :old_user_id', old_user_id=old_user_id)
		db_execute('ALTER TABLE users ALTER COLUMN name SET NOT NULL')
		db_execute('ALTER TABLE users ALTER COLUMN id TYPE integer USING (id::integer)')
		for table in user_id_tables:
			db_execute('ALTER TABLE ' + table + ' ALTER COLUMN user_id TYPE integer USING (user_id::integer)')
		for table in user_id_tables:
			db_execute('ALTER TABLE ' + table + ' ADD CONSTRAINT ' + table + '_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id)')
		db_execute('CREATE SEQUENCE users_id_seq START WITH :next_id', next_id=(max(usernames.values()) + 1 if usernames else 1))
		db_execute('ALTER TABLE users ALTER COLUMN id SET DEFAULT nextval(\'users_id_seq\')')
	op.add_column('users', sqlalchemy.Column('description', sqlalchemy.String))
	op.add_column('users', sqlalchemy.Column('expiration', sqlalchemy.DateTime))
	op.add_column('users', sqlalchemy.Column('last_login', sqlalchemy.DateTime))

	op.add_column('visits', sqlalchemy.Column('first_landing_page_id', sqlalchemy.Integer, sqlalchemy.ForeignKey('landing_pages.id')))
	op.add_column('visits', sqlalchemy.Column('user_agent', sqlalchemy.String))
	op.execute('UPDATE visits SET user_agent = visitor_details')
	op.execute('UPDATE visits SET visitor_details = NULL')
	db_schema_migration.rename_columns('visits', (
		('visit_count', 'count'),
		('visitor_details', 'details'),
		('visitor_ip', 'ip'),
		('first_visit', 'first_seen'),
		('last_visit', 'last_seen'),
	))

	# adjust the schema version metadata
	db_manager.Session.remove()
	db_manager.Session.configure(bind=op.get_bind())
	session = db_manager.Session()
	db_manager.set_metadata('schema_version', 8, session=session)
	session.commit()

def downgrade():
	db_schema_migration.rename_columns('visits', (
		('last_seen', 'last_visit'),
		('first_seen', 'first_visit'),
		('ip', 'visitor_ip'),
		('details', 'visitor_details'),
		('count', 'visit_count'),
	))
	op.execute('UPDATE visits SET visitor_details = user_agent')
	op.drop_column('visits', 'user_agent')
	op.drop_column('visits', 'first_landing_page_id')

	db_connection = op.get_bind()
	usernames = dict(tuple(db_connection.execute('SELECT name, id FROM users')))
	def db_execute(query_string, **kwargs):
		db_connection.execute(sqlalchemy.text(query_string), **kwargs)
	with db_connection.begin() as transaction:
		db_execute('ALTER TABLE users ALTER COLUMN id DROP DEFAULT')
		db_execute('DROP SEQUENCE users_id_seq')
		for table in user_id_tables:
			db_execute('ALTER TABLE ' + table + ' DROP CONSTRAINT ' + table + '_user_id_fkey')
		db_execute('ALTER TABLE users ALTER COLUMN id TYPE varchar USING (id::varchar)')
		for table in user_id_tables:
			db_execute('ALTER TABLE ' + table + ' ALTER COLUMN user_id TYPE varchar USING (user_id::varchar)')
		db_execute('ALTER TABLE users ALTER COLUMN name DROP NOT NULL')

		for new_user_id, old_user_id in usernames.items():
			old_user_id = str(old_user_id)
			db_execute(
				"""\
					INSERT INTO users (id, name, phone_carrier, phone_number, email_address, otp_secret)\
					SELECT :new_user_id, NULL, phone_carrier, phone_number, email_address, otp_secret\
					FROM users WHERE id = :old_user_id\
				""",
				new_user_id=new_user_id,
				old_user_id=old_user_id
			)
			for table in user_id_tables:
				db_execute(
					'UPDATE ' + table + ' SET user_id = :new_user_id WHERE user_id = :old_user_id',
					new_user_id=new_user_id,
					old_user_id=old_user_id
				)
		for old_user_id in usernames.values():
			db_execute('DELETE FROM users WHERE id = :old_user_id', old_user_id=str(old_user_id))
		for table in user_id_tables:
			db_execute('ALTER TABLE ' + table + ' ADD CONSTRAINT ' + table + '_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id)')
	db_schema_migration.drop_columns('users', ('name', 'last_login', 'expiration', 'description'))

	op.drop_column('storage_data', 'modified')

	op.create_table(
		'meta_data',
		sqlalchemy.Column('id', sqlalchemy.String, primary_key=True),
		sqlalchemy.Column('value_type', sqlalchemy.String, default='str'),
		sqlalchemy.Column('value', sqlalchemy.String)
	)

	db_schema_migration.drop_columns('messages', ('testing', 'reported', 'delivery_status', 'delivery_details'))

	db_schema_migration.rename_columns('deaddrop_connections', (
		('ip', 'visitor_ip'),
		('count', 'visit_count'),
		('last_seen', 'last_visit'),
		('first_seen', 'first_visit'),
	))

	op.add_column('campaigns', sqlalchemy.Column('reject_after_credentials', sqlalchemy.Boolean, default=False))
	op.execute('UPDATE campaigns SET reject_after_credentials = CASE WHEN (max_credentials IS NULL) THEN false ELSE true END')
	op.drop_column('campaigns', 'max_credentials')

	op.drop_column('authenticated_sessions', 'last_seen')
	op.add_column('authenticated_sessions', sqlalchemy.Column('last_seen', sqlalchemy.Integer, nullable=False))
	op.drop_column('authenticated_sessions', 'created')
	op.add_column('authenticated_sessions', sqlalchemy.Column('created', sqlalchemy.Integer, nullable=False))

	alert_subscriptions_type.create(op.get_bind(), checkfirst=True)
	op.add_column('alert_subscriptions', sqlalchemy.Column('type', alert_subscriptions_type, default='sms', server_default='sms', nullable=False))
	op.alter_column('alert_subscriptions', 'expiration', new_column_name='mute_timestamp')

	# adjust the schema version metadata
	op.execute('INSERT INTO meta_data (id, value_type, value) VALUES (\'schema_version\', \'int\', \'7\')')
