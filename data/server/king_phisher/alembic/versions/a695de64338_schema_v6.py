"""Schema v6

Revision ID: a695de64338
Revises: 83e4121b299
Create Date: 2015-09-28

"""

# revision identifiers, used by Alembic.
revision = 'a695de64338'
down_revision = '83e4121b299'

import os
import sys
sys.path.insert(1, os.path.abspath(os.path.join(os.path.dirname(__file__), *['..'] * 5)))

from alembic import op
from king_phisher.server.database import manager as db_manager
import sqlalchemy


def upgrade():
	op.create_table(
		'authenticated_sessions',
		sqlalchemy.Column('id', sqlalchemy.String, primary_key=True),
		sqlalchemy.Column('created', sqlalchemy.Integer, nullable=False),
		sqlalchemy.Column('last_seen', sqlalchemy.Integer, nullable=False),
		sqlalchemy.Column('user_id', sqlalchemy.String, sqlalchemy.ForeignKey('users.id'), nullable=False)
	)

	db_manager.Session.remove()
	db_manager.Session.configure(bind=op.get_bind())
	session = db_manager.Session()
	db_manager.set_meta_data('schema_version', 6, session=session)
	session.commit()

def downgrade():
	op.drop_table('authenticated_sessions')

	db_manager.Session.remove()
	db_manager.Session.configure(bind=op.get_bind())
	session = db_manager.Session()
	db_manager.set_meta_data('schema_version', 5, session=session)
	session.commit()
