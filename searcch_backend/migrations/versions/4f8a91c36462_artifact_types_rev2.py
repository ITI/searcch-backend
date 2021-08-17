"""artifact-types-rev2

Revision ID: 4f8a91c36462
Revises: 8ba2e789d21c
Create Date: 2021-08-13 02:14:22.950936

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '4f8a91c36462'
down_revision = '8ba2e789d21c'
branch_labels = None
depends_on = None


def upgrade():
    #
    # These ENUM add value statements cannot be run in the same transaction
    # where we begin to use them.  So, since the following transaction could
    # fail (although shouldn't), accept if the values already exist.
    #
    for new_value in ('software','other'):
        try:
            with op.get_context().autocommit_block():
                op.execute(
                    "alter type artifact_enum add value '%s'" % (new_value,))
        except:
            pass
    # And back to transactional mode.
    op.execute(
        "update artifacts set type='software'"
        " where type in ('code','executable')")
    op.execute(
        "update artifacts set type='other'"
        " where type in ('methodology', 'metrics', 'priorwork', 'hypothesis',"
        "                'domain', 'supportinginfo')")
    op.execute(
        "alter type artifact_enum rename to artifact_enum_old")
    op.execute(
        "create type artifact_enum as enum("
        " 'publication', 'presentation', 'dataset', 'software', 'other')")
    op.execute("alter table artifacts alter column type type artifact_enum using type::text::artifact_enum")
    op.execute("drop type artifact_enum_old")

    for new_value in ('software','other'):
        try:
            with op.get_context().autocommit_block():
                op.execute(
                    "alter type artifact_imports_type_enum add value '%s'" % (new_value,))
        except:
            pass
    op.execute(
        "update artifact_imports set type='software'"
        " where type in ('code','executable')")
    op.execute(
        "update artifact_imports set type='other'"
        " where type in ('methodology', 'metrics', 'priorwork', 'hypothesis',"
        "                'domain', 'supportinginfo')")
    op.execute(
        "alter type artifact_imports_type_enum rename to artifact_imports_type_enum_old")
    op.execute(
        "create type artifact_imports_type_enum as enum("
        " 'publication', 'presentation', 'dataset', 'software', 'other', 'unknown')")
    op.execute("alter table artifact_imports alter column type type artifact_imports_type_enum using type::text::artifact_imports_type_enum")
    op.execute("drop type artifact_imports_type_enum_old")

def downgrade():
    with op.get_context().autocommit_block():
        op.execute(
            "alter type artifact_enum add value 'code'")
    op.execute(
        "update artifacts set type='code'"
        " where type='software'")
    op.execute(
        "alter type artifact_enum rename to artifact_enum_old")
    # XXX: note that there is no going back from 'other'!
    op.execute(
        "create type artifact_enum as enum("
        " 'dataset', 'executable', 'methodology', 'metrics',"
        " 'priorwork', 'publication', 'hypothesis', 'code', 'domain',"
        " 'supportinginfo', 'other')")
    op.execute("alter table artifacts alter column type type artifact_enum using type::text::artifact_enum")
    op.execute("drop type artifact_enum_old")

    with op.get_context().autocommit_block():
        op.execute(
            "alter type artifact_imports_type_enum add value 'code'")
    op.execute(
        "update artifact_imports set type='code'"
        " where type='software'")
    op.execute(
        "alter type artifact_imports_type_enum rename to artifact_imports_type_enum_old")
    # XXX: note that there is no going back from 'other'!
    op.execute(
        "create type artifact_imports_type_enum as enum("
        " 'dataset', 'executable', 'methodology', 'metrics',"
        " 'priorwork', 'publication', 'hypothesis', 'code', 'domain',"
        " 'supportinginfo', 'other')")
    op.execute("alter table artifact_imports alter column type type artifact_imports_type_enum using type::text::artifact_imports_type_enum")
    op.execute("drop type artifact_imports_type_enum_old")
