"""schema v9

Revision ID: ba93bb36d6
Revises: b8443afcb9e
Create Date: 2018-05-31 15:34:31.667556

"""

# revision identifiers, used by Alembic.
revision = 'ba93bb36d6'
down_revision = 'b8443afcb9e'

import os
import sys
sys.path.insert(1, os.path.abspath(os.path.join(os.path.dirname(__file__), *['..'] * 5)))

from alembic import op
from king_phisher.server.database import manager as db_manager
from king_phisher.server.database import schema_migration as db_schema_migration
import sqlalchemy


def upgrade():

	op.create_table(
		'test_answers',
		sqlalchemy.Column('id', sqlalchemy.Integer, primary_key=True),
		sqlalchemy.Column('answer', sqlalchemy.String, nullable=False),
		sqlalchemy.Column('case_sensitive', sqlalchemy.Boolean),
	)

	op.create_table(
		'test_modules',
		sqlalchemy.Column('id', sqlalchemy.Integer, primary_key=True),
		sqlalchemy.Column('name', sqlalchemy.String, nullable=False),
		sqlalchemy.Column('description', sqlalchemy.String),
		sqlalchemy.Column('created', sqlalchemy.DateTime)
	)

	op.create_table(
		'tests',
		sqlalchemy.Column('id', sqlalchemy.Integer, primary_key=True),
		sqlalchemy.Column('name', sqlalchemy.Integer, nullable=False),
		sqlalchemy.Column('description', sqlalchemy.String),
		sqlalchemy.Column('created', sqlalchemy.DateTime),
		sqlalchemy.Column('minimum_score', sqlalchemy.Integer, nullable=False),
		sqlalchemy.Column('max_attempts', sqlalchemy.Integer),
		sqlalchemy.Column('user_id', sqlalchemy.Integer, sqlalchemy.ForeignKey('users.id'), nullable=False)
	)

	op.add_column('campaigns', sqlalchemy.Column('test_id', sqlalchemy.Integer, sqlalchemy.ForeignKey('tests.id'),))

	op.create_table(
		'test_submissions',
		sqlalchemy.Column('id', sqlalchemy.Integer, primary_key=True),
		sqlalchemy.Column('campaign_id', sqlalchemy.Integer, sqlalchemy.ForeignKey('campaigns.id'), nullable=False),
		sqlalchemy.Column('created', sqlalchemy.DateTime),
		sqlalchemy.Column('test_id', sqlalchemy.Integer, sqlalchemy.ForeignKey('tests.id'), nullable=False),
		sqlalchemy.Column('visit_id', sqlalchemy.String, sqlalchemy.ForeignKey('visits.id'), nullable=False),
	)

	op.create_table(
		'test_questions',
		sqlalchemy.Column('id', sqlalchemy.Integer, primary_key=True),
		sqlalchemy.Column('question', sqlalchemy.String, nullable=False),
		sqlalchemy.Column('question_type', sqlalchemy.String, nullable=False),
		sqlalchemy.Column('description', sqlalchemy.String),
		sqlalchemy.Column('hint', sqlalchemy.String),
		sqlalchemy.Column('url_reference', sqlalchemy.String),
		sqlalchemy.Column('url_hint', sqlalchemy.String),
		sqlalchemy.Column('test_answer_id', sqlalchemy.Integer, sqlalchemy.ForeignKey('test_answers.id'))
	)

	op.create_table(
		'test_question_link_test_answer',
		sqlalchemy.Column('id', sqlalchemy.Integer, primary_key=True),
		sqlalchemy.Column('test_answer_id', sqlalchemy.Integer, sqlalchemy.ForeignKey('test_answers.id'), nullable=False),
		sqlalchemy.Column('test_question_id', sqlalchemy.Integer, sqlalchemy.ForeignKey('test_questions.id'), nullable=False)
	)

	op.create_table(
		'test_submission_link_test_answer',
		sqlalchemy.Column('id', sqlalchemy.Integer, primary_key=True),
		sqlalchemy.Column('test_submission_id', sqlalchemy.Integer, sqlalchemy.ForeignKey('test_submissions.id'), nullable=False),
		sqlalchemy.Column('test_question_id', sqlalchemy.Integer, sqlalchemy.ForeignKey('test_questions.id'), nullable=False),
		sqlalchemy.Column('test_answer_id', sqlalchemy.Integer, sqlalchemy.ForeignKey('test_answers.id'), nullable=False)
	)

	op.create_table(
		'test_link_test_module',
		sqlalchemy.Column('id', sqlalchemy.Integer, primary_key=True),
		sqlalchemy.Column('test_id', sqlalchemy.Integer, sqlalchemy.ForeignKey('tests.id'), nullable=False),
		sqlalchemy.Column('test_module_id', sqlalchemy.Integer, sqlalchemy.ForeignKey('test_modules.id'), nullable=False)
	)

	op.create_table(
		'actual_answers',
		sqlalchemy.Column('id', sqlalchemy.Integer, primary_key=True),
		sqlalchemy.Column('test_question_id', sqlalchemy.Integer, sqlalchemy.ForeignKey('test_questions.id'), nullable=False),
		sqlalchemy.Column('test_answers.id', sqlalchemy.Integer, sqlalchemy.ForeignKey('test_answers.id'), nullable=False)
	)

	db_manager.Session.remove()
	db_manager.Session.configure(bind=op.get_bind())
	session = db_manager.Session()
	db_manager.set_metadata('schema_version', 9, session=session)
	session.commit()

def downgrade():
	op.drop_column('campaigns', 'test_id')
	tables = [
		'test_link_test_module',
		'test_submission_link_test_answer',
		'test_question_link_test_answer',
		'test_questions',
		'test_submissions',
		'tests',
		'test_modules',
		'test_answers',
		'actual_answers'
	]

	for table in tables:
		op.drop_table(table)

	db_manager.Session.remove()
	db_manager.Session.configure(bind=op.get_bind())
	session = db_manager.Session()
	db_manager.set_metadata('schema_version', 8, session=session)
	session.commit()
