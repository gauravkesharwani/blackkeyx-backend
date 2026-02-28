"""Timezone inference utilities for callback scheduling."""

import logging
from typing import Optional
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import phonenumbers
from phonenumbers import timezone as pn_timezone

logger = logging.getLogger(__name__)

# Map common colloquial timezone names to IANA
_COLLOQUIAL_MAP: dict[str, str] = {
    "eastern": "America/New_York",
    "et": "America/New_York",
    "est": "America/New_York",
    "edt": "America/New_York",
    "central": "America/Chicago",
    "ct": "America/Chicago",
    "cst": "America/Chicago",
    "cdt": "America/Chicago",
    "mountain": "America/Denver",
    "mt": "America/Denver",
    "mst": "America/Denver",
    "mdt": "America/Denver",
    "pacific": "America/Los_Angeles",
    "pt": "America/Los_Angeles",
    "pst": "America/Los_Angeles",
    "pdt": "America/Los_Angeles",
    "alaska": "America/Anchorage",
    "hawaii": "Pacific/Honolulu",
}

DEFAULT_TIMEZONE = "America/New_York"


def _normalize_tz(tz: str) -> Optional[str]:
    """Normalise a timezone string to IANA, returning None if invalid."""
    stripped = tz.strip()
    # Try colloquial first
    iana = _COLLOQUIAL_MAP.get(stripped.lower())
    if iana:
        return iana
    # Try as-is (already IANA)
    try:
        ZoneInfo(stripped)
        return stripped
    except (ZoneInfoNotFoundError, KeyError):
        return None


def infer_timezone_from_phone(phone: str) -> Optional[str]:
    """Infer IANA timezone from an E.164 phone number using area code."""
    try:
        parsed = phonenumbers.parse(phone, "US")
        timezones = pn_timezone.time_zones_for_number(parsed)
        if timezones:
            return list(timezones)[0]
    except phonenumbers.NumberParseException:
        logger.debug(f"Could not parse phone number for timezone inference: {phone}")
    return None


def get_investor_timezone(
    explicit_tz: Optional[str],
    phone: Optional[str],
) -> str:
    """
    Resolve the investor's timezone using a priority chain:
    1. Explicit timezone from investor profile (confirmed during call)
    2. Inferred from phone number area code
    3. Fallback to America/New_York
    """
    if explicit_tz:
        iana = _normalize_tz(explicit_tz)
        if iana:
            return iana
        logger.warning(f"Invalid timezone on profile: {explicit_tz!r}, falling back")

    if phone:
        inferred = infer_timezone_from_phone(phone)
        if inferred:
            return inferred

    return DEFAULT_TIMEZONE
