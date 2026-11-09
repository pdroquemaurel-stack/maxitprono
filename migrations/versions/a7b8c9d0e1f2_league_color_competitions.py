"""league color and competitions

Couleur de l'icône de ligue et compétitions comptées par la ligue (aucune = toutes).

Revision ID: a7b8c9d0e1f2
Revises: f6a7b8c9d0e1
Create Date: 2026-11-09 12:00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a7b8c9d0e1f2'
down_revision: Union[str, Sequence[str], None] = 'f6a7b8c9d0e1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('leagues') as batch:
        batch.add_column(sa.Column('color', sa.String(length=10), nullable=False,
                                   server_default='orange'))
    op.create_table(
        'league_competitions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('league_id', sa.Integer(), nullable=False),
        sa.Column('competition_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['league_id'], ['leagues.id']),
        sa.ForeignKeyConstraint(['competition_id'], ['competitions.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('league_id', 'competition_id',
                            name='uq_league_competitions_league_competition'),
    )
    op.create_index('ix_league_competitions_league_id', 'league_competitions', ['league_id'])


def downgrade() -> None:
    op.drop_index('ix_league_competitions_league_id', table_name='league_competitions')
    op.drop_table('league_competitions')
    with op.batch_alter_table('leagues') as batch:
        batch.drop_column('color')
