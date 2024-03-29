"""artifact-ext_id-nullable

Revision ID: 530e0b21aacd
Revises: 67619401b55d
Create Date: 2021-07-21 04:42:52.154798

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '530e0b21aacd'
down_revision = '67619401b55d'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('artifacts', 'ext_id',
               existing_type=sa.VARCHAR(length=512),
               nullable=True)
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('artifacts', 'ext_id',
               existing_type=sa.VARCHAR(length=512),
               nullable=False)
    # ### end Alembic commands ###
