"""Compatibility shims so one build runs on Home Assistant 2026.8 and 2026.9+.

Home Assistant 2026.9 replaced ``voluptuous_serialize`` with ``probatio``. The two
expose the same call shape, so pick whichever the running core ships.
"""

try:
    from probatio import to_field_list  # HA 2026.9+
except ImportError:  # pragma: no cover - exercised only on HA <= 2026.8
    from voluptuous_serialize import convert as to_field_list

__all__ = ["to_field_list"]
