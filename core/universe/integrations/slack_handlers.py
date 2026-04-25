"""
Slack Handlers Module

Implements slash command handlers, event handlers, and interaction handlers
with permission checking and thread context preservation.
"""

import asyncio
import json
import logging
import sqlite3
from datetime import datetime
from typing import Dict, Optional

try:
    from .slack_ui_builder import SlackUIBuilder
except ImportError:
    from slack_ui_builder import SlackUIBuilder

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


class PermissionChecker:
    """Checks user permissions for Slack operations."""

    ROLE_PERMISSIONS = {
        "admin": ["invoke_agent", "manage_swarm", "install_skill", "view_logs"],
        "developer": ["invoke_agent", "view_logs"],
        "user": ["invoke_agent"],
    }

    def __init__(self, db_path: str = "slack.db"):
        """
        Initialize permission checker.

        Args:
            db_path: Path to SQLite database
        """
        self.db_path = db_path
        self._init_db()
    
    def _init_db(self):
        """Initialize database with slack_users table."""
        try:
            conn = _get_db_connection(self.db_path)
            cursor = conn.cursor()
            
            # Create slack_users table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS slack_users (
                    slack_id TEXT NOT NULL,
                    team_id TEXT NOT NULL,
                    display_name TEXT,
                    role TEXT DEFAULT 'user',
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (slack_id, team_id)
                )
            """)
            
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Error initializing permission checker database: {e}")
            raise

    def get_user_role(self, team_id: str, user_id: str) -> str:
        """
        Get user's role in the workspace.

        Args:
            team_id: Slack workspace team ID
            user_id: Slack user ID

        Returns:
            User role (admin, developer, user)
        """
        try:
            conn = _get_db_connection(self.db_path)
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT role FROM slack_users
                WHERE team_id = ? AND slack_id = ?
                """,
                (team_id, user_id),
            )

            result = cursor.fetchone()
            conn.close()

            return result[0] if result else "user"
        except Exception as e:
            logger.error(f"Error getting user role: {e}")
            return "user"

    def check_permission(self, team_id: str, user_id: str, permission: str) -> bool:
        """
        Check if user has required permission.

        Args:
            team_id: Slack workspace team ID
            user_id: Slack user ID
            permission: Required permission

        Returns:
            True if user has permission, False otherwise
        """
        role = self.get_user_role(team_id, user_id)
        allowed_permissions = self.ROLE_PERMISSIONS.get(role, [])
        return permission in allowed_permissions

    def set_user_role(
        self, team_id: str, user_id: str, display_name: str, role: str
    ) -> bool:
        """
        Set a user's role in the workspace.

        Args:
            team_id: Slack workspace team ID
            user_id: Slack user ID
            display_name: User's display name
            role: Role to assign (admin, developer, user)

        Returns:
            True if role was set, False otherwise
        """
        try:
            conn = _get_db_connection(self.db_path)
            cursor = conn.cursor()

            cursor.execute(
                """
                INSERT OR REPLACE INTO slack_users
                (slack_id, team_id, display_name, role)
                VALUES (?, ?, ?, ?)
                """,
                (user_id, team_id, display_name, role),
            )
            conn.commit()
            conn.close()

            logger.info(f"Set role for {user_id}: {role}")
            return True
        except Exception as e:
            logger.error(f"Error setting user role: {e}")
            return False


class ThreadContext:
    """Manages thread context for responses."""

    @staticmethod
    def get_thread_ts(payload: Dict) -> Optional[str]:
        """
        Get thread timestamp from payload.

        Args:
            payload: Event or interaction payload

        Returns:
            Thread timestamp or None
        """
        # Check multiple possible locations for thread_ts
        return (
            payload.get("thread_ts")
            or payload.get("message", {}).get("thread_ts")
            or None
        )

    @staticmethod
    def preserve_thread(payload: Dict, response: Dict) -> Dict:
        """
        Add thread timestamp to response if in a thread.

        Args:
            payload: Original event/interaction payload
            response: Response dictionary

        Returns:
            Response with thread context preserved
        """
        thread_ts = ThreadContext.get_thread_ts(payload)
        if thread_ts:
            response["thread_ts"] = thread_ts

        return response


