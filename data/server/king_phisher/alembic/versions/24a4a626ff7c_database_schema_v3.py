"""Database Schema v3

Revision ID: 24a4a626ff7c
Revises: None
Create Date: 2015-07-17

"""

# revision identifiers, used by Alembic.
revision = '24a4a626ff7c'
down_revision = None

import os
import sys
sys.path.insert(1, os.path.abspath(os.path.join(os.path.dirname(__file__), *['..'] * 5)))

from alembic import op
from king_phisher.server.database import manager as db_manager
import sqlalchemy

def upgrade():
	op.create_table(
		'campaign_types',
		sqlalchemy.Column('id', sqlalchemy.Integer, primary_key=True),
		sqlalchemy.Column('name', sqlalchemy.String, nullable=False),
		sqlalchemy.Column('description', sqlalchemy.String)
	)

	op.create_table(
		'company_departments',
		sqlalchemy.Column('id', sqlalchemy.Integer, primary_key=True),
		sqlalchemy.Column('name', sqlalchemy.String, nullable=False),
		sqlalchemy.Column('description', sqlalchemy.String)
	)

	op.create_table(
		'industries',
		sqlalchemy.Column('id', sqlalchemy.Integer, primary_key=True),
		sqlalchemy.Column('name', sqlalchemy.String, nullable=False),
		sqlalchemy.Column('description', sqlalchemy.String)
	)

	op.create_table(
		'companies',
		sqlalchemy.Column('id', sqlalchemy.Integer, primary_key=True),
		sqlalchemy.Column('name', sqlalchemy.String, unique=True, nullable=False),
		sqlalchemy.Column('description', sqlalchemy.String),
		sqlalchemy.Column('industry_id', sqlalchemy.Integer, sqlalchemy.ForeignKey('industries.id')),
		sqlalchemy.Column('url_main', sqlalchemy.String),
		sqlalchemy.Column('url_email', sqlalchemy.String),
		sqlalchemy.Column('url_remote_access', sqlalchemy.String)
	)

	alert_subscriptions_type = sqlalchemy.Enum('email', 'sms', name='alert_subscription_type')
	alert_subscriptions_type.create(op.get_bind(), checkfirst=True)
	op.add_column('alert_subscriptions', sqlalchemy.Column('type', alert_subscriptions_type, default='sms', server_default='sms', nullable=False))
	op.add_column('alert_subscriptions', sqlalchemy.Column('mute_timestamp', sqlalchemy.DateTime))
	op.add_column('campaigns', sqlalchemy.Column('campaign_type_id', sqlalchemy.Integer, sqlalchemy.ForeignKey('campaign_types.id')))
	op.add_column('campaigns', sqlalchemy.Column('company_id', sqlalchemy.Integer, sqlalchemy.ForeignKey('companies.id')))
	op.add_column('campaigns', sqlalchemy.Column('expiration', sqlalchemy.DateTime))
	op.add_column('messages', sqlalchemy.Column('company_department_id', sqlalchemy.Integer, sqlalchemy.ForeignKey('company_departments.id')))
	op.add_column('users', sqlalchemy.Column('email_address', sqlalchemy.String))
	op.add_column('users', sqlalchemy.Column('otp_secret', sqlalchemy.String(16)))

	db_manager.Session.remove()
	db_manager.Session.configure(bind=op.get_bind())
	session = db_manager.Session()
	db_manager.set_meta_data('schema_version', 3, session=session)
	session.commit()

def downgrade():
	op.drop_column('alert_subscriptions', 'type')
	op.drop_column('alert_subscriptions', 'mute_timestamp')
	op.drop_column('campaigns', 'campaign_type_id')
	op.drop_column('campaigns', 'company_id')
	op.drop_column('campaigns', 'expiration')
	op.drop_column('messages', 'company_department_id')
	op.drop_column('users', 'email_address')
	op.drop_column('users', 'otp_secret')

	op.drop_table('campaign_types')
	op.drop_table('company_departments')
	op.drop_table('companies')
	op.drop_table('industries')

	db_manager.Session.remove()
	db_manager.Session.configure(bind=op.get_bind())
	session = db_manager.Session()
	db_manager.set_meta_data('schema_version', 2, session=session)
	session.commit()
