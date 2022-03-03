"""artifact-relations-rev2

Revision ID: 3b98c44ef5b2
Revises: 934242545eda
Create Date: 2021-08-13 02:14:22.950936

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '3b98c44ef5b2'
down_revision = '934242545eda'
branch_labels = None
depends_on = None


def upgrade():
    #
    # These ENUM add value statements cannot be run in the same transaction
    # where we begin to use them.  So, since the following transaction could
    # fail (although shouldn't), accept if the values already exist.
    #
    for new_value in ('extends', 'uses', 'describes', 'requires', 'processes', 'produces'):
        try:
            with op.get_context().autocommit_block():
                op.execute(
                    "alter type artifact_relationship_enum add value '%s'" % (new_value,))
        except:
            pass
    # And back to transactional mode.
    op.execute(
        "update artifact_relationships set relation='extends' where relation='continues'")
    op.execute(
        "update artifact_relationships set relation='cites' where relation='references'")
    op.execute(
        "update artifact_relationships set relation='describes' where relation='documents'")
    op.execute(
        "update artifact_relationships set relation='produces' where relation='compiles'")
    op.execute(
        "update artifact_relationships set relation='describes' where relation='publishes'")
    op.execute(
        "alter type artifact_relationship_enum rename to artifact_relationship_enum_old")
    op.execute(
        "create type artifact_relationship_enum as enum("
        " 'cites', 'supplements', 'extends', 'uses', 'describes',"
        " 'requires', 'processes', 'produces')")
    op.execute(
        "alter table artifact_relationships"
        " alter column relation type artifact_relationship_enum"
        "  using relation::text::artifact_relationship_enum")
    op.execute("drop type artifact_relationship_enum_old")


def downgrade():
    for new_value in ('continues', 'references', 'documents', 'compiles','publishes'):
        with op.get_context().autocommit_block():
            op.execute(
                "alter type artifact_relationship_enum add value '%s'" % (new_value,))
    # And back to transactional mode.
    # XXX: note that there is no going back from several of the new types!
    op.execute(
        "update artifact_relationships set relation='continues' where relation='extends'")
    op.execute(
        "update artifact_relationships set relation='compiles' where relation='produces'")
    op.execute(
        "update artifact_relationships set relation='publishes' where relation='describes'")
    op.execute(
        "alter type artifact_relationship_enum rename to artifact_relationship_enum_old")
    op.execute(
        "create type artifact_relationship_enum as enum("
        " 'cites', 'supplements', 'continues', 'references', 'documents',"
        " 'compiles','publishes')")
    op.execute(
        "alter table artifact_relationships"
        " alter column relation type artifact_relationship_enum"
        "  using relation::text::artifact_relationship_enum")
    op.execute("drop type artifact_relationship_enum_old")
