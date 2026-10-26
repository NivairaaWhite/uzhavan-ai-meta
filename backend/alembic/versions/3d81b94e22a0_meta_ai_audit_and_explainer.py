"""meta_ai_audit_and_explainer

Revision ID: 3d81b94e22a0
Revises: 2851b60f1a1a
Create Date: 2026-10-26 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3d81b94e22a0'
down_revision: Union[str, None] = '2851b60f1a1a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add audit columns and district to crop_listings
    op.add_column('crop_listings', sa.Column('district', sa.String(length=120), nullable=True))
    op.add_column('crop_listings', sa.Column('image_path', sa.String(length=255), nullable=True))
    op.add_column('crop_listings', sa.Column('audit_status', sa.String(length=16), server_default='none', nullable=True))
    op.add_column('crop_listings', sa.Column('audit_grade', sa.String(length=16), nullable=True))
    op.add_column('crop_listings', sa.Column('audit_confidence', sa.Float(), nullable=True))
    op.add_column('crop_listings', sa.Column('audit_defects', sa.Text(), nullable=True))
    op.add_column('crop_listings', sa.Column('audit_model', sa.String(length=40), nullable=True))
    op.create_index(op.f('ix_crop_listings_district'), 'crop_listings', ['district'], unique=False)

    # Add explanation columns to post_harvest_recommendations
    op.add_column('post_harvest_recommendations', sa.Column('explanation', sa.Text(), nullable=True))
    op.add_column('post_harvest_recommendations', sa.Column('explanation_lang', sa.String(length=8), nullable=True))


def downgrade() -> None:
    op.drop_column('post_harvest_recommendations', 'explanation_lang')
    op.drop_column('post_harvest_recommendations', 'explanation')
    op.drop_index(op.f('ix_crop_listings_district'), table_name='crop_listings')
    op.drop_column('crop_listings', 'audit_model')
    op.drop_column('crop_listings', 'audit_defects')
    op.drop_column('crop_listings', 'audit_confidence')
    op.drop_column('crop_listings', 'audit_grade')
    op.drop_column('crop_listings', 'audit_status')
    op.drop_column('crop_listings', 'image_path')
    op.drop_column('crop_listings', 'district')
