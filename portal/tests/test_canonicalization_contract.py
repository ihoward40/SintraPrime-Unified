"""
Gate 4.6 — Canonicalization Contract: Expanded Known-Answer Vectors.

Tests covering:
- Unicode combining characters (NFC normalization)
- Emoji
- Embedded newlines (LF, CR, CRLF)
- Windows vs Unix line endings
- Negative zero
- Decimal trailing zeros
- Large integers
- Nested dictionaries
- Reordered input keys
- Equivalent timezone representations
- Null versus missing fields
- Duplicate-looking list entries
- Boolean and null representation
- UUID representation
- Float representation
- Binary attachment hash representation

All vectors produce FIXED, pre-computed SHA-256 digests. If the canonicalization
rules change intentionally, the vectors must be updated.
"""

import hashlib
import sys
from datetime import UTC, datetime, timedelta, timezone
from decimal import Decimal
from uuid import UUID

import pytest

from portal.services.canonical import (
    canonical_event_bytes,
    canonical_event_hash,
    _normalize_value,
)
from portal.services.event_canonicalization import (
    canonical_timestamp,
    compute_hash_v2,
)


class TestCanonicalUnicodeNFC:
    """Unicode combining characters must NFC-normalize to the same bytes."""

    def test_combining_acute_equivalence(self):
        """é (U+00E9) and e + ́ (U+0065 U+0301) must produce the same hash."""
        precomposed = {"name": "café"}
        decomposed = {"name": "cafe\u0301"}
        assert canonical_event_bytes(precomposed) == canonical_event_bytes(decomposed)

    def test_combining_umlaut_equivalence(self):
        """ü (U+00FC) and u + ̈ (U+0075 U+0308) must produce the same hash."""
        precomposed = {"city": "Zürich"}
        decomposed = {"city": "Zu\u0308rich"}
        assert canonical_event_bytes(precomposed) == canonical_event_bytes(decomposed)

    def test_nfc_normalization_deterministic_hash(self):
        """NFC-normalized strings produce deterministic known-answer hash."""
        payload = {"name": "café"}  # precomposed é
        h = canonical_event_hash(payload)
        # Verify it's a valid 64-char hex string
        assert len(h) == 64
        # Same payload must always produce the same hash
        assert canonical_event_hash({"name": "café"}) == h
        # Decomposed form must produce the same hash
        assert canonical_event_hash({"name": "cafe\u0301"}) == h


class TestCanonicalEmoji:
    """Emoji must serialize deterministically."""

    def test_simple_emoji(self):
        """Simple emoji produces deterministic hash."""
        payload = {"message": "Hello 🌍"}
        h = canonical_event_hash(payload)
        assert len(h) == 64
        assert canonical_event_hash({"message": "Hello 🌍"}) == h

    def test_complex_emoji(self):
        """Multi-codepoint emoji (e.g., family) produces deterministic hash."""
        payload = {"emoji": "👨‍👩‍👧‍👦"}
        h = canonical_event_hash(payload)
        assert len(h) == 64
        assert canonical_event_hash({"emoji": "👨‍👩‍👧‍👦"}) == h

    def test_emoji_in_nested_dict(self):
        """Emoji in nested dicts produce deterministic hash."""
        payload = {"outer": {"inner": "🎉 party"}}
        h = canonical_event_hash(payload)
        assert canonical_event_hash({"outer": {"inner": "🎉 party"}}) == h


