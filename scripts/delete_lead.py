#!/usr/bin/env python3
"""
Script to delete a lead and all its related data by phone number.

Usage:
    python scripts/delete_lead.py +1234567890
    python scripts/delete_lead.py +1234567890 --dry-run
    python scripts/delete_lead.py +1234567890 --force
"""

import argparse
import asyncio
import os
import sys
from pathlib import Path

# Add the parent directory to path so we can import app modules
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

# Change to backend directory so .env file is found
os.chdir(backend_dir)

from sqlalchemy import delete, select, func
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from app.config import get_settings
from app.models.investor import InvestorPreferences, InvestorProfile
from app.models.consent import LeadNote, StageHistory, Consent
from app.models.embeddings import InvestorEmbedding
from app.models.matching import DealMatch
from app.models.voice import CallbackRequest, CallSession, CallTranscript


async def get_lead_by_phone(session: AsyncSession, phone: str) -> InvestorProfile | None:
    """Find a lead by phone number."""
    result = await session.execute(
        select(InvestorProfile).where(InvestorProfile.phone == phone)
    )
    return result.scalar_one_or_none()


async def count_related_records(session: AsyncSession, investor_id: str) -> dict:
    """Count all related records for a lead."""
    counts = {}

    # Count call transcripts (via call_sessions)
    call_session_ids = await session.execute(
        select(CallSession.id).where(CallSession.investor_id == investor_id)
    )
    session_ids = [row[0] for row in call_session_ids.fetchall()]

    if session_ids:
        transcript_count = await session.execute(
            select(func.count()).where(CallTranscript.call_session_id.in_(session_ids))
        )
        counts['call_transcripts'] = transcript_count.scalar() or 0
    else:
        counts['call_transcripts'] = 0

    # Count call sessions
    call_count = await session.execute(
        select(func.count()).where(CallSession.investor_id == investor_id)
    )
    counts['call_sessions'] = call_count.scalar() or 0

    # Count deal matches
    match_count = await session.execute(
        select(func.count()).where(DealMatch.investor_id == investor_id)
    )
    counts['deal_matches'] = match_count.scalar() or 0

    # Count consents
    consent_count = await session.execute(
        select(func.count()).where(Consent.investor_id == investor_id)
    )
    counts['consents'] = consent_count.scalar() or 0

    # Count stage history
    history_count = await session.execute(
        select(func.count()).where(StageHistory.investor_id == investor_id)
    )
    counts['stage_history'] = history_count.scalar() or 0

    # Count lead notes
    notes_count = await session.execute(
        select(func.count()).where(LeadNote.investor_id == investor_id)
    )
    counts['lead_notes'] = notes_count.scalar() or 0

    # Count callback requests
    callback_count = await session.execute(
        select(func.count()).where(CallbackRequest.investor_id == investor_id)
    )
    counts['callback_requests'] = callback_count.scalar() or 0

    # Count investor preferences
    prefs_count = await session.execute(
        select(func.count()).where(InvestorPreferences.investor_id == investor_id)
    )
    counts['investor_preferences'] = prefs_count.scalar() or 0

    # Count investor embeddings
    embedding_count = await session.execute(
        select(func.count()).where(InvestorEmbedding.investor_id == investor_id)
    )
    counts['investor_embeddings'] = embedding_count.scalar() or 0

    return counts


