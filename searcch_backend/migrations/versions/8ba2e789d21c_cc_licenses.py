"""cc_licenses

Revision ID: 8ba2e789d21c
Revises: affe7228e4ef
Create Date: 2021-07-22 16:41:20.484303

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy.sql import table, column

# revision identifiers, used by Alembic.
revision = '8ba2e789d21c'
down_revision = 'affe7228e4ef'
branch_labels = None
depends_on = None


def upgrade():
    data_upgrades()


def data_upgrades():
    my_table = table('licenses',
        column('short_name', sa.String),
        column('long_name', sa.String),
        column('url', sa.String),
        column('verified', sa.Boolean))

    op.bulk_insert(my_table,[
        {'short_name': 'CC-BY-4.0', 'long_name': 'Creative Commons Attribution 4.0 International Public License', 'url': 'https://creativecommons.org/licenses/by/4.0', 'verified': True},
        #{'short_name': 'CC-BY-3.0', 'long_name': 'Creative Commons Attribution 3.0 Unported', 'url': 'https://creativecommons.org/licenses/by/3.0', 'verified': True},
        #{'short_name': 'CC-BY-2.5', 'long_name': 'Creative Commons Attribution 2.5 Generic', 'url': 'https://creativecommons.org/licenses/by/2.5', 'verified': True},
        #{'short_name': 'CC-BY-2.0', 'long_name': 'Creative Commons Attribution 2.0 Generic', 'url': 'https://creativecommons.org/licenses/by/2.0', 'verified': True},
        #{'short_name': 'CC-BY-1.0', 'long_name': 'Creative Commons Attribution 1.0 Generic', 'url': 'https://creativecommons.org/licenses/by/1.0', 'verified': True},

        {'short_name': 'CC-BY-SA-4.0', 'long_name': 'Creative Commons Attribution-ShareAlike 4.0 International Public License', 'url': 'https://creativecommons.org/licenses/by-sa/4.0', 'verified': True},
        #{'short_name': 'CC-BY-SA-3.0', 'long_name': 'Creative Commons Attribution-ShareAlike 3.0 Unported', 'url': 'https://creativecommons.org/licenses/by-sa/3.0', 'verified': True},
        #{'short_name': 'CC-BY-SA-2.5', 'long_name': 'Creative Commons Attribution-ShareAlike 2.5 Generic', 'url': 'https://creativecommons.org/licenses/by-sa/2.5', 'verified': True},
        #{'short_name': 'CC-BY-SA-2.0', 'long_name': 'Creative Commons Attribution-ShareAlike 2.0 Generic', 'url': 'https://creativecommons.org/licenses/by-sa/2.0', 'verified': True},
        #{'short_name': 'CC-BY-SA-1.0', 'long_name': 'Creative Commons Attribution-ShareAlike 1.0 Generic', 'url': 'https://creativecommons.org/licenses/by-sa/1.0', 'verified': True},

        {'short_name': 'CC-BY-NC-4.0', 'long_name': 'Creative Commons Attribution-NonCommercial 4.0 International Public License', 'url': 'https://creativecommons.org/licenses/by-nc/4.0', 'verified': True},

        {'short_name': 'CC-BY-NC-SA-4.0', 'long_name': 'Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International Public License', 'url': 'https://creativecommons.org/licenses/by-nc-sa/4.0', 'verified': True},

        {'short_name': 'CC-BY-ND-4.0', 'long_name': 'Creative Commons Attribution-NoDerivatives 4.0 International Public License', 'url': 'https://creativecommons.org/licenses/by-nd/4.0', 'verified': True},

        {'short_name': 'CC-BY-NC-ND-4.0', 'long_name': 'Creative Commons Attribution-NonCommercial-NoDerivatives 4.0 International Public License', 'url': 'https://creativecommons.org/licenses/by-nc-nd/4.0', 'verified': True},

        {'short_name': 'CC0-1.0', 'long_name': 'CC0 1.0 Universal Public Domain Dedication', 'url': 'https://creativecommons.org/publicdomain/zero/1.0', 'verified': True},
    ])


def downgrade():
    pass