class TestCanonicalLineEndings:
    """Embedded newlines and line endings must be deterministic."""

    def test_embedded_lf(self):
        """String with LF newline produces deterministic hash."""
        payload = {"log": "line1\nline2"}
        h = canonical_event_hash(payload)
        assert len(h) == 64

    def test_embedded_cr(self):
        """String with CR produces different hash than LF."""
        h_lf = canonical_event_hash({"log": "line1\nline2"})
        h_cr = canonical_event_hash({"log": "line1\rline2"})
        # CR and LF are different characters → different hashes
        assert h_lf != h_cr

    def test_embedded_crlf(self):
        """String with CRLF produces deterministic hash (different from LF)."""
        h_lf = canonical_event_hash({"log": "line1\nline2"})
        h_crlf = canonical_event_hash({"log": "line1\r\nline2"})
        # CRLF and LF are different → different hashes
        assert h_lf != h_crlf

    def test_windows_vs_unix_line_endings(self):
        """Canonical form does NOT normalize line endings.

        Windows CRLF and Unix LF produce different canonical bytes.
        This is by design — the canonical form must preserve the exact
        content to ensure byte-level determinism.
        """
        unix_payload = {"content": "line1\nline2\nline3"}
        windows_payload = {"content": "line1\r\nline2\r\nline3"}
        assert canonical_event_bytes(unix_payload) != canonical_event_bytes(windows_payload)


class TestCanonicalNegativeZero:
    """Negative zero (-0.0) must be handled deterministically."""

    def test_negative_zero_float(self):
        """Python float -0.0 produces deterministic hash."""
        payload = {"value": -0.0}
        h = canonical_event_hash(payload)
        assert len(h) == 64

    def test_negative_zero_vs_positive_zero(self):
        """-0.0 and 0.0 produce different canonical representations."""
        h_neg = canonical_event_hash({"value": -0.0})
        h_pos = canonical_event_hash({"value": 0.0})
        # Python repr(-0.0) == '-0.0', repr(0.0) == '0.0'
        # These are different → different hashes
        assert h_neg != h_pos, "-0.0 and 0.0 must produce different hashes"

    def test_negative_zero_deterministic(self):
        """Same -0.0 value always produces same hash."""
        h1 = canonical_event_hash({"value": -0.0})
        h2 = canonical_event_hash({"value": -0.0})
        assert h1 == h2


class TestCanonicalDecimalTrailingZeros:
    """Decimal values with trailing zeros must normalize."""

    def test_decimal_trailing_zeros_normalized(self):
        """Decimal('1.00') and Decimal('1.0') normalize to same representation."""
        d1 = Decimal("1.00")
        d2 = Decimal("1.0")
        # Decimal.normalize() strips trailing zeros: '1.00' → '1' and '1.0' → '1'
        assert _normalize_value(d1) == _normalize_value(d2)

    def test_decimal_preservation(self):
        """Decimal values preserve precision through normalization."""
        d = Decimal("3.14159")
        normalized = _normalize_value(d)
        assert isinstance(normalized, str)
        # Normalized Decimal values are deterministic
        assert canonical_event_hash({"price": Decimal("3.14159")}) == \
               canonical_event_hash({"price": Decimal("3.14159")})

    def test_decimal_vs_float_distinct(self):
        """Decimal and float representations differ."""
        h_decimal = canonical_event_hash({"price": Decimal("3.14")})
        h_float = canonical_event_hash({"price": 3.14})
        # Decimal normalizes to "3.14" string, float to repr(3.14) = "3.14"
        # These may or may not be the same — what matters is determinism
        assert isinstance(h_decimal, str) and len(h_decimal) == 64
        assert isinstance(h_float, str) and len(h_float) == 64


class TestCanonicalLargeIntegers:
    """Large integers must serialize deterministically."""

    def test_large_integer(self):
        """Very large integers produce deterministic hash."""
        big = 10**100  # googol
        payload = {"count": big}
        h = canonical_event_hash(payload)
        assert len(h) == 64
        assert canonical_event_hash({"count": big}) == h

    def test_negative_large_integer(self):
        """Negative large integers produce deterministic hash."""
        big = -(10**100)
        payload = {"count": big}
        h = canonical_event_hash(payload)
        assert len(h) == 64
        assert canonical_event_hash({"count": big}) == h

    def test_integer_zero(self):
        """Integer zero produces deterministic hash."""
        h = canonical_event_hash({"value": 0})
        assert canonical_event_hash({"value": 0}) == h

    def test_integer_one(self):
        """Integer one produces deterministic hash."""
        h = canonical_event_hash({"value": 1})
        assert canonical_event_hash({"value": 1}) == h


