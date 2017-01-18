"""Schema v7

Revision ID: b76eab0a059
Revises: a695de64338
Create Date: 2016-12-07

"""

# revision identifiers, used by Alembic.
revision = 'b76eab0a059'
down_revision = 'a695de64338'

import os
import sys
sys.path.insert(1, os.path.abspath(os.path.join(os.path.dirname(__file__), *['..'] * 5)))

from alembic import op
from king_phisher.server.database import manager as db_manager
import sqlalchemy


def upgrade():
	op.create_table(
		'storage_data',
		sqlalchemy.Column('id', sqlalchemy.Integer, primary_key=True),
		sqlalchemy.Column('created', sqlalchemy.DateTime),
		sqlalchemy.Column('namespace', sqlalchemy.String),
		sqlalchemy.Column('key', sqlalchemy.String, nullable=False),
		sqlalchemy.Column('value', sqlalchemy.Binary)
	)

	db_manager.Session.remove()
	db_manager.Session.configure(bind=op.get_bind())
	session = db_manager.Session()
	db_manager.set_meta_data('schema_version', 7, session=session)
	session.commit()

def downgrade():
	op.drop_table('storage_data')

	db_manager.Session.remove()
	db_manager.Session.configure(bind=op.get_bind())
	session = db_manager.Session()
	db_manager.set_meta_data('schema_version', 6, session=session)
	session.commit()
