"""move-roles-to-artifact-affiliation

Revision ID: 09d7d4f03602
Revises: e323051d2731
Create Date: 2021-07-15 06:37:06.329363

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '09d7d4f03602'
down_revision = 'e323051d2731'
branch_labels = None
depends_on = None


def upgrade():
    op.drop_constraint(
        'affiliations_person_id_org_id_roles_key',
        'affiliations', type_='unique')
    op.create_unique_constraint(
        'affiliations_person_id_org_id_key', 'affiliations', ['person_id', 'org_id'])
    op.drop_column('affiliations', 'roles')
    ne = postgresql.ENUM(
        'Author', 'ContactPerson', 'Other',
        name='artifact_affiliation_enum')
    ne.create(op.get_bind())
    op.add_column(
        'artifact_affiliations',
        sa.Column('roles',
                  sa.Enum(
                      'Author', 'ContactPerson', 'Other',
                      name='artifact_affiliation_enum'),
                  nullable=True, default="Author"))
    op.execute("update artifact_affiliations set roles='Author' where roles is NULL")
    op.alter_column('artifact_affiliations', 'roles', nullable=False)
    op.drop_constraint(
        'artifact_affiliations_artifact_id_affiliation_id_key',
        'artifact_affiliations', type_='unique')
    op.create_unique_constraint(
        'artifact_affiliations_artifact_id_affiliation_id_roles_key', 'artifact_affiliations',
        ['artifact_id', 'affiliation_id', 'roles'])


def downgrade():
    op.drop_constraint(None, 'artifact_affiliations', type_='unique')
    op.create_unique_constraint(
        'artifact_affiliations_artifact_id_affiliation_id_key',
        'artifact_affiliations', ['artifact_id', 'affiliation_id'])
    op.drop_column('artifact_affiliations', 'roles')
    op.add_column(
        'affiliations',
        sa.Column('roles',
                  postgresql.ENUM('Author', 'ProjectManager', 'Researcher',
                                  'ContactPerson', 'PrincipalInvestigator',
                                  'CoPrincipalInvestigator', 'Other',
                                  name='affiliation_enum'),
                  autoincrement=False, nullable=False, default="Author"))
    op.drop_constraint(None, 'affiliations', type_='unique')
    op.create_unique_constraint(
        'affiliations_person_id_org_id_roles_key',
        'affiliations', ['person_id', 'org_id', 'roles'])