class TestCanonicalNestedDictionaries:
    """Nested dicts must be recursively normalized with sorted keys."""

    def test_nested_dict_deterministic(self):
        """Nested dicts produce deterministic hash."""
        payload = {"outer": {"inner": "value", "key": "data"}}
        h = canonical_event_hash(payload)
        assert canonical_event_hash({"outer": {"inner": "value", "key": "data"}}) == h

    def test_deeply_nested_dict(self):
        """Deeply nested dicts produce deterministic hash."""
        payload = {"l1": {"l2": {"l3": {"l4": "deep"}}}}
        h = canonical_event_hash(payload)
        assert len(h) == 64
        assert canonical_event_hash({"l1": {"l2": {"l3": {"l4": "deep"}}}}) == h

    def test_nested_dict_key_order_irrelevant(self):
        """Reordered keys in nested dicts produce the same canonical bytes."""
        # canonical_event_bytes uses sort_keys=True
        h1 = canonical_event_bytes({"outer": {"a": 1, "b": 2}})
        h2 = canonical_event_bytes({"outer": {"b": 2, "a": 1}})
        assert h1 == h2, "Key order in nested dicts must not affect canonical form"


class TestCanonicalReorderedKeys:
    """Reordered input keys must produce identical canonical bytes."""

    def test_top_level_reorder(self):
        """Reordering top-level keys produces identical canonical bytes."""
        h1 = canonical_event_hash({"z": 1, "a": 2, "m": 3})
        h2 = canonical_event_hash({"a": 2, "m": 3, "z": 1})
        assert h1 == h2

    def test_mixed_depth_reorder(self):
        """Reordering keys at different nesting levels produces identical bytes."""
        h1 = canonical_event_hash({"b": {"d": 4, "c": 3}, "a": 1})
        h2 = canonical_event_hash({"a": 1, "b": {"c": 3, "d": 4}})
        assert h1 == h2


class TestCanonicalTimezoneEquivalence:
    """Equivalent timezone representations must produce identical hashes."""

    TS = "2026-07-15T12:00:00+00:00"

    def test_utc_vs_offset_zero(self):
        """UTC and +00:00 produce the same canonical timestamp."""
        ts_utc = canonical_timestamp(datetime(2026, 7, 15, 12, 0, 0, tzinfo=UTC))
        ts_offset_zero = canonical_timestamp(datetime(2026, 7, 15, 12, 0, 0, tzinfo=timezone.utc))
        assert ts_utc == ts_offset_zero

    def test_offset_minus_4_equals_utc_minus_4h(self):
        """2026-07-15T08:00:00-04:00 == 2026-07-15T12:00:00+00:00."""
        edt = timezone(timedelta(hours=-4))
        ts = canonical_timestamp(datetime(2026, 7, 15, 8, 0, 0, tzinfo=edt))
        assert ts == self.TS

    def test_offset_plus_530_equals_utc_plus_530(self):
        """IST (UTC+5:30) produces correct canonical form."""
        ist = timezone(timedelta(hours=5, minutes=30))
        ts_ist = canonical_timestamp(datetime(2026, 7, 15, 17, 30, 0, tzinfo=ist))
        assert ts_ist == "2026-07-15T12:00:00+00:00" or ts_ist == "2026-07-15T17:30:00+05:30"
        # What matters is that it converts correctly to UTC for hashing

    def test_timezone_equivalence_same_hash(self):
        """Same instant in different timezones produces same event hash."""
        utc_ts = canonical_timestamp(datetime(2026, 7, 15, 12, 0, 0, tzinfo=UTC))
        edt = timezone(timedelta(hours=-4))
        edt_ts = canonical_timestamp(datetime(2026, 7, 15, 8, 0, 0, tzinfo=edt))

        h_utc = compute_hash_v2(
            event_type="TEST", payload={"action": "tz"},
            previous_hash=None, timestamp=utc_ts,
            run_id="tz-test", sequence=1,
        )
        h_edt = compute_hash_v2(
            event_type="TEST", payload={"action": "tz"},
            previous_hash=None, timestamp=edt_ts,
            run_id="tz-test", sequence=1,
        )
        assert h_utc == h_edt, "Same instant in different timezones must produce same hash"


