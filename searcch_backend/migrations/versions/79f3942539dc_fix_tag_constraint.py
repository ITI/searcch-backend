"""fix-tag-constraint

Revision ID: 79f3942539dc
Revises: 09d7d4f03602
Create Date: 2021-07-15 08:00:38.652619

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '79f3942539dc'
down_revision = '09d7d4f03602'
branch_labels = None
depends_on = None


def upgrade():
    op.execute("update artifact_tags set source='' where source is NULL")
    op.alter_column(
        'artifact_tags', 'source',
        existing_type=sa.VARCHAR(length=256),nullable=False)
    op.drop_constraint(
        'artifact_tags_tag_artifact_id_key', 'artifact_tags',
        type_='unique')
    op.create_unique_constraint(
        'artifact_tags_tag_artifact_id_source_key', 'artifact_tags',
        ['tag', 'artifact_id', 'source'])


def downgrade():
    op.drop_constraint(
        'artifact_tags_tag_artifact_id_source_key',
        'artifact_tags', type_='unique')
    op.create_unique_constraint(
        'artifact_tags_tag_artifact_id_key',
        'artifact_tags', ['tag', 'artifact_id'])
    op.alter_column(
        'artifact_tags', 'source',
        existing_type=sa.VARCHAR(length=256),nullable=True)
