"""Schema v4

Revision ID: 7c315088952
Revises: 24a4a626ff7c
Create Date: 2015-07-20 16:04:51.799979

"""

# revision identifiers, used by Alembic.
revision = '7c315088952'
down_revision = '24a4a626ff7c'

import os
import sys
sys.path.insert(1, os.path.abspath(os.path.join(os.path.dirname(__file__), *['..'] * 5)))

from alembic import op
from king_phisher.server.database import manager as db_manager
import sqlalchemy


def upgrade():
	op.add_column('campaigns', sqlalchemy.Column('description', sqlalchemy.String))
	op.add_column('messages', sqlalchemy.Column('opener_ip', sqlalchemy.String))
	op.add_column('messages', sqlalchemy.Column('opener_user_agent', sqlalchemy.String))

	db_manager.Session.remove()
	db_manager.Session.configure(bind=op.get_bind())
	session = db_manager.Session()
	db_manager.set_meta_data('schema_version', 4, session=session)
	session.commit()

def downgrade():
	op.drop_column('campaigns', 'description')
	op.drop_column('messages', 'opener_ip')
	op.drop_column('messages', 'opener_user_agent')

	db_manager.Session.remove()
	db_manager.Session.configure(bind=op.get_bind())
	session = db_manager.Session()
	db_manager.set_meta_data('schema_version', 3, session=session)
	session.commit()
