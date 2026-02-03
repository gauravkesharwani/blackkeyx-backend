"""Schema redesign: rename properties->deals, add asset-specific tables.

This migration implements the full schema redesign:
1. Rename properties table to deals
2. Add new columns to deals, investment_metrics, market_analysis, annual_projections
3. Widen purchase_price and total_equity_required from Integer to Numeric(15,2)
4. Create sponsor_fees, waterfall_structure, reserves tables
5. Create all 16 asset-specific tables (9 detail + 7 tenant/unit_mix)
6. Rename hospitality -> hotel in deal_type
7. Drop old tenants and property_features tables

Revision ID: 007_schema_redesign
Revises: 006_widen_target_return
Create Date: 2026-02-03

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "007_schema_redesign"
down_revision: Union[str, None] = "006_widen_target_return"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ================================================================
    # 1. RENAME properties -> deals
    # ================================================================
    op.rename_table("properties", "deals")

    # Rename indexes on the old properties table
    op.execute("ALTER INDEX idx_properties_status RENAME TO idx_deals_status")
    op.execute("ALTER INDEX idx_properties_deal_type RENAME TO idx_deals_deal_type")

    # ================================================================
    # 2. ADD NEW COLUMNS TO deals
    # ================================================================
    op.add_column("deals", sa.Column("price_per_sf", sa.Numeric(10, 2), nullable=True))
    op.add_column(
        "deals", sa.Column("replacement_cost_per_sf", sa.Numeric(10, 2), nullable=True)
    )
    op.add_column(
        "deals",
        sa.Column("discount_to_replacement_pct", sa.Numeric(5, 2), nullable=True),
    )
    # Physical attributes (from former property_features)
    op.add_column("deals", sa.Column("year_built", sa.Integer(), nullable=True))
    op.add_column("deals", sa.Column("year_renovated", sa.Integer(), nullable=True))
    op.add_column("deals", sa.Column("parking_spaces", sa.Integer(), nullable=True))

    # ================================================================
    # 3. WIDEN purchase_price and total_equity_required (Integer -> Numeric)
    # ================================================================
    op.alter_column(
        "deals",
        "purchase_price",
        existing_type=sa.Integer(),
        type_=sa.Numeric(15, 2),
        existing_nullable=True,
        postgresql_using="purchase_price::numeric(15,2)",
    )
    op.alter_column(
        "deals",
        "total_equity_required",
        existing_type=sa.Integer(),
        type_=sa.Numeric(15, 2),
        existing_nullable=True,
        postgresql_using="total_equity_required::numeric(15,2)",
    )

    # ================================================================
    # 4. RENAME hospitality -> hotel in deal_type
    # ================================================================
    op.execute("UPDATE deals SET deal_type = 'hotel' WHERE deal_type = 'hospitality'")

    # ================================================================
    # 5. ADD NEW COLUMNS TO EXISTING CHILD TABLES
    # ================================================================

    # investment_metrics: new fields
    op.add_column(
        "investment_metrics",
        sa.Column("return_from_cash_flow_pct", sa.Numeric(5, 2), nullable=True),
    )
    op.add_column(
        "investment_metrics",
        sa.Column("return_from_sale_pct", sa.Numeric(5, 2), nullable=True),
    )
    op.add_column(
        "investment_metrics",
        sa.Column("return_profile", sa.String(50), nullable=True),
    )

    # market_analysis: new fields
    op.add_column(
        "market_analysis",
        sa.Column("new_construction_pct", sa.Numeric(5, 2), nullable=True),
    )
    op.add_column(
        "market_analysis",
        sa.Column("absorption_rate", sa.Numeric(10, 2), nullable=True),
    )
    op.add_column(
        "market_analysis",
        sa.Column("landlord_pricing_power", sa.String(50), nullable=True),
    )

    # annual_projections: new fields
    op.add_column(
        "annual_projections",
        sa.Column("cash_on_cash_return", sa.Numeric(5, 2), nullable=True),
    )
    op.add_column(
        "annual_projections",
        sa.Column("irr_through_year", sa.Numeric(5, 2), nullable=True),
    )

    # ================================================================
    # 6. CREATE DEAL STRUCTURE TABLES
    # ================================================================

    # sponsor_fees (1:1 with deals)
    op.create_table(
        "sponsor_fees",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "deal_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("deals.id", ondelete="CASCADE"),
            unique=True,
            nullable=False,
        ),
        sa.Column("acquisition_fee_pct", sa.Numeric(5, 2), nullable=True),
        sa.Column("acquisition_fee_amount", sa.Numeric(15, 2), nullable=True),
        sa.Column("asset_management_fee_pct", sa.Numeric(5, 2), nullable=True),
        sa.Column("property_management_fee_pct", sa.Numeric(5, 2), nullable=True),
        sa.Column("construction_supervision_fee_pct", sa.Numeric(5, 2), nullable=True),
        sa.Column("disposition_fee_pct", sa.Numeric(5, 2), nullable=True),
        sa.Column("guarantee_fee_pct", sa.Numeric(5, 2), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    # waterfall_structure (1:1 with deals)
    op.create_table(
        "waterfall_structure",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "deal_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("deals.id", ondelete="CASCADE"),
            unique=True,
            nullable=False,
        ),
        sa.Column("preferred_return_pct", sa.Numeric(5, 2), nullable=True),
        sa.Column("promote_tier_1_pct", sa.Numeric(5, 2), nullable=True),
        sa.Column("promote_tier_1_hurdle", sa.Numeric(5, 2), nullable=True),
        sa.Column("promote_tier_2_pct", sa.Numeric(5, 2), nullable=True),
        sa.Column("promote_tier_2_hurdle", sa.Numeric(5, 2), nullable=True),
        sa.Column("sponsor_coinvest_pct", sa.Numeric(5, 2), nullable=True),
        sa.Column("sponsor_coinvest_amount", sa.Numeric(15, 2), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    # reserves (1:N with deals)
    op.create_table(
        "reserves",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "deal_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("deals.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("reserve_type", sa.String(100), nullable=False),
        sa.Column("reserve_amount", sa.Numeric(15, 2), nullable=True),
        sa.Column("reserve_purpose", sa.Text(), nullable=True),
        sa.Column("release_conditions", sa.Text(), nullable=True),
        sa.Column("lender_controlled", sa.Boolean(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("idx_reserves_deal_id", "reserves", ["deal_id"])

    # ================================================================
    # 7. CREATE ASSET-SPECIFIC TABLES
    # ================================================================

    # ----- INDUSTRIAL -----
    op.create_table(
        "industrial_details",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "deal_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("deals.id", ondelete="CASCADE"),
            unique=True,
            nullable=False,
        ),
        sa.Column("clear_height_min", sa.Numeric(5, 1), nullable=True),
        sa.Column("clear_height_max", sa.Numeric(5, 1), nullable=True),
        sa.Column("loading_docks", sa.Integer(), nullable=True),
        sa.Column("drive_in_doors", sa.Integer(), nullable=True),
        sa.Column("dock_height", sa.Numeric(5, 1), nullable=True),
        sa.Column("truck_court_depth", sa.Numeric(6, 1), nullable=True),
        sa.Column("column_spacing", sa.String(50), nullable=True),
        sa.Column("rail_access", sa.Boolean(), nullable=True),
        sa.Column("power_amps", sa.Integer(), nullable=True),
        sa.Column("power_voltage", sa.Integer(), nullable=True),
        sa.Column("crane_capacity", sa.Numeric(10, 2), nullable=True),
        sa.Column("sprinkler_system", sa.String(50), nullable=True),
        sa.Column("office_pct", sa.Numeric(5, 2), nullable=True),
        sa.Column("trailer_parking", sa.Integer(), nullable=True),
        sa.Column("cross_dock", sa.Boolean(), nullable=True),
        sa.Column("freezer_cooler_sf", sa.Integer(), nullable=True),
        sa.Column("year_built", sa.Integer(), nullable=True),
        sa.Column("year_renovated", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    op.create_table(
        "industrial_tenants",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "deal_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("deals.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("tenant_name", sa.String(255), nullable=False),
        sa.Column("square_feet", sa.Integer(), nullable=True),
        sa.Column("annual_rent", sa.Numeric(12, 2), nullable=True),
        sa.Column("rent_per_sf", sa.Numeric(8, 2), nullable=True),
        sa.Column("lease_start", sa.String(50), nullable=True),
        sa.Column("lease_expiration", sa.String(50), nullable=True),
        sa.Column("renewal_options", sa.String(255), nullable=True),
        sa.Column("renewal_option_terms", sa.Text(), nullable=True),
        sa.Column("credit_rating", sa.String(50), nullable=True),
        sa.Column("years_at_location", sa.Integer(), nullable=True),
        sa.Column("is_mission_critical", sa.Boolean(), nullable=True),
        sa.Column("distance_from_hq", sa.String(100), nullable=True),
        sa.Column("tenant_type", sa.String(100), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("idx_industrial_tenants_deal_id", "industrial_tenants", ["deal_id"])

    # ----- MULTIFAMILY -----
    op.create_table(
        "multifamily_details",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "deal_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("deals.id", ondelete="CASCADE"),
            unique=True,
            nullable=False,
        ),
        sa.Column("unit_count", sa.Integer(), nullable=True),
        sa.Column("avg_unit_size", sa.Numeric(8, 1), nullable=True),
        sa.Column("avg_rent_per_unit", sa.Numeric(10, 2), nullable=True),
        sa.Column("avg_rent_per_sf", sa.Numeric(8, 2), nullable=True),
        sa.Column("in_place_occupancy", sa.Numeric(5, 2), nullable=True),
        sa.Column("market_rent_per_unit", sa.Numeric(10, 2), nullable=True),
        sa.Column("loss_to_lease_pct", sa.Numeric(5, 2), nullable=True),
        sa.Column(
            "amenities",
            postgresql.ARRAY(sa.String()),
            server_default="{}",
            nullable=True,
        ),
        sa.Column("washer_dryer", sa.String(50), nullable=True),
        sa.Column("vintage", sa.String(50), nullable=True),
        sa.Column("recent_renovations", sa.Text(), nullable=True),
        sa.Column("renovation_premium", sa.Numeric(10, 2), nullable=True),
        sa.Column("concessions", sa.Text(), nullable=True),
        sa.Column("turnover_rate", sa.Numeric(5, 2), nullable=True),
        sa.Column("expense_ratio", sa.Numeric(5, 2), nullable=True),
        sa.Column("year_built", sa.Integer(), nullable=True),
        sa.Column("year_renovated", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    op.create_table(
        "multifamily_unit_mix",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "deal_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("deals.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("unit_type", sa.String(50), nullable=False),
        sa.Column("unit_count", sa.Integer(), nullable=True),
        sa.Column("avg_sf", sa.Numeric(8, 1), nullable=True),
        sa.Column("current_rent", sa.Numeric(10, 2), nullable=True),
        sa.Column("market_rent", sa.Numeric(10, 2), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "idx_multifamily_unit_mix_deal_id", "multifamily_unit_mix", ["deal_id"]
    )

    # ----- RETAIL -----
    op.create_table(
        "retail_details",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "deal_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("deals.id", ondelete="CASCADE"),
            unique=True,
            nullable=False,
        ),
        sa.Column("gla", sa.Integer(), nullable=True),
        sa.Column("anchor_pct_gla", sa.Numeric(5, 2), nullable=True),
        sa.Column("inline_tenant_count", sa.Integer(), nullable=True),
        sa.Column("avg_inline_rent_psf", sa.Numeric(8, 2), nullable=True),
        sa.Column("cam_rate_psf", sa.Numeric(8, 2), nullable=True),
        sa.Column("percentage_rent_tenants", sa.Integer(), nullable=True),
        sa.Column("traffic_count", sa.Integer(), nullable=True),
        sa.Column("sales_psf", sa.Numeric(10, 2), nullable=True),
        sa.Column("parking_ratio", sa.Numeric(5, 2), nullable=True),
        sa.Column("pad_sites", sa.Integer(), nullable=True),
        sa.Column("outparcels", sa.Integer(), nullable=True),
        sa.Column("grocery_anchored", sa.Boolean(), nullable=True),
        sa.Column("nnn_vs_gross", sa.String(50), nullable=True),
        sa.Column("below_market_leases", sa.Integer(), nullable=True),
        sa.Column("year_built", sa.Integer(), nullable=True),
        sa.Column("year_renovated", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    op.create_table(
        "retail_tenants",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "deal_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("deals.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("tenant_name", sa.String(255), nullable=False),
        sa.Column("tenant_category", sa.String(100), nullable=True),
        sa.Column("square_feet", sa.Integer(), nullable=True),
        sa.Column("annual_rent", sa.Numeric(12, 2), nullable=True),
        sa.Column("rent_per_sf", sa.Numeric(8, 2), nullable=True),
        sa.Column("lease_expiration", sa.String(50), nullable=True),
        sa.Column("renewal_options", sa.String(255), nullable=True),
        sa.Column("percentage_rent", sa.Boolean(), nullable=True),
        sa.Column("sales_psf", sa.Numeric(10, 2), nullable=True),
        sa.Column("co_tenancy_clause", sa.Boolean(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("idx_retail_tenants_deal_id", "retail_tenants", ["deal_id"])

    # ----- OFFICE -----
    op.create_table(
        "office_details",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "deal_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("deals.id", ondelete="CASCADE"),
            unique=True,
            nullable=False,
        ),
        sa.Column("building_class", sa.String(10), nullable=True),
        sa.Column("floor_count", sa.Integer(), nullable=True),
        sa.Column("typical_floor_plate", sa.Integer(), nullable=True),
        sa.Column("nra", sa.Integer(), nullable=True),
        sa.Column("tenant_count", sa.Integer(), nullable=True),
        sa.Column("walt_years", sa.Numeric(5, 2), nullable=True),
        sa.Column("avg_rent_psf_nnn", sa.Numeric(8, 2), nullable=True),
        sa.Column("avg_rent_psf_fsg", sa.Numeric(8, 2), nullable=True),
        sa.Column("ti_allowance_psf", sa.Numeric(8, 2), nullable=True),
        sa.Column("parking_ratio", sa.Numeric(5, 2), nullable=True),
        sa.Column(
            "building_amenities",
            postgresql.ARRAY(sa.String()),
            server_default="{}",
            nullable=True,
        ),
        sa.Column("leed_certification", sa.String(50), nullable=True),
        sa.Column("energy_star_score", sa.Integer(), nullable=True),
        sa.Column("largest_tenant_pct", sa.Numeric(5, 2), nullable=True),
        sa.Column("near_term_expirations_pct", sa.Numeric(5, 2), nullable=True),
        sa.Column("sublease_space_sf", sa.Integer(), nullable=True),
        sa.Column("year_built", sa.Integer(), nullable=True),
        sa.Column("year_renovated", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    op.create_table(
        "office_tenants",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "deal_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("deals.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("tenant_name", sa.String(255), nullable=False),
        sa.Column("square_feet", sa.Integer(), nullable=True),
        sa.Column("annual_rent", sa.Numeric(12, 2), nullable=True),
        sa.Column("rent_per_sf", sa.Numeric(8, 2), nullable=True),
        sa.Column("lease_start", sa.String(50), nullable=True),
        sa.Column("lease_expiration", sa.String(50), nullable=True),
        sa.Column("renewal_options", sa.String(255), nullable=True),
        sa.Column("ti_allowance", sa.Numeric(8, 2), nullable=True),
        sa.Column("credit_rating", sa.String(50), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("idx_office_tenants_deal_id", "office_tenants", ["deal_id"])

    # ----- SELF STORAGE -----
    op.create_table(
        "self_storage_details",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "deal_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("deals.id", ondelete="CASCADE"),
            unique=True,
            nullable=False,
        ),
        sa.Column("total_units", sa.Integer(), nullable=True),
        sa.Column("net_rentable_sf", sa.Integer(), nullable=True),
        sa.Column("climate_controlled_pct", sa.Numeric(5, 2), nullable=True),
        sa.Column("climate_controlled_units", sa.Integer(), nullable=True),
        sa.Column("drive_up_units", sa.Integer(), nullable=True),
        sa.Column("avg_rent_per_sf", sa.Numeric(8, 2), nullable=True),
        sa.Column("economic_occupancy", sa.Numeric(5, 2), nullable=True),
        sa.Column("physical_occupancy", sa.Numeric(5, 2), nullable=True),
        sa.Column("management_platform", sa.String(100), nullable=True),
        sa.Column("rv_boat_parking", sa.Boolean(), nullable=True),
        sa.Column("avg_length_of_stay", sa.Numeric(5, 1), nullable=True),
        sa.Column("street_rate_growth", sa.Numeric(5, 2), nullable=True),
        sa.Column("ecri_potential", sa.Numeric(5, 2), nullable=True),
        sa.Column("year_built", sa.Integer(), nullable=True),
        sa.Column("year_renovated", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    op.create_table(
        "self_storage_unit_mix",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "deal_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("deals.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("unit_size", sa.String(50), nullable=False),
        sa.Column("unit_count", sa.Integer(), nullable=True),
        sa.Column("rate_per_unit", sa.Numeric(10, 2), nullable=True),
        sa.Column("occupancy_pct", sa.Numeric(5, 2), nullable=True),
        sa.Column("climate_controlled", sa.Boolean(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "idx_self_storage_unit_mix_deal_id", "self_storage_unit_mix", ["deal_id"]
    )

    # ----- STUDENT HOUSING -----
    op.create_table(
        "student_housing_details",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "deal_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("deals.id", ondelete="CASCADE"),
            unique=True,
            nullable=False,
        ),
        sa.Column("total_beds", sa.Integer(), nullable=True),
        sa.Column("total_units", sa.Integer(), nullable=True),
        sa.Column("beds_per_unit_avg", sa.Numeric(4, 1), nullable=True),
        sa.Column("rent_per_bed", sa.Numeric(10, 2), nullable=True),
        sa.Column("rent_per_unit", sa.Numeric(10, 2), nullable=True),
        sa.Column("distance_to_campus", sa.String(100), nullable=True),
        sa.Column("affiliated_university", sa.String(255), nullable=True),
        sa.Column("university_enrollment", sa.Integer(), nullable=True),
        sa.Column("preleasing_pct", sa.Numeric(5, 2), nullable=True),
        sa.Column("preleasing_velocity", sa.String(100), nullable=True),
        sa.Column(
            "amenities",
            postgresql.ARRAY(sa.String()),
            server_default="{}",
            nullable=True,
        ),
        sa.Column("furnished", sa.Boolean(), nullable=True),
        sa.Column("utilities_included", sa.Boolean(), nullable=True),
        sa.Column("individual_leases", sa.Boolean(), nullable=True),
        sa.Column("on_campus_competition", sa.Text(), nullable=True),
        sa.Column("year_built", sa.Integer(), nullable=True),
        sa.Column("year_renovated", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    # ----- HOTEL -----
    op.create_table(
        "hotel_details",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "deal_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("deals.id", ondelete="CASCADE"),
            unique=True,
            nullable=False,
        ),
        sa.Column("room_count", sa.Integer(), nullable=True),
        sa.Column("avg_room_size", sa.Numeric(8, 1), nullable=True),
        sa.Column("adr", sa.Numeric(10, 2), nullable=True),
        sa.Column("revpar", sa.Numeric(10, 2), nullable=True),
        sa.Column("occupancy_rate", sa.Numeric(5, 2), nullable=True),
        sa.Column("franchise_brand", sa.String(255), nullable=True),
        sa.Column("franchise_expiration", sa.String(50), nullable=True),
        sa.Column("management_company", sa.String(255), nullable=True),
        sa.Column("fnb_revenue", sa.Numeric(15, 2), nullable=True),
        sa.Column("fnb_pct", sa.Numeric(5, 2), nullable=True),
        sa.Column("meeting_space_sf", sa.Integer(), nullable=True),
        sa.Column("star_rating", sa.Numeric(2, 1), nullable=True),
        sa.Column("trip_advisor_score", sa.Numeric(3, 1), nullable=True),
        sa.Column("pip_required", sa.Boolean(), nullable=True),
        sa.Column("pip_cost", sa.Numeric(15, 2), nullable=True),
        sa.Column("goppar", sa.Numeric(10, 2), nullable=True),
        sa.Column("comp_set_penetration", sa.Numeric(5, 2), nullable=True),
        sa.Column("year_built", sa.Integer(), nullable=True),
        sa.Column("year_renovated", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    op.create_table(
        "hotel_room_mix",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "deal_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("deals.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("room_type", sa.String(100), nullable=False),
        sa.Column("room_count", sa.Integer(), nullable=True),
        sa.Column("avg_size_sf", sa.Numeric(8, 1), nullable=True),
        sa.Column("rate", sa.Numeric(10, 2), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("idx_hotel_room_mix_deal_id", "hotel_room_mix", ["deal_id"])

    # ----- LAND -----
    op.create_table(
        "land_details",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "deal_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("deals.id", ondelete="CASCADE"),
            unique=True,
            nullable=False,
        ),
        sa.Column("acreage", sa.Numeric(10, 2), nullable=True),
        sa.Column("zoning", sa.String(100), nullable=True),
        sa.Column("entitled", sa.Boolean(), nullable=True),
        sa.Column("entitlement_status", sa.String(100), nullable=True),
        sa.Column("approved_density", sa.String(100), nullable=True),
        sa.Column("approved_use", sa.Text(), nullable=True),
        sa.Column("topography", sa.String(100), nullable=True),
        sa.Column(
            "utilities_available",
            postgresql.ARRAY(sa.String()),
            server_default="{}",
            nullable=True,
        ),
        sa.Column("environmental_status", sa.String(100), nullable=True),
        sa.Column("flood_zone", sa.String(50), nullable=True),
        sa.Column("development_timeline", sa.String(100), nullable=True),
        sa.Column("comparable_land_sales", sa.Text(), nullable=True),
        sa.Column("impact_fees", sa.Numeric(15, 2), nullable=True),
        sa.Column("infrastructure_costs", sa.Numeric(15, 2), nullable=True),
        sa.Column("absorption_projection", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    # ----- MIXED USE -----
    op.create_table(
        "mixed_use_details",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "deal_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("deals.id", ondelete="CASCADE"),
            unique=True,
            nullable=False,
        ),
        sa.Column(
            "component_types",
            postgresql.ARRAY(sa.String()),
            server_default="{}",
            nullable=True,
        ),
        sa.Column("retail_pct", sa.Numeric(5, 2), nullable=True),
        sa.Column("office_pct", sa.Numeric(5, 2), nullable=True),
        sa.Column("residential_pct", sa.Numeric(5, 2), nullable=True),
        sa.Column("parking_structure", sa.String(100), nullable=True),
        sa.Column(
            "shared_amenities",
            postgresql.ARRAY(sa.String()),
            server_default="{}",
            nullable=True,
        ),
        sa.Column("master_lease", sa.Boolean(), nullable=True),
        sa.Column("ground_floor_use", sa.String(100), nullable=True),
        sa.Column("synergy_description", sa.Text(), nullable=True),
        sa.Column("year_built", sa.Integer(), nullable=True),
        sa.Column("year_renovated", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    op.create_table(
        "mixed_use_components",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "deal_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("deals.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("component_type", sa.String(100), nullable=False),
        sa.Column("square_feet", sa.Integer(), nullable=True),
        sa.Column("noi", sa.Numeric(15, 2), nullable=True),
        sa.Column("occupancy", sa.Numeric(5, 2), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "idx_mixed_use_components_deal_id", "mixed_use_components", ["deal_id"]
    )

    # ================================================================
    # 8. DROP OLD TABLES
    # ================================================================
    op.drop_index("idx_tenants_property_id", table_name="tenants")
    op.drop_table("tenants")

    op.drop_index("idx_property_features_jsonb", table_name="property_features")
    op.drop_table("property_features")


def downgrade() -> None:
    # ================================================================
    # Reverse: recreate old tables
    # ================================================================
    op.create_table(
        "property_features",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "property_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("deals.id", ondelete="CASCADE"),
            unique=True,
            nullable=False,
        ),
        sa.Column("asset_type", sa.String(50), nullable=False),
        sa.Column(
            "features", postgresql.JSONB(), server_default="{}", nullable=False
        ),
        sa.Column("year_built", sa.Integer(), nullable=True),
        sa.Column("year_renovated", sa.Integer(), nullable=True),
        sa.Column("parking_spaces", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "idx_property_features_jsonb",
        "property_features",
        ["features"],
        postgresql_using="gin",
    )

    op.create_table(
        "tenants",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "property_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("deals.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("tenant_name", sa.String(255), nullable=False),
        sa.Column("square_feet", sa.Integer(), nullable=True),
        sa.Column("annual_rent", sa.Numeric(12, 2), nullable=True),
        sa.Column("lease_expiration", sa.String(50), nullable=True),
        sa.Column("tenant_type", sa.String(100), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("idx_tenants_property_id", "tenants", ["property_id"])

    # ================================================================
    # Reverse: drop asset-specific tables
    # ================================================================
    op.drop_index("idx_mixed_use_components_deal_id", table_name="mixed_use_components")
    op.drop_table("mixed_use_components")
    op.drop_table("mixed_use_details")

    op.drop_table("land_details")

    op.drop_index("idx_hotel_room_mix_deal_id", table_name="hotel_room_mix")
    op.drop_table("hotel_room_mix")
    op.drop_table("hotel_details")

    op.drop_table("student_housing_details")

    op.drop_index(
        "idx_self_storage_unit_mix_deal_id", table_name="self_storage_unit_mix"
    )
    op.drop_table("self_storage_unit_mix")
    op.drop_table("self_storage_details")

    op.drop_index("idx_office_tenants_deal_id", table_name="office_tenants")
    op.drop_table("office_tenants")
    op.drop_table("office_details")

    op.drop_index("idx_retail_tenants_deal_id", table_name="retail_tenants")
    op.drop_table("retail_tenants")
    op.drop_table("retail_details")

    op.drop_index(
        "idx_multifamily_unit_mix_deal_id", table_name="multifamily_unit_mix"
    )
    op.drop_table("multifamily_unit_mix")
    op.drop_table("multifamily_details")

    op.drop_index("idx_industrial_tenants_deal_id", table_name="industrial_tenants")
    op.drop_table("industrial_tenants")
    op.drop_table("industrial_details")

    # ================================================================
    # Reverse: drop deal structure tables
    # ================================================================
    op.drop_index("idx_reserves_deal_id", table_name="reserves")
    op.drop_table("reserves")
    op.drop_table("waterfall_structure")
    op.drop_table("sponsor_fees")

    # ================================================================
    # Reverse: remove new columns from child tables
    # ================================================================
    op.drop_column("annual_projections", "irr_through_year")
    op.drop_column("annual_projections", "cash_on_cash_return")

    op.drop_column("market_analysis", "landlord_pricing_power")
    op.drop_column("market_analysis", "absorption_rate")
    op.drop_column("market_analysis", "new_construction_pct")

    op.drop_column("investment_metrics", "return_profile")
    op.drop_column("investment_metrics", "return_from_sale_pct")
    op.drop_column("investment_metrics", "return_from_cash_flow_pct")

    # ================================================================
    # Reverse: rename hotel -> hospitality
    # ================================================================
    op.execute(
        "UPDATE deals SET deal_type = 'hospitality' WHERE deal_type = 'hotel'"
    )

    # ================================================================
    # Reverse: revert column widening
    # ================================================================
    op.alter_column(
        "deals",
        "purchase_price",
        existing_type=sa.Numeric(15, 2),
        type_=sa.Integer(),
        existing_nullable=True,
        postgresql_using="purchase_price::integer",
    )
    op.alter_column(
        "deals",
        "total_equity_required",
        existing_type=sa.Numeric(15, 2),
        type_=sa.Integer(),
        existing_nullable=True,
        postgresql_using="total_equity_required::integer",
    )

    # ================================================================
    # Reverse: remove new columns from deals
    # ================================================================
    op.drop_column("deals", "parking_spaces")
    op.drop_column("deals", "year_renovated")
    op.drop_column("deals", "year_built")
    op.drop_column("deals", "discount_to_replacement_pct")
    op.drop_column("deals", "replacement_cost_per_sf")
    op.drop_column("deals", "price_per_sf")

    # ================================================================
    # Reverse: rename deals -> properties
    # ================================================================
    op.execute("ALTER INDEX idx_deals_status RENAME TO idx_properties_status")
    op.execute("ALTER INDEX idx_deals_deal_type RENAME TO idx_properties_deal_type")
    op.rename_table("deals", "properties")
