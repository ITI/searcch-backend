"""add column position in persons

Revision ID: a14e700c0108
Revises: f7114d7f71ee
Create Date: 2022-12-07 22:39:19.317244

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'a14e700c0108'
down_revision = 'f7114d7f71ee'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('persons', sa.Column('position', sa.String(), nullable=True))


def downgrade():
    op.drop_column('persons', 'position')
