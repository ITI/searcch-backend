"""add_dataset_to_enum

Revision ID: 052603293888
Revises: a14e700c0108
Create Date: 2022-12-20 05:46:58.316608

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '052603293888'
down_revision = 'a14e700c0108'
branch_labels = None
depends_on = None


def upgrade():
    for new_value in ("publication", "presentation", "dag", "argus", "pcap", "netflow", "flowtools", "flowride", "fsdb", "csv", "custom", "dataset"):
        try:
            with op.get_context().autocommit_block():
                op.execute(
                    "alter type artifact_enum add value '%s'" % (new_value,))
        except:
            pass
    # ### end Alembic commands ###


def downgrade():
    pass
    # ### end Alembic commands ###
