"""Deal repository (formerly Property repository)."""

import logging
import uuid
from typing import List, Optional, Sequence, Tuple

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

logger = logging.getLogger(__name__)

from app.db.repositories.base import BaseRepository
from app.models.asset_types import (
    HotelDetails,
    HotelRoomMix,
    IndustrialDetails,
    IndustrialTenant,
    LandDetails,
    MixedUseComponent,
    MixedUseDetails,
    MultifamilyDetails,
    MultifamilyUnitMix,
    OfficeDetails,
    OfficeTenant,
    RetailDetails,
    RetailTenant,
    SelfStorageDetails,
    SelfStorageUnitMix,
    StudentHousingDetails,
)
from app.models.deal_structure import Reserve, SponsorFees, WaterfallStructure
from app.models.financial import AnnualProjection, Financing, InvestmentMetrics
from app.models.market import MarketAnalysis
from app.models.property import Deal, PropertyDocument
from app.schemas.extraction import InvestorBriefExtraction

# Backward compat alias
Property = Deal


class PropertyRepository(BaseRepository[Deal]):
    """Repository for deal operations."""

    def __init__(self, session: AsyncSession):
        super().__init__(Deal, session)

    async def get_by_status(
        self, status: str, skip: int = 0, limit: int = 100
    ) -> Sequence[Deal]:
        """Get all deals with a specific status."""
        result = await self.session.execute(
            select(Deal)
            .where(Deal.status == status)
            .order_by(Deal.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all()

    async def get_active_deals(
        self, skip: int = 0, limit: int = 100
    ) -> Tuple[Sequence[Deal], int]:
        """Get all active deals with total count."""
        count_result = await self.session.execute(
            select(func.count())
            .select_from(Deal)
            .where(Deal.status == "active")
        )
        total = count_result.scalar_one()

        result = await self.session.execute(
            select(Deal)
            .where(Deal.status == "active")
            .order_by(Deal.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        deals = result.scalars().all()

        return deals, total

    async def search_deals(
        self,
        status: Optional[str] = None,
        deal_type: Optional[str] = None,
        min_investment_max: Optional[int] = None,
        search: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> Tuple[Sequence[Deal], int]:
        """Search deals with filters."""
        query = select(Deal)

        if status:
            query = query.where(Deal.status == status)
        if deal_type:
            query = query.where(Deal.deal_type == deal_type)
        if min_investment_max is not None:
            query = query.where(Deal.minimum_investment <= min_investment_max)
        if search:
            query = query.where(
                Deal.name.ilike(f"%{search}%")
                | Deal.summary.ilike(f"%{search}%")
            )

        count_query = select(func.count()).select_from(query.subquery())
        count_result = await self.session.execute(count_query)
        total = count_result.scalar_one()

        query = query.order_by(Deal.created_at.desc()).offset(skip).limit(limit)

        result = await self.session.execute(query)
        deals = result.scalars().all()

        return deals, total

    async def update_status(
        self, id: uuid.UUID, status: str
    ) -> Optional[Deal]:
        """Update deal status."""
        deal = await self.get(id)
        if not deal:
            return None

        deal.status = status
        await self.session.flush()
        await self.session.refresh(deal)
        return deal

    async def create_with_extraction(
        self,
        extraction: InvestorBriefExtraction,
        document_s3_key: Optional[str] = None,
        document_filename: Optional[str] = None,
        deal_type: Optional[str] = None,
    ) -> Deal:
        """
        Create a deal with all related data from extraction.

        Saves: Deal, InvestmentMetrics, Financing, AnnualProjections,
        MarketAnalysis, SponsorFees, WaterfallStructure, Reserves,
        asset-specific details/tenants, and PropertyDocument.
        """
        deal_name = extraction.deal_name
        logger.info(f"Saving deal '{deal_name}' with extraction data")

        # Build target return string
        target_return_parts = []
        if extraction.investment_metrics:
            metrics = extraction.investment_metrics
            if metrics.target_irr_min and metrics.target_irr_max:
                target_return_parts.append(f"{metrics.target_irr_min}-{metrics.target_irr_max}% IRR")
            elif metrics.target_irr_min:
                target_return_parts.append(f"{metrics.target_irr_min}% IRR")
            elif metrics.target_irr_max:
                target_return_parts.append(f"{metrics.target_irr_max}% IRR")
            if metrics.target_equity_multiple:
                target_return_parts.append(f"{metrics.target_equity_multiple}x Equity Multiple")
            if metrics.target_cash_on_cash:
                target_return_parts.append(f"{metrics.target_cash_on_cash}% CoC")
            if metrics.preferred_return:
                target_return_parts.append(f"{metrics.preferred_return}% Pref")
        target_return = ", ".join(target_return_parts) if target_return_parts else "TBD"

        # Create the main Deal record
        deal_id = uuid.uuid4()
        deal = Deal(
            id=deal_id,
            name=extraction.deal_name,
            deal_type=deal_type or extraction.property_type,
            summary=extraction.executive_summary,
            thesis=extraction.investment_thesis,
            minimum_investment=extraction.minimum_investment,
            target_return=target_return,
            risk_factors=extraction.risk_factors or [],
            ideal_investor_profile=extraction.ideal_investor_profile,
            structure=extraction.deal_structure,
            timeline=extraction.hold_period_years,
            status="active",
            # Location from property_details
            address=extraction.property_details.address if extraction.property_details else None,
            city=extraction.property_details.city if extraction.property_details else None,
            state=extraction.property_details.state if extraction.property_details else None,
            zip_code=extraction.property_details.zip_code if extraction.property_details else None,
            square_feet=extraction.property_details.total_square_feet if extraction.property_details else None,
            year_built=extraction.property_details.year_built if extraction.property_details else None,
            year_renovated=extraction.property_details.year_renovated if extraction.property_details else None,
            parking_spaces=extraction.property_details.parking_spaces if extraction.property_details else None,
            # Financial
            purchase_price=extraction.purchase_price,
            price_per_sf=extraction.price_per_sf,
            replacement_cost_per_sf=extraction.replacement_cost_per_sf,
            discount_to_replacement_pct=extraction.discount_to_replacement_pct,
            total_equity_required=extraction.equity_required,
            total_capitalization=extraction.total_capitalization,
            # Strategy and sponsor
            value_add_strategy=extraction.value_add_strategy,
            sponsor_name=extraction.sponsor_name,
            sponsor_track_record=extraction.sponsor_track_record,
            # Extraction metadata
            extraction_confidence=extraction.confidence_score,
            extraction_notes=extraction.extraction_notes,
            # Document reference
            document_s3_key=document_s3_key,
            document_filename=document_filename,
        )
        self.session.add(deal)
        await self.session.flush()

        # === COMMON RELATED DATA ===

        # InvestmentMetrics
        if extraction.investment_metrics:
            m = extraction.investment_metrics
            self.session.add(InvestmentMetrics(
                id=uuid.uuid4(),
                property_id=deal_id,
                target_irr_min=m.target_irr_min,
                target_irr_max=m.target_irr_max,
                target_equity_multiple=m.target_equity_multiple,
                target_cash_on_cash=m.target_cash_on_cash,
                cap_rate_going_in=m.cap_rate_going_in,
                cap_rate_exit=m.cap_rate_exit,
                preferred_return=m.preferred_return,
                return_from_cash_flow_pct=m.return_from_cash_flow_pct,
                return_from_sale_pct=m.return_from_sale_pct,
                return_profile=m.return_profile,
            ))

        # Financing
        if extraction.financing:
            f = extraction.financing
            self.session.add(Financing(
                id=uuid.uuid4(),
                property_id=deal_id,
                loan_amount=f.loan_amount,
                ltv_ratio=f.ltv_ratio,
                interest_rate=f.interest_rate,
                loan_term_years=f.loan_term_years,
                amortization_years=f.amortization_years,
                lender_name=f.lender_name,
                loan_type=f.loan_type,
            ))

        # AnnualProjections
        for proj in extraction.annual_projections:
            self.session.add(AnnualProjection(
                id=uuid.uuid4(),
                property_id=deal_id,
                year=proj.year,
                gross_revenue=proj.gross_revenue,
                effective_gross_income=proj.effective_gross_income,
                operating_expenses=proj.operating_expenses,
                noi=proj.noi,
                cash_flow=proj.cash_flow,
                cash_on_cash_return=proj.cash_on_cash_return,
                irr_through_year=proj.irr_through_year,
            ))

        # MarketAnalysis
        if extraction.market_analysis:
            ma = extraction.market_analysis
            self.session.add(MarketAnalysis(
                id=uuid.uuid4(),
                property_id=deal_id,
                market_name=ma.market_name,
                submarket=ma.submarket,
                population_growth=ma.population_growth,
                employment_drivers=ma.employment_drivers or [],
                market_vacancy_rate=ma.market_vacancy_rate,
                market_rent_growth=ma.market_rent_growth,
                comparable_sales=ma.comparable_sales,
                new_construction_pct=ma.new_construction_pct,
                absorption_rate=ma.absorption_rate,
                landlord_pricing_power=ma.landlord_pricing_power,
            ))

        # SponsorFees
        if extraction.sponsor_fees:
            sf = extraction.sponsor_fees
            self.session.add(SponsorFees(
                id=uuid.uuid4(),
                deal_id=deal_id,
                acquisition_fee_pct=sf.acquisition_fee_pct,
                acquisition_fee_amount=sf.acquisition_fee_amount,
                asset_management_fee_pct=sf.asset_management_fee_pct,
                property_management_fee_pct=sf.property_management_fee_pct,
                construction_supervision_fee_pct=sf.construction_supervision_fee_pct,
                disposition_fee_pct=sf.disposition_fee_pct,
                guarantee_fee_pct=sf.guarantee_fee_pct,
            ))

        # WaterfallStructure
        if extraction.waterfall_structure:
            ws = extraction.waterfall_structure
            self.session.add(WaterfallStructure(
                id=uuid.uuid4(),
                deal_id=deal_id,
                preferred_return_pct=ws.preferred_return_pct,
                promote_tier_1_pct=ws.promote_tier_1_pct,
                promote_tier_1_hurdle=ws.promote_tier_1_hurdle,
                promote_tier_2_pct=ws.promote_tier_2_pct,
                promote_tier_2_hurdle=ws.promote_tier_2_hurdle,
                sponsor_coinvest_pct=ws.sponsor_coinvest_pct,
                sponsor_coinvest_amount=ws.sponsor_coinvest_amount,
            ))

        # Reserves
        for r in extraction.reserves:
            self.session.add(Reserve(
                id=uuid.uuid4(),
                deal_id=deal_id,
                reserve_type=r.reserve_type,
                reserve_amount=r.reserve_amount,
                reserve_purpose=r.reserve_purpose,
                release_conditions=r.release_conditions,
                lender_controlled=r.lender_controlled,
            ))

        # === ASSET-SPECIFIC DATA ===
        self._save_asset_specific_data(deal_id, extraction)

        # PropertyDocument
        if document_s3_key and document_filename:
            self.session.add(PropertyDocument(
                id=uuid.uuid4(),
                property_id=deal_id,
                s3_key=document_s3_key,
                filename=document_filename,
                extraction_status="completed",
            ))

        try:
            await self.session.flush()
        except Exception as e:
            logger.error(
                f"Database error while saving deal '{deal_name}' (id={deal_id}): {e}",
                exc_info=True,
            )
            raise
        await self.session.refresh(deal)
        logger.info(f"Successfully saved deal '{deal_name}' (id={deal_id})")
        return deal

    def _save_asset_specific_data(
        self, deal_id: uuid.UUID, extraction: InvestorBriefExtraction
    ) -> None:
        """Save asset-type-specific details and tenants from extraction."""
        # Industrial
        if hasattr(extraction, "industrial_details") and extraction.industrial_details:
            d = extraction.industrial_details
            self.session.add(IndustrialDetails(
                id=uuid.uuid4(), deal_id=deal_id,
                clear_height_min=d.clear_height_min, clear_height_max=d.clear_height_max,
                loading_docks=d.loading_docks, drive_in_doors=d.drive_in_doors,
                dock_height=d.dock_height, truck_court_depth=d.truck_court_depth,
                column_spacing=d.column_spacing, rail_access=d.rail_access,
                power_amps=d.power_amps, power_voltage=d.power_voltage,
                crane_capacity=d.crane_capacity, sprinkler_system=d.sprinkler_system,
                office_pct=d.office_pct, trailer_parking=d.trailer_parking,
                cross_dock=d.cross_dock, freezer_cooler_sf=d.freezer_cooler_sf,
                year_built=d.year_built, year_renovated=d.year_renovated,
            ))
        if hasattr(extraction, "industrial_tenants"):
            for t in extraction.industrial_tenants:
                self.session.add(IndustrialTenant(
                    id=uuid.uuid4(), deal_id=deal_id,
                    tenant_name=t.tenant_name, square_feet=t.square_feet,
                    annual_rent=t.annual_rent, rent_per_sf=t.rent_per_sf,
                    lease_start=t.lease_start, lease_expiration=t.lease_expiration,
                    renewal_options=t.renewal_options, renewal_option_terms=t.renewal_option_terms,
                    credit_rating=t.credit_rating, years_at_location=t.years_at_location,
                    is_mission_critical=t.is_mission_critical, distance_from_hq=t.distance_from_hq,
                    tenant_type=t.tenant_type,
                ))

        # Multifamily
        if hasattr(extraction, "multifamily_details") and extraction.multifamily_details:
            d = extraction.multifamily_details
            self.session.add(MultifamilyDetails(
                id=uuid.uuid4(), deal_id=deal_id,
                unit_count=d.unit_count, avg_unit_size=d.avg_unit_size,
                avg_rent_per_unit=d.avg_rent_per_unit, avg_rent_per_sf=d.avg_rent_per_sf,
                in_place_occupancy=d.in_place_occupancy, market_rent_per_unit=d.market_rent_per_unit,
                loss_to_lease_pct=d.loss_to_lease_pct, amenities=d.amenities,
                washer_dryer=d.washer_dryer, vintage=d.vintage,
                recent_renovations=d.recent_renovations, renovation_premium=d.renovation_premium,
                concessions=d.concessions, turnover_rate=d.turnover_rate,
                expense_ratio=d.expense_ratio, year_built=d.year_built,
                year_renovated=d.year_renovated,
            ))
        if hasattr(extraction, "multifamily_unit_mix"):
            for u in extraction.multifamily_unit_mix:
                self.session.add(MultifamilyUnitMix(
                    id=uuid.uuid4(), deal_id=deal_id,
                    unit_type=u.unit_type, unit_count=u.unit_count,
                    avg_sf=u.avg_sf, current_rent=u.current_rent,
                    market_rent=u.market_rent,
                ))

        # Retail
        if hasattr(extraction, "retail_details") and extraction.retail_details:
            d = extraction.retail_details
            self.session.add(RetailDetails(
                id=uuid.uuid4(), deal_id=deal_id,
                gla=d.gla, anchor_pct_gla=d.anchor_pct_gla,
                inline_tenant_count=d.inline_tenant_count, avg_inline_rent_psf=d.avg_inline_rent_psf,
                cam_rate_psf=d.cam_rate_psf, percentage_rent_tenants=d.percentage_rent_tenants,
                traffic_count=d.traffic_count, sales_psf=d.sales_psf,
                parking_ratio=d.parking_ratio, pad_sites=d.pad_sites,
                outparcels=d.outparcels, grocery_anchored=d.grocery_anchored,
                nnn_vs_gross=d.nnn_vs_gross, below_market_leases=d.below_market_leases,
                year_built=d.year_built, year_renovated=d.year_renovated,
            ))
        if hasattr(extraction, "retail_tenants"):
            for t in extraction.retail_tenants:
                self.session.add(RetailTenant(
                    id=uuid.uuid4(), deal_id=deal_id,
                    tenant_name=t.tenant_name, tenant_category=t.tenant_category,
                    square_feet=t.square_feet, annual_rent=t.annual_rent,
                    rent_per_sf=t.rent_per_sf, lease_expiration=t.lease_expiration,
                    renewal_options=t.renewal_options, percentage_rent=t.percentage_rent,
                    sales_psf=t.sales_psf, co_tenancy_clause=t.co_tenancy_clause,
                ))

        # Office
        if hasattr(extraction, "office_details") and extraction.office_details:
            d = extraction.office_details
            self.session.add(OfficeDetails(
                id=uuid.uuid4(), deal_id=deal_id,
                building_class=d.building_class, floor_count=d.floor_count,
                typical_floor_plate=d.typical_floor_plate, nra=d.nra,
                tenant_count=d.tenant_count, walt_years=d.walt_years,
                avg_rent_psf_nnn=d.avg_rent_psf_nnn, avg_rent_psf_fsg=d.avg_rent_psf_fsg,
                ti_allowance_psf=d.ti_allowance_psf, parking_ratio=d.parking_ratio,
                building_amenities=d.building_amenities, leed_certification=d.leed_certification,
                energy_star_score=d.energy_star_score, largest_tenant_pct=d.largest_tenant_pct,
                near_term_expirations_pct=d.near_term_expirations_pct, sublease_space_sf=d.sublease_space_sf,
                year_built=d.year_built, year_renovated=d.year_renovated,
            ))
        if hasattr(extraction, "office_tenants"):
            for t in extraction.office_tenants:
                self.session.add(OfficeTenant(
                    id=uuid.uuid4(), deal_id=deal_id,
                    tenant_name=t.tenant_name, square_feet=t.square_feet,
                    annual_rent=t.annual_rent, rent_per_sf=t.rent_per_sf,
                    lease_start=t.lease_start, lease_expiration=t.lease_expiration,
                    renewal_options=t.renewal_options, ti_allowance=t.ti_allowance,
                    credit_rating=t.credit_rating,
                ))

        # Self Storage
        if hasattr(extraction, "self_storage_details") and extraction.self_storage_details:
            d = extraction.self_storage_details
            self.session.add(SelfStorageDetails(
                id=uuid.uuid4(), deal_id=deal_id,
                total_units=d.total_units, net_rentable_sf=d.net_rentable_sf,
                climate_controlled_pct=d.climate_controlled_pct, climate_controlled_units=d.climate_controlled_units,
                drive_up_units=d.drive_up_units, avg_rent_per_sf=d.avg_rent_per_sf,
                economic_occupancy=d.economic_occupancy, physical_occupancy=d.physical_occupancy,
                management_platform=d.management_platform, rv_boat_parking=d.rv_boat_parking,
                avg_length_of_stay=d.avg_length_of_stay, street_rate_growth=d.street_rate_growth,
                ecri_potential=d.ecri_potential, year_built=d.year_built,
                year_renovated=d.year_renovated,
            ))
        if hasattr(extraction, "self_storage_unit_mix"):
            for u in extraction.self_storage_unit_mix:
                self.session.add(SelfStorageUnitMix(
                    id=uuid.uuid4(), deal_id=deal_id,
                    unit_size=u.unit_size, unit_count=u.unit_count,
                    rate_per_unit=u.rate_per_unit, occupancy_pct=u.occupancy_pct,
                    climate_controlled=u.climate_controlled,
                ))

        # Student Housing
        if hasattr(extraction, "student_housing_details") and extraction.student_housing_details:
            d = extraction.student_housing_details
            self.session.add(StudentHousingDetails(
                id=uuid.uuid4(), deal_id=deal_id,
                total_beds=d.total_beds, total_units=d.total_units,
                beds_per_unit_avg=d.beds_per_unit_avg, rent_per_bed=d.rent_per_bed,
                rent_per_unit=d.rent_per_unit, distance_to_campus=d.distance_to_campus,
                affiliated_university=d.affiliated_university, university_enrollment=d.university_enrollment,
                preleasing_pct=d.preleasing_pct, preleasing_velocity=d.preleasing_velocity,
                amenities=d.amenities, furnished=d.furnished,
                utilities_included=d.utilities_included, individual_leases=d.individual_leases,
                on_campus_competition=d.on_campus_competition, year_built=d.year_built,
                year_renovated=d.year_renovated,
            ))

        # Hotel
        if hasattr(extraction, "hotel_details") and extraction.hotel_details:
            d = extraction.hotel_details
            self.session.add(HotelDetails(
                id=uuid.uuid4(), deal_id=deal_id,
                room_count=d.room_count, avg_room_size=d.avg_room_size,
                adr=d.adr, revpar=d.revpar, occupancy_rate=d.occupancy_rate,
                franchise_brand=d.franchise_brand, franchise_expiration=d.franchise_expiration,
                management_company=d.management_company, fnb_revenue=d.fnb_revenue,
                fnb_pct=d.fnb_pct, meeting_space_sf=d.meeting_space_sf,
                star_rating=d.star_rating, trip_advisor_score=d.trip_advisor_score,
                pip_required=d.pip_required, pip_cost=d.pip_cost,
                goppar=d.goppar, comp_set_penetration=d.comp_set_penetration,
                year_built=d.year_built, year_renovated=d.year_renovated,
            ))
        if hasattr(extraction, "hotel_room_mix"):
            for r in extraction.hotel_room_mix:
                self.session.add(HotelRoomMix(
                    id=uuid.uuid4(), deal_id=deal_id,
                    room_type=r.room_type, room_count=r.room_count,
                    avg_size_sf=r.avg_size_sf, rate=r.rate,
                ))

        # Land
        if hasattr(extraction, "land_details") and extraction.land_details:
            d = extraction.land_details
            self.session.add(LandDetails(
                id=uuid.uuid4(), deal_id=deal_id,
                acreage=d.acreage, zoning=d.zoning, entitled=d.entitled,
                entitlement_status=d.entitlement_status, approved_density=d.approved_density,
                approved_use=d.approved_use, topography=d.topography,
                utilities_available=d.utilities_available, environmental_status=d.environmental_status,
                flood_zone=d.flood_zone, development_timeline=d.development_timeline,
                comparable_land_sales=d.comparable_land_sales, impact_fees=d.impact_fees,
                infrastructure_costs=d.infrastructure_costs, absorption_projection=d.absorption_projection,
            ))

        # Mixed Use
        if hasattr(extraction, "mixed_use_details") and extraction.mixed_use_details:
            d = extraction.mixed_use_details
            self.session.add(MixedUseDetails(
                id=uuid.uuid4(), deal_id=deal_id,
                component_types=d.component_types, retail_pct=d.retail_pct,
                office_pct=d.office_pct, residential_pct=d.residential_pct,
                parking_structure=d.parking_structure, shared_amenities=d.shared_amenities,
                master_lease=d.master_lease, ground_floor_use=d.ground_floor_use,
                synergy_description=d.synergy_description, year_built=d.year_built,
                year_renovated=d.year_renovated,
            ))
        if hasattr(extraction, "mixed_use_components"):
            for c in extraction.mixed_use_components:
                self.session.add(MixedUseComponent(
                    id=uuid.uuid4(), deal_id=deal_id,
                    component_type=c.component_type, square_feet=c.square_feet,
                    noi=c.noi, occupancy=c.occupancy,
                ))

    async def get_with_all_relations(self, id: uuid.UUID) -> Optional[Deal]:
        """Get deal with all related data loaded."""
        result = await self.session.execute(
            select(Deal)
            .options(
                selectinload(Deal.investment_metrics),
                selectinload(Deal.financing),
                selectinload(Deal.annual_projections),
                selectinload(Deal.market_analysis),
                selectinload(Deal.sponsor_fees),
                selectinload(Deal.waterfall_structure),
                selectinload(Deal.reserves),
            )
            .where(Deal.id == id)
        )
        deal = result.scalar_one_or_none()

        if deal:
            # Load asset-specific relations based on deal_type
            await self._load_asset_specific_relations(deal)

        return deal

    async def _load_asset_specific_relations(self, deal: Deal) -> None:
        """Eagerly load asset-specific relationships based on deal_type."""
        dt = deal.deal_type
        load_map = {
            "industrial": [Deal.industrial_details, Deal.industrial_tenants],
            "multifamily": [Deal.multifamily_details, Deal.multifamily_unit_mix],
            "retail": [Deal.retail_details, Deal.retail_tenants],
            "office": [Deal.office_details, Deal.office_tenants],
            "self-storage": [Deal.self_storage_details, Deal.self_storage_unit_mix],
            "student-housing": [Deal.student_housing_details],
            "hotel": [Deal.hotel_details, Deal.hotel_room_mix],
            "land": [Deal.land_details],
            "mixed-use": [Deal.mixed_use_details, Deal.mixed_use_components],
        }

        relations = load_map.get(dt, [])
        if relations:
            options = [selectinload(rel) for rel in relations]
            result = await self.session.execute(
                select(Deal).options(*options).where(Deal.id == deal.id)
            )
            # The selectinload will populate the relationships on the existing deal
            result.scalar_one_or_none()
