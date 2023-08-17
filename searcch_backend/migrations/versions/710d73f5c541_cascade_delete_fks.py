"""cascade_delete_fks

Revision ID: 710d73f5c541
Revises: 
Create Date: 2023-06-17 07:55:20.663545

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '710d73f5c541'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    # op.create_table('artifact_search_view',
    # sa.Column('dummy_id', sa.Integer(), nullable=False),
    # sa.Column('artifact_group_id', sa.Integer(), nullable=False),
    # sa.Column('artifact_id', sa.Integer(), nullable=True),
    # sa.Column('doc_vector', postgresql.TSVECTOR(), nullable=True),
    # sa.ForeignKeyConstraint(['artifact_group_id'], ['artifact_groups.id'], ondelete='CASCADE'),
    # sa.PrimaryKeyConstraint('dummy_id')
    # )
    # op.drop_table('alembic_lock')
    op.drop_constraint('affiliations_org_id_fkey', 'affiliations', type_='foreignkey')
    op.drop_constraint('affiliations_person_id_fkey', 'affiliations', type_='foreignkey')
    op.create_foreign_key(None, 'affiliations', 'persons', ['person_id'], ['id'], ondelete='CASCADE')
    op.create_foreign_key(None, 'affiliations', 'organizations', ['org_id'], ['id'], ondelete='CASCADE')
    op.drop_constraint('artifact_affiliations_affiliation_id_fkey', 'artifact_affiliations', type_='foreignkey')
    op.drop_constraint('artifact_affiliations_artifact_id_fkey', 'artifact_affiliations', type_='foreignkey')
    op.create_foreign_key(None, 'artifact_affiliations', 'artifacts', ['artifact_id'], ['id'], ondelete='CASCADE')
    op.create_foreign_key(None, 'artifact_affiliations', 'affiliations', ['affiliation_id'], ['id'], ondelete='CASCADE')
    op.drop_constraint('artifact_badges_artifact_id_fkey', 'artifact_badges', type_='foreignkey')
    op.drop_constraint('artifact_badges_badge_id_fkey', 'artifact_badges', type_='foreignkey')
    op.create_foreign_key(None, 'artifact_badges', 'artifacts', ['artifact_id'], ['id'], ondelete='CASCADE')
    op.create_foreign_key(None, 'artifact_badges', 'badges', ['badge_id'], ['id'], ondelete='CASCADE')
    op.drop_constraint('artifact_curations_artifact_id_fkey', 'artifact_curations', type_='foreignkey')
    op.drop_constraint('artifact_curations_curator_id_fkey', 'artifact_curations', type_='foreignkey')
    op.create_foreign_key(None, 'artifact_curations', 'artifacts', ['artifact_id'], ['id'], ondelete='CASCADE')
    op.create_foreign_key(None, 'artifact_curations', 'users', ['curator_id'], ['id'], ondelete='CASCADE')
    op.drop_constraint('artifact_favorites_artifact_group_id_fkey', 'artifact_favorites', type_='foreignkey')
    op.drop_constraint('artifact_favorites_artifact_id_fkey', 'artifact_favorites', type_='foreignkey')
    op.drop_constraint('artifact_favorites_user_id_fkey', 'artifact_favorites', type_='foreignkey')
    op.create_foreign_key(None, 'artifact_favorites', 'users', ['user_id'], ['id'], ondelete='CASCADE')
    op.create_foreign_key(None, 'artifact_favorites', 'artifacts', ['artifact_id'], ['id'], ondelete='CASCADE')
    op.create_foreign_key(None, 'artifact_favorites', 'artifact_groups', ['artifact_group_id'], ['id'], ondelete='CASCADE')
    op.drop_constraint('artifact_file_members_file_content_id_fkey', 'artifact_file_members', type_='foreignkey')
    op.drop_constraint('artifact_file_members_parent_file_id_fkey', 'artifact_file_members', type_='foreignkey')
    op.create_foreign_key(None, 'artifact_file_members', 'artifact_files', ['parent_file_id'], ['id'], ondelete='CASCADE')
    op.create_foreign_key(None, 'artifact_file_members', 'file_content', ['file_content_id'], ['id'], ondelete='CASCADE')
    op.drop_constraint('artifact_files_artifact_id_fkey', 'artifact_files', type_='foreignkey')
    op.drop_constraint('artifact_files_file_content_id_fkey', 'artifact_files', type_='foreignkey')
    op.create_foreign_key(None, 'artifact_files', 'artifacts', ['artifact_id'], ['id'], ondelete='CASCADE')
    op.create_foreign_key(None, 'artifact_files', 'file_content', ['file_content_id'], ['id'], ondelete='CASCADE')
    op.drop_constraint('artifact_funding_artifact_id_fkey', 'artifact_funding', type_='foreignkey')
    op.drop_constraint('artifact_funding_funding_org_id_fkey', 'artifact_funding', type_='foreignkey')
    op.create_foreign_key(None, 'artifact_funding', 'artifacts', ['artifact_id'], ['id'], ondelete='CASCADE')
    op.create_foreign_key(None, 'artifact_funding', 'organizations', ['funding_org_id'], ['id'], ondelete='CASCADE')
    op.drop_constraint('artifact_groups_id_next_version_key', 'artifact_groups', type_='unique')
    op.drop_constraint('artifact_groups_owner_id_fkey', 'artifact_groups', type_='foreignkey')
    op.create_foreign_key(None, 'artifact_groups', 'users', ['owner_id'], ['id'], ondelete='CASCADE')
    op.create_foreign_key(None, 'artifact_groups', 'artifact_publications', ['publication_id'], ['id'], ondelete='CASCADE')
    op.drop_constraint('artifact_imports_artifact_group_id_fkey', 'artifact_imports', type_='foreignkey')
    op.drop_constraint('artifact_imports_artifact_id_fkey', 'artifact_imports', type_='foreignkey')
    op.drop_constraint('artifact_imports_owner_id_fkey', 'artifact_imports', type_='foreignkey')
    op.drop_constraint('artifact_imports_parent_artifact_id_fkey', 'artifact_imports', type_='foreignkey')
    op.create_foreign_key(None, 'artifact_imports', 'users', ['owner_id'], ['id'], ondelete='CASCADE')
    op.create_foreign_key(None, 'artifact_imports', 'artifact_groups', ['artifact_group_id'], ['id'], ondelete='CASCADE')
    op.create_foreign_key(None, 'artifact_imports', 'artifacts', ['parent_artifact_id'], ['id'], ondelete='CASCADE')
    op.create_foreign_key(None, 'artifact_imports', 'artifacts', ['artifact_id'], ['id'], ondelete='CASCADE')
    op.drop_constraint('artifact_metadata_artifact_id_fkey', 'artifact_metadata', type_='foreignkey')
    op.create_foreign_key(None, 'artifact_metadata', 'artifacts', ['artifact_id'], ['id'], ondelete='CASCADE')
    op.drop_constraint('artifact_owner_request_action_by_user_id_fkey', 'artifact_owner_request', type_='foreignkey')
    op.drop_constraint('artifact_owner_request_artifact_group_id_fkey', 'artifact_owner_request', type_='foreignkey')
    op.drop_constraint('artifact_owner_request_user_id_fkey', 'artifact_owner_request', type_='foreignkey')
    op.create_foreign_key(None, 'artifact_owner_request', 'users', ['user_id'], ['id'], ondelete='CASCADE')
    op.create_foreign_key(None, 'artifact_owner_request', 'artifact_groups', ['artifact_group_id'], ['id'], ondelete='CASCADE')
    op.create_foreign_key(None, 'artifact_owner_request', 'users', ['action_by_user_id'], ['id'], ondelete='CASCADE')
    op.drop_constraint('artifact_publications_publisher_id_fkey', 'artifact_publications', type_='foreignkey')
    op.create_foreign_key(None, 'artifact_publications', 'users', ['publisher_id'], ['id'], ondelete='CASCADE')
    op.drop_constraint('artifact_ratings_artifact_group_id_fkey', 'artifact_ratings', type_='foreignkey')
    op.drop_constraint('artifact_ratings_artifact_id_fkey', 'artifact_ratings', type_='foreignkey')
    op.drop_constraint('artifact_ratings_user_id_fkey', 'artifact_ratings', type_='foreignkey')
    op.create_foreign_key(None, 'artifact_ratings', 'users', ['user_id'], ['id'], ondelete='CASCADE')
    op.create_foreign_key(None, 'artifact_ratings', 'artifacts', ['artifact_id'], ['id'], ondelete='CASCADE')
    op.create_foreign_key(None, 'artifact_ratings', 'artifact_groups', ['artifact_group_id'], ['id'], ondelete='CASCADE')
    op.drop_constraint('artifact_relationships_artifact_group_id_fkey', 'artifact_relationships', type_='foreignkey')
    op.drop_constraint('artifact_relationships_artifact_id_fkey', 'artifact_relationships', type_='foreignkey')
    op.drop_constraint('artifact_relationships_related_artifact_group_id_fkey', 'artifact_relationships', type_='foreignkey')
    op.drop_constraint('artifact_relationships_related_artifact_id_fkey', 'artifact_relationships', type_='foreignkey')
    op.create_foreign_key(None, 'artifact_relationships', 'artifacts', ['artifact_id'], ['id'], ondelete='CASCADE')
    op.create_foreign_key(None, 'artifact_relationships', 'artifact_groups', ['artifact_group_id'], ['id'], ondelete='CASCADE')
    op.create_foreign_key(None, 'artifact_relationships', 'artifacts', ['related_artifact_id'], ['id'], ondelete='CASCADE')
    op.create_foreign_key(None, 'artifact_relationships', 'artifact_groups', ['related_artifact_group_id'], ['id'], ondelete='CASCADE')
    op.drop_constraint('artifact_releases_artifact_id_fkey', 'artifact_releases', type_='foreignkey')
    op.create_foreign_key(None, 'artifact_releases', 'artifacts', ['artifact_id'], ['id'], ondelete='CASCADE')
    op.alter_column('artifact_requests', 'project',
               existing_type=sa.TEXT(),
               nullable=False)
    op.alter_column('artifact_requests', 'project_description',
               existing_type=sa.TEXT(),
               nullable=False)
    op.alter_column('artifact_requests', 'representative_researcher_email',
               existing_type=sa.TEXT(),
               nullable=False)
    op.alter_column('artifact_requests', 'researchers',
               existing_type=sa.TEXT(),
               nullable=False)
    op.drop_constraint('artifact_requests_artifact_group_id_requester_user_id_key', 'artifact_requests', type_='unique')
    op.drop_constraint('artifact_requests_artifact_group_id_fkey', 'artifact_requests', type_='foreignkey')
    op.drop_constraint('artifact_requests_requester_user_id_fkey', 'artifact_requests', type_='foreignkey')
    op.create_foreign_key(None, 'artifact_requests', 'artifact_groups', ['artifact_group_id'], ['id'], ondelete='CASCADE')
    op.create_foreign_key(None, 'artifact_requests', 'users', ['requester_user_id'], ['id'], ondelete='CASCADE')
    op.drop_constraint('artifact_reviews_artifact_group_id_fkey1', 'artifact_reviews', type_='foreignkey')
    op.drop_constraint('artifact_reviews_artifact_id_fkey', 'artifact_reviews', type_='foreignkey')
    op.drop_constraint('artifact_reviews_user_id_fkey', 'artifact_reviews', type_='foreignkey')
    op.create_foreign_key(None, 'artifact_reviews', 'users', ['user_id'], ['id'], ondelete='CASCADE')
    op.create_foreign_key(None, 'artifact_reviews', 'artifacts', ['artifact_id'], ['id'], ondelete='CASCADE')
    op.create_foreign_key(None, 'artifact_reviews', 'artifact_groups', ['artifact_group_id'], ['id'], ondelete='CASCADE')
    op.drop_constraint('artifact_tags_artifact_id_fkey', 'artifact_tags', type_='foreignkey')
    op.create_foreign_key(None, 'artifact_tags', 'artifacts', ['artifact_id'], ['id'], ondelete='CASCADE')
    op.alter_column('artifacts', 'anonymization',
               existing_type=postgresql.ENUM('cryptopan-full', 'cryptopan-host', 'remove-host', 'none', 'custom', name='anon_type'),
               nullable=True,
               existing_server_default=sa.text("'none'::anon_type"))
    op.alter_column('artifacts', 'irb',
               existing_type=sa.BOOLEAN(),
               nullable=False,
               existing_server_default=sa.text('false'))
    op.alter_column('artifacts', 'type',
               existing_type=postgresql.ENUM('publication', 'presentation', 'dag', 'argus', 'pcap', 'netflow', 'flowtools', 'flowride', 'fsdb', 'csv', 'custom', 'dataset', name='artifact_enum'),
               nullable=True,
               existing_server_default=sa.text("'custom'::artifact_enum"))
    op.drop_constraint('artifacts_artifact_group_id_fkey', 'artifacts', type_='foreignkey')
    op.drop_constraint('artifacts_exporter_id_fkey', 'artifacts', type_='foreignkey')
    op.drop_constraint('artifacts_importer_id_fkey', 'artifacts', type_='foreignkey')
    op.drop_constraint('artifacts_license_id_fkey', 'artifacts', type_='foreignkey')
    op.drop_constraint('artifacts_owner_id_fkey', 'artifacts', type_='foreignkey')
    op.drop_constraint('artifacts_parent_id_fkey', 'artifacts', type_='foreignkey')
    op.create_foreign_key(None, 'artifacts', 'artifact_groups', ['artifact_group_id'], ['id'], ondelete='CASCADE')
    op.create_foreign_key(None, 'artifacts', 'licenses', ['license_id'], ['id'], ondelete='CASCADE')
    op.create_foreign_key(None, 'artifacts', 'users', ['owner_id'], ['id'], ondelete='CASCADE')
    op.create_foreign_key(None, 'artifacts', 'importers', ['importer_id'], ['id'], ondelete='CASCADE')
    op.create_foreign_key(None, 'artifacts', 'exporters', ['exporter_id'], ['id'], ondelete='CASCADE')
    op.create_foreign_key(None, 'artifacts', 'artifacts', ['parent_id'], ['id'], ondelete='CASCADE')
    op.create_unique_constraint(None, 'dua', ['collection', 'provider'])
    op.drop_constraint('importer_schedules_artifact_import_id_fkey', 'importer_schedules', type_='foreignkey')
    op.drop_constraint('importer_schedules_importer_instance_id_fkey', 'importer_schedules', type_='foreignkey')
    op.create_foreign_key(None, 'importer_schedules', 'artifact_imports', ['artifact_import_id'], ['id'], ondelete='CASCADE')
    op.create_foreign_key(None, 'importer_schedules', 'importer_instances', ['importer_instance_id'], ['id'], ondelete='CASCADE')
    op.alter_column('labels', 'artifact_id',
               existing_type=sa.INTEGER(),
               nullable=True)
    op.drop_constraint('link_to_artifact', 'labels', type_='foreignkey')
    op.create_foreign_key(None, 'labels', 'artifacts', ['artifact_id'], ['id'], ondelete='CASCADE')
    op.drop_index('org_idx', table_name='organizations')
    op.drop_constraint('person_metadata_person_id_fkey', 'person_metadata', type_='foreignkey')
    op.create_foreign_key(None, 'person_metadata', 'persons', ['person_id'], ['id'], ondelete='CASCADE')
    op.drop_index('person_idx', table_name='persons')
    op.drop_constraint('recent_views_artifact_group_id_fkey', 'recent_views', type_='foreignkey')
    op.drop_constraint('recent_views_user_id_fkey', 'recent_views', type_='foreignkey')
    op.create_foreign_key(None, 'recent_views', 'artifact_groups', ['artifact_group_id'], ['id'], ondelete='CASCADE')
    op.create_foreign_key(None, 'recent_views', 'users', ['user_id'], ['id'], ondelete='CASCADE')
    op.drop_constraint('sessions_user_id_fkey', 'sessions', type_='foreignkey')
    op.create_foreign_key(None, 'sessions', 'users', ['user_id'], ['id'], ondelete='CASCADE')
    op.drop_constraint('stats_views_artifact_group_id_fkey', 'stats_views', type_='foreignkey')
    op.drop_constraint('stats_views_user_id_fkey', 'stats_views', type_='foreignkey')
    op.create_foreign_key(None, 'stats_views', 'artifact_groups', ['artifact_group_id'], ['id'], ondelete='CASCADE')
    op.create_foreign_key(None, 'stats_views', 'users', ['user_id'], ['id'], ondelete='CASCADE')
    op.drop_constraint('user_affiliations_org_id_fkey', 'user_affiliations', type_='foreignkey')
    op.drop_constraint('user_affiliations_user_id_fkey', 'user_affiliations', type_='foreignkey')
    op.create_foreign_key(None, 'user_affiliations', 'users', ['user_id'], ['id'], ondelete='CASCADE')
    op.create_foreign_key(None, 'user_affiliations', 'organizations', ['org_id'], ['id'], ondelete='CASCADE')
    op.drop_constraint('user_authorizations_user_id_fkey', 'user_authorizations', type_='foreignkey')
    op.create_foreign_key(None, 'user_authorizations', 'users', ['user_id'], ['id'], ondelete='CASCADE')
    op.drop_constraint('users_person_id_fkey', 'users', type_='foreignkey')
    op.create_foreign_key(None, 'users', 'persons', ['person_id'], ['id'], ondelete='CASCADE')
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint(None, 'users', type_='foreignkey')
    op.create_foreign_key('users_person_id_fkey', 'users', 'persons', ['person_id'], ['id'])
    op.drop_constraint(None, 'user_authorizations', type_='foreignkey')
    op.create_foreign_key('user_authorizations_user_id_fkey', 'user_authorizations', 'users', ['user_id'], ['id'])
    op.drop_constraint(None, 'user_affiliations', type_='foreignkey')
    op.drop_constraint(None, 'user_affiliations', type_='foreignkey')
    op.create_foreign_key('user_affiliations_user_id_fkey', 'user_affiliations', 'users', ['user_id'], ['id'])
    op.create_foreign_key('user_affiliations_org_id_fkey', 'user_affiliations', 'organizations', ['org_id'], ['id'])
    op.drop_constraint(None, 'stats_views', type_='foreignkey')
    op.drop_constraint(None, 'stats_views', type_='foreignkey')
    op.create_foreign_key('stats_views_user_id_fkey', 'stats_views', 'users', ['user_id'], ['id'])
    op.create_foreign_key('stats_views_artifact_group_id_fkey', 'stats_views', 'artifact_groups', ['artifact_group_id'], ['id'])
    op.drop_constraint(None, 'sessions', type_='foreignkey')
    op.create_foreign_key('sessions_user_id_fkey', 'sessions', 'users', ['user_id'], ['id'])
    op.drop_constraint(None, 'recent_views', type_='foreignkey')
    op.drop_constraint(None, 'recent_views', type_='foreignkey')
    op.create_foreign_key('recent_views_user_id_fkey', 'recent_views', 'users', ['user_id'], ['id'])
    op.create_foreign_key('recent_views_artifact_group_id_fkey', 'recent_views', 'artifact_groups', ['artifact_group_id'], ['id'])
    op.create_index('person_idx', 'persons', ['person_tsv'], unique=False)
    op.drop_constraint(None, 'person_metadata', type_='foreignkey')
    op.create_foreign_key('person_metadata_person_id_fkey', 'person_metadata', 'persons', ['person_id'], ['id'])
    op.create_index('org_idx', 'organizations', ['org_tsv'], unique=False)
    op.drop_constraint(None, 'labels', type_='foreignkey')
    op.create_foreign_key('link_to_artifact', 'labels', 'artifacts', ['artifact_id'], ['id'])
    op.alter_column('labels', 'artifact_id',
               existing_type=sa.INTEGER(),
               nullable=False)
    op.drop_constraint(None, 'importer_schedules', type_='foreignkey')
    op.drop_constraint(None, 'importer_schedules', type_='foreignkey')
    op.create_foreign_key('importer_schedules_importer_instance_id_fkey', 'importer_schedules', 'importer_instances', ['importer_instance_id'], ['id'])
    op.create_foreign_key('importer_schedules_artifact_import_id_fkey', 'importer_schedules', 'artifact_imports', ['artifact_import_id'], ['id'])
    op.drop_constraint(None, 'dua', type_='unique')
    op.drop_constraint(None, 'artifacts', type_='foreignkey')
    op.drop_constraint(None, 'artifacts', type_='foreignkey')
    op.drop_constraint(None, 'artifacts', type_='foreignkey')
    op.drop_constraint(None, 'artifacts', type_='foreignkey')
    op.drop_constraint(None, 'artifacts', type_='foreignkey')
    op.drop_constraint(None, 'artifacts', type_='foreignkey')
    op.create_foreign_key('artifacts_parent_id_fkey', 'artifacts', 'artifacts', ['parent_id'], ['id'])
    op.create_foreign_key('artifacts_owner_id_fkey', 'artifacts', 'users', ['owner_id'], ['id'])
    op.create_foreign_key('artifacts_license_id_fkey', 'artifacts', 'licenses', ['license_id'], ['id'])
    op.create_foreign_key('artifacts_importer_id_fkey', 'artifacts', 'importers', ['importer_id'], ['id'])
    op.create_foreign_key('artifacts_exporter_id_fkey', 'artifacts', 'exporters', ['exporter_id'], ['id'])
    op.create_foreign_key('artifacts_artifact_group_id_fkey', 'artifacts', 'artifact_groups', ['artifact_group_id'], ['id'])
    op.alter_column('artifacts', 'type',
               existing_type=postgresql.ENUM('publication', 'presentation', 'dag', 'argus', 'pcap', 'netflow', 'flowtools', 'flowride', 'fsdb', 'csv', 'custom', 'dataset', name='artifact_enum'),
               nullable=False,
               existing_server_default=sa.text("'custom'::artifact_enum"))
    op.alter_column('artifacts', 'irb',
               existing_type=sa.BOOLEAN(),
               nullable=True,
               existing_server_default=sa.text('false'))
    op.alter_column('artifacts', 'anonymization',
               existing_type=postgresql.ENUM('cryptopan-full', 'cryptopan-host', 'remove-host', 'none', 'custom', name='anon_type'),
               nullable=False,
               existing_server_default=sa.text("'none'::anon_type"))
    op.drop_constraint(None, 'artifact_tags', type_='foreignkey')
    op.create_foreign_key('artifact_tags_artifact_id_fkey', 'artifact_tags', 'artifacts', ['artifact_id'], ['id'])
    op.drop_constraint(None, 'artifact_reviews', type_='foreignkey')
    op.drop_constraint(None, 'artifact_reviews', type_='foreignkey')
    op.drop_constraint(None, 'artifact_reviews', type_='foreignkey')
    op.create_foreign_key('artifact_reviews_user_id_fkey', 'artifact_reviews', 'users', ['user_id'], ['id'])
    op.create_foreign_key('artifact_reviews_artifact_id_fkey', 'artifact_reviews', 'artifacts', ['artifact_id'], ['id'])
    op.create_foreign_key('artifact_reviews_artifact_group_id_fkey1', 'artifact_reviews', 'artifact_groups', ['artifact_group_id'], ['id'])
    op.drop_constraint(None, 'artifact_requests', type_='foreignkey')
    op.drop_constraint(None, 'artifact_requests', type_='foreignkey')
    op.create_foreign_key('artifact_requests_requester_user_id_fkey', 'artifact_requests', 'users', ['requester_user_id'], ['id'])
    op.create_foreign_key('artifact_requests_artifact_group_id_fkey', 'artifact_requests', 'artifact_groups', ['artifact_group_id'], ['id'])
    op.create_unique_constraint('artifact_requests_artifact_group_id_requester_user_id_key', 'artifact_requests', ['artifact_group_id', 'requester_user_id'])
    op.alter_column('artifact_requests', 'researchers',
               existing_type=sa.TEXT(),
               nullable=True)
    op.alter_column('artifact_requests', 'representative_researcher_email',
               existing_type=sa.TEXT(),
               nullable=True)
    op.alter_column('artifact_requests', 'project_description',
               existing_type=sa.TEXT(),
               nullable=True)
    op.alter_column('artifact_requests', 'project',
               existing_type=sa.TEXT(),
               nullable=True)
    op.drop_constraint(None, 'artifact_releases', type_='foreignkey')
    op.create_foreign_key('artifact_releases_artifact_id_fkey', 'artifact_releases', 'artifacts', ['artifact_id'], ['id'])
    op.drop_constraint(None, 'artifact_relationships', type_='foreignkey')
    op.drop_constraint(None, 'artifact_relationships', type_='foreignkey')
    op.drop_constraint(None, 'artifact_relationships', type_='foreignkey')
    op.drop_constraint(None, 'artifact_relationships', type_='foreignkey')
    op.create_foreign_key('artifact_relationships_related_artifact_id_fkey', 'artifact_relationships', 'artifacts', ['related_artifact_id'], ['id'])
    op.create_foreign_key('artifact_relationships_related_artifact_group_id_fkey', 'artifact_relationships', 'artifact_groups', ['related_artifact_group_id'], ['id'])
    op.create_foreign_key('artifact_relationships_artifact_id_fkey', 'artifact_relationships', 'artifacts', ['artifact_id'], ['id'])
    op.create_foreign_key('artifact_relationships_artifact_group_id_fkey', 'artifact_relationships', 'artifact_groups', ['artifact_group_id'], ['id'])
    op.drop_constraint(None, 'artifact_ratings', type_='foreignkey')
    op.drop_constraint(None, 'artifact_ratings', type_='foreignkey')
    op.drop_constraint(None, 'artifact_ratings', type_='foreignkey')
    op.create_foreign_key('artifact_ratings_user_id_fkey', 'artifact_ratings', 'users', ['user_id'], ['id'])
    op.create_foreign_key('artifact_ratings_artifact_id_fkey', 'artifact_ratings', 'artifacts', ['artifact_id'], ['id'])
    op.create_foreign_key('artifact_ratings_artifact_group_id_fkey', 'artifact_ratings', 'artifact_groups', ['artifact_group_id'], ['id'])
    op.drop_constraint(None, 'artifact_publications', type_='foreignkey')
    op.create_foreign_key('artifact_publications_publisher_id_fkey', 'artifact_publications', 'users', ['publisher_id'], ['id'])
    op.drop_constraint(None, 'artifact_owner_request', type_='foreignkey')
    op.drop_constraint(None, 'artifact_owner_request', type_='foreignkey')
    op.drop_constraint(None, 'artifact_owner_request', type_='foreignkey')
    op.create_foreign_key('artifact_owner_request_user_id_fkey', 'artifact_owner_request', 'users', ['user_id'], ['id'])
    op.create_foreign_key('artifact_owner_request_artifact_group_id_fkey', 'artifact_owner_request', 'artifact_groups', ['artifact_group_id'], ['id'])
    op.create_foreign_key('artifact_owner_request_action_by_user_id_fkey', 'artifact_owner_request', 'users', ['action_by_user_id'], ['id'])
    op.drop_constraint(None, 'artifact_metadata', type_='foreignkey')
    op.create_foreign_key('artifact_metadata_artifact_id_fkey', 'artifact_metadata', 'artifacts', ['artifact_id'], ['id'])
    op.drop_constraint(None, 'artifact_imports', type_='foreignkey')
    op.drop_constraint(None, 'artifact_imports', type_='foreignkey')
    op.drop_constraint(None, 'artifact_imports', type_='foreignkey')
    op.drop_constraint(None, 'artifact_imports', type_='foreignkey')
    op.create_foreign_key('artifact_imports_parent_artifact_id_fkey', 'artifact_imports', 'artifacts', ['parent_artifact_id'], ['id'])
    op.create_foreign_key('artifact_imports_owner_id_fkey', 'artifact_imports', 'users', ['owner_id'], ['id'])
    op.create_foreign_key('artifact_imports_artifact_id_fkey', 'artifact_imports', 'artifacts', ['artifact_id'], ['id'])
    op.create_foreign_key('artifact_imports_artifact_group_id_fkey', 'artifact_imports', 'artifact_groups', ['artifact_group_id'], ['id'])
    op.drop_constraint(None, 'artifact_groups', type_='foreignkey')
    op.drop_constraint(None, 'artifact_groups', type_='foreignkey')
    op.create_foreign_key('artifact_groups_owner_id_fkey', 'artifact_groups', 'users', ['owner_id'], ['id'])
    op.create_unique_constraint('artifact_groups_id_next_version_key', 'artifact_groups', ['id', 'next_version'])
    op.drop_constraint(None, 'artifact_funding', type_='foreignkey')
    op.drop_constraint(None, 'artifact_funding', type_='foreignkey')
    op.create_foreign_key('artifact_funding_funding_org_id_fkey', 'artifact_funding', 'organizations', ['funding_org_id'], ['id'])
    op.create_foreign_key('artifact_funding_artifact_id_fkey', 'artifact_funding', 'artifacts', ['artifact_id'], ['id'])
    op.drop_constraint(None, 'artifact_files', type_='foreignkey')
    op.drop_constraint(None, 'artifact_files', type_='foreignkey')
    op.create_foreign_key('artifact_files_file_content_id_fkey', 'artifact_files', 'file_content', ['file_content_id'], ['id'])
    op.create_foreign_key('artifact_files_artifact_id_fkey', 'artifact_files', 'artifacts', ['artifact_id'], ['id'])
    op.drop_constraint(None, 'artifact_file_members', type_='foreignkey')
    op.drop_constraint(None, 'artifact_file_members', type_='foreignkey')
    op.create_foreign_key('artifact_file_members_parent_file_id_fkey', 'artifact_file_members', 'artifact_files', ['parent_file_id'], ['id'])
    op.create_foreign_key('artifact_file_members_file_content_id_fkey', 'artifact_file_members', 'file_content', ['file_content_id'], ['id'])
    op.drop_constraint(None, 'artifact_favorites', type_='foreignkey')
    op.drop_constraint(None, 'artifact_favorites', type_='foreignkey')
    op.drop_constraint(None, 'artifact_favorites', type_='foreignkey')
    op.create_foreign_key('artifact_favorites_user_id_fkey', 'artifact_favorites', 'users', ['user_id'], ['id'])
    op.create_foreign_key('artifact_favorites_artifact_id_fkey', 'artifact_favorites', 'artifacts', ['artifact_id'], ['id'])
    op.create_foreign_key('artifact_favorites_artifact_group_id_fkey', 'artifact_favorites', 'artifact_groups', ['artifact_group_id'], ['id'])
    op.drop_constraint(None, 'artifact_curations', type_='foreignkey')
    op.drop_constraint(None, 'artifact_curations', type_='foreignkey')
    op.create_foreign_key('artifact_curations_curator_id_fkey', 'artifact_curations', 'users', ['curator_id'], ['id'])
    op.create_foreign_key('artifact_curations_artifact_id_fkey', 'artifact_curations', 'artifacts', ['artifact_id'], ['id'])
    op.drop_constraint(None, 'artifact_badges', type_='foreignkey')
    op.drop_constraint(None, 'artifact_badges', type_='foreignkey')
    op.create_foreign_key('artifact_badges_badge_id_fkey', 'artifact_badges', 'badges', ['badge_id'], ['id'])
    op.create_foreign_key('artifact_badges_artifact_id_fkey', 'artifact_badges', 'artifacts', ['artifact_id'], ['id'])
    op.drop_constraint(None, 'artifact_affiliations', type_='foreignkey')
    op.drop_constraint(None, 'artifact_affiliations', type_='foreignkey')
    op.create_foreign_key('artifact_affiliations_artifact_id_fkey', 'artifact_affiliations', 'artifacts', ['artifact_id'], ['id'])
    op.create_foreign_key('artifact_affiliations_affiliation_id_fkey', 'artifact_affiliations', 'affiliations', ['affiliation_id'], ['id'])
    op.drop_constraint(None, 'affiliations', type_='foreignkey')
    op.drop_constraint(None, 'affiliations', type_='foreignkey')
    op.create_foreign_key('affiliations_person_id_fkey', 'affiliations', 'persons', ['person_id'], ['id'])
    op.create_foreign_key('affiliations_org_id_fkey', 'affiliations', 'organizations', ['org_id'], ['id'])
    # op.create_table('alembic_lock',
    # sa.Column('locked', sa.BOOLEAN(), autoincrement=False, nullable=True)
    # )
    # op.drop_table('artifact_search_view')
    # ### end Alembic commands ###