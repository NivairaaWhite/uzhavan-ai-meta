"""post-harvest advisor: spoilage profiles, storage facilities, processing
units, recommendation log

Revision ID: 2851b60f1a1a
Revises: 64990fb87cbf
Create Date: 2026-09-18 12:00:00.000000
"""
from alembic import op
import sqlalchemy as sa


revision = '2851b60f1a1a'
down_revision = '64990fb87cbf'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'crop_spoilage_profiles',
        sa.Column('crop_type', sa.String(length=80), nullable=False),
        sa.Column(
            'tier',
            sa.Enum('HIGHLY_PERISHABLE', 'SEMI_PERISHABLE', 'DURABLE', name='perishabilitytier'),
            nullable=False,
        ),
        sa.Column('shelf_life_ambient_days', sa.Float(), nullable=False),
        sa.Column('shelf_life_cold_storage_days', sa.Float(), nullable=False),
        sa.Column('daily_value_decay_pct', sa.Float(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('crop_type'),
    )

    op.create_table(
        'storage_facilities',
        sa.Column('id', sa.String(length=32), nullable=False),
        sa.Column('name', sa.String(length=160), nullable=False),
        sa.Column('district', sa.String(length=120), nullable=False),
        sa.Column('latitude', sa.Float(), nullable=False),
        sa.Column('longitude', sa.Float(), nullable=False),
        sa.Column('capacity_kg', sa.Float(), nullable=False),
        sa.Column('available_capacity_kg', sa.Float(), nullable=False),
        sa.Column('cost_per_kg_per_day', sa.Float(), nullable=False),
        sa.Column('supported_crop_types', sa.Text(), nullable=True),
        sa.Column('contact_phone', sa.String(length=15), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_storage_facilities_district'), 'storage_facilities', ['district'], unique=False)

    op.create_table(
        'processing_units',
        sa.Column('id', sa.String(length=32), nullable=False),
        sa.Column('name', sa.String(length=160), nullable=False),
        sa.Column('district', sa.String(length=120), nullable=False),
        sa.Column('latitude', sa.Float(), nullable=False),
        sa.Column('longitude', sa.Float(), nullable=False),
        sa.Column('output_product', sa.String(length=120), nullable=True),
        sa.Column('daily_intake_capacity_kg', sa.Float(), nullable=False),
        sa.Column('remaining_intake_today_kg', sa.Float(), nullable=False),
        sa.Column('price_per_kg', sa.Float(), nullable=False),
        sa.Column('accepted_crop_types', sa.Text(), nullable=True),
        sa.Column('contact_phone', sa.String(length=15), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_processing_units_district'), 'processing_units', ['district'], unique=False)

    op.create_table(
        'post_harvest_recommendations',
        sa.Column('id', sa.String(length=32), nullable=False),
        sa.Column('farmer_id', sa.String(length=32), nullable=False),
        sa.Column('listing_id', sa.String(length=32), nullable=True),
        sa.Column('crop_type', sa.String(length=80), nullable=False),
        sa.Column('quantity_kg', sa.Float(), nullable=False),
        sa.Column('district', sa.String(length=120), nullable=False),
        sa.Column('latitude', sa.Float(), nullable=False),
        sa.Column('longitude', sa.Float(), nullable=False),
        sa.Column(
            'perishability_tier',
            sa.Enum('HIGHLY_PERISHABLE', 'SEMI_PERISHABLE', 'DURABLE', name='perishabilitytier'),
            nullable=False,
        ),
        sa.Column('sell_now_kg', sa.Float(), nullable=True),
        sa.Column('store_kg', sa.Float(), nullable=True),
        sa.Column('process_kg', sa.Float(), nullable=True),
        sa.Column('at_risk_kg', sa.Float(), nullable=True),
        sa.Column('wholesale_price_per_kg', sa.Float(), nullable=True),
        sa.Column('expected_net_value', sa.Float(), nullable=True),
        sa.Column('baseline_sell_all_today_value', sa.Float(), nullable=True),
        sa.Column('projected_savings', sa.Float(), nullable=True),
        sa.Column('reasoning', sa.Text(), nullable=True),
        sa.Column('allocation_detail_json', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['farmer_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['listing_id'], ['crop_listings.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        op.f('ix_post_harvest_recommendations_farmer_id'),
        'post_harvest_recommendations', ['farmer_id'], unique=False,
    )
    op.create_index(
        op.f('ix_post_harvest_recommendations_crop_type'),
        'post_harvest_recommendations', ['crop_type'], unique=False,
    )


def downgrade():
    op.drop_index(op.f('ix_post_harvest_recommendations_crop_type'), table_name='post_harvest_recommendations')
    op.drop_index(op.f('ix_post_harvest_recommendations_farmer_id'), table_name='post_harvest_recommendations')
    op.drop_table('post_harvest_recommendations')
    op.drop_index(op.f('ix_processing_units_district'), table_name='processing_units')
    op.drop_table('processing_units')
    op.drop_index(op.f('ix_storage_facilities_district'), table_name='storage_facilities')
    op.drop_table('storage_facilities')
    op.drop_table('crop_spoilage_profiles')
    sa.Enum(name='perishabilitytier').drop(op.get_bind(), checkfirst=True)