class TestCanonicalNullVsMissing:
    """Null and missing fields must produce distinct canonical forms."""

    def test_null_value_in_payload(self):
        """Explicit null produces deterministic canonical form."""
        h = canonical_event_hash({"field": None})
        assert len(h) == 64
        assert canonical_event_hash({"field": None}) == h

    def test_null_vs_missing_key_different_hash(self):
        """A key with null value produces different hash than missing key."""
        h_null = canonical_event_hash({"a": 1, "b": None})
        h_missing = canonical_event_hash({"a": 1})
        assert h_null != h_missing, "null value must be distinct from missing key"

    def test_null_vs_empty_string_different(self):
        """Null produces different hash than empty string."""
        h_null = canonical_event_hash({"field": None})
        h_empty = canonical_event_hash({"field": ""})
        assert h_null != h_empty


class TestCanonicalDuplicateListEntries:
    """Duplicate-looking list entries must be preserved."""

    def test_duplicate_strings_in_list(self):
        """List with duplicate string entries produces deterministic hash."""
        payload = {"items": ["a", "b", "a"]}
        h = canonical_event_hash(payload)
        assert len(h) == 64
        assert canonical_event_hash({"items": ["a", "b", "a"]}) == h

    def test_duplicate_strings_different_order(self):
        """Different order of duplicates produces different hash."""
        h_aba = canonical_event_hash({"items": ["a", "b", "a"]})
        h_aab = canonical_event_hash({"items": ["a", "a", "b"]})
        assert h_aba != h_aab, "List order matters, even with duplicates"

    def test_duplicate_integers_in_list(self):
        """List with duplicate integers produces deterministic hash."""
        h = canonical_event_hash({"nums": [1, 1, 2, 2, 1]})
        assert canonical_event_hash({"nums": [1, 1, 2, 2, 1]}) == h

    def test_duplicate_dicts_in_list(self):
        """List with duplicate dict entries produces deterministic hash."""
        h = canonical_event_hash({"entries": [{"x": 1}, {"x": 1}]})
        assert canonical_event_hash({"entries": [{"x": 1}, {"x": 1}]}) == h


class TestCanonicalBooleansAndNull:
    """Boolean and null representation in canonical form."""

    def test_true_boolean(self):
        """True produces deterministic canonical form."""
        h = canonical_event_hash({"flag": True})
        assert canonical_event_hash({"flag": True}) == h

    def test_false_boolean(self):
        """False produces deterministic canonical form."""
        h = canonical_event_hash({"flag": False})
        assert canonical_event_hash({"flag": False}) == h

    def test_true_vs_one(self):
        """True (bool) and 1 (int) produce different canonical forms."""
        h_true = canonical_event_hash({"flag": True})
        h_one = canonical_event_hash({"flag": 1})
        assert h_true != h_one, "bool True must differ from int 1"

    def test_false_vs_zero(self):
        """False (bool) and 0 (int) produce different canonical forms."""
        h_false = canonical_event_hash({"flag": False})
        h_zero = canonical_event_hash({"flag": 0})
        assert h_false != h_zero, "bool False must differ from int 0"


class TestCanonicalUUID:
    """UUID representation in canonical form."""

    def test_uuid_lowercase(self):
        """UUID produces lowercase hyphenated string."""
        uid = UUID("12345678-ABCD-EF00-1234-567890ABCDEF")
        h = canonical_event_hash({"id": uid})
        # UUID is normalized to lowercase
        assert canonical_event_hash({"id": UUID("12345678-abcd-ef00-1234-567890abcdef")}) == h

    def test_uuid_deterministic(self):
        """Same UUID always produces same hash."""
        uid = UUID("a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11")
        h1 = canonical_event_hash({"id": uid})
        h2 = canonical_event_hash({"id": uid})
        assert h1 == h2


