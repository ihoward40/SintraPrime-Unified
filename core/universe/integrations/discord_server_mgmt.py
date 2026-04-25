"""
Discord Server Management - Guild configuration and role-based permissions

Provides:
- Guild configuration system
- Role-based permissions
- Channel auto-setup
- Configuration persistence
- Server statistics tracking
"""

import discord
from typing import Optional, Dict, List, Set
from datetime import datetime
from enum import Enum
import json
import logging

logger = logging.getLogger(__name__)


class PermissionLevel(Enum):
    """Permission level enumeration"""
    OWNER = 4
    ADMIN = 3
    MODERATOR = 2
    USER = 1
    GUEST = 0


class ChannelType(Enum):
    """Channel type enumeration"""
    CONTROL = "control"
    LOGS = "logs"
    ALERTS = "alerts"
    RESULTS = "results"


class ServerConfig:
    """Server-specific configuration"""
    
    def __init__(self, guild_id: str, guild_name: str):
        """Initialize server config"""
        self.guild_id = guild_id
        self.guild_name = guild_name
        self.prefix = "!"
        self.enabled_features: Set[str] = {
            "prefix_commands",
            "slash_commands",
            "reactions",
            "auto_logs"
        }
        self.channels: Dict[ChannelType, int] = {}
        self.role_permissions: Dict[int, PermissionLevel] = {}
        self.mod_roles: Set[int] = set()
        self.admin_roles: Set[int] = set()
        self.created_at = datetime.now()
        self.updated_at = datetime.now()
        self.stats = {
            "commands_executed": 0,
            "tasks_created": 0,
            "agents_spawned": 0,
            "message_count": 0
        }
    
    def to_dict(self) -> Dict:
        """Convert config to dictionary"""
        return {
            "guild_id": self.guild_id,
            "guild_name": self.guild_name,
            "prefix": self.prefix,
            "enabled_features": list(self.enabled_features),
            "channels": {k.value: v for k, v in self.channels.items()},
            "role_permissions": self.role_permissions,
            "mod_roles": list(self.mod_roles),
            "admin_roles": list(self.admin_roles),
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "stats": self.stats
        }
    
    @classmethod
    def from_dict(cls, data: Dict):
        """Create config from dictionary"""
        config = cls(data["guild_id"], data["guild_name"])
        config.prefix = data.get("prefix", "!")
        config.enabled_features = set(data.get("enabled_features", []))
        config.channels = {
            ChannelType[k.upper()]: v 
            for k, v in data.get("channels", {}).items()
        }
        config.role_permissions = data.get("role_permissions", {})
        config.mod_roles = set(data.get("mod_roles", []))
        config.admin_roles = set(data.get("admin_roles", []))
        config.stats = data.get("stats", {})
        return config


