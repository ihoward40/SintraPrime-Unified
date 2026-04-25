"""
Slack OAuth 2.0 Authentication Module

Handles OAuth flow, token management, and credential storage for Slack integration.
"""

import hashlib
import hmac
import json
import logging
import secrets
import time
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple
from urllib.parse import urlencode
import sqlite3

logger = logging.getLogger(__name__)


# Global dictionary to keep in-memory database connections alive
_SHARED_DB_CONNECTIONS = {}


def _get_db_connection(db_path: str):
    """
    Get a database connection with proper URI handling.
    
    For shared in-memory databases (file::memory:?cache=shared), we keep the
    connection open in a global dict to prevent the database from being destroyed
    when all user connections are closed.
    
    Args:
        db_path: Database path or URI
        
    Returns:
        SQLite connection object
    """
    # Check if db_path is a shared in-memory URI
    if 'file::memory:' in db_path:
        # Keep a persistent connection open for shared in-memory databases
        if db_path not in _SHARED_DB_CONNECTIONS:
            conn = sqlite3.connect(db_path, uri=True, check_same_thread=False)
            _SHARED_DB_CONNECTIONS[db_path] = conn
            logger.debug(f"Created persistent connection for shared in-memory DB: {db_path}")
        # Return a new connection, the persistent one ensures the DB stays alive
        return sqlite3.connect(db_path, uri=True, check_same_thread=False)
    elif db_path.startswith('file:'):
        return sqlite3.connect(db_path, uri=True)
    else:
        return sqlite3.connect(db_path)


