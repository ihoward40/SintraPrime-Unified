"""GitHub App Authentication for M3C - Least Privilege Credential.

This module implements GitHub App authentication with device flow,
providing fine-grained permissions restricted to the exact repository
and minimum permission required for the certified M2-B capability.
"""

from __future__ import annotations

import hashlib
import json
import os
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

import requests


class GitHubAppAuthStatus(Enum):
    """Authentication status."""
    UNINITIALIZED = "UNINITIALIZED"
    PENDING_AUTH = "PENDING_AUTH"
    AUTHENTICATED = "AUTHENTICATED"
    EXPIRED = "EXPIRED"
    REVOKED = "REVOKED"
    ERROR = "ERROR"


@dataclass(frozen=True)
class GitHubAppConfig:
    """GitHub App configuration for device flow."""
    client_id: str
    device_code_url: str = "https://github.com/login/device/code"
    token_url: str = "https://github.com/login/oauth/access_token"
    api_url: str = "https://api.github.com"
    # GitHub App device flow uses same scopes as OAuth App
    # Permissions are controlled by App configuration, not scopes
    timeout_seconds: int = 300
    poll_interval_seconds: int = 5
    
    # Expected least-privilege configuration
    expected_repository: str = "ihoward40/SintraPrime-Unified"
    expected_permissions: Dict[str, str] = field(default_factory=lambda: {
        "pull_requests": "write",
        "metadata": "read"
    })


@dataclass(frozen=True)
class GitHubAppTokenResponse:
    """GitHub App token response (REDACTED for safety)."""
    access_token_redacted: str
    token_type: str
    scope: str
    expires_in: Optional[int] = None
    refresh_token_redacted: Optional[str] = None

    @classmethod
    def from_raw(cls, raw: Dict[str, Any]) -> 'GitHubAppTokenResponse':
        """Create from raw response with redaction."""
        access_token = raw.get("access_token", "")
        refresh_token = raw.get("refresh_token")

        return cls(
            access_token_redacted=f"ghu_**REDACTED_{hashlib.sha256(access_token.encode()).hexdigest()[:8]}**",
            token_type=raw.get("token_type", "bearer"),
            scope=raw.get("scope", ""),
            expires_in=raw.get("expires_in"),
            refresh_token_redacted=f"ghr_**REDACTED_{hashlib.sha256(refresh_token.encode()).hexdigest()[:8]}**" if refresh_token else None
        )

    def to_safe_dict(self) -> Dict[str, Any]:
        """Return safe dict for logging/evidence."""
        return {
            "access_token_redacted": self.access_token_redacted,
            "token_type": self.token_type,
            "scope": self.scope,
            "expires_in": self.expires_in,
            "refresh_token_redacted": self.refresh_token_redacted
        }


@dataclass(frozen=True)
class GitHubAppUserIdentity:
    """GitHub authenticated user identity via GitHub App."""
    login: str
    account_id: int
    avatar_url: str
    html_url: str
    type: str
    name: Optional[str] = None
    email: Optional[str] = None
    public_repos: int = 0
    created_at: str = ""
    identity_hash: str = ""

    def __post_init__(self):
        if not self.identity_hash:
            content = f"{self.login}|{self.account_id}|{self.html_url}"
            object.__setattr__(self, 'identity_hash', hashlib.sha256(content.encode()).hexdigest())


@dataclass(frozen=True)
class GitHubAppInstallation:
    """GitHub App installation details."""
    installation_id: int
    account_login: str
    account_id: int
    repository_selection: str  # "all" or "selected"
    repositories: List[Dict[str, Any]]
    permissions: Dict[str, str]
    events: List[str]
    created_at: str
    updated_at: str

    def verify_least_privilege(self, expected_repo: str) -> Dict[str, Any]:
        """Verify installation matches least-privilege requirements."""
        results = {
            "single_repo": False,
            "correct_repo": False,
            "correct_permissions": False,
            "no_excess_permissions": False,
            "details": {}
        }
        
        # Check repository selection
        if self.repository_selection == "selected":
            results["single_repo"] = True
            repo_names = [r.get("full_name", "") for r in self.repositories]
            if expected_repo in repo_names and len(repo_names) == 1:
                results["correct_repo"] = True
                results["details"]["repositories"] = repo_names
        
        # Check permissions - pull_requests: write and metadata: read only
        expected_perms = {"pull_requests": "write", "metadata": "read"}
        actual_perms = {k: v for k, v in self.permissions.items() if v != "none"}
        if actual_perms == expected_perms:
            results["correct_permissions"] = True
            results["no_excess_permissions"] = True
        results["details"]["permissions"] = actual_perms
        
        results["overall_pass"] = all([
            results["single_repo"],
            results["correct_repo"],
            results["correct_permissions"],
            results["no_excess_permissions"]
        ])
        
        return results


