"""add_artifact_requests

Revision ID: f7114d7f71ee
Revises: 7fa25575444c
Create Date: 2022-11-11 23:12:56.276129

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'f7114d7f71ee'
down_revision = '7fa25575444c'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('artifact_requests',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('requester_user_id', sa.Integer(), nullable=False),
        sa.Column('agreement_file', sa.LargeBinary(), nullable=False),
        sa.Column('research_desc', sa.Text(), nullable=True),
        sa.Column('research_that_interact', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['requester_user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade():
    op.drop_table('artifact_requests')
