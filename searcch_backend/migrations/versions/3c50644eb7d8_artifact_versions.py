"""artifact_versions

Revision ID: 3c50644eb7d8
Revises: 3b98c44ef5b2
Create Date: 2022-03-07 04:18:48.975818

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '3c50644eb7d8'
down_revision = '3b98c44ef5b2'
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()

    op.create_table('file_content',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('content', sa.LargeBinary(), nullable=False),
        sa.Column('hash', sa.LargeBinary(), nullable=False),
        sa.Column('size', sa.BigInteger(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_unique_constraint(None, 'file_content', ['hash'])

    op.add_column('artifact_files', sa.Column('file_content_id', sa.Integer(), nullable=True))
    op.create_foreign_key(None, 'artifact_files', 'file_content', ['file_content_id'], ['id'])
    #conn.execute("insert into file_content (content,hash,size) select af1.content,sha256(af1.content),af1.size from artifact_files as af1 where af1.content is not NULL and sha256(af1.content) not in (select hash from file_content where hash=sha256(af1.content))")
    #conn.execute("update artifact_files set file_content_id=fc1.id from (select id,hash from file_content) fc1 where content is not NULL and fc1.hash=sha256(content)")
    conn.execute("insert into file_content (content,hash,size) select af.content,sha256(af.content),af.size from artifact_files as af where af.content is not NULL on conflict do nothing")
    conn.execute("update artifact_files set file_content_id=fc1.id from (select id,hash from file_content) fc1 where content is not NULL and fc1.hash=sha256(content)")
    op.drop_column('artifact_files', 'content')

    op.add_column('artifact_file_members', sa.Column('file_content_id', sa.Integer(), nullable=True))
    op.create_foreign_key(None, 'artifact_file_members', 'file_content', ['file_content_id'], ['id'])
    #conn.execute("insert into file_content (content,hash,size) select afm1.content,sha256(afm1.content),afm1.size from artifact_file_members as afm1 where afm1.content is not NULL and not exists(select id from file_content where hash=sha256(afm1.content))")
    conn.execute("insert into file_content (content,hash,size) select afm1.content,sha256(afm1.content),afm1.size from artifact_file_members as afm1 where afm1.content is not NULL on conflict do nothing")
    conn.execute("update artifact_file_members set file_content_id=fc1.id from (select id,hash from file_content) fc1 where content is not NULL and fc1.hash=sha256(content)")
    op.drop_column('artifact_file_members', 'content')

    op.create_table('artifact_groups',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('owner_id', sa.Integer(), nullable=False),
        sa.Column('publication_id', sa.Integer()),
        sa.Column('next_version', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['owner_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['publication_id'], ['artifact_publications.id'], ),
        sa.UniqueConstraint('id', 'next_version'),
        sa.PrimaryKeyConstraint('id')
    )
    conn.execute("insert into artifact_groups (id, owner_id, publication_id, next_version) select a.id, a.owner_id, ap.id, 1 from artifacts as a left join artifact_publications as ap on a.id=ap.artifact_id")
    conn.execute("select setval('artifact_groups_id_seq', (select max(id) from artifact_groups), TRUE)")

    op.add_column('artifact_publications', sa.Column('version', sa.Integer(), nullable=True))
    op.execute("update artifact_publications set version=0")
    op.alter_column('artifact_publications', 'version', existing_type=sa.INTEGER(), nullable=False)

    op.drop_column('artifacts', 'version')
    op.add_column('artifacts', sa.Column('artifact_group_id', sa.Integer(), nullable=True))
    op.create_foreign_key(None, 'artifacts', 'artifact_groups', ['artifact_group_id'], ['id'])
    conn.execute("update artifacts set artifact_group_id=id")
    op.alter_column('artifacts', 'artifact_group_id',  existing_type=sa.INTEGER(), nullable=False)

    op.add_column('artifact_favorites', sa.Column('artifact_group_id', sa.Integer(), nullable=True))
    conn.execute("update artifact_favorites set artifact_group_id=artifact_id")
    op.alter_column('artifact_favorites', 'artifact_group_id',  existing_type=sa.INTEGER(), nullable=False)
    op.drop_constraint('artifact_favorites_artifact_id_user_id_key', 'artifact_favorites', type_='unique')
    op.create_unique_constraint(None, 'artifact_favorites', ['artifact_group_id', 'user_id'])
    op.create_foreign_key(None, 'artifact_favorites', 'artifact_groups', ['artifact_group_id'], ['id'])
    op.alter_column('artifact_favorites', 'artifact_id',  existing_type=sa.INTEGER(), nullable=True)

    op.add_column('artifact_imports', sa.Column('artifact_group_id', sa.Integer(), nullable=True))
    op.add_column('artifact_imports', sa.Column('parent_artifact_id', sa.Integer(), nullable=True))
    conn.execute("update artifact_imports set artifact_group_id=artifact_id")
    op.drop_constraint('artifact_imports_owner_id_url_artifact_id_key', 'artifact_imports', type_='unique')
    op.create_unique_constraint(None, 'artifact_imports', ['owner_id', 'url', 'artifact_group_id', 'artifact_id'])
    op.create_foreign_key(None, 'artifact_imports', 'artifact_groups', ['artifact_group_id'], ['id'])
    op.create_foreign_key(None, 'artifact_imports', 'artifacts', ['parent_artifact_id'], ['id'])

    op.add_column('artifact_ratings', sa.Column('artifact_group_id', sa.Integer(), nullable=True))
    conn.execute("update artifact_ratings set artifact_group_id=artifact_id")
    op.alter_column('artifact_ratings', 'artifact_group_id',  existing_type=sa.INTEGER(), nullable=False)
    op.drop_constraint('artifact_ratings_artifact_id_user_id_key', 'artifact_ratings', type_='unique')
    op.create_unique_constraint(None, 'artifact_ratings', ['artifact_group_id', 'user_id'])
    op.create_foreign_key(None, 'artifact_ratings', 'artifact_groups', ['artifact_group_id'], ['id'])
    op.alter_column('artifact_ratings', 'artifact_id',  existing_type=sa.INTEGER(), nullable=True)

    op.add_column('artifact_relationships', sa.Column('artifact_group_id', sa.Integer(), nullable=True))
    op.add_column('artifact_relationships', sa.Column('related_artifact_group_id', sa.Integer(), nullable=True))
    conn.execute("update artifact_relationships set artifact_group_id=artifact_id")
    conn.execute("update artifact_relationships set related_artifact_group_id=related_artifact_id")
    op.alter_column('artifact_relationships', 'artifact_group_id',  existing_type=sa.INTEGER(), nullable=False)
    op.alter_column('artifact_relationships', 'related_artifact_group_id',  existing_type=sa.INTEGER(), nullable=False)
    op.drop_constraint('artifact_relationships_artifact_id_relation_related_artifac_key', 'artifact_relationships', type_='unique')
    op.create_unique_constraint(None, 'artifact_relationships', ['artifact_group_id', 'relation', 'related_artifact_group_id'])
    op.create_foreign_key(None, 'artifact_relationships', 'artifact_groups', ['artifact_group_id'], ['id'])
    op.create_foreign_key(None, 'artifact_relationships', 'artifact_groups', ['related_artifact_group_id'], ['id'])
    op.alter_column('artifact_relationships', 'artifact_id',  existing_type=sa.INTEGER(), nullable=True)
    op.alter_column('artifact_relationships', 'related_artifact_id',  existing_type=sa.INTEGER(), nullable=True)

    op.add_column('artifact_reviews', sa.Column('artifact_group_id', sa.Integer(), nullable=True))
    op.create_foreign_key(None, 'artifact_reviews', 'artifact_groups', ['artifact_group_id'], ['id'])
    conn.execute("update artifact_reviews set artifact_group_id=artifact_id")
    op.alter_column('artifact_reviews', 'artifact_group_id', existing_type=sa.INTEGER(), nullable=False)
    op.create_foreign_key(None, 'artifact_reviews', 'artifact_groups', ['artifact_group_id'], ['id'])
    op.alter_column('artifact_reviews', 'artifact_id',  existing_type=sa.INTEGER(), nullable=True)

    op.drop_index('doc_idx')
    op.execute('DROP MATERIALIZED VIEW artifact_search_view')
    op.execute(
        "create materialized view artifact_search_view AS "
        " select A.artifact_group_id as artifact_group_id, A.id as artifact_id, to_tsvector('english', coalesce(A.title, '') || ' ' || coalesce(A.description, '') || ' ' || coalesce(AM.metadata_str, '') || ' ' || coalesce(AT.tag_str, '')) as doc_vector"
        " from "
        " ("
        "     select artifact_group_id, id, title, description"
        "     from artifacts"
        " ) A "
        " inner join "
        " ("
        "     select id"
        "     from artifact_groups"
        "     where publication_id is not NULL"
        " ) AG on AG.id = A.artifact_group_id"
        " left join "
        " ("
        "     select artifact_id, replace(string_agg(value, ' '), ',', ' ') as metadata_str"
        "     from artifact_metadata "
        "     where name IN ('full_name', 'topics', 'languages', 'owner_login', 'owner_name')"
        "     group by artifact_id"
        " ) AM on A.id = AM.artifact_id"
        " left join "
        " ("
        "     select artifact_id, string_agg(tag, ' ') as tag_str "
        "     from artifact_tags "
        "     group by artifact_id"
        " ) AT on AM.artifact_id = AT.artifact_id;"
    )
    op.create_index('doc_idx', 'artifact_search_view', [sa.text("doc_vector")], postgresql_using='gin')
    op.execute("refresh materialized view public.artifact_search_view;")

    op.execute("DROP TRIGGER IF EXISTS refresh_mat_view on artifacts;")
    op.execute(
        "create trigger refresh_mat_view"
        " after insert or update or delete or truncate"
        " on artifact_groups for each statement "
        " execute procedure refresh_mat_view();"
    )


def downgrade():
    raise Exception("aborting data-destructive downgrade")

    conn = op.get_bind()

    op.execute("DROP TRIGGER IF EXISTS refresh_mat_view on artifact_groups;")
    op.drop_index('doc_idx')
    op.execute('DROP MATERIALIZED VIEW artifact_search_view;')

    op.add_column('artifacts', sa.Column('parent_id', sa.INTEGER(), autoincrement=False, nullable=True))
    op.add_column('artifacts', sa.Column('exporter_id', sa.INTEGER(), autoincrement=False, nullable=True))
    op.drop_constraint(None, 'artifacts', type_='foreignkey')
    op.create_foreign_key('artifacts_parent_id_fkey', 'artifacts', 'artifacts', ['parent_id'], ['id'])
    op.create_foreign_key('artifacts_exporter_id_fkey', 'artifacts', 'exporters', ['exporter_id'], ['id'])
    op.alter_column('artifacts', 'version',
               existing_type=sa.INTEGER(),
               nullable=False)
    op.drop_column('artifacts', 'artifact_group_id')
    op.drop_column('artifacts', 'parent_version')
    op.drop_constraint(None, 'artifact_reviews', type_='foreignkey')
    op.drop_column('artifact_reviews', 'artifact_group_id')
    op.add_column('artifact_relationships', sa.Column('related_artifact_id', sa.INTEGER(), autoincrement=False, nullable=True))
    op.add_column('artifact_relationships', sa.Column('artifact_id', sa.INTEGER(), autoincrement=False, nullable=True))
    op.drop_constraint(None, 'artifact_relationships', type_='foreignkey')
    op.drop_constraint(None, 'artifact_relationships', type_='foreignkey')
    op.create_foreign_key('artifact_relationships_related_artifact_id_fkey', 'artifact_relationships', 'artifacts', ['related_artifact_id'], ['id'])
    op.create_foreign_key('artifact_relationships_artifact_id_fkey', 'artifact_relationships', 'artifacts', ['artifact_id'], ['id'])
    op.drop_constraint(None, 'artifact_relationships', type_='unique')
    op.create_unique_constraint('artifact_relationships_artifact_id_relation_related_artifac_key', 'artifact_relationships', ['artifact_id', 'relation', 'related_artifact_id'])
    op.drop_column('artifact_relationships', 'artifact_group_id')
    op.drop_column('artifact_relationships', 'related_artifact_group_id')
    op.add_column('artifact_ratings', sa.Column('artifact_id', sa.INTEGER(), autoincrement=False, nullable=False))
    op.drop_constraint(None, 'artifact_ratings', type_='foreignkey')
    op.create_foreign_key('artifact_ratings_artifact_id_fkey', 'artifact_ratings', 'artifacts', ['artifact_id'], ['id'])
    op.drop_constraint(None, 'artifact_ratings', type_='unique')
    op.create_unique_constraint('artifact_ratings_artifact_id_user_id_key', 'artifact_ratings', ['artifact_id', 'user_id'])
    op.drop_column('artifact_ratings', 'artifact_group_id')
    op.drop_constraint(None, 'artifact_imports', type_='foreignkey')
    op.drop_constraint(None, 'artifact_imports', type_='unique')
    op.create_unique_constraint('artifact_imports_owner_id_url_artifact_id_key', 'artifact_imports', ['owner_id', 'url', 'artifact_id'])
    op.drop_column('artifact_imports', 'artifact_group_id')
    op.add_column('artifact_files', sa.Column('size', sa.BIGINT(), autoincrement=False, nullable=True))
    op.add_column('artifact_files', sa.Column('content', postgresql.BYTEA(), autoincrement=False, nullable=True))
    op.drop_constraint(None, 'artifact_files', type_='foreignkey')
    op.drop_column('artifact_files', 'content_id')
    op.add_column('artifact_favorites', sa.Column('artifact_id', sa.INTEGER(), autoincrement=False, nullable=False))
    op.drop_constraint(None, 'artifact_favorites', type_='foreignkey')
    op.create_foreign_key('artifact_favorites_artifact_id_fkey', 'artifact_favorites', 'artifacts', ['artifact_id'], ['id'])
    op.drop_constraint(None, 'artifact_favorites', type_='unique')
    op.create_unique_constraint('artifact_favorites_artifact_id_user_id_key', 'artifact_favorites', ['artifact_id', 'user_id'])
    op.drop_column('artifact_favorites', 'artifact_group_id')
    op.create_table('exporters',
    sa.Column('id', sa.INTEGER(), autoincrement=True, nullable=False),
    sa.Column('name', sa.VARCHAR(length=32), autoincrement=False, nullable=False),
    sa.Column('version', sa.VARCHAR(length=32), autoincrement=False, nullable=True),
    sa.PrimaryKeyConstraint('id', name='exporters_pkey'),
    sa.UniqueConstraint('name', 'version', name='exporters_name_version_key')
    )
    op.drop_table('file_content')
    op.drop_table('artifact_groups')

    op.execute(
        "create materialized view artifact_search_view AS "
        " select A.id as artifact_id, to_tsvector('english', coalesce(A.title, '') || ' ' || coalesce(A.description, '') || ' ' || coalesce(AM.metadata_str, '') || ' ' || coalesce(AT.tag_str, '')) as doc_vector"
        " from "
        " ("
        "     select id, title, description"
        "     from artifacts"
        " ) A "
        " left join "
        " ("
        "     select artifact_id, replace(string_agg(value, ' '), ',', ' ') as metadata_str"
        "     from artifact_metadata "
        "     where name IN ('full_name', 'topics', 'languages', 'owner_login', 'owner_name')"
        "     group by artifact_id"
        " ) AM on A.id = AM.artifact_id"
        " left join "
        " ("
        "     select artifact_id, string_agg(tag, ' ') as tag_str "
        "     from artifact_tags "
        "     group by artifact_id"
        " ) AT on AM.artifact_id = AT.artifact_id"
        " where AG.publication_id is not NULL;"
    )
    op.create_index('doc_idx', 'artifact_search_view', [sa.text("doc_vector")], postgresql_using='gin')
    op.execute("refresh materialized view public.artifact_search_view;")
    op.execute(
        "create trigger refresh_mat_view"
        " after insert or update or delete or truncate"
        " on artifacts for each statement "
        " execute procedure refresh_mat_view();"
    )