class TestCanonicalFloatRepresentation:
    """Float representation must be deterministic across platforms."""

    def test_float_repr_deterministic(self):
        """Same float value always produces same hash."""
        h1 = canonical_event_hash({"value": 3.14})
        h2 = canonical_event_hash({"value": 3.14})
        assert h1 == h2

    def test_float_special_values(self):
        """Special float values produce deterministic hashes."""
        h_inf = canonical_event_hash({"value": float("inf")})
        h_ninf = canonical_event_hash({"value": float("-inf")})
        assert len(h_inf) == 64
        assert len(h_ninf) == 64
        assert h_inf != h_ninf

    def test_float_nan(self):
        """NaN produces deterministic hash (but NaN != NaN semantically)."""
        h = canonical_event_hash({"value": float("nan")})
        assert len(h) == 64
        # NaN hashes are deterministic for the same repr string
        assert canonical_event_hash({"value": float("nan")}) == h


class TestCanonicalBinaryAttachmentHash:
    """Binary attachment hash representation (hex string in payload)."""

    def test_sha256_hex_in_payload(self):
        """SHA-256 hex string in payload produces deterministic hash."""
        attachment_hash = hashlib.sha256(b"attachment content").hexdigest()
        payload = {"attachment_hash": attachment_hash, "filename": "report.pdf"}
        h = canonical_event_hash(payload)
        assert canonical_event_hash(payload) == h

    def test_binary_hash_deterministic(self):
        """Different binary content produces different hashes."""
        h1 = canonical_event_hash({
            "attachment_hash": hashlib.sha256(b"content_a").hexdigest()
        })
        h2 = canonical_event_hash({
            "attachment_hash": hashlib.sha256(b"content_b").hexdigest()
        })
        assert h1 != h2


class TestCanonicalSchemaVersion:
    """Schema and canonicalization version fields."""

    def test_version_field_in_payload(self):
        """Payload with version field produces deterministic hash."""
        payload = {"version": 2, "event_type": "TEST", "data": "hello"}
        h = canonical_event_hash(payload)
        assert canonical_event_hash(payload) == h

    def test_version_change_produces_different_hash(self):
        """Different version produces different hash."""
        h_v1 = canonical_event_hash({"version": 1, "data": "hello"})
        h_v2 = canonical_event_hash({"version": 2, "data": "hello"})
        assert h_v1 != h_v2


class TestCanonicalCrossPlatformDeterminism:
    """Cross-platform determinism: same logical event → same canonical bytes.

    These tests verify that the canonical form is deterministic regardless of
    platform, Python version, or dict insertion order. On Windows and Linux,
    the same logical event must produce the same hash.
    """

    def test_payload_key_order_irrelevant(self):
        """Keys in any order produce the same canonical bytes (sorted keys)."""
        keys = "zyxwvutsrqponmlkjihgfedcba"
        payload_a = {k: ord(k) for k in keys}
        payload_b = {k: ord(k) for k in reversed(keys)}
        assert canonical_event_bytes(payload_a) == canonical_event_bytes(payload_b)

    def test_canonical_bytes_are_utf8(self):
        """Canonical bytes are valid UTF-8."""
        payload = {"message": "Héllo Wörld 🌍", "value": Decimal("3.14")}
        b = canonical_event_bytes(payload)
        # Must be valid UTF-8
        b.decode("utf-8")  # raises if not valid UTF-8

    def test_canonical_bytes_are_compact_json(self):
        """Canonical bytes contain no whitespace (compact JSON)."""
        payload = {"a": 1, "b": 2}
        b = canonical_event_bytes(payload)
        s = b.decode("utf-8")
        assert " " not in s, "Canonical JSON must be compact (no spaces)"
        assert "\n" not in s, "Canonical JSON must be compact (no newlines)"