"""providers

Remplace `api_id` (identifiant API-Football) par le couple `provider` + `external_id`
sur les compétitions et les matchs, et ajoute la colonne `provider` du journal
des appels.

Données existantes : tout ce qui a un `api_id` vient d'API-Football, sauf la
compétition démo (api_id 999999) qui devient provider « demo », identifiant « demo »
(celui attendu par scripts/seed_demo.py).

Revision ID: b7c1d2e3f4a5
Revises: abe340e3b4d5
Create Date: 2026-11-04 22:00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'b7c1d2e3f4a5'
down_revision: Union[str, Sequence[str], None] = 'abe340e3b4d5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

DEMO_API_ID = 999999


def upgrade() -> None:
    # 1. Nouvelles colonnes, d'abord facultatives pour pouvoir les remplir
    with op.batch_alter_table('competitions') as batch:
        batch.add_column(sa.Column('provider', sa.String(length=20), nullable=True))
        batch.add_column(sa.Column('external_id', sa.String(length=40), nullable=True))
    with op.batch_alter_table('matches') as batch:
        batch.add_column(sa.Column('provider', sa.String(length=20), nullable=True))
        batch.add_column(sa.Column('external_id', sa.String(length=40), nullable=True))
    with op.batch_alter_table('api_call_logs') as batch:
        batch.add_column(sa.Column('provider', sa.String(length=20), nullable=False,
                                   server_default='api_football'))

    # 2. Reprise des données
    op.execute("UPDATE competitions SET external_id = CAST(api_id AS VARCHAR(40)), "
               "provider = 'api_football'")
    op.execute(f"UPDATE competitions SET external_id = 'demo', provider = 'demo' "
               f"WHERE api_id = {DEMO_API_ID}")
    op.execute("UPDATE matches SET external_id = CAST(api_id AS VARCHAR(40)), "
               "provider = 'api_football' WHERE api_id IS NOT NULL")

    # 3. Contraintes, puis suppression de api_id
    with op.batch_alter_table('competitions') as batch:
        batch.alter_column('provider', existing_type=sa.String(length=20), nullable=False)
        batch.alter_column('external_id', existing_type=sa.String(length=40), nullable=False)
        batch.create_unique_constraint('uq_competitions_provider_external_id',
                                       ['provider', 'external_id'])
        batch.drop_column('api_id')
    with op.batch_alter_table('matches') as batch:
        batch.create_unique_constraint('uq_matches_provider_external_id',
                                       ['provider', 'external_id'])
        batch.drop_column('api_id')


def downgrade() -> None:
    # Retour en arrière possible seulement si toutes les données viennent d'API-Football
    other = op.get_bind().execute(sa.text(
        "SELECT COUNT(*) FROM competitions WHERE provider NOT IN ('api_football', 'demo')"
    )).scalar()
    if other:
        raise RuntimeError("Des compétitions viennent d'un autre fournisseur : "
                           "lancer d'abord scripts/reset_football_data.py avec API-Football")
    with op.batch_alter_table('competitions') as batch:
        batch.add_column(sa.Column('api_id', sa.Integer(), nullable=True))
    with op.batch_alter_table('matches') as batch:
        batch.add_column(sa.Column('api_id', sa.Integer(), nullable=True))
    op.execute("UPDATE competitions SET api_id = CAST(external_id AS INTEGER) "
               "WHERE provider = 'api_football'")
    op.execute(f"UPDATE competitions SET api_id = {DEMO_API_ID} WHERE provider = 'demo'")
    op.execute("UPDATE matches SET api_id = CAST(external_id AS INTEGER) "
               "WHERE provider = 'api_football'")

    with op.batch_alter_table('matches') as batch:
        batch.drop_constraint('uq_matches_provider_external_id', type_='unique')
        batch.drop_column('external_id')
        batch.drop_column('provider')
        batch.create_unique_constraint('uq_matches_api_id', ['api_id'])
    with op.batch_alter_table('competitions') as batch:
        batch.drop_constraint('uq_competitions_provider_external_id', type_='unique')
        batch.drop_column('external_id')
        batch.drop_column('provider')
        batch.alter_column('api_id', existing_type=sa.Integer(), nullable=False)
        batch.create_unique_constraint('uq_competitions_api_id', ['api_id'])
    with op.batch_alter_table('api_call_logs') as batch:
        batch.drop_column('provider')
