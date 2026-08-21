"""Gate 4C provider-owned non-production HTTP adapter.

This adapter is intentionally limited to Postman Echo. It provides a real HTTPS
boundary with no meaningful persistent provider-side effect. Redirects are never
followed, DNS answers are validated, and the actual socket resolver is pinned to
the exact approved addresses resolved for the request.
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

ADAPTER_ID = "provider.postman-echo-v1"
OPERATION_ID = "echo_write"
ENVIRONMENT = "provider_test"
RISK_CLASS = "E1"
PROVIDER_HOST = "postman-echo.com"
APPROVED_PATH = "/post"
APPROVED_URL = f"https://{PROVIDER_HOST}{APPROVED_PATH}"


class ProviderBoundaryError(RuntimeError):
    """Raised whenever the Gate 4C HTTP boundary fails closed."""


def canonical_json_hash(payload: dict[str, Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _validate_public_ip(value: str) -> str:
    ip = ipaddress.ip_address(value)
    if not ip.is_global:
        raise ProviderBoundaryError(f"Resolved provider address is not globally routable: {value}")
    return str(ip)


def validate_destination(url: str) -> None:
    parsed = urlsplit(url)
    if parsed.scheme != "https":
        raise ProviderBoundaryError("Gate 4C requires HTTPS")
    if parsed.username or parsed.password or parsed.port not in (None, 443):
        raise ProviderBoundaryError("Gate 4C destination authority is not allowlisted")
    if (parsed.hostname or "").lower() != PROVIDER_HOST:
        raise ProviderBoundaryError("Gate 4C destination host is not allowlisted")
    if parsed.path != APPROVED_PATH or parsed.query or parsed.fragment:
        raise ProviderBoundaryError("Gate 4C destination path is not allowlisted")


async def resolve_provider_ips(host: str = PROVIDER_HOST) -> tuple[str, ...]:
    if host != PROVIDER_HOST:
        raise ProviderBoundaryError("DNS resolution requested for an unapproved host")
    loop = __import__("asyncio").get_running_loop()
    records = await loop.getaddrinfo(host, 443, type=socket.SOCK_STREAM)
    ips = sorted({_validate_public_ip(record[4][0]) for record in records})
    if not ips:
        raise ProviderBoundaryError("Provider DNS resolution returned no usable addresses")
    return tuple(ips)


class PinnedResolver(AbstractResolver):
    """Resolver that can return only the addresses approved before the request."""

    def __init__(self, *, host: str, ips: tuple[str, ...]):
        if host != PROVIDER_HOST or not ips:
            raise ProviderBoundaryError("Pinned resolver requires the approved provider host and addresses")
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
class ProviderReceipt:
    status: int
    payload_hash: str
    response_hash: str
    resolved_ips: tuple[str, ...]
    provider_url: str


class PostmanEchoProviderAdapter:
    adapter_id = ADAPTER_ID
    operation_id = OPERATION_ID
    environment = ENVIRONMENT
    risk_class = RISK_CLASS
    provider_host = PROVIDER_HOST
    compensation = "logical-only"
    provider_rollback_required = False

    @staticmethod
    def canonicalize_payload(payload: dict[str, Any]) -> tuple[dict[str, Any], str]:
        if not isinstance(payload, dict) or not payload:
            raise ProviderBoundaryError("Provider-test payload must be a non-empty object")
        canonical = json.loads(
            json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
        )
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
            "credential_access": True,
            "production_reachable": False,
            "provider_persistent_state": False,
            "compensation": self.compensation,
            "provider_rollback_required": self.provider_rollback_required,
        }
        receipt["receipt_hash"] = canonical_json_hash(receipt)
        return receipt

    async def execute_once(
        self,
        *,
        payload: dict[str, Any],
        credential_header: str | None = None,
        timeout_seconds: float = 10.0,
        destination: str = APPROVED_URL,
    ) -> ProviderReceipt:
        validate_destination(destination)
        canonical, payload_hash = self.canonicalize_payload(payload)
        pinned_ips = await resolve_provider_ips(PROVIDER_HOST)
        resolver = PinnedResolver(host=PROVIDER_HOST, ips=pinned_ips)
        connector = aiohttp.TCPConnector(resolver=resolver, use_dns_cache=False, ttl_dns_cache=0)
        timeout = aiohttp.ClientTimeout(total=timeout_seconds)
        headers = {"Content-Type": "application/json"}
        if credential_header is not None:
            headers["Authorization"] = credential_header

        async with (
            aiohttp.ClientSession(connector=connector, timeout=timeout) as session,
            session.post(
                destination,
                json=canonical,
                headers=headers,
                allow_redirects=False,
            ) as response,
        ):
            if 300 <= response.status < 400:
                location = response.headers.get("Location")
                raise ProviderBoundaryError(
                    f"Provider redirect blocked before follow: status={response.status} location={location!r}"
                )
            if response.status == 429:
                raise ProviderBoundaryError("Provider rate limit returned 429")
            if response.status < 200 or response.status >= 300:
                raise ProviderBoundaryError(f"Provider returned unexpected status {response.status}")
            body = await response.read()
            response_hash = hashlib.sha256(body).hexdigest()
            return ProviderReceipt(
                status=response.status,
                payload_hash=payload_hash,
                response_hash=response_hash,
                resolved_ips=pinned_ips,
                provider_url=str(response.url),
            )


postman_echo_provider_adapter = PostmanEchoProviderAdapter()
