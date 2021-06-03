"""add org search index

Revision ID: 5719ad4da4b4
Revises: 453fd3ba16a0
Create Date: 2021-04-09 19:09:29.737553

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '5719ad4da4b4'
down_revision = '453fd3ba16a0'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('organizations', sa.Column('org_tsv', postgresql.TSVECTOR(), nullable=True))
    
    # instantiate the org_tsv vector with existing data
    op.execute(
        "UPDATE organizations "
        "SET org_tsv = to_tsvector('english', coalesce(name, '') || ' ' || coalesce(state, '') || ' ' || coalesce(country, '') || ' ' || coalesce(address, ''));")

    op.execute(
        "CREATE OR REPLACE FUNCTION public.organization_tsvector_update_trigger() RETURNS trigger"
        " LANGUAGE plpgsql"
        " AS $$"
        " BEGIN"
        "   new.org_tsv := to_tsvector('english', coalesce(new.name, '') || ' ' || coalesce(new.state, '') || ' ' || coalesce(new.country, '') || ' ' || coalesce(new.address, ''));"
        "   return new;"
        " END"
        " $$;")
    op.execute(
        "CREATE TRIGGER tsvector_update BEFORE INSERT OR UPDATE"
        " ON public.organizations FOR EACH ROW EXECUTE PROCEDURE"
        "  public.organization_tsvector_update_trigger();")

    op.create_index('org_idx', 'organizations', [sa.text("org_tsv")], postgresql_using='gin')

def downgrade():
    op.drop_index('org_idx')
    op.execute("DROP TRIGGER IF EXISTS tsvector_update on public.organizations;")
    op.execute("DROP FUNCTION IF EXISTS public.organization_tsvector_update_trigger;")
    op.drop_column('organizations', 'org_tsv')