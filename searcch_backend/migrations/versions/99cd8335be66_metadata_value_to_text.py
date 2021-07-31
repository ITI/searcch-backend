"""metadata-value-to-text

Revision ID: 99cd8335be66
Revises: 6458fd36a501
Create Date: 2021-07-29 16:03:33.907589

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '99cd8335be66'
down_revision = '6458fd36a501'
branch_labels = None
depends_on = None


def drop_view():
    op.drop_index('doc_idx')
    op.execute('DROP MATERIALIZED VIEW artifact_search_view;')


def create_and_refresh_view():
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
    op.create_index('doc_idx', 'artifact_search_view', [sa.text("doc_vector")], postgresql_using='gin')
    op.execute("refresh materialized view public.artifact_search_view;")


def upgrade():
    drop_view()
    op.alter_column('artifact_metadata', 'value',
        existing_type=sa.VARCHAR(length=16384),
        type_=sa.VARCHAR(length=4*1024*1024),nullable=False)
    create_and_refresh_view()


def downgrade():
    drop_view()
    op.alter_column('artifact_metadata', 'value',
        existing_type=sa.VARCHAR(length=4*1024*1024),
        type_=sa.VARCHAR(length=16384),nullable=False)
    create_and_refresh_view()
