"""Shared helpers for ÖkOfen absolute-datetime fields (Party endzeit, Urlaub start/ende).

The device's own web client (app.min.js, DateTimeDecorator) stores these
fields as a Unix timestamp that represents *local* wall-clock time, but
computed as if that wall-clock time were UTC (i.e. it does not apply any
further timezone shift beyond what's already baked into the value). In
other words: `datetime.utcfromtimestamp(raw_value)` gives you the local
time shown on the device's touch panel directly, with no additional
timezone math needed.
"""
from datetime import datetime, timezone
from typing import Any, Optional

from homeassistant.util import dt as dt_util


def device_seconds_to_datetime(value: Any) -> Optional[datetime]:
    """Convert the device's raw timestamp value to a timezone-aware UTC datetime."""
    try:
        raw = float(value)
    except (TypeError, ValueError):
        return None
    if raw <= 0:
        return None
    naive_local = datetime.utcfromtimestamp(raw)
    aware_local = naive_local.replace(tzinfo=dt_util.DEFAULT_TIME_ZONE)
    return dt_util.as_utc(aware_local)


def datetime_to_device_seconds(value: datetime) -> int:
    """Convert a (possibly timezone-aware) datetime back to the device's raw format."""
    local_dt = dt_util.as_local(value)
    naive_local = local_dt.replace(tzinfo=None)
    return int(naive_local.replace(tzinfo=timezone.utc).timestamp())
