"""match minute

Minute de jeu d'un match en cours, donnée par le fournisseur (vide sinon).

Revision ID: b8c9d0e1f2a3
Revises: a7b8c9d0e1f2
Create Date: 2026-11-10 18:00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b8c9d0e1f2a3'
down_revision: Union[str, Sequence[str], None] = 'a7b8c9d0e1f2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('matches') as batch:
        batch.add_column(sa.Column('minute', sa.Integer(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table('matches') as batch:
        batch.drop_column('minute')