class SlackAuthManager:
    """Manages OAuth 2.0 authentication with Slack."""

    SLACK_OAUTH_URL = "https://slack.com/oauth/v2/authorize"
    SLACK_TOKEN_URL = "https://slack.com/api/oauth.v2.access"
    SLACK_SCOPES = [
        "app_mentions:read",
        "channels:history",
        "channels:read",
        "channels:manage",
        "chat:write",
        "commands",
        "groups:history",
        "groups:read",
        "im:history",
        "im:read",
        "mpim:history",
        "mpim:read",
        "reactions:read",
        "reactions:write",
        "users:read",
        "users:read.email",
        "team:read",
        "incoming-webhook",
    ]

    def __init__(self, client_id: str, client_secret: str, db_path: str = "slack.db"):
        """
        Initialize Slack auth manager.

        Args:
            client_id: Slack app client ID
            client_secret: Slack app client secret
            db_path: Path to SQLite database for storing credentials
        """
        self.client_id = client_id
        self.client_secret = client_secret
        self.db_path = db_path
        self._init_db()
        self._oauth_states = {}  # In-memory state tracking (should use Redis in production)

    def _init_db(self):
        """Initialize database for storing team credentials."""
        try:
            conn = _get_db_connection(self.db_path)
            cursor = conn.cursor()
            
            # Create slack_teams table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS slack_teams (
                    team_id TEXT PRIMARY KEY,
                    team_name TEXT NOT NULL,
                    bot_token TEXT NOT NULL,
                    access_token TEXT NOT NULL,
                    installed_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            conn.commit()
            conn.close()
            logger.debug(f"Database initialized: {self.db_path}")
        except Exception as e:
            logger.error(f"Database initialization failed: {e}")
            raise

    def generate_oauth_url(self, redirect_uri: str, team_id: Optional[str] = None) -> Tuple[str, str]:
        """
        Generate OAuth authorization URL.

        Args:
            redirect_uri: Callback URI for OAuth redirect
            team_id: Optional workspace team ID for workspace-specific installation

        Returns:
            Tuple of (authorization_url, state_token)
        """
        state = secrets.token_urlsafe(32)
        self._oauth_states[state] = {
            "created_at": time.time(),
            "team_id": team_id,
            "redirect_uri": redirect_uri,
        }

        params = {
            "client_id": self.client_id,
            "scope": ",".join(self.SLACK_SCOPES),
            "redirect_uri": redirect_uri,
            "state": state,
        }

        if team_id:
            params["team"] = team_id

        url = f"{self.SLACK_OAUTH_URL}?{urlencode(params)}"
        logger.debug(f"Generated OAuth URL for state {state}")
        return url, state

    def validate_state(self, state: str, max_age: int = 600) -> bool:
        """
        Validate OAuth state token.

        Args:
            state: State token to validate
            max_age: Maximum age of state token in seconds (default 10 minutes)

        Returns:
            True if state is valid, False otherwise
        """
        if state not in self._oauth_states:
            logger.warning(f"Invalid state token: {state}")
            return False

        state_data = self._oauth_states[state]
        age = time.time() - state_data["created_at"]

        if age > max_age:
            logger.warning(f"State token expired: {state} (age: {age}s)")
            del self._oauth_states[state]
            return False

        return True

    def exchange_code_for_tokens(
        self, code: str, redirect_uri: str, state: str
    ) -> Optional[Dict]:
        """
        Exchange authorization code for access tokens.

        Args:
            code: Authorization code from OAuth callback
            redirect_uri: Redirect URI used in authorization request
            state: State token from authorization request

        Returns:
            Dictionary with bot_token, access_token, and team info, or None if failed
        """
        if not self.validate_state(state):
            logger.error("Invalid or expired state token")
            return None

        import requests

        try:
            response = requests.post(
                self.SLACK_TOKEN_URL,
                data={
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "code": code,
                    "redirect_uri": redirect_uri,
                },
                timeout=10,
            )

            if response.status_code != 200:
                logger.error(f"Token exchange failed: {response.text}")
                return None

            data = response.json()

            if not data.get("ok"):
                logger.error(f"Slack API error: {data.get('error')}")
                return None

            # Clean up state token
            del self._oauth_states[state]

            logger.info(f"Successfully exchanged code for tokens (team: {data['team_id']})")
            return {
                "bot_token": data.get("bot_token"),
                "access_token": data.get("access_token"),
                "team_id": data.get("team_id"),
                "team_name": data.get("team_name"),
                "user_id": data.get("user_id"),
                "app_id": data.get("app_id"),
                "scope": data.get("scope", ""),
            }
        except Exception as e:
            logger.error(f"Error exchanging code for tokens: {e}")
            return None

    def save_team_credentials(
        self, team_id: str, team_name: str, bot_token: str, access_token: str
    ) -> bool:
        """
        Save team credentials to database.

        Args:
            team_id: Slack workspace team ID
            team_name: Slack workspace name
            bot_token: Bot token for app-level operations
            access_token: User-level access token

        Returns:
            True if saved successfully, False otherwise
        """
        try:
            conn = _get_db_connection(self.db_path)
            cursor = conn.cursor()

            cursor.execute(
                """
                INSERT OR REPLACE INTO slack_teams
                (team_id, team_name, bot_token, access_token, updated_at)
                VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
                """,
                (team_id, team_name, bot_token, access_token),
            )
            conn.commit()
            conn.close()

            logger.info(f"Team credentials saved: {team_id} ({team_name})")
            return True
        except Exception as e:
            logger.error(f"Error saving team credentials: {e}")
            return False

    def get_team_credentials(self, team_id: str) -> Optional[Dict]:
        """
        Retrieve team credentials from database.

        Args:
            team_id: Slack workspace team ID

        Returns:
            Dictionary with bot_token and access_token, or None if not found
        """
        try:
            conn = _get_db_connection(self.db_path)
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT team_id, team_name, bot_token, access_token, installed_at
                FROM slack_teams WHERE team_id = ?
                """,
                (team_id,),
            )

            result = cursor.fetchone()
            conn.close()

            if not result:
                logger.warning(f"Team credentials not found: {team_id}")
                return None

            return {
                "team_id": result[0],
                "team_name": result[1],
                "bot_token": result[2],
                "access_token": result[3],
                "installed_at": result[4],
            }
        except Exception as e:
            logger.error(f"Error retrieving team credentials: {e}")
            return None

    def get_all_teams(self) -> list:
        """
        Retrieve all registered teams.

        Returns:
            List of team dictionaries
        """
        try:
            conn = _get_db_connection(self.db_path)
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT team_id, team_name, bot_token, access_token, installed_at
                FROM slack_teams ORDER BY installed_at DESC
                """
            )

            results = cursor.fetchall()
            conn.close()

            return [
                {
                    "team_id": r[0],
                    "team_name": r[1],
                    "bot_token": r[2],
                    "access_token": r[3],
                    "installed_at": r[4],
                }
                for r in results
            ]
        except Exception as e:
            logger.error(f"Error retrieving teams: {e}")
            return []

    def revoke_team(self, team_id: str) -> bool:
        """
        Revoke/remove a team's installation.

        Args:
            team_id: Slack workspace team ID

        Returns:
            True if revoked successfully, False otherwise
        """
        try:
            conn = _get_db_connection(self.db_path)
            cursor = conn.cursor()

            cursor.execute("DELETE FROM slack_teams WHERE team_id = ?", (team_id,))
            conn.commit()
            conn.close()

            logger.info(f"Team revoked: {team_id}")
            return True
        except Exception as e:
            logger.error(f"Error revoking team: {e}")
            return False

    def verify_request_signature(
        self, timestamp: str, body: str, signature: str
    ) -> bool:
        """
        Verify Slack request signature for security.

        Args:
            timestamp: X-Slack-Request-Timestamp header
            body: Request body as string
            signature: X-Slack-Signature header

        Returns:
            True if signature is valid, False otherwise
        """
        # Check timestamp is within 5 minutes
        request_time = int(timestamp)
        current_time = int(time.time())

        if abs(current_time - request_time) > 300:
            logger.warning("Request timestamp outside acceptable window")
            return False

        # Verify signature
        sig_basestring = f"v0:{timestamp}:{body}"
        my_signature = (
            "v0="
            + hmac.new(
                self.client_secret.encode(),
                sig_basestring.encode(),
                hashlib.sha256,
            ).hexdigest()
        )

        is_valid = hmac.compare_digest(my_signature, signature)

        if not is_valid:
            logger.warning("Invalid request signature")

        return is_valid
