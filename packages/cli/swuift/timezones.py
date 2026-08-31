"""IANA timezone validation and UTC/local conversion helpers."""

from __future__ import annotations

from datetime import datetime, timezone
from functools import lru_cache
from zoneinfo import (
    ZoneInfo,
    ZoneInfoNotFoundError,
    available_timezones,
    reset_tzpath,
)

UTC = timezone.utc
# Use the declared tzdata package on every operating system instead of allowing
# host-specific timezone databases to change the accepted catalog.
reset_tzpath(())


@lru_cache(maxsize=1)
def timezone_catalog() -> tuple[str, ...]:
    """Return every IANA timezone available to this SWUIFT installation."""
    return tuple(sorted(available_timezones() | {"UTC"}))


def validate_timezone(name: str) -> str:
    """Validate and return a normalized, non-empty IANA timezone name."""
    normalized = str(name).strip()
    if not normalized:
        raise ValueError("timezone is required; use an IANA name such as America/Denver")
    try:
        ZoneInfo(normalized)
    except ZoneInfoNotFoundError as exc:
        raise ValueError(
            f"Unknown IANA timezone {normalized!r}. "
            "Run `swuift --list-timezones` to list supported values."
        ) from exc
    return normalized


def local_to_utc(local_time: datetime, timezone_name: str) -> datetime:
    """Convert an unambiguous local wall time to a naive UTC datetime."""
    if local_time.tzinfo is not None:
        raise ValueError("Local simulation timestamps must not include a UTC offset.")
    name = validate_timezone(timezone_name)
    zone = ZoneInfo(name)
    fold_zero = local_time.replace(tzinfo=zone, fold=0)
    fold_one = local_time.replace(tzinfo=zone, fold=1)
    round_zero = fold_zero.astimezone(UTC).astimezone(zone)
    round_one = fold_one.astimezone(UTC).astimezone(zone)
    zero_matches = round_zero.replace(tzinfo=None) == local_time
    one_matches = round_one.replace(tzinfo=None) == local_time

    if not zero_matches and not one_matches:
        raise ValueError(
            f"{local_time.isoformat(sep=' ')} does not exist in {name} "
            "because of a daylight-saving transition."
        )
    if zero_matches and one_matches and fold_zero.utcoffset() != fold_one.utcoffset():
        raise ValueError(
            f"{local_time.isoformat(sep=' ')} is ambiguous in {name} "
            "because of a daylight-saving transition."
        )
    return fold_zero.astimezone(UTC).replace(tzinfo=None)


def utc_to_local(utc_time: datetime, timezone_name: str) -> datetime:
    """Convert a naive or UTC-aware datetime to an aware local datetime."""
    name = validate_timezone(timezone_name)
    if utc_time.tzinfo is None:
        aware_utc = utc_time.replace(tzinfo=UTC)
    else:
        aware_utc = utc_time.astimezone(UTC)
    return aware_utc.astimezone(ZoneInfo(name))


def utc_isoformat(utc_time: datetime) -> str:
    """Render a datetime as an explicit ISO-8601 UTC timestamp."""
    if utc_time.tzinfo is None:
        aware_utc = utc_time.replace(tzinfo=UTC)
    else:
        aware_utc = utc_time.astimezone(UTC)
    return aware_utc.isoformat().replace("+00:00", "Z")


def localized_timestamp(utc_time: datetime, timezone_name: str) -> dict[str, str]:
    """Return explicit UTC and local representations for metadata outputs."""
    local_time = utc_to_local(utc_time, timezone_name)
    compact_offset = local_time.strftime("%z")
    offset = f"{compact_offset[:3]}:{compact_offset[3:]}" if compact_offset else ""
    return {
        "utc": utc_isoformat(utc_time),
        "local": local_time.isoformat(),
        "timezone": validate_timezone(timezone_name),
        "offset": offset,
        "abbreviation": local_time.tzname() or "",
    }


def format_local_time(
    utc_time: datetime,
    timezone_name: str,
    *,
    format_string: str = "%Y/%m/%d %H:%M",
) -> str:
    """Format UTC simulation time for display with zone and offset."""
    local_time = utc_to_local(utc_time, timezone_name)
    offset = local_time.strftime("%z")
    rendered_offset = f"{offset[:3]}:{offset[3:]}" if offset else ""
    abbreviation = local_time.tzname() or timezone_name
    details = [f"UTC{rendered_offset}"] if rendered_offset else []
    if timezone_name != abbreviation:
        details.append(timezone_name)
    suffix = f"{abbreviation} ({'; '.join(details)})" if details else abbreviation
    return f"{local_time.strftime(format_string)} {suffix}".strip()
