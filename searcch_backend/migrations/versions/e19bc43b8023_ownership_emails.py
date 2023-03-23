"""ownership emails

Revision ID: e19bc43b8023
Revises: f29a393d7f66
Create Date: 2023-03-23 00:35:45.632038

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'e19bc43b8023'
down_revision = 'f29a393d7f66'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('ownership_emails',
    sa.Column('email', sa.String(length=256), nullable=False),
    sa.Column('key', sa.String(length=64), nullable=False),
    sa.Column('valid_until', sa.DateTime(), nullable=False),
    sa.Column('opt_out', sa.Boolean(), nullable=False),
    sa.PrimaryKeyConstraint('email')
    )
    op.create_table('ownership_invitations',
    sa.Column('email', sa.String(length=256), nullable=False),
    sa.Column('artifact_group_id', sa.Integer(), nullable=False),
    sa.Column('attempts', sa.Integer(), nullable=False),
    sa.Column('last_attempt', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['artifact_group_id'], ['artifact_groups.id'], ),
    sa.ForeignKeyConstraint(['email'], ['ownership_emails.email'], ),
    sa.PrimaryKeyConstraint('email', 'artifact_group_id')
    )


def downgrade():
    op.drop_table('ownership_invitations')
    op.drop_table('ownership_emails')
