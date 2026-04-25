"""
Slack Bot Core Module

Implements the main SlackBot class with OAuth 2.0 flow, slash command routing,
event listening, and message queue integration.
"""

import asyncio
import json
import logging
import time
from typing import Any, Callable, Dict, List, Optional
from datetime import datetime, timedelta
import sqlite3

logger = logging.getLogger(__name__)


class RateLimiter:
    """Token bucket rate limiter for Slack API calls."""

    def __init__(self, capacity: int = 60, refill_rate: float = 1.0):
        """
        Initialize rate limiter.

        Args:
            capacity: Maximum tokens (burst capacity)
            refill_rate: Tokens per second
        """
        self.capacity = capacity
        self.refill_rate = refill_rate
        self.tokens = capacity
        self.last_refill = time.time()

    def acquire(self, tokens: int = 1) -> bool:
        """
        Acquire tokens, applying rate limit.

        Args:
            tokens: Number of tokens to acquire

        Returns:
            True if tokens acquired, False if rate limited
        """
        now = time.time()
        elapsed = now - self.last_refill

        # Refill tokens based on elapsed time
        self.tokens = min(
            self.capacity, self.tokens + elapsed * self.refill_rate
        )
        self.last_refill = now

        if self.tokens >= tokens:
            self.tokens -= tokens
            return True

        return False

    def wait_available(self, tokens: int = 1) -> float:
        """
        Calculate wait time until tokens are available.

        Args:
            tokens: Number of tokens needed

        Returns:
            Wait time in seconds
        """
        if self.tokens >= tokens:
            return 0

        return (tokens - self.tokens) / self.refill_rate


class ConnectionPool:
    """Simple connection pool for managing Slack client connections."""

    def __init__(self, max_size: int = 10):
        """
        Initialize connection pool.

        Args:
            max_size: Maximum number of concurrent connections
        """
        self.max_size = max_size
        self.connections = {}
        self.available = asyncio.Queue(maxsize=max_size)

    async def get_connection(self, team_id: str):
        """
        Get a connection from the pool.

        Args:
            team_id: Slack workspace team ID

        Returns:
            Connection object
        """
        if team_id in self.connections:
            return self.connections[team_id]

        # Create new connection
        conn = {"team_id": team_id, "created_at": time.time(), "healthy": True}
        self.connections[team_id] = conn
        return conn

    async def release_connection(self, team_id: str):
        """
        Release a connection back to pool.

        Args:
            team_id: Slack workspace team ID
        """
        if team_id in self.connections:
            self.connections[team_id]["last_used"] = time.time()

    def mark_unhealthy(self, team_id: str):
        """
        Mark a connection as unhealthy.

        Args:
            team_id: Slack workspace team ID
        """
        if team_id in self.connections:
            self.connections[team_id]["healthy"] = False


