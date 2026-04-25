"""
Discord Bridge - Core Discord Bot Integration for SintraPrime UniVerse

Provides seamless Discord bot functionality with:
- Prefix and slash command routing
- Event listeners and handlers
- Connection management
- Presence/status updates
"""

import discord
from discord.ext import commands
from discord import app_commands
import logging
import asyncio
from datetime import datetime
from typing import Optional, Dict, List, Callable
import json

from .discord_handlers import DiscordHandlers
from .discord_embeds import DiscordEmbeds
from .discord_server_mgmt import ServerManager

logger = logging.getLogger(__name__)


class DiscordBot(commands.Cog):
    """Main Discord Bot class for SintraPrime UniVerse agent orchestration"""
    
    def __init__(self, token: str, agent_framework=None, event_hub=None):
        """
        Initialize Discord Bot
        
        Args:
            token: Discord bot token
            agent_framework: Agent execution framework reference
            event_hub: Event distribution system
        """
        self.token = token
        self.agent_framework = agent_framework
        self.event_hub = event_hub
        
        # Initialize intents
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        intents.guilds = True
        intents.dm_messages = True
        
        # Create bot instance
        self.bot = commands.Bot(
            command_prefix="!",
            intents=intents,
            help_command=None
        )
        
        # Initialize handlers and managers
        self.handlers = DiscordHandlers(self.agent_framework)
        self.embeds = DiscordEmbeds()
        self.server_manager = ServerManager()
        
        # State tracking
        self.command_stats: Dict = {}
        self.error_handlers: Dict[str, Callable] = {}
        self.registered_commands: List[str] = []
        self.connected = False
        self.start_time = None
        
        # Register event listeners
        self._register_events()
        self._register_commands()
    
    def _register_events(self):
        """Register all Discord event listeners"""
        
        @self.bot.event
        async def on_ready():
            """Called when bot successfully connects to Discord"""
            logger.info(f"Bot connected as {self.bot.user}")
            self.connected = True
            self.start_time = datetime.now()
            
            # Update presence
            await self.update_presence(
                activity=discord.Activity(
                    type=discord.ActivityType.playing,
                    name="Agent Orchestration | /help"
                )
            )
            
            # Initialize servers
            for guild in self.bot.guilds:
                await self.server_manager.initialize_guild(guild)
            
            logger.info(f"Bot ready. Serving {len(self.bot.guilds)} servers")
        
        @self.bot.event
        async def on_message(message: discord.Message):
            """Process incoming messages"""
            if message.author == self.bot.user:
                return
            
            # Log message
            logger.debug(f"Message from {message.author}: {message.content}")
            
            # Process commands
            await self.bot.process_commands(message)
        
        @self.bot.event
        async def on_guild_join(guild: discord.Guild):
            """Called when bot joins a new server"""
            logger.info(f"Joined guild: {guild.name} ({guild.id})")
            await self.server_manager.initialize_guild(guild)
            
            # Send welcome message
            welcome_embed = self.embeds.create_welcome_embed(guild)
            for channel in guild.text_channels:
                if channel.permissions_for(guild.me).send_messages:
                    await channel.send(embed=welcome_embed)
                    break
        
        @self.bot.event
        async def on_guild_remove(guild: discord.Guild):
            """Called when bot leaves a server"""
            logger.info(f"Left guild: {guild.name} ({guild.id})")
            await self.server_manager.cleanup_guild(guild.id)
        
        @self.bot.event
        async def on_command_error(ctx: commands.Context, error: Exception):
            """Handle command errors"""
            logger.error(f"Command error in {ctx.command}: {error}")
            
            error_embed = self.embeds.create_error_embed(
                title="Command Error",
                description=str(error),
                error_type=type(error).__name__
            )
            await ctx.send(embed=error_embed)
        
        @self.bot.event
        async def on_interaction(interaction: discord.Interaction):
            """Handle interactions (buttons, selects, modals)"""
            logger.debug(f"Interaction: {interaction.type}")
    
    def _register_commands(self):
        """Register all commands"""
        
        # Prefix commands
        @self.bot.command(name="agent")
        async def agent_command(ctx: commands.Context, *, query: str):
            """Execute agent command"""
            await self.handlers.handle_agent_command(ctx, query)
            self._record_command("agent")
        
        @self.bot.command(name="swarm")
        async def swarm_command(ctx: commands.Context, *, args: str):
            """Manage swarm operations"""
            await self.handlers.handle_swarm_command(ctx, args)
            self._record_command("swarm")
        
        @self.bot.command(name="skill")
        async def skill_command(ctx: commands.Context, *, args: str):
            """Search and manage skills"""
            await self.handlers.handle_skill_command(ctx, args)
            self._record_command("skill")
        
        @self.bot.command(name="status")
        async def status_command(ctx: commands.Context):
            """Get bot and agent status"""
            status_embed = self.embeds.create_status_embed(
                bot_status="Connected",
                uptime=self._get_uptime(),
                agents_active=self.handlers.get_active_agents_count()
            )
            await ctx.send(embed=status_embed)
            self._record_command("status")
        
        @self.bot.command(name="help")
        async def help_command(ctx: commands.Context):
            """Display help information"""
            help_embed = self.embeds.create_help_embed()
            await ctx.send(embed=help_embed)
            self._record_command("help")
        
        # Slash commands
        @self.bot.tree.command(name="agent", description="Execute agent command")
        @app_commands.describe(query="Agent command or query")
        async def slash_agent(interaction: discord.Interaction, query: str):
            """Slash command version of !agent"""
            await interaction.response.defer()
            await self.handlers.handle_agent_command(interaction, query)
            self._record_command("slash_agent")
        
        @self.bot.tree.command(name="swarm", description="Manage swarm operations")
        @app_commands.describe(operation="swarm operation (list, create, delete)")
        async def slash_swarm(interaction: discord.Interaction, operation: str):
            """Slash command version of !swarm"""
            await interaction.response.defer()
            await self.handlers.handle_swarm_command(interaction, operation)
            self._record_command("slash_swarm")
        
        @self.bot.tree.command(name="status", description="Get bot status")
        async def slash_status(interaction: discord.Interaction):
            """Slash command for bot status"""
            status_embed = self.embeds.create_status_embed(
                bot_status="Connected",
                uptime=self._get_uptime(),
                agents_active=self.handlers.get_active_agents_count()
            )
            await interaction.response.send_message(embed=status_embed)
            self._record_command("slash_status")
    
    async def update_presence(self, activity: discord.Activity = None, 
                            status: discord.Status = discord.Status.online):
        """Update bot presence/status"""
        try:
            await self.bot.change_presence(status=status, activity=activity)
            logger.info(f"Presence updated: {activity.name if activity else 'idle'}")
        except Exception as e:
            logger.error(f"Failed to update presence: {e}")
    
    async def send_message(self, channel_id: int, embed: discord.Embed, 
                          content: str = None) -> Optional[discord.Message]:
        """Send message to specific channel"""
        try:
            channel = self.bot.get_channel(channel_id)
            if not channel:
                logger.error(f"Channel {channel_id} not found")
                return None
            
            return await channel.send(content=content, embed=embed)
        except Exception as e:
            logger.error(f"Failed to send message: {e}")
            return None
    
    async def send_dm(self, user_id: int, embed: discord.Embed) -> bool:
        """Send DM to user"""
        try:
            user = await self.bot.fetch_user(user_id)
            await user.send(embed=embed)
            return True
        except Exception as e:
            logger.error(f"Failed to send DM to {user_id}: {e}")
            return False
    
    def _record_command(self, command: str):
        """Record command execution statistics"""
        if command not in self.command_stats:
            self.command_stats[command] = {"count": 0, "last_used": None}
        
        self.command_stats[command]["count"] += 1
        self.command_stats[command]["last_used"] = datetime.now().isoformat()
    
    def _get_uptime(self) -> str:
        """Get bot uptime"""
        if not self.start_time:
            return "Unknown"
        
        delta = datetime.now() - self.start_time
        hours, remainder = divmod(int(delta.total_seconds()), 3600)
        minutes, seconds = divmod(remainder, 60)
        
        return f"{hours}h {minutes}m {seconds}s"
    
    async def connect(self):
        """Connect bot to Discord"""
        try:
            logger.info("Connecting to Discord...")
            await self.bot.start(self.token)
        except Exception as e:
            logger.error(f"Failed to connect: {e}")
            raise
    
    async def disconnect(self):
        """Disconnect bot from Discord"""
        try:
            if self.bot:
                await self.bot.close()
            self.connected = False
            logger.info("Bot disconnected")
        except Exception as e:
            logger.error(f"Failed to disconnect: {e}")
    
    def get_stats(self) -> Dict:
        """Get bot statistics"""
        return {
            "connected": self.connected,
            "uptime": self._get_uptime(),
            "servers": len(self.bot.guilds),
            "commands_executed": sum(s["count"] for s in self.command_stats.values()),
            "command_stats": self.command_stats
        }


# Factory function for easy instantiation
def create_discord_bot(token: str, agent_framework=None, event_hub=None) -> DiscordBot:
    """Factory function to create Discord bot instance"""
    return DiscordBot(token, agent_framework, event_hub)
