"""add_request_ticket_data

Revision ID: 0fedf439118e
Revises: 2db8a5ca425e
Create Date: 2023-02-16 07:33:22.842834

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '0fedf439118e'
down_revision = '2db8a5ca425e'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('artifact_requests', sa.Column('ticket_id', sa.Integer(), nullable=True))

    
def downgrade():
    op.drop_column('artifact_requests', sa.Column('ticket_id', sa.Integer(), nullable=True))