"""Schema v5

Revision ID: 83e4121b299
Revises: 7c315088952
Create Date: 2015-08-21

"""

# revision identifiers, used by Alembic.
revision = '83e4121b299'
down_revision = '7c315088952'

import os
import sys
sys.path.insert(1, os.path.abspath(os.path.join(os.path.dirname(__file__), *['..'] * 5)))

from alembic import op
from king_phisher.server.database import manager as db_manager
import sqlalchemy


def upgrade():
	op.drop_column('messages', 'company_name')

	db_manager.Session.remove()
	db_manager.Session.configure(bind=op.get_bind())
	session = db_manager.Session()
	db_manager.set_meta_data('schema_version', 5, session=session)
	session.commit()

def downgrade():
	op.add_column('messages', sqlalchemy.Column('company_name', sqlalchemy.String))

	db_manager.Session.remove()
	db_manager.Session.configure(bind=op.get_bind())
	session = db_manager.Session()
	db_manager.set_meta_data('schema_version', 4, session=session)
	session.commit()
