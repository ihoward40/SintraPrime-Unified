"""
Document Management System (DMS) Connectors for SintraPrime-Unified.

Supports:
  - NetDocuments (REST API)
  - iManage Work (REST API)
  - Worldox (file system + API)
  - Clio Manage (REST API)
  - MyCase (REST API)
  - PracticePanther (REST API)

All credentials are loaded from environment variables — never hard-coded.
"""

from __future__ import annotations

import abc
import logging
import os
from dataclasses import dataclass, field
from typing import Any, BinaryIO, Dict, List, Optional
from urllib.parse import urljoin

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

DEFAULT_TIMEOUT = 30  # seconds


def _build_session(retries: int = 3, backoff: float = 0.5) -> requests.Session:
    """Return a requests.Session with retry logic."""
    session = requests.Session()
    retry = Retry(
        total=retries,
        backoff_factor=backoff,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------


@dataclass
class DMSDocument:
    """Represents a document returned by or sent to a DMS."""

    doc_id: str
    name: str
    matter_id: Optional[str] = None
    version: Optional[str] = None
    content_type: str = "application/octet-stream"
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DMSMatter:
    """Represents a matter/case in a DMS."""

    matter_id: str
    name: str
    client_name: Optional[str] = None
    status: str = "open"
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SearchResult:
    """Single search hit from a DMS search."""

    doc_id: str
    name: str
    score: float = 0.0
    snippet: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Abstract base class
# ---------------------------------------------------------------------------


class DMSConnector(abc.ABC):
    """Abstract base class for all DMS connectors."""

    name: str = "base"

    def __init__(self) -> None:
        self._session = _build_session()

    # ------------------------------------------------------------------
    # Abstract interface
    # ------------------------------------------------------------------

    @abc.abstractmethod
    def authenticate(self) -> None:
        """Perform authentication and configure session headers."""

    @abc.abstractmethod
    def upload_document(
        self,
        matter_id: str,
        filename: str,
        content: BinaryIO,
        content_type: str = "application/pdf",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> DMSDocument:
        """Upload a document to the DMS and return its metadata."""

    @abc.abstractmethod
    def download_document(self, doc_id: str) -> bytes:
        """Download a document by ID and return its raw bytes."""

    @abc.abstractmethod
    def search(self, query: str, matter_id: Optional[str] = None, limit: int = 25) -> List[SearchResult]:
        """Full-text search across the DMS."""

    @abc.abstractmethod
    def create_matter(self, name: str, client_name: str, **kwargs: Any) -> DMSMatter:
        """Create a new matter/case in the DMS."""

    @abc.abstractmethod
    def list_matters(self, status: str = "open", limit: int = 50) -> List[DMSMatter]:
        """List matters, optionally filtered by status."""

    # ------------------------------------------------------------------
    # Shared helpers
    # ------------------------------------------------------------------

    def _get(self, url: str, **kwargs: Any) -> requests.Response:
        resp = self._session.get(url, timeout=DEFAULT_TIMEOUT, **kwargs)
        resp.raise_for_status()
        return resp

    def _post(self, url: str, **kwargs: Any) -> requests.Response:
        resp = self._session.post(url, timeout=DEFAULT_TIMEOUT, **kwargs)
        resp.raise_for_status()
        return resp

    def _put(self, url: str, **kwargs: Any) -> requests.Response:
        resp = self._session.put(url, timeout=DEFAULT_TIMEOUT, **kwargs)
        resp.raise_for_status()
        return resp

    def _delete(self, url: str, **kwargs: Any) -> requests.Response:
        resp = self._session.delete(url, timeout=DEFAULT_TIMEOUT, **kwargs)
        resp.raise_for_status()
        return resp


# ---------------------------------------------------------------------------
# NetDocuments
# ---------------------------------------------------------------------------


class NetDocumentsConnector(DMSConnector):
    """
    NetDocuments REST API connector.

    Env vars:
        NETDOCUMENTS_CLIENT_ID
        NETDOCUMENTS_CLIENT_SECRET
        NETDOCUMENTS_CABINET_ID
        NETDOCUMENTS_BASE_URL  (default https://api.netdocuments.com/v2)
    """

    name = "netdocuments"
    _TOKEN_URL = "https://api.netdocuments.com/v2/OAuth"

    def __init__(self) -> None:
        super().__init__()
        self._client_id = os.environ["NETDOCUMENTS_CLIENT_ID"]
        self._client_secret = os.environ["NETDOCUMENTS_CLIENT_SECRET"]
        self._cabinet_id = os.environ["NETDOCUMENTS_CABINET_ID"]
        self._base_url = os.getenv("NETDOCUMENTS_BASE_URL", "https://api.netdocuments.com/v2")
        self._access_token: Optional[str] = None

    def authenticate(self) -> None:
        resp = self._session.post(
            self._TOKEN_URL,
            data={
                "grant_type": "client_credentials",
                "client_id": self._client_id,
                "client_secret": self._client_secret,
                "scope": "full",
            },
            timeout=DEFAULT_TIMEOUT,
        )
        resp.raise_for_status()
        self._access_token = resp.json()["access_token"]
        self._session.headers.update({"Authorization": f"Bearer {self._access_token}"})
        logger.info("NetDocuments: authenticated successfully")

    def upload_document(
        self,
        matter_id: str,
        filename: str,
        content: BinaryIO,
        content_type: str = "application/pdf",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> DMSDocument:
        url = urljoin(self._base_url, f"/v2/Document")
        payload = {
            "cabinet": self._cabinet_id,
            "matter": matter_id,
            "fileName": filename,
        }
        if metadata:
            payload.update(metadata)
        files = {"file": (filename, content, content_type)}
        resp = self._post(url, data=payload, files=files)
        data = resp.json()
        return DMSDocument(
            doc_id=data["docId"],
            name=data.get("name", filename),
            matter_id=matter_id,
            version=data.get("version", "1"),
            content_type=content_type,
            metadata=data,
        )

    def download_document(self, doc_id: str) -> bytes:
        url = urljoin(self._base_url, f"/v2/Document/{doc_id}/download")
        resp = self._get(url)
        return resp.content

    def search(self, query: str, matter_id: Optional[str] = None, limit: int = 25) -> List[SearchResult]:
        url = urljoin(self._base_url, "/v2/Search")
        params: Dict[str, Any] = {"q": query, "cabinet": self._cabinet_id, "count": limit}
        if matter_id:
            params["matter"] = matter_id
        resp = self._get(url, params=params)
        results = []
        for item in resp.json().get("results", []):
            results.append(
                SearchResult(
                    doc_id=item["docId"],
                    name=item.get("name", ""),
                    score=item.get("score", 0.0),
                    snippet=item.get("snippet"),
                    metadata=item,
                )
            )
        return results

    def create_matter(self, name: str, client_name: str, **kwargs: Any) -> DMSMatter:
        url = urljoin(self._base_url, "/v2/Matter")
        payload = {"name": name, "clientName": client_name, "cabinet": self._cabinet_id, **kwargs}
        resp = self._post(url, json=payload)
        data = resp.json()
        return DMSMatter(matter_id=data["matterId"], name=data.get("name", name), client_name=client_name, metadata=data)

    def list_matters(self, status: str = "open", limit: int = 50) -> List[DMSMatter]:
        url = urljoin(self._base_url, "/v2/Matters")
        resp = self._get(url, params={"status": status, "count": limit, "cabinet": self._cabinet_id})
        matters = []
        for item in resp.json().get("matters", []):
            matters.append(
                DMSMatter(
                    matter_id=item["matterId"],
                    name=item.get("name", ""),
                    client_name=item.get("clientName"),
                    status=item.get("status", status),
                    metadata=item,
                )
            )
        return matters


# ---------------------------------------------------------------------------
# iManage Work
# ---------------------------------------------------------------------------


class IManageConnector(DMSConnector):
    """
    iManage Work REST API connector.

    Env vars:
        IMANAGE_CLIENT_ID
        IMANAGE_CLIENT_SECRET
        IMANAGE_SERVER_URL      (e.g. https://myserver.imanage.com)
        IMANAGE_CUSTOMER_ID
        IMANAGE_LIBRARY
    """

    name = "imanage"

    def __init__(self) -> None:
        super().__init__()
        self._client_id = os.environ["IMANAGE_CLIENT_ID"]
        self._client_secret = os.environ["IMANAGE_CLIENT_SECRET"]
        self._server_url = os.environ["IMANAGE_SERVER_URL"].rstrip("/")
        self._customer_id = os.environ["IMANAGE_CUSTOMER_ID"]
        self._library = os.environ["IMANAGE_LIBRARY"]
        self._access_token: Optional[str] = None

    def authenticate(self) -> None:
        url = f"{self._server_url}/auth/oauth2/token"
        resp = self._session.post(
            url,
            data={
                "grant_type": "client_credentials",
                "client_id": self._client_id,
                "client_secret": self._client_secret,
                "scope": "openid",
            },
            timeout=DEFAULT_TIMEOUT,
        )
        resp.raise_for_status()
        self._access_token = resp.json()["access_token"]
        self._session.headers.update({"X-Auth-Token": self._access_token})
        logger.info("iManage: authenticated successfully")

    def _api(self, path: str) -> str:
        return f"{self._server_url}/work/api/v2/customers/{self._customer_id}/{path}"

    def upload_document(
        self,
        matter_id: str,
        filename: str,
        content: BinaryIO,
        content_type: str = "application/pdf",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> DMSDocument:
        url = self._api(f"libraries/{self._library}/documents")
        meta = {"document_number": matter_id, "name": filename, **(metadata or {})}
        files = {"file": (filename, content, content_type)}
        resp = self._post(url, data=meta, files=files)
        data = resp.json().get("data", {})
        return DMSDocument(
            doc_id=data.get("id", ""),
            name=data.get("name", filename),
            matter_id=matter_id,
            version=str(data.get("version", 1)),
            content_type=content_type,
            metadata=data,
        )

    def download_document(self, doc_id: str) -> bytes:
        url = self._api(f"libraries/{self._library}/documents/{doc_id}/download")
        resp = self._get(url)
        return resp.content

    def search(self, query: str, matter_id: Optional[str] = None, limit: int = 25) -> List[SearchResult]:
        url = self._api(f"libraries/{self._library}/search")
        params: Dict[str, Any] = {"q": query, "limit": limit}
        if matter_id:
            params["workspace_id"] = matter_id
        resp = self._get(url, params=params)
        results = []
        for item in resp.json().get("data", {}).get("results", []):
            results.append(
                SearchResult(
                    doc_id=item.get("id", ""),
                    name=item.get("name", ""),
                    score=item.get("score", 0.0),
                    snippet=item.get("summary"),
                    metadata=item,
                )
            )
        return results

    def create_matter(self, name: str, client_name: str, **kwargs: Any) -> DMSMatter:
        url = self._api(f"libraries/{self._library}/workspaces")
        payload = {"name": name, "description": client_name, **kwargs}
        resp = self._post(url, json=payload)
        data = resp.json().get("data", {})
        return DMSMatter(matter_id=data.get("id", ""), name=name, client_name=client_name, metadata=data)

    def list_matters(self, status: str = "open", limit: int = 50) -> List[DMSMatter]:
        url = self._api(f"libraries/{self._library}/workspaces")
        resp = self._get(url, params={"limit": limit})
        matters = []
        for item in resp.json().get("data", {}).get("workspaces", []):
            matters.append(
                DMSMatter(
                    matter_id=item.get("id", ""),
                    name=item.get("name", ""),
                    status=status,
                    metadata=item,
                )
            )
        return matters


# ---------------------------------------------------------------------------
# Worldox
# ---------------------------------------------------------------------------


class WorldoxConnector(DMSConnector):
    """
    Worldox connector — hybrid file-system + REST API approach.

    Env vars:
        WORLDOX_API_URL
        WORLDOX_API_KEY
        WORLDOX_USERNAME
        WORLDOX_PASSWORD
    """

    name = "worldox"

    def __init__(self) -> None:
        super().__init__()
        self._api_url = os.environ["WORLDOX_API_URL"].rstrip("/")
        self._api_key = os.environ["WORLDOX_API_KEY"]
        self._username = os.environ["WORLDOX_USERNAME"]
        self._password = os.environ["WORLDOX_PASSWORD"]
        self._token: Optional[str] = None

    def authenticate(self) -> None:
        resp = self._session.post(
            f"{self._api_url}/api/authenticate",
            json={"username": self._username, "password": self._password},
            headers={"X-API-Key": self._api_key},
            timeout=DEFAULT_TIMEOUT,
        )
        resp.raise_for_status()
        self._token = resp.json().get("token")
        self._session.headers.update({"X-API-Key": self._api_key, "X-Auth-Token": self._token})
        logger.info("Worldox: authenticated successfully")

    def upload_document(
        self,
        matter_id: str,
        filename: str,
        content: BinaryIO,
        content_type: str = "application/pdf",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> DMSDocument:
        url = f"{self._api_url}/api/documents/upload"
        files = {"file": (filename, content, content_type)}
        data = {"matterId": matter_id, "filename": filename, **(metadata or {})}
        resp = self._post(url, files=files, data=data)
        result = resp.json()
        return DMSDocument(
            doc_id=result.get("docId", ""),
            name=filename,
            matter_id=matter_id,
            content_type=content_type,
            metadata=result,
        )

    def download_document(self, doc_id: str) -> bytes:
        url = f"{self._api_url}/api/documents/{doc_id}/content"
        resp = self._get(url)
        return resp.content

    def search(self, query: str, matter_id: Optional[str] = None, limit: int = 25) -> List[SearchResult]:
        url = f"{self._api_url}/api/documents/search"
        params: Dict[str, Any] = {"query": query, "limit": limit}
        if matter_id:
            params["matterId"] = matter_id
        resp = self._get(url, params=params)
        results = []
        for item in resp.json().get("documents", []):
            results.append(
                SearchResult(doc_id=item.get("docId", ""), name=item.get("name", ""), metadata=item)
            )
        return results

    def create_matter(self, name: str, client_name: str, **kwargs: Any) -> DMSMatter:
        url = f"{self._api_url}/api/matters"
        resp = self._post(url, json={"name": name, "clientName": client_name, **kwargs})
        data = resp.json()
        return DMSMatter(matter_id=data.get("matterId", ""), name=name, client_name=client_name, metadata=data)

    def list_matters(self, status: str = "open", limit: int = 50) -> List[DMSMatter]:
        url = f"{self._api_url}/api/matters"
        resp = self._get(url, params={"status": status, "limit": limit})
        return [
            DMSMatter(
                matter_id=m.get("matterId", ""),
                name=m.get("name", ""),
                client_name=m.get("clientName"),
                status=m.get("status", status),
                metadata=m,
            )
            for m in resp.json().get("matters", [])
        ]


# ---------------------------------------------------------------------------
# Clio Manage
# ---------------------------------------------------------------------------


class ClioConnector(DMSConnector):
    """
    Clio Manage REST API connector (OAuth2).

    Env vars:
        CLIO_CLIENT_ID
        CLIO_CLIENT_SECRET
        CLIO_REFRESH_TOKEN
        CLIO_BASE_URL   (default https://app.clio.com/api/v4)
    """

    name = "clio"
    _TOKEN_URL = "https://app.clio.com/oauth/token"

    def __init__(self) -> None:
        super().__init__()
        self._client_id = os.environ["CLIO_CLIENT_ID"]
        self._client_secret = os.environ["CLIO_CLIENT_SECRET"]
        self._refresh_token = os.environ["CLIO_REFRESH_TOKEN"]
        self._base_url = os.getenv("CLIO_BASE_URL", "https://app.clio.com/api/v4")
        self._access_token: Optional[str] = None

    def authenticate(self) -> None:
        resp = self._session.post(
            self._TOKEN_URL,
            data={
                "grant_type": "refresh_token",
                "client_id": self._client_id,
                "client_secret": self._client_secret,
                "refresh_token": self._refresh_token,
            },
            timeout=DEFAULT_TIMEOUT,
        )
        resp.raise_for_status()
        payload = resp.json()
        self._access_token = payload["access_token"]
        self._session.headers.update({"Authorization": f"Bearer {self._access_token}"})
        logger.info("Clio: authenticated successfully")

    def upload_document(
        self,
        matter_id: str,
        filename: str,
        content: BinaryIO,
        content_type: str = "application/pdf",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> DMSDocument:
        # Step 1: create document stub
        stub_url = f"{self._base_url}/documents"
        stub_payload: Dict[str, Any] = {
            "data": {
                "name": filename,
                "parent": {"id": int(matter_id), "type": "Matter"},
            }
        }
        if metadata:
            stub_payload["data"].update(metadata)
        stub_resp = self._post(stub_url, json=stub_payload)
        doc_data = stub_resp.json().get("data", {})
        doc_id = str(doc_data.get("id", ""))
        put_url = doc_data.get("latest_document_version", {}).get("put_url", "")
        # Step 2: upload content to pre-signed URL
        if put_url:
            requests.put(put_url, data=content, headers={"Content-Type": content_type}, timeout=DEFAULT_TIMEOUT)
        # Step 3: mark upload complete
        self._patch_upload_complete(doc_id, doc_data)
        return DMSDocument(
            doc_id=doc_id,
            name=filename,
            matter_id=matter_id,
            content_type=content_type,
            metadata=doc_data,
        )

    def _patch_upload_complete(self, doc_id: str, doc_data: Dict[str, Any]) -> None:
        version_id = doc_data.get("latest_document_version", {}).get("id")
        if version_id:
            url = f"{self._base_url}/document_versions/{version_id}"
            self._session.patch(
                url,
                json={"data": {"uuid": doc_data.get("latest_document_version", {}).get("uuid", "")}},
                timeout=DEFAULT_TIMEOUT,
            )

    def download_document(self, doc_id: str) -> bytes:
        url = f"{self._base_url}/documents/{doc_id}/download"
        resp = self._get(url)
        return resp.content

    def search(self, query: str, matter_id: Optional[str] = None, limit: int = 25) -> List[SearchResult]:
        url = f"{self._base_url}/documents"
        params: Dict[str, Any] = {"query": query, "limit": limit, "fields": "id,name,parent"}
        if matter_id:
            params["matter_id"] = matter_id
        resp = self._get(url, params=params)
        return [
            SearchResult(
                doc_id=str(item.get("id", "")),
                name=item.get("name", ""),
                metadata=item,
            )
            for item in resp.json().get("data", [])
        ]

    def create_matter(self, name: str, client_name: str, **kwargs: Any) -> DMSMatter:
        url = f"{self._base_url}/matters"
        resp = self._post(url, json={"data": {"description": name, "client": {"name": client_name}, **kwargs}})
        data = resp.json().get("data", {})
        return DMSMatter(
            matter_id=str(data.get("id", "")),
            name=data.get("description", name),
            client_name=client_name,
            metadata=data,
        )

    def list_matters(self, status: str = "open", limit: int = 50) -> List[DMSMatter]:
        url = f"{self._base_url}/matters"
        resp = self._get(url, params={"status": status, "limit": limit, "fields": "id,description,status,client"})
        return [
            DMSMatter(
                matter_id=str(m.get("id", "")),
                name=m.get("description", ""),
                client_name=(m.get("client") or {}).get("name"),
                status=m.get("status", status),
                metadata=m,
            )
            for m in resp.json().get("data", [])
        ]


# ---------------------------------------------------------------------------
# MyCase
# ---------------------------------------------------------------------------


class MyCaseConnector(DMSConnector):
    """
    MyCase REST API connector (API key auth).

    Env vars:
        MYCASE_API_KEY
        MYCASE_BASE_URL  (default https://api.mycase.com/v1)
    """

    name = "mycase"

    def __init__(self) -> None:
        super().__init__()
        self._api_key = os.environ["MYCASE_API_KEY"]
        self._base_url = os.getenv("MYCASE_BASE_URL", "https://api.mycase.com/v1")

    def authenticate(self) -> None:
        self._session.headers.update({"Authorization": f"Token {self._api_key}", "Accept": "application/json"})
        logger.info("MyCase: API key configured")

    def upload_document(
        self,
        matter_id: str,
        filename: str,
        content: BinaryIO,
        content_type: str = "application/pdf",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> DMSDocument:
        url = f"{self._base_url}/cases/{matter_id}/documents"
        files = {"document[file]": (filename, content, content_type)}
        resp = self._post(url, files=files)
        data = resp.json()
        return DMSDocument(
            doc_id=str(data.get("id", "")),
            name=data.get("filename", filename),
            matter_id=matter_id,
            content_type=content_type,
            metadata=data,
        )

    def download_document(self, doc_id: str) -> bytes:
        url = f"{self._base_url}/documents/{doc_id}/download"
        resp = self._get(url)
        return resp.content

    def search(self, query: str, matter_id: Optional[str] = None, limit: int = 25) -> List[SearchResult]:
        params: Dict[str, Any] = {"q": query, "per_page": limit}
        if matter_id:
            url = f"{self._base_url}/cases/{matter_id}/documents"
        else:
            url = f"{self._base_url}/documents"
        resp = self._get(url, params=params)
        return [
            SearchResult(doc_id=str(d.get("id", "")), name=d.get("filename", ""), metadata=d)
            for d in resp.json().get("documents", [])
        ]

    def create_matter(self, name: str, client_name: str, **kwargs: Any) -> DMSMatter:
        url = f"{self._base_url}/cases"
        resp = self._post(url, json={"case": {"name": name, "client_name": client_name, **kwargs}})
        data = resp.json().get("case", {})
        return DMSMatter(matter_id=str(data.get("id", "")), name=name, client_name=client_name, metadata=data)

    def list_matters(self, status: str = "open", limit: int = 50) -> List[DMSMatter]:
        url = f"{self._base_url}/cases"
        resp = self._get(url, params={"status": status, "per_page": limit})
        return [
            DMSMatter(
                matter_id=str(c.get("id", "")),
                name=c.get("name", ""),
                client_name=c.get("client_name"),
                status=c.get("status", status),
                metadata=c,
            )
            for c in resp.json().get("cases", [])
        ]


# ---------------------------------------------------------------------------
# PracticePanther
# ---------------------------------------------------------------------------


class PracticePantherConnector(DMSConnector):
    """
    PracticePanther REST API connector.

    Env vars:
        PRACTICEPANTHER_ACCESS_TOKEN
        PRACTICEPANTHER_BASE_URL  (default https://api.practicepanther.com/v1)
    """

    name = "practicepanther"

    def __init__(self) -> None:
        super().__init__()
        self._access_token = os.environ["PRACTICEPANTHER_ACCESS_TOKEN"]
        self._base_url = os.getenv("PRACTICEPANTHER_BASE_URL", "https://api.practicepanther.com/v1")

    def authenticate(self) -> None:
        self._session.headers.update(
            {"Authorization": f"Bearer {self._access_token}", "Content-Type": "application/json"}
        )
        logger.info("PracticePanther: access token configured")

    def upload_document(
        self,
        matter_id: str,
        filename: str,
        content: BinaryIO,
        content_type: str = "application/pdf",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> DMSDocument:
        url = f"{self._base_url}/documents"
        files = {"file": (filename, content, content_type)}
        data: Dict[str, Any] = {"matter_id": matter_id, "name": filename}
        if metadata:
            data.update(metadata)
        resp = self._post(url, files=files, data=data)
        result = resp.json()
        return DMSDocument(
            doc_id=str(result.get("id", "")),
            name=result.get("name", filename),
            matter_id=matter_id,
            content_type=content_type,
            metadata=result,
        )

    def download_document(self, doc_id: str) -> bytes:
        url = f"{self._base_url}/documents/{doc_id}/download"
        resp = self._get(url)
        return resp.content

    def search(self, query: str, matter_id: Optional[str] = None, limit: int = 25) -> List[SearchResult]:
        url = f"{self._base_url}/documents"
        params: Dict[str, Any] = {"search": query, "per_page": limit}
        if matter_id:
            params["matter_id"] = matter_id
        resp = self._get(url, params=params)
        return [
            SearchResult(doc_id=str(d.get("id", "")), name=d.get("name", ""), metadata=d)
            for d in resp.json().get("data", [])
        ]

    def create_matter(self, name: str, client_name: str, **kwargs: Any) -> DMSMatter:
        url = f"{self._base_url}/matters"
        resp = self._post(url, json={"name": name, "client_name": client_name, **kwargs})
        data = resp.json()
        return DMSMatter(matter_id=str(data.get("id", "")), name=name, client_name=client_name, metadata=data)

    def list_matters(self, status: str = "open", limit: int = 50) -> List[DMSMatter]:
        url = f"{self._base_url}/matters"
        resp = self._get(url, params={"status": status, "per_page": limit})
        return [
            DMSMatter(
                matter_id=str(m.get("id", "")),
                name=m.get("name", ""),
                client_name=m.get("client_name"),
                status=m.get("status", status),
                metadata=m,
            )
            for m in resp.json().get("data", [])
        ]


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

_DMS_REGISTRY: Dict[str, type] = {
    "netdocuments": NetDocumentsConnector,
    "imanage": IManageConnector,
    "worldox": WorldoxConnector,
    "clio": ClioConnector,
    "mycase": MyCaseConnector,
    "practicepanther": PracticePantherConnector,
}


def get_dms_connector(platform: str) -> DMSConnector:
    """
    Factory function — return an authenticated DMSConnector for *platform*.

    Args:
        platform: One of 'netdocuments', 'imanage', 'worldox', 'clio',
                  'mycase', 'practicepanther'.

    Returns:
        An authenticated DMSConnector instance.

    Raises:
        ValueError: If *platform* is not recognised.
        KeyError: If required environment variables are missing.
    """
    cls = _DMS_REGISTRY.get(platform.lower())
    if cls is None:
        raise ValueError(f"Unknown DMS platform: {platform!r}. Choices: {list(_DMS_REGISTRY)}")
    connector: DMSConnector = cls()
    connector.authenticate()
    return connector