class SlackHandlers:
    """Factory for creating Slack command and event handlers."""

    def __init__(self, bot, db_path: str = "slack.db"):
        """
        Initialize handlers.

        Args:
            bot: SlackBot instance
            db_path: Path to SQLite database
        """
        self.bot = bot
        self.db_path = db_path
        self.permission_checker = PermissionChecker(db_path)

    async def handle_agent_command(
        self, team_id: str, user_id: str, text: str, channel_id: str
    ) -> Dict:
        """
        Handle /agent command to invoke an agent.

        Args:
            team_id: Slack workspace team ID
            user_id: User who invoked command
            text: Command arguments
            channel_id: Channel ID

        Returns:
            Response payload
        """
        if not self.permission_checker.check_permission(team_id, user_id, "invoke_agent"):
            return {
                "response_type": "ephemeral",
                "text": "❌ You don't have permission to invoke agents.",
            }

        # Parse command: /agent <task> <query>
        parts = text.strip().split(maxsplit=1)
        if len(parts) < 2:
            return {
                "response_type": "ephemeral",
                "text": "Usage: `/agent <task> <query>`",
            }

        task_name, query = parts[0], parts[1]

        # Log the interaction
        self.bot.log_interaction(
            team_id,
            user_id,
            "invoke_agent",
            {"task": task_name, "query": query},
        )

        # Create status message
        status_msg = SlackUIBuilder.create_status_message(
            f"Agent: {task_name}", "running", f"Executing: {query}"
        )

        # In a real implementation, this would invoke the actual agent
        # For now, simulate with a status message
        status_msg["response_type"] = "in_channel"
        return status_msg

    async def handle_swarm_command(
        self, team_id: str, user_id: str, text: str, channel_id: str
    ) -> Dict:
        """
        Handle /swarm command to invoke a swarm team.

        Args:
            team_id: Slack workspace team ID
            user_id: User who invoked command
            text: Command arguments
            channel_id: Channel ID

        Returns:
            Response payload
        """
        if not self.permission_checker.check_permission(team_id, user_id, "manage_swarm"):
            return {
                "response_type": "ephemeral",
                "text": "❌ You don't have permission to manage swarms.",
            }

        # Parse command: /swarm <team> <task>
        parts = text.strip().split(maxsplit=1)
        if len(parts) < 2:
            return {
                "response_type": "ephemeral",
                "text": "Usage: `/swarm <team> <task>`",
            }

        team_name, task = parts[0], parts[1]

        # Log the interaction
        self.bot.log_interaction(
            team_id,
            user_id,
            "invoke_swarm",
            {"team": team_name, "task": task},
        )

        # Create status message
        status_msg = SlackUIBuilder.create_status_message(
            f"Swarm: {team_name}", "running", f"Executing: {task}"
        )

        status_msg["response_type"] = "in_channel"
        return status_msg

    async def handle_skill_command(
        self, team_id: str, user_id: str, text: str, channel_id: str
    ) -> Dict:
        """
        Handle /skill command for skill discovery and management.

        Args:
            team_id: Slack workspace team ID
            user_id: User who invoked command
            text: Command arguments
            channel_id: Channel ID

        Returns:
            Response payload
        """
        # Parse command: /skill search <name> or /skill install <name>
        parts = text.strip().split(maxsplit=1)

        if not parts or parts[0] not in ["search", "install", "list"]:
            return {
                "response_type": "ephemeral",
                "text": "Usage: `/skill search|install|list [name]`",
            }

        action = parts[0]
        skill_name = parts[1] if len(parts) > 1 else ""

        # Log the interaction
        self.bot.log_interaction(
            team_id,
            user_id,
            f"skill_{action}",
            {"skill": skill_name},
        )

        if action == "search":
            if not skill_name:
                return {
                    "response_type": "ephemeral",
                    "text": "Please specify skill name to search.",
                }

            # Create search results message
            blocks = [
                SlackUIBuilder.create_header_block(f"🔍 Skill Search: {skill_name}"),
                SlackUIBuilder.create_section_block(
                    f"Searching for skills matching: *{skill_name}*"
                ),
            ]

            return {"blocks": blocks}

        elif action == "install":
            if not self.permission_checker.check_permission(
                team_id, user_id, "install_skill"
            ):
                return {
                    "response_type": "ephemeral",
                    "text": "❌ You don't have permission to install skills.",
                }

            return {
                "response_type": "ephemeral",
                "text": f"Installing skill: {skill_name}",
            }

        elif action == "list":
            # List available skills
            blocks = [
                SlackUIBuilder.create_header_block("📚 Available Skills"),
                SlackUIBuilder.create_section_block("_No skills currently available_"),
            ]

            return {"blocks": blocks}

        return {
            "response_type": "ephemeral",
            "text": f"Unknown action: {action}",
        }

    async def handle_message_event(self, event_data: Dict) -> None:
        """
        Handle message event.

        Args:
            event_data: Event payload from Slack
        """
        team_id = event_data.get("team_id")
        user_id = event_data.get("user_id")
        text = event_data.get("text", "")
        channel_id = event_data.get("channel")

        logger.debug(f"Message event: {team_id}/{user_id}: {text[:50]}")

        # Log the interaction
        if user_id:
            self.bot.log_interaction(
                team_id,
                user_id,
                "message_received",
                {"channel": channel_id, "preview": text[:100]},
            )

    async def handle_app_mention_event(self, event_data: Dict) -> None:
        """
        Handle app mention event.

        Args:
            event_data: Event payload from Slack
        """
        team_id = event_data.get("team_id")
        user_id = event_data.get("user_id")
        text = event_data.get("text", "")
        channel_id = event_data.get("channel")

        logger.debug(f"App mention: {team_id}/{user_id}: {text[:50]}")

        # Log the interaction
        self.bot.log_interaction(
            team_id,
            user_id,
            "app_mention",
            {"channel": channel_id, "text": text},
        )

    async def handle_reaction_added_event(self, event_data: Dict) -> None:
        """
        Handle reaction added event.

        Args:
            event_data: Event payload from Slack
        """
        team_id = event_data.get("team_id")
        user_id = event_data.get("user_id")
        reaction = event_data.get("reaction")

        logger.debug(f"Reaction: {team_id}/{user_id} reacted with :{reaction}:")

        # Log the interaction
        self.bot.log_interaction(
            team_id,
            user_id,
            "reaction_added",
            {"reaction": reaction},
        )

    async def handle_button_action(self, team_id: str, payload: Dict) -> Dict:
        """
        Handle button click action.

        Args:
            team_id: Slack workspace team ID
            payload: Action payload

        Returns:
            Response payload
        """
        user_id = payload.get("user", {}).get("id")
        button_value = payload.get("actions", [{}])[0].get("value")

        logger.debug(f"Button action: {user_id} clicked {button_value}")

        # Log the interaction
        self.bot.log_interaction(
            team_id,
            user_id,
            "button_action",
            {"value": button_value},
        )

        return {
            "response_type": "ephemeral",
            "text": f"Button action processed: {button_value}",
        }

    async def handle_modal_submission(self, team_id: str, payload: Dict) -> Dict:
        """
        Handle modal form submission.

        Args:
            team_id: Slack workspace team ID
            payload: Modal submission payload

        Returns:
            Response payload
        """
        user_id = payload.get("user", {}).get("id")
        callback_id = payload.get("callback_id")
        values = payload.get("view", {}).get("state", {}).get("values", {})

        logger.debug(f"Modal submission: {user_id} submitted {callback_id}")

        # Log the interaction
        self.bot.log_interaction(
            team_id,
            user_id,
            f"modal_{callback_id}",
            {"values_count": len(values)},
        )

        return {
            "response_action": "clear",
        }

    async def handle_shortcut_action(self, team_id: str, payload: Dict) -> Dict:
        """
        Handle shortcut invocation.

        Args:
            team_id: Slack workspace team ID
            payload: Shortcut payload

        Returns:
            Response payload
        """
        user_id = payload.get("user", {}).get("id")
        callback_id = payload.get("callback_id")

        logger.debug(f"Shortcut: {user_id} invoked {callback_id}")

        # Log the interaction
        self.bot.log_interaction(
            team_id,
            user_id,
            f"shortcut_{callback_id}",
            {},
        )

        return {"text": f"Shortcut {callback_id} executed"}


def create_handlers(bot, db_path: str = "slack.db") -> SlackHandlers:
    """
    Factory function to create and configure handlers.

    Args:
        bot: SlackBot instance
        db_path: Path to SQLite database

    Returns:
        Configured SlackHandlers instance
    """
    handlers = SlackHandlers(bot, db_path)

    # Register slash command handlers
    bot.register_slash_handler("agent", handlers.handle_agent_command)
    bot.register_slash_handler("swarm", handlers.handle_swarm_command)
    bot.register_slash_handler("skill", handlers.handle_skill_command)

    # Register event handlers
    bot.register_event_handler("message", handlers.handle_message_event)
    bot.register_event_handler("app_mention", handlers.handle_app_mention_event)
    bot.register_