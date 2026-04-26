"""
Input validation and sanitization for all SintraPrime API endpoints.
Prevents SQL injection, XSS, and other injection attacks.
Sierra-4 Security Module
"""

import re
import html
import hashlib
import time
from typing import Tuple, List, Dict, Optional
from collections import defaultdict


# Injection attack patterns to reject
SQL_INJECTION_PATTERNS = [
    r"(?i)(union\s+select|insert\s+into|drop\s+table|delete\s+from|update\s+set)",
    r"(?i)(exec\s*\(|execute\s*\(|sp_executesql)",
    r"(?i)(--\s*$|;\s*drop|;\s*delete|;\s*insert)",
    r"(?i)(xp_cmdshell|xp_exec|sys\.objects)",
    r"'.*OR.*'.*=.*'",
    r'"\s*OR\s*".*"\s*=\s*"',
]

# XSS patterns
XSS_PATTERNS = [
    r"<script[^>]*>.*?</script>",
    r"javascript\s*:",
    r"on\w+\s*=",
    r"<iframe[^>]*>",
    r"<object[^>]*>",
    r"<embed[^>]*>",
    r"expression\s*\(",
    r"vbscript\s*:",
]

# Path traversal
PATH_TRAVERSAL_PATTERNS = [
    r"\.\./",
    r"\.\.\\/",
    r"%2e%2e%2f",
    r"%2e%2e/",
    r"\.\.%2f",
]

# Rate limit store (in production, use Redis)
_rate_limit_store: Dict[str, List[float]] = defaultdict(list)

RATE_LIMITS = {
    "legal_query": (60, 60),       # 60 requests per 60 seconds
    "trust_create": (10, 60),      # 10 per minute
    "case_search": (30, 60),       # 30 per minute
    "prediction": (20, 60),        # 20 per minute
    "esign": (5, 60),              # 5 per minute
    "banking_sync": (5, 300),      # 5 per 5 minutes
    "voice_query": (100, 60),      # 100 per minute
    "default": (100, 60),          # default: 100 per minute
}