async def delete_lead_data(session: AsyncSession, investor_id: str) -> dict:
    """Delete all data related to a lead. Returns counts of deleted records."""
    deleted = {}

    # 1. Delete call transcripts (via call_sessions)
    call_session_ids = await session.execute(
        select(CallSession.id).where(CallSession.investor_id == investor_id)
    )
    session_ids = [row[0] for row in call_session_ids.fetchall()]

    if session_ids:
        result = await session.execute(
            delete(CallTranscript).where(CallTranscript.call_session_id.in_(session_ids))
        )
        deleted['call_transcripts'] = result.rowcount
    else:
        deleted['call_transcripts'] = 0

    # 2. Delete callback requests (must precede call_sessions — FK to both tables)
    result = await session.execute(
        delete(CallbackRequest).where(CallbackRequest.investor_id == investor_id)
    )
    deleted['callback_requests'] = result.rowcount

    # 3. Delete call sessions
    result = await session.execute(
        delete(CallSession).where(CallSession.investor_id == investor_id)
    )
    deleted['call_sessions'] = result.rowcount

    # 4. Delete deal matches
    result = await session.execute(
        delete(DealMatch).where(DealMatch.investor_id == investor_id)
    )
    deleted['deal_matches'] = result.rowcount

    # 5. Delete consents
    result = await session.execute(
        delete(Consent).where(Consent.investor_id == investor_id)
    )
    deleted['consents'] = result.rowcount

    # 6. Delete stage history
    result = await session.execute(
        delete(StageHistory).where(StageHistory.investor_id == investor_id)
    )
    deleted['stage_history'] = result.rowcount

    # 7. Delete lead notes
    result = await session.execute(
        delete(LeadNote).where(LeadNote.investor_id == investor_id)
    )
    deleted['lead_notes'] = result.rowcount

    # 8. Delete investor preferences
    result = await session.execute(
        delete(InvestorPreferences).where(InvestorPreferences.investor_id == investor_id)
    )
    deleted['investor_preferences'] = result.rowcount

    # 9. Delete investor embeddings
    result = await session.execute(
        delete(InvestorEmbedding).where(InvestorEmbedding.investor_id == investor_id)
    )
    deleted['investor_embeddings'] = result.rowcount

    # 10. Delete the lead itself
    result = await session.execute(
        delete(InvestorProfile).where(InvestorProfile.id == investor_id)
    )
    deleted['investor_profiles'] = result.rowcount

    return deleted


async def main(phone: str, dry_run: bool = False, force: bool = False) -> int:
    """Main function to delete a lead by phone number."""
    settings = get_settings()

    engine = create_async_engine(settings.async_database_url)
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        # Find the lead
        lead = await get_lead_by_phone(session, phone)

        if not lead:
            print(f"Error: No lead found with phone number: {phone}")
            return 1

        print(f"\nFound lead:")
        print(f"  ID:    {lead.id}")
        print(f"  Name:  {lead.name}")
        print(f"  Phone: {lead.phone}")
        print(f"  Stage: {lead.stage}")
        print(f"  Score: {lead.lead_score}")
        print(f"  Created: {lead.created_at}")

        # Count related records
        counts = await count_related_records(session, lead.id)

        print(f"\nRelated records to be deleted:")
        total = 0
        for table, count in counts.items():
            print(f"  {table}: {count}")
            total += count
        print(f"  ---")
        print(f"  Total related records: {total}")
        print(f"  + 1 investor_profiles record")

        if dry_run:
            print(f"\n[DRY RUN] No data was deleted.")
            return 0

        # Confirm deletion
        if not force:
            print(f"\nAre you sure you want to delete this lead and all related data?")
            response = input("Type 'yes' to confirm: ")
            if response.lower() != 'yes':
                print("Aborted.")
                return 1

        # Perform deletion
        try:
            deleted = await delete_lead_data(session, lead.id)
            await session.commit()

            print(f"\nSuccessfully deleted:")
            for table, count in deleted.items():
                print(f"  {table}: {count}")

            print(f"\nLead {phone} and all related data have been deleted.")
            return 0

        except Exception as e:
            await session.rollback()
            print(f"\nError during deletion: {e}")
            return 1

    await engine.dispose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Delete a lead and all related data by phone number"
    )
    parser.add_argument(
        "phone",
        help="Phone number of the lead to delete (e.g., +1234567890)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be deleted without actually deleting"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Skip confirmation prompt"
    )

    args = parser.parse_args()

    exit_code = asyncio.run(main(args.phone, args.dry_run, args.force))
    sys.exit(exit_code)
