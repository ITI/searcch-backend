"""add user_ipd_credential table

Revision ID: f29a393d7f66
Revises: b11c5baa16f9
Create Date: 2023-02-20 12:50:55.824852

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'f29a393d7f66'
down_revision = 'b11c5baa16f9'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('user_idp_credentials',
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('github_id', sa.Integer(), nullable=True),
    sa.Column('google_id', sa.String(length=256), nullable=True),
    sa.Column('cilogon_id', sa.String(length=256), nullable=True),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('user_id'),
    sa.UniqueConstraint('github_id', 'google_id', 'cilogon_id')
    )


def downgrade():
    op.drop_table('user_idp_credentials')
