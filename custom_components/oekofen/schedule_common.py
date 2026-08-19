"""Shared helpers for ÖkOfen weekly time-program (Zeitprogramm) entities.

The device's own weekday indexing was confirmed against a live device:
tag[0] = Sunday ... tag[6] = Saturday (NOT the usual Monday-first order).
Each weekday can hold up to 3 independent start/end time blocks
(zeitreihe[0..2]), and a "block" value of -1 means the day is disabled.
"""
from datetime import time as dt_time
from typing import Any, Dict, List, Optional

# Device's own weekday indexing: 0=Sunday .. 6=Saturday
DAY_NAMES = ["Sonntag", "Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag"]
DAY_ABBR = ["So", "Mo", "Di", "Mi", "Do", "Fr", "Sa"]

CIRCUIT_LABELS = {
    "hk": "Heizkreis",
    "ww": "Warmwasser",
    "zirkp": "Zirkulationspumpe",
}

PROGRAM_LABELS = {0: "Zeit 1", 1: "Zeit 2"}

BLOCKS_PER_DAY = 3


def build_schedule_slots(circuits: Dict[str, List[int]]) -> List[Dict[str, Any]]:
    """Build one entry per (circuit type, index, program, weekday) that exists."""
    slots: List[Dict[str, Any]] = []
    for circuit_type, label in CIRCUIT_LABELS.items():
        for idx in circuits.get(circuit_type, []):
            for program in (0, 1):
                for day in range(7):
                    base = (
                        f"CAPPL:LOCAL.{circuit_type}[{idx}]"
                        f".zeitprogramm[{program}].tag[{day}]"
                    )
                    slots.append(
                        {
                            "circuit_type": circuit_type,
                            "circuit_index": idx,
                            "program": program,
                            "day": day,
                            "base": base,
                            "key": f"{circuit_type}{idx}_zeit{program + 1}_{DAY_ABBR[day]}",
                            "label": f"{label} {idx + 1} {PROGRAM_LABELS[program]} {DAY_NAMES[day]}",
                        }
                    )
    return slots


def seconds_to_time(value: Any) -> Optional[dt_time]:
    """Convert the device's "seconds since midnight" value to a time object."""
    try:
        total = int(float(value))
    except (TypeError, ValueError):
        return None
    total = max(0, min(total, 86399))
    hours, remainder = divmod(total, 3600)
    minutes, seconds = divmod(remainder, 60)
    return dt_time(hour=hours, minute=minutes, second=seconds)


def time_to_seconds(value: dt_time) -> int:
    """Convert a time object back to "seconds since midnight" for the device."""
    return value.hour * 3600 + value.minute * 60 + value.second