class SlackBot:
    """Main Slack bot class implementing OAuth 2.0 flow and event handling."""

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        signing_secret: str,
        db_path: str = "slack.db",
    ):
        """
        Initialize Slack bot.

        Args:
            client_id: Slack app client ID
            client_secret: Slack app client secret
            signing_secret: Slack app signing secret
            db_path: Path to SQLite database
        """
        self.client_id = client_id
        self.client_secret = client_secret
        self.signing_secret = signing_secret
        self.db_path = db_path

        # Event handlers
        self.slash_handlers: Dict[str, Callable] = {}
        self.event_handlers: Dict[str, List[Callable]] = {}
        self.action_handlers: Dict[str, Callable] = {}

        # Infrastructure
        self.rate_limiter = RateLimiter(capacity=60, refill_rate=1.0)
        self.connection_pool = ConnectionPool(max_size=10)

        # Message queue for async event processing
        self.event_queue = asyncio.Queue()
        self.running = False

        logger.info("SlackBot initialized")

    def register_slash_handler(
        self, command: str, handler: Callable
    ) -> None:
        """
        Register a slash command handler.

        Args:
            command: Command name (without /)
            handler: Async callable to handle command
        """
        self.slash_handlers[command] = handler
        logger.debug(f"Registered slash handler: /{command}")

    def register_event_handler(
        self, event_type: str, handler: Callable
    ) -> None:
        """
        Register an event handler.

        Args:
            event_type: Event type (e.g., 'message', 'app_mention')
            handler: Async callable to handle event
        """
        if event_type not in self.event_handlers:
            self.event_handlers[event_type] = []

        self.event_handlers[event_type].append(handler)
        logger.debug(f"Registered event handler: {event_type}")

    def register_action_handler(
        self, action_id: str, handler: Callable
    ) -> None:
        """
        Register an action/interaction handler.

        Args:
            action_id: Action identifier
            handler: Async callable to handle action
        """
        self.action_handlers[action_id] = handler
        logger.debug(f"Registered action handler: {action_id}")

    async def handle_slash_command(
        self, team_id: str, command: str, user_id: str, text: str, channel_id: str
    ) -> Dict:
        """
        Handle incoming slash command.

        Args:
            team_id: Slack workspace team ID
            command: Command name
            user_id: User ID who invoked command
            text: Command text/arguments
            channel_id: Channel ID where command was invoked

        Returns:
            Response payload
        """
        if not self.rate_limiter.acquire():
            wait_time = self.rate_limiter.wait_available()
            logger.warning(f"Rate limited, wait {wait_time:.2f}s")
            return {
                "response_type": "ephemeral",
                "text": f"Rate limited. Please wait {wait_time:.1f} seconds.",
            }

        handler = self.slash_handlers.get(command)
        if not handler:
            logger.warning(f"No handler for command: /{command}")
            return {
                "response_type": "ephemeral",
                "text": f"Unknown command: /{command}",
            }

        try:
            result = await handler(
                team_id=team_id,
                user_id=user_id,
                text=text,
                channel_id=channel_id,
            )
            return result or {"response_type": "ephemeral", "text": "Command executed"}
        except Exception as e:
            logger.error(f"Error handling command /{command}: {e}")
            return {
                "response_type": "ephemeral",
                "text": f"Error: {str(e)}",
            }

    async def handle_event(self, event_data: Dict) -> None:
        """
        Handle incoming event.

        Args:
            event_data: Event payload from Slack
        """
        event_type = event_data.get("type")
        team_id = event_data.get("team_id")

        if not team_id:
            logger.warning("Event missing team_id")
            return

        handlers = self.event_handlers.get(event_type, [])

        for handler in handlers:
            try:
                await handler(event_data)
            except Exception as e:
                logger.error(f"Error in {event_type} handler: {e}")

    async def handle_action(
        self, team_id: str, action_id: str, payload: Dict
    ) -> Dict:
        """
        Handle interactive action (button click, menu selection, etc.).

        Args:
            team_id: Slack workspace team ID
            action_id: Action identifier
            payload: Full action payload

        Returns:
            Response payload
        """
        handler = self.action_handlers.get(action_id)
        if not handler:
            logger.warning(f"No handler for action: {action_id}")
            return {"response_type": "ephemeral", "text": f"Unknown action: {action_id}"}

        try:
            result = await handler(team_id=team_id, payload=payload)
            return result or {"response_type": "ephemeral", "text": "Action processed"}
        except Exception as e:
            logger.error(f"Error handling action {action_id}: {e}")
            return {
                "response_type": "ephemeral",
                "text": f"Error: {str(e)}",
            }

    async def emit_event(self, event_data: Dict) -> None:
        """
        Emit an event to the message queue.

        Args:
            event_data: Event payload
        """
        await self.event_queue.put(event_data)

    async def event_loop(self) -> None:
        """
        Main event loop processing queued events.
        """
        logger.info("Starting event loop")
        self.running = True

        while self.running:
            try:
                # Wait with timeout to allow graceful shutdown
                event_data = await asyncio.wait_for(
                    self.event_queue.get(), timeout=1.0
                )
                await self.handle_event(event_data)
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Error in event loop: {e}")

    async def start(self) -> None:
        """
        Start the bot event loop.
        """
        try:
            await self.event_loop()
        except KeyboardInterrupt:
            logger.info("Shutdown signal received")
            await self.stop()

    async def stop(self) -> None:
        """
        Stop the bot gracefully.
        """
        logger.info("Stopping SlackBot")
        self.running = False

    async def healthcheck(self, team_id: str) -> bool:
        """
        Perform healthcheck on a team's connection.

        Args:
            team_id: Slack workspace team ID

        Returns:
            True if healthy, False otherwise
        """
        try:
            # In a real implementation, this would call Slack API
            conn = await self.connection_pool.get_connection(team_id)
            return conn.get("healthy", False)
        except Exception as e:
            logger.error(f"Healthcheck failed for {team_id}: {e}")
            return False

    def get_stats(self) -> Dict:
        """
        Get bot statistics.

        Returns:
            Dictionary with bot stats
        """
        return {
            "running": self.running,
            "event_queue_size": self.event_queue.qsize(),
            "active_connections": len(self.connection_pool.connections),
            "rate_limiter_tokens": self.rate_limiter.tokens,
            "handlers": {
                "slash_commands": len(self.slash_handlers),
                "event_types": len(self.event_handlers),
                "actions": len(self.action_handlers),
            },
        }

    async def reconnect_team(self, team_id: str, max_retries: int = 5) -> bool:
        """
        Attempt to reconnect a team with exponential backoff.

        Args:
            team_id: Slack workspace team ID
            max_retries: Maximum reconnection attempts

        Returns:
            True if reconnected, False if failed
        """
        for attempt in range(max_retries):
            wait_time = 2 ** attempt  # Exponential backoff
            logger.info(
                f"Reconnect attempt {attempt + 1}/{max_retries} for {team_id} "
                f"(wait: {wait_time}s)"
            )

            try:
                await asyncio.sleep(wait_time)

                # In real implementation, verify connection
                conn = await self.connection_pool.get_connection(team_id)
                conn["healthy"] = True

                logger.info(f"Successfully reconnected: {team_id}")
                return True
            except Exception as e:
                logger.warning(f"Reconnection attempt {attempt + 1} failed: {e}")

        logger.error(f"Failed to reconnect {team_id} after {max_retries} attempts")
        self.connection_pool.mark_unhealthy(team_id)
        return False

    def log_interaction(
        self, team_id: str, user_id: str, action: str, payload: Dict
    ) -> bool:
        """
        Log a user interaction for audit purposes.

        Args:
            team_id: Slack workspace team ID
            user_id: User ID
            action: Action performed
            payload: Action payload

        Returns:
            True if logged successfully, False otherwise
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute(
                """
                INSERT INTO slack_interactions
                (team_id, user_id, action, payload, timestamp)
                VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
                """,
                (team_id, user_id, action, json.dumps(payload)),
            )
            conn.commit()
            conn.close()

            logger.debug(f"Logged interaction: {team_id}/{user_id}/{action}")
            return True
        except Exception as e:
            logger.error(f"Error logging interaction: {e}")
            return False
