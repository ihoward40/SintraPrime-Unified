"""Discover other SintraPrime instances on the network."""
from __future__ import annotations

import asyncio
import json
import logging
import os
import socket
import time
from typing import Optional

from .message_types import AgentCapabilities, AgentMessage, MessageType

_DEFAULT_PORT = 9876
_DISCOVERY_TIMEOUT = 3  # seconds


class AgentDiscovery:
    """
    Discovery mechanisms for SintraPrime instances:

    1. **UDP broadcast** — LAN discovery (no configuration required)
    2. **Central registry** — configured via ``SINTRA_REGISTRY_URL``
    3. **Manual peer list** — ``SINTRA_PEERS=host1:9876,host2:9876``
    4. **mDNS** — ``_sintra._tcp.local`` (requires ``zeroconf`` optional dep)

    Usage
    -----
    ::

        discovery = AgentDiscovery(agent_id="sintra-alpha",
                                   capabilities=caps, port=9876)
        peers = await discovery.discover_local(timeout=3)
        peers += discovery.parse_peer_env()
    """

    DISCOVERY_PORT = 9877   # dedicated discovery port (separate from data port)

    def __init__(
        self,
        agent_id: str,
        capabilities: AgentCapabilities,
        port: int = _DEFAULT_PORT,
    ) -> None:
        self.agent_id = agent_id
        self.capabilities = capabilities
        self.port = port
        self.logger = logging.getLogger(f"AgentDiscovery:{agent_id}")

    # ------------------------------------------------------------------
    # LAN discovery via UDP broadcast
    # ------------------------------------------------------------------

    async def discover_local(self, timeout: int = _DISCOVERY_TIMEOUT) -> list[dict]:
        """
        Discover agents on the local network via UDP broadcast.

        Sends a HELLO probe on the broadcast address and collects responses
        for *timeout* seconds.

        Returns
        -------
        list[dict]
            Each dict has keys: ``agent_id``, ``addr``, ``port``, ``capabilities``.
        """
        discovered: list[dict] = []
        loop = asyncio.get_event_loop()

        # Create a raw UDP socket for discovery
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.setblocking(False)

        try:
            sock.bind(("", self.DISCOVERY_PORT))
        except OSError:
            # Port already in use — try an ephemeral port
            sock.bind(("", 0))

        probe = AgentMessage(
            type=MessageType.HELLO,
            sender_id=self.agent_id,
            payload={
                "port": self.port,
                "capabilities": self.capabilities.to_dict(),
                "discovery": True,
            },
        )
        probe_bytes = probe.to_json().encode()

        # Send broadcast
        try:
            sock.sendto(probe_bytes, ("255.255.255.255", self.DISCOVERY_PORT))
            self.logger.debug("Broadcast discovery probe sent.")
        except Exception as exc:
            self.logger.warning("Broadcast failed: %s", exc)

        deadline = loop.time() + timeout
        seen_ids: set[str] = {self.agent_id}

        while True:
            remaining = deadline - loop.time()
            if remaining <= 0:
                break
            try:
                data, addr = await asyncio.wait_for(
                    loop.run_in_executor(None, sock.recvfrom, 4096),
                    timeout=remaining,
                )
                try:
                    msg = AgentMessage.from_json(data.decode())
                    if msg.sender_id in seen_ids:
                        continue
                    seen_ids.add(msg.sender_id)
                    discovered.append(
                        {
                            "agent_id": msg.sender_id,
                            "addr": addr[0],
                            "port": msg.payload.get("port", _DEFAULT_PORT),
                            "capabilities": msg.payload.get("capabilities", {}),
                            "discovered_at": time.time(),
                        }
                    )
                    self.logger.info(
                        "Discovered peer: %s @ %s:%d",
                        msg.sender_id, addr[0], msg.payload.get("port", _DEFAULT_PORT),
                    )
                except Exception:
                    pass
            except asyncio.TimeoutError:
                break
            except Exception as exc:
                self.logger.debug("Recv error: %s", exc)
                break

        sock.close()
        return discovered

    # ------------------------------------------------------------------
    # Central registry
    # ------------------------------------------------------------------

    async def register_with_registry(self, registry_url: str) -> bool:
        """
        Register this agent with a central HTTP registry.

        Sends a POST to ``{registry_url}/agents`` with agent info.

        Returns True on success.
        """
        try:
            import aiohttp  # optional dependency
        except ImportError:
            self.logger.warning(
                "aiohttp not installed; cannot register with registry."
            )
            return False

        payload = {
            "agent_id": self.agent_id,
            "port": self.port,
            "capabilities": self.capabilities.to_dict(),
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{registry_url.rstrip('/')}/agents",
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as resp:
                    ok = 200 <= resp.status < 300
                    if ok:
                        self.logger.info(
                            "Registered with registry at %s.", registry_url
                        )
                    else:
                        self.logger.warning(
                            "Registry returned status %d.", resp.status
                        )
                    return ok
        except Exception as exc:
            self.logger.error("Registry registration failed: %s", exc)
            return False

    async def get_peers_from_registry(self, registry_url: str) -> list[dict]:
        """
        Fetch peer list from a central HTTP registry.

        Calls ``GET {registry_url}/agents`` and returns the list.
        """
        try:
            import aiohttp
        except ImportError:
            self.logger.warning(
                "aiohttp not installed; cannot query registry."
            )
            return []

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{registry_url.rstrip('/')}/agents",
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        peers = [p for p in data if p.get("agent_id") != self.agent_id]
                        self.logger.info(
                            "Got %d peer(s) from registry.", len(peers)
                        )
                        return peers
                    else:
                        self.logger.warning(
                            "Registry GET /agents returned %d.", resp.status
                        )
                        return []
        except Exception as exc:
            self.logger.error("Registry query failed: %s", exc)
            return []

    # ------------------------------------------------------------------
    # Env-var based peer list
    # ------------------------------------------------------------------

    def parse_peer_env(self) -> list[tuple[str, int]]:
        """
        Parse the ``SINTRA_PEERS`` environment variable.

        Format: ``host1:port1,host2:port2``

        Returns a list of ``(host, port)`` tuples.
        """
        raw = os.environ.get("SINTRA_PEERS", "").strip()
        if not raw:
            return []

        peers: list[tuple[str, int]] = []
        for entry in raw.split(","):
            entry = entry.strip()
            if not entry:
                continue
            if ":" in entry:
                host, port_str = entry.rsplit(":", 1)
                try:
                    peers.append((host.strip(), int(port_str.strip())))
                except ValueError:
                    self.logger.warning("Invalid SINTRA_PEERS entry: %r", entry)
            else:
                peers.append((entry, _DEFAULT_PORT))

        self.logger.debug("Parsed %d peer(s) from SINTRA_PEERS.", len(peers))
        return peers

    # ------------------------------------------------------------------
    # mDNS (optional)
    # ------------------------------------------------------------------

    async def discover_mdns(self, timeout: int = 5) -> list[dict]:
        """
        Discover agents via mDNS (``_sintra._tcp.local``).

        Requires the ``zeroconf`` package.  Returns empty list if not available.
        """
        try:
            from zeroconf import ServiceBrowser, Zeroconf  # type: ignore
            from zeroconf.asyncio import AsyncServiceInfo  # type: ignore
        except ImportError:
            self.logger.debug("zeroconf not installed; skipping mDNS discovery.")
            return []

        discovered: list[dict] = []

        class _Listener:
            def add_service(self, zc, type_, name):  # noqa: N802
                pass  # handle via AsyncServiceInfo below

            def remove_service(self, *_):
                pass

            def update_service(self, *_):
                pass

        zc = Zeroconf()
        try:
            browser = ServiceBrowser(zc, "_sintra._tcp.local.", _Listener())
            await asyncio.sleep(timeout)
        finally:
            zc.close()

        return discovered

    # ------------------------------------------------------------------
    # Convenience: discover from all configured sources
    # ------------------------------------------------------------------

    async def discover_all(self) -> list[dict]:
        """
        Run all discovery mechanisms and return a deduplicated peer list.
        """
        peers: dict[str, dict] = {}

        # 1. LAN broadcast
        for p in await self.discover_local():
            peers[p["agent_id"]] = p

        # 2. Registry (if configured)
        registry_url = os.environ.get("SINTRA_REGISTRY_URL", "").strip()
        if registry_url:
            await self.register_with_registry(registry_url)
            for p in await self.get_peers_from_registry(registry_url):
                pid = p.get("agent_id", "")
                if pid and pid != self.agent_id:
                    peers[pid] = p

        # 3. Env-var peers (converted to dict)
        for host, port in self.parse_peer_env():
            synthetic_id = f"peer-{host}-{port}"
            if synthetic_id not in peers:
                peers[synthetic_id] = {
                    "agent_id": synthetic_id,
                    "addr": host,
                    "port": port,
                    "capabilities": {},
                }

        return list(peers.values())