class ServerManager:
    """Manages server configurations and permissions"""
    
    def __init__(self, db_connection=None):
        """
        Initialize server manager
        
        Args:
            db_connection: Optional database connection for persistence
        """
        self.configs: Dict[str, ServerConfig] = {}
        self.db = db_connection
    
    async def initialize_guild(self, guild: discord.Guild):
        """Initialize new guild configuration"""
        guild_id = str(guild.id)
        
        if guild_id not in self.configs:
            config = ServerConfig(guild_id, guild.name)
            self.configs[guild_id] = config
            
            logger.info(f"Initialized guild config for {guild.name}")
            
            # Auto-setup channels if possible
            await self._setup_default_channels(guild, config)
            
            # Save to database
            await self._save_config(guild_id, config)
    
    async def cleanup_guild(self, guild_id: str):
        """Clean up guild configuration when bot leaves"""
        if guild_id in self.configs:
            await self._delete_config(guild_id)
            del self.configs[guild_id]
            logger.info(f"Cleaned up guild config for {guild_id}")
    
    async def _setup_default_channels(self, guild: discord.Guild, config: ServerConfig):
        """Auto-setup default channels"""
        channel_names = {
            ChannelType.CONTROL: "agent-control",
            ChannelType.LOGS: "agent-logs",
            ChannelType.ALERTS: "agent-alerts",
            ChannelType.RESULTS: "agent-results"
        }
        
        for channel_type, channel_name in channel_names.items():
            # Check if channel exists
            existing = discord.utils.find(lambda c: c.name == channel_name, guild.text_channels)
            
            if existing:
                config.channels[channel_type] = existing.id
            else:
                try:
                    # Create channel if it doesn't exist
                    new_channel = await guild.create_text_channel(
                        name=channel_name,
                        topic=f"SintraPrime UniVerse - {channel_type.value.replace('_', ' ').title()}"
                    )
                    config.channels[channel_type] = new_channel.id
                    logger.info(f"Created channel {channel_name} in {guild.name}")
                except Exception as e:
                    logger.error(f"Failed to create channel {channel_name}: {e}")
    
    def get_config(self, guild_id: str) -> Optional[ServerConfig]:
        """Get guild configuration"""
        return self.configs.get(str(guild_id))
    
    def set_prefix(self, guild_id: str, prefix: str) -> bool:
        """Set command prefix for guild"""
        guild_id = str(guild_id)
        config = self.configs.get(guild_id)
        
        if not config:
            return False
        
        if not (1 <= len(prefix) <= 5):
            return False
        
        config.prefix = prefix
        config.updated_at = datetime.now()
        return True
    
    def set_channel(self, guild_id: str, channel_type: ChannelType, 
                   channel_id: int) -> bool:
        """Set channel for specific purpose"""
        guild_id = str(guild_id)
        config = self.configs.get(guild_id)
        
        if not config:
            return False
        
        config.channels[channel_type] = channel_id
        config.updated_at = datetime.now()
        return True
    
    def get_channel(self, guild_id: str, channel_type: ChannelType) -> Optional[int]:
        """Get channel ID for specific purpose"""
        guild_id = str(guild_id)
        config = self.configs.get(guild_id)
        
        if not config:
            return None
        
        return config.channels.get(channel_type)
    
    def assign_mod_role(self, guild_id: str, role_id: int) -> bool:
        """Assign moderator role"""
        guild_id = str(guild_id)
        config = self.configs.get(guild_id)
        
        if not config:
            return False
        
        config.mod_roles.add(role_id)
        config.updated_at = datetime.now()
        return True
    
    def assign_admin_role(self, guild_id: str, role_id: int) -> bool:
        """Assign admin role"""
        guild_id = str(guild_id)
        config = self.configs.get(guild_id)
        
        if not config:
            return False
        
        config.admin_roles.add(role_id)
        config.updated_at = datetime.now()
        return True
    
    def check_permission(self, guild_id: str, user: discord.Member, 
                        required_level: PermissionLevel) -> bool:
        """Check if user has required permission level"""
        guild_id = str(guild_id)
        config = self.configs.get(guild_id)
        
        if not config:
            return False
        
        # Owner check
        if user.id == user.guild.owner_id:
            return True
        
        # Admin check
        if any(role.id in config.admin_roles for role in user.roles):
            return required_level.value <= PermissionLevel.ADMIN.value
        
        # Moderator check
        if any(role.id in config.mod_roles for role in user.roles):
            return required_level.value <= PermissionLevel.MODERATOR.value
        
        # Default user level
        return required_level.value <= PermissionLevel.USER.value
    
    def enable_feature(self, guild_id: str, feature: str) -> bool:
        """Enable a feature"""
        guild_id = str(guild_id)
        config = self.configs.get(guild_id)
        
        if not config:
            return False
        
        config.enabled_features.add(feature)
        config.updated_at = datetime.now()
        return True
    
    def disable_feature(self, guild_id: str, feature: str) -> bool:
        """Disable a feature"""
        guild_id = str(guild_id)
        config = self.configs.get(guild_id)
        
        if not config:
            return False
        
        config.enabled_features.discard(feature)
        config.updated_at = datetime.now()
        return True
    
    def is_feature_enabled(self, guild_id: str, feature: str) -> bool:
        """Check if feature is enabled"""
        guild_id = str(guild_id)
        config = self.configs.get(guild_id)
        
        if not config:
            return False
        
        return feature in config.enabled_features
    
    def record_stat(self, guild_id: str, stat_name: str, increment: int = 1):
        """Record guild statistic"""
        guild_id = str(guild_id)
        config = self.configs.get(guild_id)
        
        if not config:
            return
        
        if stat_name in config.stats:
            config.stats[stat_name] += increment
        else:
            config.stats[stat_name] = increment
        
        config.updated_at = datetime.now()
    
    def get_stats(self, guild_id: str) -> Dict:
        """Get guild statistics"""
        guild_id = str(guild_id)
        config = self.configs.get(guild_id)
        
        if not config:
            return {}
        
        return {
            **config.stats,
            "uptime": str(datetime.now() - config.created_at),
            "last_updated": config.updated_at.isoformat()
        }
    
    def get_all_configs(self) -> List[ServerConfig]:
        """Get all guild configurations"""
        return list(self.configs.values())
    
    async def _save_config(self, guild_id: str, config: ServerConfig):
        """Save configuration to database"""
        if not self.db:
            return
        
        try:
            # In production, save to database
            logger.debug(f"Saving config for guild {guild_id}")
        except Exception as e:
            logger.error(f"Failed to save config: {e}")
    
    async def _delete_config(self, guild_id: str):
        """Delete configuration from database"""
        if not self.db:
            return
        
        try:
            # In production, delete from database
            logger.debug(f"Deleting config for guild {guild_id}")
        except Exception as e:
            logger.error(f"Failed to delete config: {e}")
    
    def export_configs(self) -> Dict:
        """Export all configurations"""
        return {
            guild_id: config.to_dict()
            for guild_id, config in self.configs.items()
        }
    
    def import_configs(self, data: Dict):
        """Import configurations"""
        for guild_id, config_data in data.items():
            config = ServerConfig.from_dict(config_data)
            self.configs[guild_id] = config
        
        logger.info(f"Imported {len(data)} guild configurations")


class GuildPermissionManager:
    """Manages fine-grained permissions for guild members"""
    
    def __init__(self):
        """Initialize permission manager"""
        self.user_permissions: Dict[str, Dict[int, PermissionLevel]] = {}
    
    def set_user_permission(self, guild_id: str, user_id: int, 
                           level: PermissionLevel):
        """Set specific user permission level"""
        guild_id = str(guild_id)
        
        if guild_id not in self.user_permissions:
            self.user_permissions[guild_id] = {}
        
        self.user_permissions[guild_id][user_id] = level
    
    def get_user_permission(self, guild_id: str, user_id: int) -> Optional[PermissionLevel]:
        """Get specific user permission level"""
        guild_id = str(guild_id)
        
        if guild_id not in self.user_permissions:
            return None
        
        return self.user_permissions[guild_id].get(user_id)
    
    def remove_user_permission(self, guild_id: str, user_id: int) -> bool:
        """Remove specific user permission"""
        guild_id = str(guild_id)
        
        if guild_id not in self.user_permissions:
            return False
        
        if user_id in self.user_permissions[guild_id]:
            del self.user_permissions[guild_id][user_id]
            return True
        
        return False
