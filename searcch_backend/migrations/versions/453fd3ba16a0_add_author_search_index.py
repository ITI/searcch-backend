"""add author search index

Revision ID: 453fd3ba16a0
Revises: c312ec44b050
Create Date: 2021-04-09 18:00:18.840680

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '453fd3ba16a0'
down_revision = 'c312ec44b050'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('persons', sa.Column('person_tsv', postgresql.TSVECTOR(), nullable=True))
    
    # instantiate the person_tsv vector with existing data
    op.execute(
        "UPDATE persons "
        "SET person_tsv = to_tsvector('english', coalesce(name, '') || ' ' || coalesce(email, ''));")

    op.execute(
        "CREATE OR REPLACE FUNCTION public.persons_tsvector_update_trigger() RETURNS trigger"
        " LANGUAGE plpgsql"
        " AS $$"
        " BEGIN"
        "   new.person_tsv := to_tsvector('english', coalesce(new.name, '') || ' ' || coalesce(new.email, ''));"
        "   return new;"
        " END"
        " $$;")
    op.execute(
        "CREATE TRIGGER tsvector_update BEFORE INSERT OR UPDATE"
        " ON public.persons FOR EACH ROW EXECUTE PROCEDURE"
        "  public.persons_tsvector_update_trigger();")

    op.create_index('person_idx', 'persons', [sa.text("person_tsv")], postgresql_using='gin')

def downgrade():
    op.drop_index('person_idx')
    op.execute("DROP TRIGGER IF EXISTS tsvector_update on persons;")
    op.execute("DROP FUNCTION IF EXISTS public.persons_tsvector_update_trigger;")
    op.drop_column('persons', 'person_tsv')
