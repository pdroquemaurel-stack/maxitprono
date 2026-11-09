"""rank snapshots

Rang de chaque joueur au classement général à la fin de chaque journée de matchs.
Remplie au prochain calcul des points (table vide : tout est reconstruit).

Revision ID: f6a7b8c9d0e1
Revises: e5f6a7b8c9d0
Create Date: 2026-11-09 23:30:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f6a7b8c9d0e1'
down_revision: Union[str, Sequence[str], None] = 'e5f6a7b8c9d0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'rank_snapshots',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('day', sa.Date(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('rank', sa.Integer(), nullable=False),
        sa.Column('points', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('day', 'user_id', name='uq_rank_snapshots_day_user'),
    )
    op.create_index(op.f('ix_rank_snapshots_day'), 'rank_snapshots', ['day'])
    op.create_index(op.f('ix_rank_snapshots_user_id'), 'rank_snapshots', ['user_id'])


def downgrade() -> None:
    op.drop_index(op.f('ix_rank_snapshots_user_id'), table_name='rank_snapshots')
    op.drop_index(op.f('ix_rank_snapshots_day'), table_name='rank_snapshots')
    op.drop_table('rank_snapshots')
