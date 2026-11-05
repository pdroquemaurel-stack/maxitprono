"""admin and game settings

Accès au back-office (users.is_admin) et réglages du jeu modifiables (une seule ligne).

Revision ID: 699df63c3059
Revises: 356e0b307166
Create Date: 2026-11-05 00:20:52.615078

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import app.models.types


# revision identifiers, used by Alembic.
revision: str = '699df63c3059'
down_revision: Union[str, Sequence[str], None] = '356e0b307166'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('game_settings',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('winner_points', sa.Integer(), nullable=False),
    sa.Column('exact_bonus', sa.Integer(), nullable=False),
    sa.Column('league_max_members', sa.Integer(), nullable=False),
    sa.Column('updated_at', app.models.types.UTCDateTime(timezone=True), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('users') as batch:
        batch.add_column(sa.Column('is_admin', sa.Boolean(), server_default=sa.false(), nullable=False))


def downgrade() -> None:
    with op.batch_alter_table('users') as batch:
        batch.drop_column('is_admin')
    op.drop_table('game_settings')
