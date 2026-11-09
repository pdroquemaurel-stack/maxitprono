"""prediction days ahead

Réglage admin : nombre de jours à venir dont les matchs sont proposés aux pronostics.

Revision ID: c3d4e5f6a7b8
Revises: 6082103a8647
Create Date: 2026-11-09 10:00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'c3d4e5f6a7b8'
down_revision: Union[str, Sequence[str], None] = '6082103a8647'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('game_settings') as batch:
        batch.add_column(sa.Column('prediction_days_ahead', sa.Integer(), server_default='14',
                                   nullable=False))


def downgrade() -> None:
    with op.batch_alter_table('game_settings') as batch:
        batch.drop_column('prediction_days_ahead')
