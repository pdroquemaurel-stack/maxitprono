"""match matchday

Numéro de journée donné par le fournisseur (vide en phase à élimination directe).

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-11-09 22:30:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd4e5f6a7b8c9'
down_revision: Union[str, Sequence[str], None] = 'c3d4e5f6a7b8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('matches') as batch:
        batch.add_column(sa.Column('matchday', sa.Integer(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table('matches') as batch:
        batch.drop_column('matchday')
