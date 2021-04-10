"""update person table

Revision ID: c312ec44b050
Revises: c43eb4aa4eab
Create Date: 2021-04-09 10:26:09.623266

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'c312ec44b050'
down_revision = 'c43eb4aa4eab'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('persons', sa.Column('profile_photo', postgresql.BYTEA(), nullable=True))
    op.add_column('persons', sa.Column('research_interests', sa.Text(), nullable=True))
    op.add_column('persons', sa.Column('website', sa.Text(), nullable=True))
    

def downgrade():
    op.drop_column('persons', 'profile_photo')
    op.drop_column('persons', 'research_interests')
    op.drop_column('persons', 'website')
    