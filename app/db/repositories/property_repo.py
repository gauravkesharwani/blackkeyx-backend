"""Property/Deal repository."""

import uuid
from typing import List, Optional, Sequence, Tuple

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.repositories.base import BaseRepository
from app.models.financial import AnnualProjection, Financing, InvestmentMetrics, Tenant
from app.models.market import MarketAnalysis
from app.models.property import Property, PropertyDocument, PropertyFeature
from app.schemas.extraction import InvestorBriefExtraction


class PropertyRepository(BaseRepository[Property]):
    """Repository for property/deal operations."""

    def __init__(self, session: AsyncSession):
        super().__init__(Property, session)

    async def get_with_features(self, id: uuid.UUID) -> Optional[Property]:
        """Get property with features loaded."""
        result = await self.session.execute(
            select(Property)
            .options(selectinload(Property.features))
            .where(Property.id == id)
        )
        return result.scalar_one_or_none()

    async def get_by_status(
        self, status: str, skip: int = 0, limit: int = 100
    ) -> Sequence[Property]:
        """Get all properties with a specific status."""
        result = await self.session.execute(
            select(Property)
            .where(Property.status == status)
            .order_by(Property.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all()

    async def get_active_deals(
        self, skip: int = 0, limit: int = 100
    ) -> Tuple[Sequence[Property], int]:
        """Get all active deals with total count."""
        # Count total active
        count_result = await self.session.execute(
            select(func.count())
            .select_from(Property)
            .where(Property.status == "active")
        )
        total = count_result.scalar_one()

        # Get deals
        result = await self.session.execute(
            select(Property)
            .where(Property.status == "active")
            .order_by(Property.created_at.desc())
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
    ) -> Tuple[Sequence[Property], int]:
        """
        Search deals with filters.
        Returns (deals, total_count).
        """
        query = select(Property)

        if status:
            query = query.where(Property.status == status)
        if deal_type:
            query = query.where(Property.deal_type == deal_type)
        if min_investment_max is not None:
            query = query.where(Property.minimum_investment <= min_investment_max)
        if search:
            query = query.where(
                Property.name.ilike(f"%{search}%")
                | Property.summary.ilike(f"%{search}%")
            )

        # Count total
        count_query = select(func.count()).select_from(query.subquery())
        count_result = await self.session.execute(count_query)
        total = count_result.scalar_one()

        # Order and paginate
        query = query.order_by(Property.created_at.desc()).offset(skip).limit(limit)

        result = await self.session.execute(query)
        deals = result.scalars().all()

        return deals, total

    async def create_with_features(
        self,
        property_data: dict,
        features_data: Optional[dict] = None,
    ) -> Property:
        """Create a property with optional features."""
        property_obj = Property(**property_data)
        self.session.add(property_obj)
        await self.session.flush()

        if features_data:
            features = PropertyFeature(
                property_id=property_obj.id,
                **features_data,
            )
            self.session.add(features)
            await self.session.flush()

        await self.session.refresh(property_obj)
        return property_obj

    async def update_status(
        self, id: uuid.UUID, status: str
    ) -> Optional[Property]:
        """Update property status."""
        property_obj = await self.get(id)
        if not property_obj:
            return None

        property_obj.status = status
        await self.session.flush()
        await self.session.refresh(property_obj)

        return property_obj

    async def create_with_extraction(
        self,
        extraction: InvestorBriefExtraction,
        document_s3_key: Optional[str] = None,
        document_filename: Optional[str] = None,
    ) -> Property:
        """
        Create a property with all related data from extraction.

        This method saves:
        - Property (main record)
        - InvestmentMetrics (if available)
        - Financing (if available)
        - Tenants (if available)
        - AnnualProjections (if available)
        - MarketAnalysis (if available)
        - PropertyDocument (if document info provided)
        """
        # Build target return string from available metrics
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

        # Create the main Property record
        property_id = uuid.uuid4()
        property_obj = Property(
            id=property_id,
            name=extraction.deal_name,
            deal_type=extraction.property_type,
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
            # Financial
            total_equity_required=int(extraction.equity_required) if extraction.equity_required else None,
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
        self.session.add(property_obj)
        await self.session.flush()

        # Create InvestmentMetrics if available
        if extraction.investment_metrics:
            metrics = extraction.investment_metrics
            investment_metrics = InvestmentMetrics(
                id=uuid.uuid4(),
                property_id=property_id,
                target_irr_min=metrics.target_irr_min,
                target_irr_max=metrics.target_irr_max,
                target_equity_multiple=metrics.target_equity_multiple,
                target_cash_on_cash=metrics.target_cash_on_cash,
                cap_rate_going_in=metrics.cap_rate_going_in,
                cap_rate_exit=metrics.cap_rate_exit,
                preferred_return=metrics.preferred_return,
            )
            self.session.add(investment_metrics)

        # Create Financing if available
        if extraction.financing:
            fin = extraction.financing
            financing = Financing(
                id=uuid.uuid4(),
                property_id=property_id,
                loan_amount=fin.loan_amount,
                ltv_ratio=fin.ltv_ratio,
                interest_rate=fin.interest_rate,
                loan_term_years=fin.loan_term_years,
                amortization_years=fin.amortization_years,
                lender_name=fin.lender_name,
                loan_type=fin.loan_type,
            )
            self.session.add(financing)

        # Create Tenants if available
        if extraction.major_tenants:
            for tenant_data in extraction.major_tenants:
                tenant = Tenant(
                    id=uuid.uuid4(),
                    property_id=property_id,
                    tenant_name=tenant_data.tenant_name,
                    square_feet=tenant_data.square_feet,
                    annual_rent=tenant_data.annual_rent,
                    lease_expiration=tenant_data.lease_expiration,
                    tenant_type=tenant_data.tenant_type,
                )
                self.session.add(tenant)

        # Create AnnualProjections if available
        if extraction.annual_projections:
            for proj_data in extraction.annual_projections:
                projection = AnnualProjection(
                    id=uuid.uuid4(),
                    property_id=property_id,
                    year=proj_data.year,
                    gross_revenue=proj_data.gross_revenue,
                    effective_gross_income=proj_data.effective_gross_income,
                    operating_expenses=proj_data.operating_expenses,
                    noi=proj_data.noi,
                    cash_flow=proj_data.cash_flow,
                )
                self.session.add(projection)

        # Create MarketAnalysis if available
        if extraction.market_analysis:
            market = extraction.market_analysis
            market_analysis = MarketAnalysis(
                id=uuid.uuid4(),
                property_id=property_id,
                market_name=market.market_name,
                submarket=market.submarket,
                population_growth=market.population_growth,
                employment_drivers=market.employment_drivers or [],
                market_vacancy_rate=market.market_vacancy_rate,
                market_rent_growth=market.market_rent_growth,
                comparable_sales=market.comparable_sales,
            )
            self.session.add(market_analysis)

        # Create PropertyDocument if document info provided
        if document_s3_key and document_filename:
            property_document = PropertyDocument(
                id=uuid.uuid4(),
                property_id=property_id,
                s3_key=document_s3_key,
                filename=document_filename,
                extraction_status="completed",
            )
            self.session.add(property_document)

        await self.session.flush()
        await self.session.refresh(property_obj)
        return property_obj

    async def get_with_all_relations(self, id: uuid.UUID) -> Optional[Property]:
        """Get property with all related data loaded."""
        result = await self.session.execute(
            select(Property)
            .options(
                selectinload(Property.features),
                selectinload(Property.investment_metrics),
                selectinload(Property.financing),
                selectinload(Property.tenants),
                selectinload(Property.annual_projections),
                selectinload(Property.market_analysis),
            )
            .where(Property.id == id)
        )
        return result.scalar_one_or_none()
