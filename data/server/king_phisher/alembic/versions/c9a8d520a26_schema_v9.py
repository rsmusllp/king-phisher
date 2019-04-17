"""Schema v9

Revision ID: b8443afcb9e
Revises: b76eab0a059
Create Date: 2018-10-25

"""

# revision identifiers, used by Alembic.
revision = 'c9a8d520a26'
down_revision = 'b8443afcb9e'

import os
import sys
sys.path.insert(1, os.path.abspath(os.path.join(os.path.dirname(__file__), *['..'] * 5)))

from alembic import op
from king_phisher.server.database import manager as db_manager
from king_phisher.server.database import schema_migration as db_schema_migration
import sqlalchemy

def upgrade():
	op.add_column('campaigns', sqlalchemy.Column('credential_regex_username', sqlalchemy.String))
	op.add_column('campaigns', sqlalchemy.Column('credential_regex_password', sqlalchemy.String))
	op.add_column('campaigns', sqlalchemy.Column('credential_regex_mfa_token', sqlalchemy.String))

	op.add_column('credentials', sqlalchemy.Column('mfa_token', sqlalchemy.String))
	op.add_column('credentials', sqlalchemy.Column('regex_validated', sqlalchemy.Boolean))

	op.add_column('users', sqlalchemy.Column('access_level', sqlalchemy.Integer))
	op.execute('UPDATE users SET access_level = 1000')
	op.alter_column('users', 'access_level', nullable=False)

	# adjust the schema version metadata
	db_manager.Session.remove()
	db_manager.Session.configure(bind=op.get_bind())
	session = db_manager.Session()
	db_manager.set_metadata('schema_version', 9, session=session)
	session.commit()

def downgrade():
	db_schema_migration.drop_columns('users', ('access_level',))
	db_schema_migration.drop_columns('credentials', ('regex_validated', 'mfa_token'))
	db_schema_migration.drop_columns('campaigns', ('credential_regex_mfa_token', 'credential_regex_password', 'credential_regex_username'))

	# adjust the schema version metadata
	db_manager.Session.remove()
	db_manager.Session.configure(bind=op.get_bind())
	session = db_manager.Session()
	db_manager.set_metadata('schema_version', 8, session=session)
	session.commit()
