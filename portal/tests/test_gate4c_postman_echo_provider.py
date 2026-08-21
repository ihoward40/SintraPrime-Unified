"""Gate 4C network-boundary certification for Postman Echo provider test adapter."""

from __future__ import annotations

import os
import socket

import pytest

from portal.services import postman_echo_provider_adapter as adapter_module
from portal.services.postman_echo_provider_adapter import (
    APPROVED_URL,
    PROVIDER_HOST,
    PinnedResolver,
    ProviderBoundaryError,
    postman_echo_provider_adapter,
    validate_destination,
)


class _FakeResponse:
    def __init__(self, *, status: int, location: str | None = None, body: bytes = b"{}"):
        self.status = status
        self.headers = {"Location": location} if location else {}
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

    def post(self, url, **kwargs):
        type(self).calls.append({"url": url, **kwargs})
        return type(self).response


def test_destination_allowlist_rejects_scheme_host_path_and_query_escape() -> None:
    validate_destination(APPROVED_URL)
    bad = (
        "http://postman-echo.com/post",
        "https://example.com/post",
        "https://postman-echo.com/get",
        "https://postman-echo.com/post?next=https://example.com",
        "https://user:pass@postman-echo.com/post",
    )
    for destination in bad:
        with pytest.raises(ProviderBoundaryError):
            validate_destination(destination)


def test_pinned_resolver_refuses_host_escape_and_non_public_addresses() -> None:
    resolver = PinnedResolver(host=PROVIDER_HOST, ips=("8.8.8.8",))

    with pytest.raises(ProviderBoundaryError, match="unapproved hostname"):
        __import__("asyncio").run(resolver.resolve("example.com", 443, socket.AF_INET))

    for address in ("127.0.0.1", "10.0.0.5", "169.254.169.254", "::1"):
        with pytest.raises(ProviderBoundaryError, match="not globally routable"):
            PinnedResolver(host=PROVIDER_HOST, ips=(address,))


def test_resolver_returns_only_preapproved_pinned_addresses() -> None:
    resolver = PinnedResolver(host=PROVIDER_HOST, ips=("8.8.8.8", "1.1.1.1"))
    rows = __import__("asyncio").run(resolver.resolve(PROVIDER_HOST, 443, socket.AF_INET))
    assert {row["host"] for row in rows} == {"8.8.8.8", "1.1.1.1"}
    assert all(row["hostname"] == PROVIDER_HOST for row in rows)


@pytest.mark.asyncio
async def test_30x_redirect_is_never_followed_and_credentials_cannot_cross_host(monkeypatch) -> None:
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

    with pytest.raises(ProviderBoundaryError, match="Provider redirect blocked before follow"):
        await postman_echo_provider_adapter.execute_once(
            payload={"gate": "4c"},
            credential_header="Bearer synthetic-gate4c-token",
        )

    assert len(_FakeSession.calls) == 1
    call = _FakeSession.calls[0]
    assert call["url"] == APPROVED_URL
    assert call["allow_redirects"] is False
    assert call["headers"]["Authorization"] == "Bearer synthetic-gate4c-token"
    assert all("attacker.invalid" not in str(value) for value in call.values())


@pytest.mark.asyncio
async def test_dns_resolution_is_pinned_into_actual_http_connector(monkeypatch) -> None:
    _FakeSession.calls = []
    _FakeSession.response = _FakeResponse(status=200, body=b'{"ok":true}')
    captured: dict = {}

    async def fake_resolve(host: str = PROVIDER_HOST):
        return ("8.8.8.8", "1.1.1.1")

    def fake_connector(**kwargs):
        captured.update(kwargs)
        return object()

    monkeypatch.setattr(adapter_module, "resolve_provider_ips", fake_resolve)
    monkeypatch.setattr(adapter_module.aiohttp, "ClientSession", _FakeSession)
    monkeypatch.setattr(adapter_module.aiohttp, "TCPConnector", fake_connector)

    receipt = await postman_echo_provider_adapter.execute_once(payload={"gate": "4c"})

    assert receipt.resolved_ips == ("8.8.8.8", "1.1.1.1")
    assert isinstance(captured["resolver"], PinnedResolver)
    assert captured["resolver"].host == PROVIDER_HOST
    assert captured["resolver"].ips == receipt.resolved_ips
    assert captured["use_dns_cache"] is False
    assert captured["ttl_dns_cache"] == 0


@pytest.mark.asyncio
async def test_live_postman_echo_https_boundary() -> None:
    """Cross a real provider-owned HTTP boundary without persistent provider state."""
    if os.environ.get("GATE4C_LIVE_HTTP") != "1":
        pytest.skip("Live Gate 4C provider call is certified only in its dedicated workflow")
    receipt = await postman_echo_provider_adapter.execute_once(
        payload={"gate": "4c", "purpose": "provider-boundary-certification"},
        timeout_seconds=15.0,
    )
    assert receipt.status == 200
    assert receipt.provider_url == APPROVED_URL
    assert receipt.resolved_ips
    assert len(receipt.payload_hash) == 64
    assert len(receipt.response_hash) == 64