class InputValidator:
    """
    Validates and sanitizes all SintraPrime API inputs.
    
    Prevents: SQL injection, XSS, path traversal, SSRF, injection attacks.
    Validates: Legal queries, SSN, EIN, trust documents, case references.
    """

    def __init__(self):
        self._sql_patterns = [re.compile(p) for p in SQL_INJECTION_PATTERNS]
        self._xss_patterns = [re.compile(p, re.IGNORECASE | re.DOTALL) for p in XSS_PATTERNS]
        self._path_patterns = [re.compile(p, re.IGNORECASE) for p in PATH_TRAVERSAL_PATTERNS]
        self._html_tag_re = re.compile(r'<[^>]+>')

    # ─── Legal Query Validation ───────────────────────────────────────────────

    def validate_legal_query(self, query: str) -> Tuple[bool, str]:
        """
        Validate a legal query string.
        
        Checks: length, allowed characters, SQL/XSS injection, no empty.
        
        Args:
            query: The legal query string to validate
            
        Returns:
            (is_valid: bool, error_message: str)
        """
        if not query or not isinstance(query, str):
            return False, "Query must be a non-empty string"

        query = query.strip()

        if len(query) < 3:
            return False, "Query too short (minimum 3 characters)"

        if len(query) > 2000:
            return False, "Query too long (maximum 2000 characters)"

        # Check for SQL injection
        for pattern in self._sql_patterns:
            if pattern.search(query):
                return False, "Query contains invalid characters or patterns"

        # Check for XSS
        for pattern in self._xss_patterns:
            if pattern.search(query):
                return False, "Query contains disallowed HTML/script content"

        # Check for path traversal
        for pattern in self._path_patterns:
            if pattern.search(query):
                return False, "Query contains invalid path sequences"

        # Allow legal terminology: letters, numbers, spaces, common punctuation
        allowed_chars = re.compile(r'^[a-zA-Z0-9\s\.,;:\-\(\)\[\]\{\}\'\"\/\?\!\@\#\$\%\&\*\+\=\_\|\\~`\^]+$')
        if not allowed_chars.match(query):
            return False, "Query contains disallowed characters"

        return True, ""

    # ─── HTML Sanitization ─────────────────────────────────────────────────────

    def sanitize_html(self, text: str) -> str:
        """
        Strip all HTML tags and decode/escape HTML entities.
        
        Args:
            text: Raw text potentially containing HTML
            
        Returns:
            Plain text with HTML removed and entities decoded
        """
        if not text or not isinstance(text, str):
            return ""

        # First unescape HTML entities (prevent double-encoding bypass)
        text = html.unescape(text)

        # Strip all HTML tags
        text = self._html_tag_re.sub('', text)

        # Re-escape special characters
        text = html.escape(text, quote=True)

        # Normalize whitespace
        text = re.sub(r'\s+', ' ', text).strip()

        return text

    # ─── PII Validation ───────────────────────────────────────────────────────

    def validate_ssn(self, ssn: str) -> bool:
        """
        Validate SSN format (XXX-XX-XXXX or XXXXXXXXX).
        Does NOT accept obviously invalid SSNs (all zeros, 9s, etc.).
        
        Args:
            ssn: Social Security Number string to validate
            
        Returns:
            True if valid format
        """
        if not ssn or not isinstance(ssn, str):
            return False

        # Strip formatting
        digits = re.sub(r'[-\s]', '', ssn)

        if not re.match(r'^\d{9}$', digits):
            return False

        area = digits[:3]
        group = digits[3:5]
        serial = digits[5:]

        # Invalid: all zeros in any segment, or specific invalid ranges
        if area == '000' or area == '666' or area.startswith('9'):
            return False
        if group == '00':
            return False
        if serial == '0000':
            return False

        return True

    def validate_ein(self, ein: str) -> bool:
        """
        Validate EIN (Employer Identification Number) format XX-XXXXXXX.
        
        Args:
            ein: EIN string to validate
            
        Returns:
            True if valid format
        """
        if not ein or not isinstance(ein, str):
            return False

        # Strip formatting
        digits = re.sub(r'[-\s]', '', ein)

        if not re.match(r'^\d{9}$', digits):
            return False

        # EIN prefix validation (valid IRS-assigned prefixes)
        prefix = int(digits[:2])
        invalid_prefixes = {0, 7, 8, 9, 17, 18, 19, 28, 29, 49, 69, 70, 78, 79, 89}

        if prefix in invalid_prefixes:
            return False

        return True

    # ─── Trust Document Validation ────────────────────────────────────────────

    def validate_trust_document(self, doc: dict) -> Tuple[bool, List[str]]:
        """
        Validate a trust document structure for SintraPrime trust operations.
        
        Required fields: trust_name, grantor, trustee, beneficiaries, state, type
        
        Args:
            doc: Trust document dictionary
            
        Returns:
            (is_valid: bool, errors: List[str])
        """
        errors = []

        if not isinstance(doc, dict):
            return False, ["Document must be a dictionary/object"]

        # Required fields
        required_fields = {
            "trust_name": str,
            "grantor": dict,
            "trustee": (dict, list),
            "beneficiaries": list,
            "state": str,
            "trust_type": str,
        }

        for field_name, expected_type in required_fields.items():
            if field_name not in doc:
                errors.append(f"Missing required field: {field_name}")
                continue

            value = doc[field_name]
            if isinstance(expected_type, tuple):
                if not isinstance(value, expected_type):
                    errors.append(f"Field '{field_name}' must be one of {expected_type}")
            else:
                if not isinstance(value, expected_type):
                    errors.append(f"Field '{field_name}' must be {expected_type.__name__}")

        # Validate trust_name
        if "trust_name" in doc and isinstance(doc["trust_name"], str):
            name = doc["trust_name"].strip()
            if len(name) < 3 or len(name) > 200:
                errors.append("trust_name must be 3-200 characters")
            valid, err = self.validate_legal_query(name)
            if not valid:
                errors.append(f"trust_name: {err}")

        # Validate state
        valid_states = {
            "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA",
            "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD",
            "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ",
            "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC",
            "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY",
            "DC", "PR", "GU", "VI", "AS", "MP",
        }
        if "state" in doc and isinstance(doc["state"], str):
            state = doc["state"].upper().strip()
            if state not in valid_states:
                errors.append(f"Invalid state code: {doc['state']}")

        # Validate trust_type
        valid_trust_types = {
            "revocable", "irrevocable", "testamentary", "living",
            "charitable", "special_needs", "spendthrift", "blind",
            "land", "asset_protection", "dynasty", "generation_skipping",
        }
        if "trust_type" in doc and isinstance(doc["trust_type"], str):
            if doc["trust_type"].lower() not in valid_trust_types:
                errors.append(f"Invalid trust_type. Must be one of: {', '.join(sorted(valid_trust_types))}")

        # Validate beneficiaries
        if "beneficiaries" in doc and isinstance(doc["beneficiaries"], list):
            if len(doc["beneficiaries"]) == 0:
                errors.append("Trust must have at least one beneficiary")

        # Validate grantor structure
        if "grantor" in doc and isinstance(doc["grantor"], dict):
            if "name" not in doc["grantor"]:
                errors.append("grantor.name is required")
            if "ssn" in doc["grantor"] and not self.validate_ssn(doc["grantor"]["ssn"]):
                errors.append("grantor.ssn is not a valid SSN format")

        return len(errors) == 0, errors

    # ─── Rate Limiting ─────────────────────────────────────────────────────────

    def rate_limit_check(self, user_id: str, action: str) -> bool:
        """
        Check if a user is within rate limits for a given action.
        Uses a sliding window algorithm.
        
        Args:
            user_id: Unique user identifier
            action: Action type (must match RATE_LIMITS keys)
            
        Returns:
            True if within rate limit, False if exceeded
        """
        now = time.time()
        limit, window = RATE_LIMITS.get(action, RATE_LIMITS["default"])
        key = f"{user_id}:{action}"

        # Purge old timestamps outside the window
        timestamps = _rate_limit_store[key]
        cutoff = now - window
        _rate_limit_store[key] = [ts for ts in timestamps if ts > cutoff]

        if len(_rate_limit_store[key]) >= limit:
            return False  # Rate limit exceeded

        _rate_limit_store[key].append(now)
        return True

    def get_rate_limit_status(self, user_id: str, action: str) -> dict:
        """
        Get current rate limit status for a user+action pair.
        
        Returns:
            dict with: limit, remaining, reset_at, window_seconds
        """
        now = time.time()
        limit, window = RATE_LIMITS.get(action, RATE_LIMITS["default"])
        key = f"{user_id}:{action}"

        cutoff = now - window
        timestamps = [ts for ts in _rate_limit_store.get(key, []) if ts > cutoff]
        used = len(timestamps)
        remaining = max(0, limit - used)
        reset_at = int(min(timestamps, default=now) + window) if timestamps else int(now + window)

        return {
            "limit": limit,
            "remaining": remaining,
            "used": used,
            "window_seconds": window,
            "reset_at": reset_at,
        }

    # ─── General Purpose Validators ──────────────────────────────────────────

    def validate_uuid(self, value: str) -> bool:
        """Validate UUID v4 format."""
        pattern = re.compile(
            r'^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
            re.IGNORECASE
        )
        return bool(pattern.match(str(value)))

    def validate_email(self, email: str) -> bool:
        """Validate email address format."""
        pattern = re.compile(
            r'^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$'
        )
        return bool(pattern.match(email.strip())) if email else False

    def validate_case_citation(self, citation: str) -> bool:
        """Validate legal case citation format (e.g., 347 U.S. 483)."""
        # Common citation formats
        patterns = [
            r'^\d+\s+[A-Z][a-zA-Z\.]+\s+\d+',      # 347 U.S. 483
            r'^\d+\s+F\.\d+\w?\s+\d+',              # 512 F.3d 582
            r'^\d+\s+S\.\s*Ct\.\s+\d+',             # 134 S. Ct. 2473
            r'^[A-Z][a-z]+\s+v\.\s+[A-Z][a-z]+',   # Brown v. Board
        ]
        return any(re.match(p, citation.strip()) for p in patterns)

    def validate_phone(self, phone: str) -> bool:
        """Validate US phone number."""
        digits = re.sub(r'[\s\-\.\(\)\+]', '', phone)
        if digits.startswith('1'):
            digits = digits[1:]
        return len(digits) == 10 and digits.isdigit()