@dataclass(frozen=True)
class GitHubAppAuthSession:
    """Complete authenticated session via GitHub App."""
    session_id: str
    config: GitHubAppConfig
    token: GitHubAppTokenResponse
    user: GitHubAppUserIdentity
    installation: Optional[GitHubAppInstallation]
    authenticated_at: float
    expires_at: Optional[float]
    status: GitHubAppAuthStatus = GitHubAppAuthStatus.AUTHENTICATED
    scopes_granted: List[str] = field(default_factory=list)

    def to_safe_dict(self) -> Dict[str, Any]:
        """Return safe dict for evidence (no raw tokens)."""
        return {
            "session_id": self.session_id,
            "client_id": self.config.client_id,
            "token": self.token.to_safe_dict(),
            "user": {
                "login": self.user.login,
                "account_id": self.user.account_id,
                "avatar_url": self.user.avatar_url,
                "html_url": self.user.html_url,
                "type": self.user.type,
                "name": self.user.name,
                "email": self.user.email,
                "public_repos": self.user.public_repos,
                "created_at": self.user.created_at,
                "identity_hash": self.user.identity_hash
            },
            "installation": self.installation.__dict__ if self.installation else None,
            "authenticated_at": self.authenticated_at,
            "expires_at": self.expires_at,
            "status": self.status.value,
            "scopes_granted": self.scopes_granted
        }


