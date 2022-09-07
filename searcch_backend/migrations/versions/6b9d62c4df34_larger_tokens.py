
"""larger-tokens

Revision ID: 6b9d62c4df34
Revises: 3c50644eb7d8
Create Date: 2022-05-12 19:39:08.975818

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '6b9d62c4df34'
down_revision = '3c50644eb7d8'
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column('sessions', 'sso_token', existing_type=sa.String(64), type_=sa.String(256), nullable=False)

def downgrade():
    op.alter_column('sessions', 'sso_token', existing_type=sa.String(256), type_=sa.String(64), nullable=False)
