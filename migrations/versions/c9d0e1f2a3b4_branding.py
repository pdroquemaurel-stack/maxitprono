"""branding

Personnalisation du jeu dans l'admin (nom, logo, couleurs) et son historique.

Revision ID: c9d0e1f2a3b4
Revises: b8c9d0e1f2a3
Create Date: 2026-11-10 10:00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

from app.models.types import UTCDateTime


revision: str = 'c9d0e1f2a3b4'
down_revision: Union[str, Sequence[str], None] = 'b8c9d0e1f2a3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'branding',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('app_name', sa.String(30), nullable=False),
        sa.Column('logo_part1', sa.String(30), nullable=False),
        sa.Column('logo_part2', sa.String(30), nullable=False),
        sa.Column('publisher_name', sa.String(30), nullable=False),
        sa.Column('tagline_fr', sa.String(60), nullable=False),
        sa.Column('tagline_en', sa.String(60), nullable=False),
        sa.Column('color_primary', sa.String(7), nullable=False),
        sa.Column('color_dark', sa.String(7), nullable=False),
        sa.Column('updated_at', UTCDateTime(), nullable=False),
    )
    op.create_table(
        'branding_changes',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='SET NULL')),
        sa.Column('field', sa.String(30), nullable=False),
        sa.Column('old_value', sa.String(60), nullable=False),
        sa.Column('new_value', sa.String(60), nullable=False),
        sa.Column('changed_at', UTCDateTime(), nullable=False),
    )
    op.create_index('ix_branding_changes_changed_at', 'branding_changes', ['changed_at'])


def downgrade() -> None:
    op.drop_index('ix_branding_changes_changed_at', 'branding_changes')
    op.drop_table('branding_changes')
    op.drop_table('branding')
