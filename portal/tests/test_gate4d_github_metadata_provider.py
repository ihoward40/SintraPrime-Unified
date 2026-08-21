"""Gate 4D-B network-boundary certification for public GitHub metadata reads."""

from __future__ import annotations

import os
import socket

import pytest

from portal.services import github_metadata_read_adapter as adapter_module
from portal.services.github_metadata_read_adapter import (
    APPROVED_PAYLOAD,
    APPROVED_URL,
    PROVIDER_HOST,
    PinnedResolver,
    ProviderBoundaryError,
    github_metadata_read_adapter,
    validate_destination,
)


class _FakeResponse:
    def __init__(
        self,
        *,
        status: int,
        location: str | None = None,
        body: bytes = b'{"full_name":"ihoward40/SintraPrime-Unified"}',
        rate_remaining: str | None = None,
    ):
        self.status = status
        self.headers: dict[str, str] = {}
        if location:
            self.headers["Location"] = location
        if rate_remaining is not None:
            self.headers["X-RateLimit-Remaining"] = rate_remaining
        self._body = body
        self.url = APPROVED_URL

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def read(self) -> bytes:
        return self._body


class _FakeSession:
    calls: list[dict] = []
    response = _FakeResponse(status=200)

    def __init__(self, *args, **kwargs):
        self.kwargs = kwargs

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    def get(self, url, **kwargs):
        type(self).calls.append({"method": "GET", "url": url, **kwargs})
        return type(self).response


def test_destination_allowlist_is_exact() -> None:
    validate_destination(APPROVED_URL)
    bad = (
        "http://api.github.com/repos/ihoward40/SintraPrime-Unified",
        "https://github.com/repos/ihoward40/SintraPrime-Unified",
        "https://api.github.com/repos/ihoward40/other",
        "https://api.github.com/repos/ihoward40/SintraPrime-Unified/contents",
        "https://api.github.com/repos/ihoward40/SintraPrime-Unified?ref=main",
        "https://user:pass@api.github.com/repos/ihoward40/SintraPrime-Unified",
    )
    for destination in bad:
        with pytest.raises(ProviderBoundaryError):
            validate_destination(destination)


def test_payload_allows_only_repository_metadata_get() -> None:
    canonical, _ = github_metadata_read_adapter.canonicalize_payload(APPROVED_PAYLOAD)
    assert canonical == {"method": "GET", "resource": "repository_metadata"}
    for payload in (
        {"method": "POST", "resource": "repository_metadata"},
        {"method": "HEAD", "resource": "repository_metadata"},
        {"method": "GET", "resource": "contents"},
        {"method": "GET", "resource": "repository_metadata", "path": "README.md"},
    ):
        with pytest.raises(ProviderBoundaryError, match="repository metadata GET"):
            github_metadata_read_adapter.canonicalize_payload(payload)


def test_pinned_resolver_refuses_host_escape_and_non_public_addresses() -> None:
    resolver = PinnedResolver(host=PROVIDER_HOST, ips=("8.8.8.8",))
    with pytest.raises(ProviderBoundaryError, match="unapproved hostname"):
        __import__("asyncio").run(resolver.resolve("attacker.invalid", 443, socket.AF_INET))
    for address in ("127.0.0.1", "10.0.0.5", "169.254.169.254", "::1"):
        with pytest.raises(ProviderBoundaryError, match="not globally routable"):
            PinnedResolver(host=PROVIDER_HOST, ips=(address,))


def test_resolver_returns_only_preapproved_pinned_addresses() -> None:
    resolver = PinnedResolver(host=PROVIDER_HOST, ips=("8.8.8.8", "1.1.1.1"))
    rows = __import__("asyncio").run(resolver.resolve(PROVIDER_HOST, 443, socket.AF_INET))
    assert {row["host"] for row in rows} == {"8.8.8.8", "1.1.1.1"}
    assert all(row["hostname"] == PROVIDER_HOST for row in rows)


@pytest.mark.asyncio
async def test_redirect_is_never_followed_and_no_credentials_are_sent(monkeypatch) -> None:
    _FakeSession.calls = []
    _FakeSession.response = _FakeResponse(
        status=302,
        location="https://attacker.invalid/collect",
    )

    async def fake_resolve(host: str = PROVIDER_HOST):
        assert host == PROVIDER_HOST
        return ("8.8.8.8",)

    monkeypatch.setattr(adapter_module, "resolve_provider_ips", fake_resolve)
    monkeypatch.setattr(adapter_module.aiohttp, "ClientSession", _FakeSession)
    monkeypatch.setattr(adapter_module.aiohttp, "TCPConnector", lambda **kwargs: object())

    with pytest.raises(ProviderBoundaryError, match="GitHub redirect blocked before follow"):
        await github_metadata_read_adapter.execute_once(payload=APPROVED_PAYLOAD)

    assert len(_FakeSession.calls) == 1
    call = _FakeSession.calls[0]
    assert call["method"] == "GET"
    assert call["url"] == APPROVED_URL
    assert call["allow_redirects"] is False
    assert "Authorization" not in call["headers"]
    assert all("attacker.invalid" not in str(value) for value in call.values())


@pytest.mark.asyncio
async def test_dns_resolution_is_pinned_into_actual_http_connector(monkeypatch) -> None:
    _FakeSession.calls = []
    _FakeSession.response = _FakeResponse(status=200)
    captured: dict = {}

    async def fake_resolve(host: str = PROVIDER_HOST):
        return ("8.8.8.8", "1.1.1.1")

    def fake_connector(**kwargs):
        captured.update(kwargs)
        return object()

    monkeypatch.setattr(adapter_module, "resolve_provider_ips", fake_resolve)
    monkeypatch.setattr(adapter_module.aiohttp, "ClientSession", _FakeSession)
    monkeypatch.setattr(adapter_module.aiohttp, "TCPConnector", fake_connector)

    receipt = await github_metadata_read_adapter.execute_once(payload=APPROVED_PAYLOAD)

    assert receipt.resolved_ips == ("8.8.8.8", "1.1.1.1")
    assert isinstance(captured["resolver"], PinnedResolver)
    assert captured["resolver"].host == PROVIDER_HOST
    assert captured["resolver"].ips == receipt.resolved_ips
    assert captured["use_dns_cache"] is False
    assert captured["ttl_dns_cache"] == 0
    assert _FakeSession.calls[0]["method"] == "GET"
    assert "Authorization" not in _FakeSession.calls[0]["headers"]


@pytest.mark.asyncio
async def test_live_public_github_metadata_boundary() -> None:
    if os.environ.get("GATE4D_LIVE_HTTP") != "1":
        pytest.skip("Live Gate 4D-B public GitHub call runs only in its dedicated workflow")
    receipt = await github_metadata_read_adapter.execute_once(
        payload=APPROVED_PAYLOAD,
        timeout_seconds=15.0,
    )
    assert receipt.status == 200
    assert receipt.provider_url == APPROVED_URL
    assert receipt.resolved_ips
    assert len(receipt.payload_hash) == 64
    assert len(receipt.response_hash) == 64
