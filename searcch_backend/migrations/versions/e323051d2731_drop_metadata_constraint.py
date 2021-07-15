"""drop-metadata-constraint

Revision ID: e323051d2731
Revises: 1cc167c394bc
Create Date: 2021-07-13 03:39:32.865335

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'e323051d2731'
down_revision = '1cc167c394bc'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("artifact_metadata", schema=None) as batch_op:
        batch_op.drop_constraint("artifact_metadata_name_artifact_id_value_type_key", type_="unique")


def downgrade():
    with op.batch_alter_table("artifact_metadata", schema=None) as batch_op:
        op.create_unique_constraint("artifact_metadata_name_artifact_id_value_type_key",
                                    ["name", "artifact_id", "value", "type"])
