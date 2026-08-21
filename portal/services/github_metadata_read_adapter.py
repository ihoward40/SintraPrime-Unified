"""Gate 4D-B public GitHub repository-metadata read adapter.

This adapter is intentionally narrower than a general GitHub connector. It can
perform exactly one unauthenticated GET against the public repository metadata
endpoint for ihoward40/SintraPrime-Unified. It cannot accept credentials, follow
redirects, select another repository, read repository contents, or perform any
write-capable HTTP method.
"""

from __future__ import annotations

import hashlib
import ipaddress
import json
import socket
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlsplit

import aiohttp
from aiohttp.abc import AbstractResolver

from portal.services.postman_echo_provider_adapter import ProviderBoundaryError

ADAPTER_ID = "provider.github-metadata-read-v1"
OPERATION_ID = "repository_metadata_read"
ENVIRONMENT = "provider_readonly"
RISK_CLASS = "E0"
PROVIDER_HOST = "api.github.com"
APPROVED_PATH = "/repos/ihoward40/SintraPrime-Unified"
APPROVED_URL = f"https://{PROVIDER_HOST}{APPROVED_PATH}"
APPROVED_PAYLOAD = {"method": "GET", "resource": "repository_metadata"}
LOCAL_RATE_LIMIT_PER_MINUTE = 1


