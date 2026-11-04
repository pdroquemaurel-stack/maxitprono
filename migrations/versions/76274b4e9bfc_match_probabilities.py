"""match probabilities

Pourcentages 1 / N / 2 prédits par le fournisseur (vides s'il n'en donne pas).

Revision ID: 76274b4e9bfc
Revises: b7c1d2e3f4a5
Create Date: 2026-11-04 22:27:01.398644

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '76274b4e9bfc'
down_revision: Union[str, Sequence[str], None] = 'b7c1d2e3f4a5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('matches') as batch:
        batch.add_column(sa.Column('prob_home', sa.Integer(), nullable=True))
        batch.add_column(sa.Column('prob_draw', sa.Integer(), nullable=True))
        batch.add_column(sa.Column('prob_away', sa.Integer(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table('matches') as batch:
        batch.drop_column('prob_away')
        batch.drop_column('prob_draw')
        batch.drop_column('prob_home')
