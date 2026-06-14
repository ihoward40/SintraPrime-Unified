"""
SintraPrime UniVerse Integrations Module

Provides integration with external platforms and services.
"""

try:
    from .discord_bridge import DiscordBot, create_discord_bot
    from .discord_handlers import DiscordHandlers
    from .discord_embeds import DiscordEmbeds, DiscordComponents
    from .discord_server_mgmt import ServerManager, ServerConfig, PermissionLevel, GuildPermissionManager
    _discord_available = True
except ImportError:
    DiscordBot = None  # type: ignore[assignment,misc]
    create_discord_bot = None  # type: ignore[assignment]
    DiscordHandlers = None  # type: ignore[assignment,misc]
    DiscordEmbeds = None  # type: ignore[assignment,misc]
    DiscordComponents = None  # type: ignore[assignment,misc]
    ServerManager = None  # type: ignore[assignment,misc]
    ServerConfig = None  # type: ignore[assignment,misc]
    PermissionLevel = None  # type: ignore[assignment,misc]
    GuildPermissionManager = None  # type: ignore[assignment,misc]
    _discord_available = False

__all__ = [
    "DiscordBot",
    "create_discord_bot",
    "DiscordHandlers",
    "DiscordEmbeds",
    "DiscordComponents",
    "ServerManager",
    "ServerConfig",
    "PermissionLevel",
    "GuildPermissionManager",
]

__version__ = "1.0.0"
