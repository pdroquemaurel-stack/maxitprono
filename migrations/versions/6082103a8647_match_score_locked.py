"""match score locked

Score corrigé par l'admin : la synchronisation ne touche plus au statut ni au score.

Revision ID: 6082103a8647
Revises: 699df63c3059
Create Date: 2026-11-05 00:26:12.327806

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6082103a8647'
down_revision: Union[str, Sequence[str], None] = '699df63c3059'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('matches') as batch:
        batch.add_column(sa.Column('score_locked', sa.Boolean(), server_default=sa.false(),
                                   nullable=False))


def downgrade() -> None:
    with op.batch_alter_table('matches') as batch:
        batch.drop_column('score_locked')
