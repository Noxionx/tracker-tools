from __future__ import annotations

import re

from app.core.http import DEFAULT_USER_AGENT

BYTE_UNITS = {
    "b": 1,
    "kb": 10**3,
    "mb": 10**6,
    "gb": 10**9,
    "tb": 10**12,
    "pb": 10**15,
    "kib": 2**10,
    "mib": 2**20,
    "gib": 2**30,
    "tib": 2**40,
    "pib": 2**50,
}


def parse_bytes(value: str | int | float | None) -> float:
    """Convert a numeric string with optional byte unit to bytes."""

    if value is None:
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)

    normalized = value.strip().replace("\u00a0", " ")
    if not normalized:
        return 0.0

    match = re.match(r"^([0-9]+(?:[.,][0-9]+)?)\s*([A-Za-z]{0,3})$", normalized)
    if not match:
        return 0.0

    number = float(match.group(1).replace(",", "."))
    unit = (match.group(2) or "b").lower()
    multiplier = BYTE_UNITS.get(unit, BYTE_UNITS["b"])
    return number * multiplier


__all__ = ["DEFAULT_USER_AGENT", "parse_bytes"]
