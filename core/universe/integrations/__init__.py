"""
SintraPrime UniVerse Integrations Module

Provides integration with external platforms and services.
"""

from .discord_bridge import DiscordBot, create_discord_bot
from .discord_handlers import DiscordHandlers
from .discord_embeds import DiscordEmbeds, DiscordComponents
from .discord_server_mgmt import ServerManager, ServerConfig, PermissionLevel, GuildPermissionManager

__all__ = [
    "DiscordBot",
    "create_discord_bot",
    "DiscordHandlers",
    "DiscordEmbeds",
    "DiscordComponents",
    "ServerManager",
    "ServerConfig",
    "PermissionLevel",
    "GuildPermissionManager"
]

__version__ = "1.0.0"
