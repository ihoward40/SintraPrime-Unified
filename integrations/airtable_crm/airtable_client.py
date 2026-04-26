"""
Airtable REST API client for SintraPrime CRM integration.

Provides a thin, synchronous wrapper around the Airtable REST API v0.
Supports all CRUD operations with automatic rate-limiting and retry logic.
"""
import json
import logging
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict, Generator, List, Optional

logger = logging.getLogger("airtable_client")
logger.setLevel(logging.INFO)

AIRTABLE_API_BASE = "https://api.airtable.com/v0"
MAX_RECORDS_PER_REQUEST = 10
RATE_LIMIT_DELAY = 0.25  # 250ms between requests (Airtable limit: 5 req/sec)


class AirtableError(Exception):
    """Raised when an Airtable API call fails."""
    def __init__(self, message: str, status_code: int = 0, response_body: str = ""):
        super().__init__(message)
        self.status_code = status_code
        self.response_body = response_body


class AirtableClient:
    """Low-level Airtable REST API client.

    Usage:
        client = AirtableClient(
            api_key=os.environ["AIRTABLE_API_KEY"],
            base_id="appXXXXXXXXXXXXXX"
        )
        records = client.list_records("Contacts")
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_id: Optional[str] = None,
        timeout: int = 30,
        max_retries: int = 3,
    ):
        self.api_key = api_key or os.environ.get("AIRTABLE_API_KEY", "")
        self.base_id = base_id or os.environ.get("AIRTABLE_BASE_ID", "")
        self.timeout = timeout
        self.max_retries = max_retries
        self._last_request_time: float = 0.0

        if not self.api_key:
            logger.warning("AIRTABLE_API_KEY not set — API calls will fail.")
        if not self.base_id:
            logger.warning("AIRTABLE_BASE_ID not set — API calls will fail.")

    # ------------------------------------------------------------------
    # Core HTTP helpers
    # ------------------------------------------------------------------

    def _rate_limit(self) -> None:
        """Enforce Airtable's rate limit (5 requests/second)."""
        elapsed = time.time() - self._last_request_time
        if elapsed < RATE_LIMIT_DELAY:
            time.sleep(RATE_LIMIT_DELAY - elapsed)
        self._last_request_time = time.time()

    def _make_request(
        self,
        method: str,
        path: str,
        body: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """Make an authenticated request to the Airtable API."""
        self._rate_limit()

        url = f"{AIRTABLE_API_BASE}/{self.base_id}/{path}"
        if params:
            url += "?" + urllib.parse.urlencode(params)

        data = json.dumps(body).encode("utf-8") if body else None
        req = urllib.request.Request(url, data=data, method=method)
        req.add_header("Authorization", f"Bearer {self.api_key}")
        req.add_header("Content-Type", "application/json")

        for attempt in range(self.max_retries):
            try:
                with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                    return json.loads(resp.read().decode("utf-8"))
            except urllib.error.HTTPError as exc:
                body_text = exc.read().decode("utf-8", errors="replace")
                if exc.code == 429:  # Rate limited
                    wait = 2 ** attempt
                    logger.warning("Rate limited; waiting %ds (attempt %d)", wait, attempt + 1)
                    time.sleep(wait)
                    continue
                raise AirtableError(
                    f"Airtable API error {exc.code}: {exc.reason}",
                    status_code=exc.code,
                    response_body=body_text,
                ) from exc
            except urllib.error.URLError as exc:
                if attempt < self.max_retries - 1:
                    time.sleep(1)
                    continue
                raise AirtableError(f"Network error: {exc.reason}") from exc

        raise AirtableError("Max retries exceeded")

    # ------------------------------------------------------------------
    # Record CRUD
    # ------------------------------------------------------------------

    def list_records(
        self,
        table_name: str,
        view: Optional[str] = None,
        filter_formula: Optional[str] = None,
        sort: Optional[List[Dict[str, str]]] = None,
        max_records: Optional[int] = None,
        fields: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """List all records in a table, handling pagination automatically."""
        all_records: List[Dict[str, Any]] = []
        offset: Optional[str] = None

        while True:
            params: Dict[str, str] = {"pageSize": "100"}
            if view:
                params["view"] = view
            if filter_formula:
                params["filterByFormula"] = filter_formula
            if offset:
                params["offset"] = offset
            if fields:
                for i, f in enumerate(fields):
                    params[f"fields[{i}]"] = f
            if sort:
                for i, s in enumerate(sort):
                    params[f"sort[{i}][field]"] = s.get("field", "")
                    params[f"sort[{i}][direction]"] = s.get("direction", "asc")

            response = self._make_request("GET", urllib.parse.quote(table_name), params=params)
            records = response.get("records", [])
            all_records.extend(records)

            if max_records and len(all_records) >= max_records:
                all_records = all_records[:max_records]
                break

            offset = response.get("offset")
            if not offset:
                break

        logger.info("Listed %d records from %s", len(all_records), table_name)
        return all_records

    def get_record(self, table_name: str, record_id: str) -> Dict[str, Any]:
        """Get a single record by ID."""
        path = f"{urllib.parse.quote(table_name)}/{record_id}"
        return self._make_request("GET", path)

    def create_record(
        self, table_name: str, fields: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create a single record."""
        response = self._make_request(
            "POST",
            urllib.parse.quote(table_name),
            body={"fields": fields},
        )
        logger.info("Created record %s in %s", response.get("id"), table_name)
        return response

    def create_records(
        self, table_name: str, records: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Bulk create up to 10 records at once."""
        created = []
        for i in range(0, len(records), MAX_RECORDS_PER_REQUEST):
            batch = records[i : i + MAX_RECORDS_PER_REQUEST]
            response = self._make_request(
                "POST",
                urllib.parse.quote(table_name),
                body={"records": [{"fields": r} for r in batch]},
            )
            created.extend(response.get("records", []))
        logger.info("Bulk created %d records in %s", len(created), table_name)
        return created

    def update_record(
        self,
        table_name: str,
        record_id: str,
        fields: Dict[str, Any],
        merge: bool = True,
    ) -> Dict[str, Any]:
        """Update a record. If merge=True, uses PATCH (partial update); else PUT (full replace)."""
        method = "PATCH" if merge else "PUT"
        path = f"{urllib.parse.quote(table_name)}/{record_id}"
        response = self._make_request(method, path, body={"fields": fields})
        logger.info("Updated record %s in %s", record_id, table_name)
        return response

    def delete_record(self, table_name: str, record_id: str) -> Dict[str, Any]:
        """Delete a record by ID."""
        path = f"{urllib.parse.quote(table_name)}/{record_id}"
        response = self._make_request("DELETE", path)
        logger.info("Deleted record %s from %s", record_id, table_name)
        return response

    def delete_records(self, table_name: str, record_ids: List[str]) -> List[Dict[str, Any]]:
        """Bulk delete up to 10 records at once."""
        deleted = []
        for i in range(0, len(record_ids), MAX_RECORDS_PER_REQUEST):
            batch = record_ids[i : i + MAX_RECORDS_PER_REQUEST]
            params = {f"records[{j}]": rid for j, rid in enumerate(batch)}
            response = self._make_request(
                "DELETE",
                urllib.parse.quote(table_name),
                params=params,
            )
            deleted.extend(response.get("records", []))
        logger.info("Bulk deleted %d records from %s", len(deleted), table_name)
        return deleted

    def search_records(
        self,
        table_name: str,
        search_field: str,
        search_value: str,
    ) -> List[Dict[str, Any]]:
        """Search records by field value using Airtable formula."""
        formula = f"SEARCH(\"{search_value}\", {{{search_field}}})"
        return self.list_records(table_name, filter_formula=formula)

    def upsert_record(
        self,
        table_name: str,
        fields: Dict[str, Any],
        match_field: str,
        match_value: str,
    ) -> Dict[str, Any]:
        """Create or update a record based on a unique field match."""
        existing = self.search_records(table_name, match_field, match_value)
        if existing:
            record_id = existing[0]["id"]
            return self.update_record(table_name, record_id, fields)
        return self.create_record(table_name, fields)

    # ------------------------------------------------------------------
    # Schema inspection
    # ------------------------------------------------------------------

    def get_base_schema(self) -> Dict[str, Any]:
        """Get the schema (tables and fields) of the base."""
        url = f"https://api.airtable.com/v0/meta/bases/{self.base_id}/tables"
        req = urllib.request.Request(url, method="GET")
        req.add_header("Authorization", f"Bearer {self.api_key}")
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception as exc:
            raise AirtableError(f"Failed to get schema: {exc}") from exc
