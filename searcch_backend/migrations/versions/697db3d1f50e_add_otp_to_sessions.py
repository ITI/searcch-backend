"""add_otp_to_sessions

Revision ID: 697db3d1f50e
Revises: 710d73f5c541
Create Date: 2023-07-12 11:36:22.957366

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '697db3d1f50e'
down_revision = '710d73f5c541'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('sessions', sa.Column('otp', sa.Integer(), nullable=True))


def downgrade():
    op.drop_column('sessions', 'otp')

