"""venue

Revision ID: e030638b4df0
Revises: 43d79542de81
Create Date: 2022-12-14 21:40:22.488401

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'e030638b4df0'
down_revision = '43d79542de81'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('recurring_venues',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('type', sa.Enum('conference', 'journal', 'magazine', 'newspaper', 'periodical', 'event', 'other', name='recurring_venue_enum'), nullable=False),
    sa.Column('title', sa.String(length=1024), nullable=False),
    sa.Column('abbrev', sa.String(length=64), nullable=True),
    sa.Column('url', sa.String(length=1024), nullable=False),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('publisher_url', sa.String(length=1024), nullable=True),
    sa.Column('verified', sa.Boolean(), nullable=False),
    sa.Column('recurring_venue_tsv', postgresql.TSVECTOR(), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )

    op.execute(
        "CREATE OR REPLACE FUNCTION public.recurring_venues_tsvector_update_trigger() RETURNS trigger"
        " LANGUAGE plpgsql"
        " AS $$"
        " BEGIN"
        "   new.recurring_venue_tsv := to_tsvector('english', coalesce(new.title, '') || ' ' || coalesce(new.abbrev, ''));"
        "   return new;"
        " END"
        " $$;")
    op.execute(
        "CREATE TRIGGER tsvector_update BEFORE INSERT OR UPDATE"
        " ON public.recurring_venues FOR EACH ROW EXECUTE PROCEDURE"
        "  public.recurring_venues_tsvector_update_trigger();")

    op.create_index('recurring_venue_idx', 'recurring_venues', [sa.text("recurring_venue_tsv")], postgresql_using='gin')

    op.create_table('venues',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('type', sa.Enum('conference', 'journal', 'magazine', 'newspaper', 'periodical', 'event', 'other', name='venue_enum'), nullable=False),
    sa.Column('title', sa.String(length=1024), nullable=False),
    sa.Column('abbrev', sa.String(length=64), nullable=True),
    sa.Column('url', sa.String(length=1024), nullable=False),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('location', sa.String(length=1024), nullable=True),
    sa.Column('year', sa.Integer(), nullable=True),
    sa.Column('month', sa.Integer(), nullable=True),
    sa.Column('start_day', sa.Integer(), nullable=True),
    sa.Column('end_day', sa.Integer(), nullable=True),
    sa.Column('publisher', sa.String(length=1024), nullable=True),
    sa.Column('publisher_location', sa.String(length=1024), nullable=True),
    sa.Column('publisher_url', sa.String(length=1024), nullable=True),
    sa.Column('isbn', sa.String(length=128), nullable=True),
    sa.Column('issn', sa.String(length=128), nullable=True),
    sa.Column('doi', sa.String(length=128), nullable=True),
    sa.Column('volume', sa.Integer(), nullable=True),
    sa.Column('issue', sa.Integer(), nullable=True),
    sa.Column('verified', sa.Boolean(), nullable=False),
    sa.Column('recurring_venue_id', sa.Integer(), nullable=True),
    sa.Column('venue_tsv', postgresql.TSVECTOR(), nullable=True),
    sa.ForeignKeyConstraint(['recurring_venue_id'], ['recurring_venues.id'], ),
    sa.PrimaryKeyConstraint('id')
    )

    op.execute(
        "CREATE OR REPLACE FUNCTION public.venues_tsvector_update_trigger() RETURNS trigger"
        " LANGUAGE plpgsql"
        " AS $$"
        " BEGIN"
        "   new.venue_tsv := to_tsvector('english', coalesce(new.title, '') || ' ' || coalesce(new.abbrev, ''));"
        "   return new;"
        " END"
        " $$;")
    op.execute(
        "CREATE TRIGGER tsvector_update BEFORE INSERT OR UPDATE"
        " ON public.venues FOR EACH ROW EXECUTE PROCEDURE"
        "  public.venues_tsvector_update_trigger();")

    op.create_index('venue_idx', 'venues', [sa.text("venue_tsv")], postgresql_using='gin')

    op.create_table('artifact_venues',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('artifact_id', sa.Integer(), nullable=False),
    sa.Column('venue_id', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['artifact_id'], ['artifacts.id'], ),
    sa.ForeignKeyConstraint(['venue_id'], ['venues.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('artifact_id', 'venue_id')
    )


def downgrade():
    op.drop_index('recurring_venue_idx')
    op.execute("DROP TRIGGER IF EXISTS tsvector_update on recurring_venues;")
    op.execute("DROP FUNCTION IF EXISTS public.recurring_venues_tsvector_update_trigger;")
    op.drop_column('recurring_venues', 'recurring_venue_tsv')
    op.drop_index('venue_idx')
    op.execute("DROP TRIGGER IF EXISTS tsvector_update on venues;")
    op.execute("DROP FUNCTION IF EXISTS public.venues_tsvector_update_trigger;")
    op.drop_column('venues', 'venue_tsv')
    op.drop_table('artifact_venues')
    op.drop_table('venues')
    op.drop_table('recurring_venues')