class GitHubAppAuthenticator:
    """Handles GitHub App device flow authentication with least-privilege verification."""

    def __init__(self, config: GitHubAppConfig):
        self.config = config
        self.session: Optional[GitHubAppAuthSession] = None
        self._raw_token: Optional[str] = None  # Only held in memory, never logged

    def start_device_flow(self) -> Dict[str, Any]:
        """Start GitHub device code flow for GitHub App."""
        data = {
            "client_id": self.config.client_id,
            # GitHub App device flow doesn't use scopes - permissions are from App config
        }
        headers = {"Accept": "application/json"}

        response = requests.post(self.config.device_code_url, data=data, headers=headers, timeout=30)
        response.raise_for_status()
        return response.json()

    def poll_for_token(self, device_code: str, interval: int) -> Optional[Dict[str, Any]]:
        """Poll for access token."""
        data = {
            "client_id": self.config.client_id,
            "device_code": device_code,
            "grant_type": "urn:ietf:params:oauth:grant-type:device_code"
        }
        headers = {"Accept": "application/json"}

        response = requests.post(self.config.token_url, data=data, headers=headers, timeout=30)

        if response.status_code == 200:
            return response.json()
        elif response.status_code == 400:
            error = response.json().get("error")
            if error == "authorization_pending":
                return None
            elif error == "slow_down":
                return {"error": "slow_down"}
            elif error in ("expired_token", "access_denied"):
                return {"error": error}
        return None

    def complete_device_auth(self, device_code: str, user_code: str, verification_uri: str) -> GitHubAppAuthSession:
        """Complete device code authentication flow."""
        print(f"\n=== GITHUB APP AUTHENTICATION REQUIRED ===")
        print(f"Visit: {verification_uri}")
        print(f"Enter code: {user_code}")
        print(f"Waiting for authorization...")

        start_time = time.time()
        interval = self.config.poll_interval_seconds

        while time.time() - start_time < self.config.timeout_seconds:
            result = self.poll_for_token(device_code, interval)
            if result:
                if "error" in result:
                    if result["error"] == "slow_down":
                        interval += 5
                        continue
                    else:
                        raise PermissionError(f"Authentication failed: {result['error']}")

                # Success - got token
                self._raw_token = result["access_token"]
                token_response = GitHubAppTokenResponse.from_raw(result)

                # Fetch user identity
                user = self.fetch_user_identity()

                # Fetch installations to verify least privilege
                installation = self.fetch_installation()

                # FAIL CLOSED: Installation binding required for M3C
                if installation is None:
                    raise PermissionError(
                        f"GitHub App installation not found for expected repository "
                        f"'{self.config.expected_repository}'. "
                        f"Installation binding required for M3C certification."
                    )

                # Determine expiry
                expires_in = result.get("expires_in")
                expires_at = time.time() + expires_in if expires_in else None

                # Parse granted scopes (GitHub App device flow returns scopes)
                scopes_granted = result.get("scope", "").split(",") if result.get("scope") else []

                self.session = GitHubAppAuthSession(
                    session_id=str(uuid.uuid4()),
                    config=self.config,
                    token=token_response,
                    user=user,
                    installation=installation,
                    authenticated_at=time.time(),
                    expires_at=expires_at,
                    scopes_granted=scopes_granted
                )

                print(f"Authenticated as: {user.login} ({user.html_url})")
                print(f"Installation: {installation.account_login}/{installation.repository_selection}")
                print(f"Permissions: {installation.permissions}")
                return self.session

            time.sleep(interval)

        raise TimeoutError("Authentication timed out")

    def fetch_user_identity(self) -> GitHubAppUserIdentity:
        """Fetch authenticated user identity from GitHub API."""
        if not self._raw_token:
            raise RuntimeError("Not authenticated")

        headers = {
            "Authorization": f"Bearer {self._raw_token}",
            "Accept": "application/vnd.github+json"
        }

        response = requests.get(f"{self.config.api_url}/user", headers=headers, timeout=30)
        response.raise_for_status()
        data = response.json()

        # Fetch emails
        email = None
        emails_resp = requests.get(f"{self.config.api_url}/user/emails", headers=headers, timeout=30)
        if emails_resp.status_code == 200:
            emails = emails_resp.json()
            primary = next((e for e in emails if e.get("primary")), None)
            if primary:
                email = primary.get("email")

        return GitHubAppUserIdentity(
            login=data["login"],
            account_id=data["id"],
            avatar_url=data["avatar_url"],
            html_url=data["html_url"],
            type=data["type"],
            name=data.get("name"),
            email=email,
            public_repos=data.get("public_repos", 0),
            created_at=data.get("created_at", "")
        )

    def fetch_installation(self) -> Optional[GitHubAppInstallation]:
        """Fetch GitHub App installation for the authenticated user."""
        if not self._raw_token:
            return None

        headers = {
            "Authorization": f"Bearer {self._raw_token}",
            "Accept": "application/vnd.github+json"
        }

        # Get user's installations
        response = requests.get(f"{self.config.api_url}/user/installations", headers=headers, timeout=30)
        if response.status_code != 200:
            return None

        data = response.json()
        installations = data.get("installations", [])
        
        if not installations:
            return None

        # Find installation for expected repository
        for inst in installations:
            inst_id = inst.get("id")
            # Get repositories for this installation
            repos_resp = requests.get(
                f"{self.config.api_url}/user/installations/{inst_id}/repositories",
                headers=headers,
                timeout=30
            )
            if repos_resp.status_code == 200:
                repos_data = repos_resp.json()
                repos = repos_data.get("repositories", [])
                repo_names = [r.get("full_name", "") for r in repos]
                if self.config.expected_repository in repo_names:
                    return GitHubAppInstallation(
                        installation_id=inst_id,
                        account_login=inst.get("account", {}).get("login", ""),
                        account_id=inst.get("account", {}).get("id", 0),
                        repository_selection=inst.get("repository_selection", ""),
                        repositories=repos,
                        permissions=inst.get("permissions", {}),
                        events=inst.get("events", []),
                        created_at=inst.get("created_at", ""),
                        updated_at=inst.get("updated_at", "")
                    )
        
        # Return first installation if expected not found
        # FAIL CLOSED: No fallback to first installation - must match expected repo exactly
        return None

    def verify_repository_access(self, owner: str, repo: str) -> Dict[str, Any]:
        """Verify repository access and return metadata."""
        if not self.session:
            raise RuntimeError("Not authenticated")

        headers = {
            "Authorization": f"Bearer {self._raw_token}",
            "Accept": "application/vnd.github+json"
        }

        response = requests.get(f"{self.config.api_url}/repos/{owner}/{repo}", headers=headers, timeout=30)

        if response.status_code == 404:
            return {"accessible": False, "reason": "Not found"}
        elif response.status_code == 403:
            return {"accessible": False, "reason": "Forbidden"}
        elif response.status_code != 200:
            return {"accessible": False, "reason": f"HTTP {response.status_code}"}

        data = response.json()
        return {
            "accessible": True,
            "repo_id": data["id"],
            "full_name": data["full_name"],
            "private": data["private"],
            "owner_login": data["owner"]["login"],
            "default_branch": data["default_branch"],
            "permissions": data.get("permissions", {}),
            "url": data["html_url"]
        }

    def verify_pr_access(self, owner: str, repo: str, pr_number: int) -> Dict[str, Any]:
        """Verify PR access."""
        if not self.session:
            raise RuntimeError("Not authenticated")

        headers = {
            "Authorization": f"Bearer {self._raw_token}",
            "Accept": "application/vnd.github+json"
        }

        response = requests.get(
            f"{self.config.api_url}/repos/{owner}/{repo}/pulls/{pr_number}",
            headers=headers,
            timeout=30
        )

        if response.status_code == 404:
            return {"accessible": False, "reason": "Not found"}
        elif response.status_code == 403:
            return {"accessible": False, "reason": "Forbidden"}
        elif response.status_code != 200:
            return {"accessible": False, "reason": f"HTTP {response.status_code}"}

        data = response.json()
        return {
            "accessible": True,
            "pr_id": data["id"],
            "number": data["number"],
            "title": data["title"],
            "state": data["state"],
            "url": data["html_url"],
            "author": data["user"]["login"]
        }

    def dry_run_pr_comment_create(
        self,
        owner: str,
        repo: str,
        pr_number: int,
        body: str
    ) -> Dict[str, Any]:
        """Perform zero-write dry run: verify we COULD create PR comment without doing so."""
        if not self.session:
            raise RuntimeError("Not authenticated")

        # Verify repo access
        repo_check = self.verify_repository_access(owner, repo)
        if not repo_check["accessible"]:
            return {"success": False, "reason": f"Repository access failed: {repo_check['reason']}"}

        # Verify PR access
        pr_check = self.verify_pr_access(owner, repo, pr_number)
        if not pr_check["accessible"]:
            return {"success": False, "reason": f"PR access failed: {pr_check['reason']}"}

        # Check permissions - need pull_requests: write
        permissions = repo_check.get("permissions", {})
        # Note: PR comment creation requires pull_requests: write or issues: write
        # We verify the App has the correct permissions
        installation = self.session.installation
        if not installation:
            return {"success": False, "reason": "No installation found"}

        perm_check = installation.verify_least_privilege(f"{owner}/{repo}")
        if not perm_check["overall_pass"]:
            return {"success": False, "reason": f"Installation permissions not least-privilege: {perm_check}"}

        # Check if PR is open
        if pr_check.get("state") != "open":
            return {"success": False, "reason": f"PR is not open: {pr_check.get('state')}"}

        # All checks pass - we could create comment
        return {
            "success": True,
            "repository": repo_check,
            "target": pr_check,
            "would_post_to": f"{self.config.api_url}/repos/{owner}/{repo}/issues/{pr_number}/comments",
            "body_length": len(body),
            "body_hash": hashlib.sha256(body.encode()).hexdigest()
        }

    def get_rate_limit(self) -> Dict[str, Any]:
        """Get current rate limit status."""
        if not self.session:
            raise RuntimeError("Not authenticated")

        headers = {
            "Authorization": f"Bearer {self._raw_token}",
            "Accept": "application/vnd.github+json"
        }

        response = requests.get(f"{self.config.api_url}/rate_limit", headers=headers, timeout=30)
        if response.status_code == 200:
            return response.json()
        return {}


def create_app_config_from_env() -> GitHubAppConfig:
    """Create app config from environment variables."""
    client_id = os.environ.get("GITHUB_APP_CLIENT_ID")
    if not client_id:
        raise ValueError("GITHUB_APP_CLIENT_ID environment variable required")

    return GitHubAppConfig(client_id=client_id)