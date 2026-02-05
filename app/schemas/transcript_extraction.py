"""Schemas for extracting investor insights from call transcripts."""

from typing import List, Optional

from pydantic import BaseModel, Field


class ExtractedInvestorProfile(BaseModel):
    """Extracted fields for investor_profiles table."""

    name: Optional[str] = Field(
        None, description="Investor's name if mentioned during the call"
    )
    timeline: Optional[str] = Field(
        None,
        description="Investment timeline: '0-3 months', '3-6 months', '6-12 months', '12+ months'",
    )
    capital_available: Optional[int] = Field(
        None,
        description="Capital amount in USD if a specific dollar amount was mentioned",
    )
    investment_preferences: List[str] = Field(
        default_factory=list,
        description="Property types mentioned: industrial, multifamily, office, retail, self-storage",
    )
    investment_thesis: Optional[str] = Field(
        None, description="Brief summary of their investment goals and motivations"
    )
    risk_tolerance: Optional[str] = Field(
        None, description="Risk tolerance level: conservative, moderate, aggressive"
    )


class ExtractedInvestorPreferences(BaseModel):
    """Extracted fields for investor_preferences table."""

    property_types: List[str] = Field(
        default_factory=list,
        description="Property types: industrial, multifamily, office, retail, self-storage, mixed-use",
    )
    preferred_markets: List[str] = Field(
        default_factory=list,
        description="Cities or metro areas they want to invest in",
    )
    excluded_markets: List[str] = Field(
        default_factory=list,
        description="Cities or areas they explicitly want to avoid",
    )
    risk_tolerance_level: Optional[str] = Field(
        None, description="Risk tolerance: conservative, moderate, or aggressive"
    )
    investment_strategy: Optional[str] = Field(
        None, description="Strategy: core, core_plus, value_add, or opportunistic"
    )
    hold_period_min: Optional[int] = Field(
        None, description="Minimum hold period in years"
    )
    hold_period_max: Optional[int] = Field(
        None, description="Maximum hold period in years"
    )
    investment_experience: Optional[str] = Field(
        None,
        description="Experience level: first_time, some_experience, experienced, or sophisticated",
    )
    specific_concerns: Optional[str] = Field(
        None, description="Any specific concerns or requirements mentioned"
    )
    preferred_structures: List[str] = Field(
        default_factory=list,
        description="Deal structures mentioned: LP, GP, JV, REIT, DST",
    )
    target_irr_min: Optional[float] = Field(
        None, description="Minimum target IRR percentage (e.g., 12.0 for 12%)"
    )
    target_irr_max: Optional[float] = Field(
        None, description="Maximum target IRR percentage (e.g., 18.0 for 18%)"
    )


class TranscriptInsightExtraction(BaseModel):
    """Complete extraction result from a call transcript."""

    profile_updates: ExtractedInvestorProfile = Field(
        ..., description="Updates for the investor_profiles table"
    )
    preferences_updates: ExtractedInvestorPreferences = Field(
        ..., description="Updates for the investor_preferences table"
    )
    confidence_score: float = Field(
        ..., ge=0, le=1, description="Overall confidence in extraction quality (0-1)"
    )
    call_summary: str = Field(
        ..., description="Brief summary of the call for admin review"
    )
    key_discussion_points: List[str] = Field(
        default_factory=list, description="Key topics discussed during the call"
    )
    follow_up_items: List[str] = Field(
        default_factory=list, description="Items requiring follow-up action"
    )
    extraction_notes: Optional[str] = Field(
        None, description="Notes about extraction quality or any issues encountered"
    )