def canonical_json_hash(payload: dict[str, Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _validate_public_ip(value: str) -> str:
    ip = ipaddress.ip_address(value)
    if not ip.is_global:
        raise ProviderBoundaryError(f"Resolved GitHub address is not globally routable: {value}")
    return str(ip)


def validate_destination(url: str) -> None:
    parsed = urlsplit(url)
    if parsed.scheme != "https":
        raise ProviderBoundaryError("Gate 4D-B requires HTTPS")
    if parsed.username or parsed.password or parsed.port not in (None, 443):
        raise ProviderBoundaryError("Gate 4D-B destination authority is not allowlisted")
    if (parsed.hostname or "").lower() != PROVIDER_HOST:
        raise ProviderBoundaryError("Gate 4D-B destination host is not allowlisted")
    if parsed.path != APPROVED_PATH or parsed.query or parsed.fragment:
        raise ProviderBoundaryError("Gate 4D-B destination path is not allowlisted")


async def resolve_provider_ips(host: str = PROVIDER_HOST) -> tuple[str, ...]:
    if host != PROVIDER_HOST:
        raise ProviderBoundaryError("DNS resolution requested for an unapproved GitHub host")
    loop = __import__("asyncio").get_running_loop()
    records = await loop.getaddrinfo(host, 443, type=socket.SOCK_STREAM)
    ips = sorted({_validate_public_ip(record[4][0]) for record in records})
    if not ips:
        raise ProviderBoundaryError("GitHub DNS resolution returned no usable addresses")
    return tuple(ips)


class PinnedResolver(AbstractResolver):
    """Resolver restricted to the addresses approved before the request."""

    def __init__(self, *, host: str, ips: tuple[str, ...]):
        if host != PROVIDER_HOST or not ips:
            raise ProviderBoundaryError("Pinned resolver requires the approved GitHub host and addresses")
        self.host = host
        self.ips = tuple(_validate_public_ip(ip) for ip in ips)

    async def resolve(
        self, host: str, port: int = 0, family: int = socket.AF_INET
    ) -> list[dict[str, Any]]:
        if host != self.host:
            raise ProviderBoundaryError("Resolver escape to an unapproved hostname was blocked")
        result: list[dict[str, Any]] = []
        for ip in self.ips:
            addr = ipaddress.ip_address(ip)
            fam = socket.AF_INET6 if addr.version == 6 else socket.AF_INET
            if family not in (socket.AF_UNSPEC, fam):
                continue
            result.append(
                {
                    "hostname": host,
                    "host": ip,
                    "port": port,
                    "family": fam,
                    "proto": 0,
                    "flags": 0,
                }
            )
        if not result:
            raise ProviderBoundaryError("No pinned address matched the requested socket family")
        return result

    async def close(self) -> None:
        return None


@dataclass(frozen=True)
class GitHubMetadataReceipt:
    status: int
    payload_hash: str
    response_hash: str
    resolved_ips: tuple[str, ...]
    provider_url: str


class GitHubMetadataReadAdapter:
    adapter_id = ADAPTER_ID
    operation_id = OPERATION_ID
    environment = ENVIRONMENT
    risk_class = RISK_CLASS
    provider_host = PROVIDER_HOST
    compensation = "none-read-only"
    provider_rollback_required = False
    local_rate_limit_per_minute = LOCAL_RATE_LIMIT_PER_MINUTE

    @staticmethod
    def canonicalize_payload(payload: dict[str, Any]) -> tuple[dict[str, Any], str]:
        if not isinstance(payload, dict):
            raise ProviderBoundaryError("Gate 4D-B payload must be an object")
        canonical = json.loads(
            json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
        )
        if canonical != APPROVED_PAYLOAD:
            raise ProviderBoundaryError("Gate 4D-B permits only repository metadata GET")
        return canonical, canonical_json_hash(canonical)

    def validate_destination(self, destination: str) -> None:
        validate_destination(destination)

    def preflight(self, *, destination: str, payload: dict[str, Any]) -> dict[str, Any]:
        validate_destination(destination)
        canonical, payload_hash = self.canonicalize_payload(payload)
        receipt = {
            "adapter_id": self.adapter_id,
            "operation_id": self.operation_id,
            "environment": self.environment,
            "risk_class": self.risk_class,
            "destination": destination,
            "payload": canonical,
            "payload_hash": payload_hash,
            "network_access": True,
            "credential_access": False,
            "production_reachable": True,
            "provider_persistent_state": False,
            "compensation": self.compensation,
            "provider_rollback_required": self.provider_rollback_required,
            "http_method": "GET",
        }
        receipt["receipt_hash"] = canonical_json_hash(receipt)
        return receipt

    async def execute_once(
        self,
        *,
        payload: dict[str, Any],
        timeout_seconds: float = 10.0,
        destination: str = APPROVED_URL,
    ) -> GitHubMetadataReceipt:
        validate_destination(destination)
        _, payload_hash = self.canonicalize_payload(payload)
        pinned_ips = await resolve_provider_ips(PROVIDER_HOST)
        resolver = PinnedResolver(host=PROVIDER_HOST, ips=pinned_ips)
        connector = aiohttp.TCPConnector(resolver=resolver, use_dns_cache=False, ttl_dns_cache=0)
        timeout = aiohttp.ClientTimeout(total=timeout_seconds)
        headers = {
            "Accept": "application/vnd.github+json",
            "User-Agent": "SintraPrime-Gate4D-B",
            "X-GitHub-Api-Version": "2022-11-28",
        }

        async with (
            aiohttp.ClientSession(connector=connector, timeout=timeout) as session,
            session.get(
                destination,
                headers=headers,
                allow_redirects=False,
            ) as response,
        ):
            if 300 <= response.status < 400:
                location = response.headers.get("Location")
                raise ProviderBoundaryError(
                    f"GitHub redirect blocked before follow: status={response.status} location={location!r}"
                )
            if response.status in (403, 429) and response.headers.get("X-RateLimit-Remaining") == "0":
                raise ProviderBoundaryError(f"Provider rate limit returned {response.status}")
            if response.status != 200:
                raise ProviderBoundaryError(f"GitHub returned unexpected status {response.status}")
            body = await response.read()
            try:
                data = json.loads(body)
            except json.JSONDecodeError as exc:
                raise ProviderBoundaryError("GitHub metadata response was not valid JSON") from exc
            if data.get("full_name") != "ihoward40/SintraPrime-Unified":
                raise ProviderBoundaryError("GitHub metadata response did not match the approved repository")
            response_hash = hashlib.sha256(body).hexdigest()
            return GitHubMetadataReceipt(
                status=response.status,
                payload_hash=payload_hash,
                response_hash=response_hash,
                resolved_ips=pinned_ips,
                provider_url=str(response.url),
            )


github_metadata_read_adapter = GitHubMetadataReadAdapter()
