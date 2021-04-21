"""new search index as materialized view

Revision ID: c43eb4aa4eab
Revises: 0ec6f66e9e5f
Create Date: 2021-03-31 17:46:05.791358

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'c43eb4aa4eab'
down_revision = '0ec6f66e9e5f'
branch_labels = None
depends_on = None


def upgrade():
    # add new setup for search index
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
        " ) AT on AM.artifact_id = AT.artifact_id;"
    )

    op.execute(
        "create or replace function refresh_mat_view()"
        " returns trigger language plpgsql"
        " as $$"
        " begin"
        "     refresh materialized view artifact_search_view;"
        "     return null;"
        " end $$;"
    )
    op.execute(
        "create trigger refresh_mat_view"
        " after insert or update or delete or truncate"
        " on artifacts for each statement "
        " execute procedure refresh_mat_view();"
    )
    op.execute(
        "create trigger refresh_mat_view"
        " after insert or update or delete or truncate"
        " on artifact_metadata for each statement "
        " execute procedure refresh_mat_view();"
    )
    op.execute(
        "create trigger refresh_mat_view"
        " after insert or update or delete or truncate"
        " on artifact_tags for each statement "
        " execute procedure refresh_mat_view();"
    )
    op.create_index('doc_idx', 'artifact_search_view', [sa.text("doc_vector")], postgresql_using='gin')
    
    # remove existing search index setup
    op.drop_index('document_idx')
    op.execute("DROP TRIGGER IF EXISTS tsvector_update on artifacts;")
    op.execute("DROP FUNCTION IF EXISTS public.artifacts_tsvector_update_trigger;")
    op.drop_column('artifacts', 'document_with_idx')

def downgrade():
    op.drop_index('doc_idx')
    op.execute("DROP TRIGGER IF EXISTS refresh_mat_view on artifacts;")
    op.execute("DROP TRIGGER IF EXISTS refresh_mat_view on artifact_metadata;")
    op.execute("DROP TRIGGER IF EXISTS refresh_mat_view on artifact_tags;")
    op.execute("DROP FUNCTION IF EXISTS public.refresh_mat_view;")
    op.execute('DROP MATERIALIZED VIEW IF EXISTS artifact_search_view;')

    op.add_column('artifacts', sa.Column('document_with_idx', postgresql.TSVECTOR(), nullable=True))
    op.execute(
        "CREATE FUNCTION public.artifacts_tsvector_update_trigger() RETURNS trigger"
        " LANGUAGE plpgsql"
        " AS $$"
        " begin"
        "   new.document_with_idx := to_tsvector('english', coalesce(new.title, '') || ' ' || coalesce(new.description, ''));"
        "   return new;"
        " end"
        " $$;"
    )
    op.execute(
        "CREATE TRIGGER tsvector_update BEFORE INSERT OR UPDATE"
        " ON public.artifacts FOR EACH ROW EXECUTE PROCEDURE"
        " public.artifacts_tsvector_update_trigger();"
    )
    op.create_index('document_idx', 'artifacts', [sa.text("document_with_idx")], postgresql_using='gin')
