"""add_dataset_metadata

Revision ID: 2db8a5ca425e
Revises: a14e700c0108
Create Date: 2023-01-28 08:18:58.085364

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '2db8a5ca425e'
down_revision = 'a14e700c0108'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('artifacts', sa.Column('datasetCategory', sa.Text(), nullable=True))
    op.add_column('artifacts', sa.Column('datasetSubCategory', sa.Text(), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('artifacts', 'datasetCategory')
    op.drop_column('artifacts', 'datasetSubCategory')
    # ### end Alembic commands ###
