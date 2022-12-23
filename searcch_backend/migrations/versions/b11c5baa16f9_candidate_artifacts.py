"""candidate-artifacts

Revision ID: b11c5baa16f9
Revises: 5732a6402677
Create Date: 2022-12-21 23:43:11.648014

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'b11c5baa16f9'
down_revision = '5732a6402677'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('artifact_imports', sa.Column('autofollow', sa.Boolean()))
    op.create_table('candidate_artifacts',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('url', sa.String(length=1024), nullable=False),
    sa.Column('ctime', sa.DateTime(), nullable=False),
    sa.Column('mtime', sa.DateTime(), nullable=True),
    sa.Column('type', sa.Enum('publication', 'presentation', 'dataset', 'software', 'other', name='candidate_artifact_enum'), nullable=True),
    sa.Column('title', sa.Text(), nullable=True),
    sa.Column('name', sa.Text(), nullable=True),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('owner_id', sa.Integer(), nullable=False),
    sa.Column('artifact_import_id', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(['artifact_import_id'], ['artifact_imports.id'], ),
    sa.ForeignKeyConstraint(['owner_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('candidate_artifact_metadata',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('candidate_artifact_id', sa.Integer(), nullable=True),
    sa.Column('name', sa.String(length=64), nullable=False),
    sa.Column('value', sa.String(length=16384), nullable=False),
    sa.Column('type', sa.String(length=256), nullable=True),
    sa.Column('source', sa.String(length=256), nullable=True),
    sa.ForeignKeyConstraint(['candidate_artifact_id'], ['candidate_artifacts.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('name', 'candidate_artifact_id', 'value', 'type')
    )
    op.create_table('candidate_artifact_relationships',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('artifact_id', sa.Integer(), nullable=True),
    sa.Column('relation', sa.Enum('cites', 'supplements', 'extends', 'uses', 'describes', 'requires', 'processes', 'produces', name='candidate_artifact_relationship_enum'), nullable=True),
    sa.Column('related_candidate_id', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(['artifact_id'], ['artifacts.id'], ),
    sa.ForeignKeyConstraint(['related_candidate_id'], ['candidate_artifacts.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('artifact_id', 'relation', 'related_candidate_id')
    )
    op.create_table('candidate_relationships',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('candidate_artifact_id', sa.Integer(), nullable=True),
    sa.Column('relation', sa.Enum('cites', 'supplements', 'extends', 'uses', 'describes', 'requires', 'processes', 'produces', name='candidate_relationship_enum'), nullable=True),
    sa.Column('related_candidate_id', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(['candidate_artifact_id'], ['candidate_artifacts.id'], ),
    sa.ForeignKeyConstraint(['related_candidate_id'], ['candidate_artifacts.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('candidate_artifact_id', 'relation', 'related_candidate_id')
    )


def downgrade():
    op.drop_column('artifact_imports', 'autofollow')
    op.drop_table('candidate_relationships')
    op.drop_table('candidate_artifact_relationships')
    op.drop_table('candidate_artifact_metadata')
    op.drop_table('candidate_artifacts')
