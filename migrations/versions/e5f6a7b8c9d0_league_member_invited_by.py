"""league member invited by

Membre dont le lien d'invitation a fait venir le joueur (badge Rassembleur).

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-11-09 23:00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e5f6a7b8c9d0'
down_revision: Union[str, Sequence[str], None] = 'd4e5f6a7b8c9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('league_members') as batch:
        batch.add_column(sa.Column('invited_by_id', sa.Integer(), nullable=True))
        batch.create_foreign_key('fk_league_members_invited_by_id_users', 'users',
                                 ['invited_by_id'], ['id'])


def downgrade() -> None:
    with op.batch_alter_table('league_members') as batch:
        batch.drop_constraint('fk_league_members_invited_by_id_users', type_='foreignkey')
        batch.drop_column('invited_by_id')
