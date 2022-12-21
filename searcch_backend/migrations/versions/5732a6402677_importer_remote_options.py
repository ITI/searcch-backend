"""importer-remote-options

Revision ID: 5732a6402677
Revises: e030638b4df0
Create Date: 2022-12-19 21:22:49.982934

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '5732a6402677'
down_revision = 'e030638b4df0'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('artifact_imports', sa.Column('noextract', sa.Boolean()))
    op.add_column('artifact_imports', sa.Column('nofetch', sa.Boolean()))
    op.add_column('artifact_imports', sa.Column('noremove', sa.Boolean()))


def downgrade():
    op.drop_column('artifact_imports', 'noremove')
    op.drop_column('artifact_imports', 'nofetch')
    op.drop_column('artifact_imports', 'noextract')
