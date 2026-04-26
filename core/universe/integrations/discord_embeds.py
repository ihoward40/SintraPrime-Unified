"""
Discord Embeds & UI Builder - Rich embed factories and interactive components

Provides:
- Rich embed creation for all message types
- Interactive button builders
- Select menu components
- Status messages with progress bars
- Error/success formatting
"""

import discord
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class MessageType(Enum):
    """Message type enumeration"""
    SUCCESS = "success"
    ERROR = "error"
    INFO = "info"
    WARNING = "warning"
    PROGRESS = "progress"
    ALERT = "alert"


class DiscordEmbeds:
    """Factory for creating rich Discord embeds"""
    
    # Color palette
    COLOR_SUCCESS = discord.Color.green()
    COLOR_ERROR = discord.Color.red()
    COLOR_INFO = discord.Color.blue()
    COLOR_WARNING = discord.Color.orange()
    COLOR_PROGRESS = discord.Color.gold()
    COLOR_ALERT = discord.Color.dark_red()
    
    def create_welcome_embed(self, guild: discord.Guild) -> discord.Embed:
        """Create welcome embed for new server"""
        embed = discord.Embed(
            title=f"Welcome to SintraPrime UniVerse!",
            description="Your intelligent agent orchestration platform is ready",
            color=self.COLOR_SUCCESS,
            timestamp=datetime.now()
        )
        
        embed.set_thumbnail(url=guild.icon.url if guild.icon else "")
        embed.add_field(
            name="🚀 Quick Start",
            value="Type `!help` to see available commands",
            inline=False
        )
        embed.add_field(
            name="📚 Commands",
            value="• `!agent` - Manage agents\n• `!swarm` - Manage swarms\n• `!skill` - Manage skills",
            inline=False
        )
        embed.add_field(
            name="💡 Tips",
            value="Use `/` for slash commands or `!` for prefix commands",
            inline=False
        )
        
        embed.set_footer(text="SintraPrime UniVerse | Agent Orchestration Platform")
        return embed
    
    def create_error_embed(self, title: str, description: str, 
                          error_type: str = None, stacktrace: str = None) -> discord.Embed:
        """Create error embed"""
        embed = discord.Embed(
            title=f"❌ {title}",
            description=description,
            color=self.COLOR_ERROR,
            timestamp=datetime.now()
        )
        
        if error_type:
            embed.add_field(name="Error Type", value=f"`{error_type}`", inline=False)
        
        if stacktrace:
            # Limit stacktrace to 1024 characters
            trace = stacktrace[:1024]
            embed.add_field(name="Details", value=f"```{trace}```", inline=False)
        
        return embed
    
    def create_success_embed(self, title: str, description: str, 
                            fields: Dict[str, str] = None) -> discord.Embed:
        """Create success embed"""
        embed = discord.Embed(
            title=f"✅ {title}",
            description=description,
            color=self.COLOR_SUCCESS,
            timestamp=datetime.now()
        )
        
        if fields:
            for key, value in fields.items():
                embed.add_field(name=key, value=value, inline=True)
        
        return embed
    
    def create_info_embed(self, title: str, description: str,
                         fields: Dict[str, str] = None) -> discord.Embed:
        """Create info embed"""
        embed = discord.Embed(
            title=f"ℹ️ {title}",
            description=description,
            color=self.COLOR_INFO,
            timestamp=datetime.now()
        )
        
        if fields:
            for key, value in fields.items():
                embed.add_field(name=key, value=value, inline=True)
        
        return embed
    
    def create_warning_embed(self, title: str, description: str) -> discord.Embed:
        """Create warning embed"""
        embed = discord.Embed(
            title=f"⚠️ {title}",
            description=description,
            color=self.COLOR_WARNING,
            timestamp=datetime.now()
        )
        return embed
    
    def create_progress_embed(self, title: str, progress: int, 
                             total: int = 100, details: str = None) -> discord.Embed:
        """Create progress embed with progress bar"""
        percent = min(100, max(0, int((progress / total) * 100)))
        filled = int(percent / 5)
        bar = "▓" * filled + "░" * (20 - filled)
        
        embed = discord.Embed(
            title=f"🔄 {title}",
            description=f"`{bar}` {percent}%",
            color=self.COLOR_PROGRESS,
            timestamp=datetime.now()
        )
        
        if details:
            embed.add_field(name="Details", value=details, inline=False)
        
        return embed
    
    def create_status_embed(self, bot_status: str, uptime: str, 
                           agents_active: int) -> discord.Embed:
        """Create bot status embed"""
        embed = discord.Embed(
            title="🤖 Bot Status",
            color=self.COLOR_INFO,
            timestamp=datetime.now()
        )
        
        status_emoji = "🟢" if bot_status == "Connected" else "🔴"
        embed.add_field(
            name="Connection",
            value=f"{status_emoji} {bot_status}",
            inline=True
        )
        embed.add_field(
            name="Uptime",
            value=uptime,
            inline=True
        )
        embed.add_field(
            name="Active Agents",
            value=f"{agents_active}",
            inline=True
        )
        
        return embed
    
    def create_help_embed(self) -> discord.Embed:
        """Create comprehensive help embed"""
        embed = discord.Embed(
            title="📚 Command Help",
            description="Complete command reference for SintraPrime UniVerse",
            color=self.COLOR_INFO,
            timestamp=datetime.now()
        )
        
        # Agent commands
        embed.add_field(
            name="🤖 Agent Commands",
            value=(
                "`!agent list` - List all agents\n"
                "`!agent create <name> <role> <desc>` - Create agent\n"
                "`!agent status <name>` - Get agent status\n"
                "`!agent execute <name> <task>` - Execute task"
            ),
            inline=False
        )
        
        # Swarm commands
        embed.add_field(
            name="🐝 Swarm Commands",
            value=(
                "`!swarm list` - List all swarms\n"
                "`!swarm create <name>` - Create swarm\n"
                "`!swarm add <swarm> <agent>` - Add agent to swarm\n"
                "`!swarm status <name>` - Get swarm status"
            ),
            inline=False
        )
        
        # Skill commands
        embed.add_field(
            name="⚙️ Skill Commands",
            value=(
                "`!skill list` - List installed skills\n"
                "`!skill search <query>` - Search skills\n"
                "`!skill install <name>` - Install skill\n"
                "`!skill info <name>` - Get skill info"
            ),
            inline=False
        )
        
        # System commands
        embed.add_field(
            name="🛠️ System Commands",
            value=(
                "`!status` - Bot status\n"
                "`!help` - Show this help"
            ),
            inline=False
        )
        
        embed.set_footer(text="Use `/` prefix for slash commands | Support: support@sintraprime.com")
        return embed
    
    def create_agent_card(self, agent_name: str, role: str, status: str,
                         tasks_completed: int, success_rate: float) -> discord.Embed:
        """Create agent profile card"""
        embed = discord.Embed(
            title=f"🤖 {agent_name}",
            color=self.COLOR_INFO,
            timestamp=datetime.now()
        )
        
        status_emoji = "🟢" if status == "active" else "⚪"
        embed.add_field(name="Status", value=f"{status_emoji} {status.title()}", inline=True)
        embed.add_field(name="Role", value=role.title(), inline=True)
        embed.add_field(name="Tasks Completed", value=str(tasks_completed), inline=True)
        embed.add_field(name="Success Rate", value=f"{success_rate:.1f}%", inline=True)
        
        return embed
    
    def create_swarm_card(self, swarm_name: str, agent_count: int,
                         status: str, total_tasks: int) -> discord.Embed:
        """Create swarm profile card"""
        embed = discord.Embed(
            title=f"🐝 {swarm_name}",
            color=self.COLOR_INFO,
            timestamp=datetime.now()
        )
        
        status_emoji = "🟢" if status == "active" else "⚪"
        embed.add_field(name="Status", value=f"{status_emoji} {status.title()}", inline=True)
        embed.add_field(name="Agent Count", value=str(agent_count), inline=True)
        embed.add_field(name="Total Tasks", value=str(total_tasks), inline=True)
        
        return embed
    
    def create_task_card(self, task_id: str, task_type: str, status: str,
                        assigned_to: str = None, progress: int = 0) -> discord.Embed:
        """Create task card"""
        embed = discord.Embed(
            title=f"📋 Task: {task_id}",
            color=self.COLOR_PROGRESS,
            timestamp=datetime.now()
        )
        
        status_color_map = {
            "pending": "⚪",
            "active": "🟡",
            "completed": "🟢",
            "failed": "🔴"
        }
        
        status_emoji = status_color_map.get(status, "❓")
        embed.add_field(name="Status", value=f"{status_emoji} {status.title()}", inline=True)
        embed.add_field(name="Type", value=task_type, inline=True)
        
        if assigned_to:
            embed.add_field(name="Assigned To", value=assigned_to, inline=True)
        
        if progress > 0:
            filled = int(progress / 5)
            bar = "▓" * filled + "░" * (20 - filled)
            embed.add_field(name="Progress", value=f"`{bar}` {progress}%", inline=False)
        
        return embed
    
    def create_leaderboard_embed(self, title: str, entries: List[tuple]) -> discord.Embed:
        """Create leaderboard embed
        
        Args:
            title: Leaderboard title
            entries: List of (name, score) tuples
        """
        embed = discord.Embed(
            title=f"🏆 {title}",
            color=discord.Color.gold(),
            timestamp=datetime.now()
        )
        
        medals = ["🥇", "🥈", "🥉"]
        
        leaderboard = ""
        for i, (name, score) in enumerate(entries[:10]):
            medal = medals[i] if i < 3 else f"{i+1}."
            leaderboard += f"{medal} **{name}** - {score}\n"
        
        embed.description = leaderboard
        return embed
    
    def create_execution_result_embed(self, task_id: str, success: bool,
                                     duration: float, result: str = None,
                                     error: str = None) -> discord.Embed:
        """Create execution result embed"""
        if success:
            embed = self.create_success_embed(
                title="Task Completed",
                description=f"Task `{task_id}` executed successfully"
            )
            if result:
                embed.add_field(name="Result", value=result[:1024], inline=False)
        else:
            embed = self.create_error_embed(
                title="Task Failed",
                description=f"Task `{task_id}` failed during execution"
            )
            if error:
                embed.add_field(name="Error", value=error[:1024], inline=False)
        
        embed.add_field(name="Duration", value=f"{duration:.2f}s", inline=True)
        
        return embed


class DiscordComponents:
    """Factory for creating interactive Discord components"""
    
    @staticmethod
    def create_agent_buttons() -> discord.ui.View:
        """Create action buttons for agent operations"""
        view = discord.ui.View()
        
        button_create = discord.ui.Button(
            style=discord.ButtonStyle.green,
            label="Create Agent",
            emoji="🆕"
        )
        
        button_list = discord.ui.Button(
            style=discord.ButtonStyle.blurple,
            label="List Agents",
            emoji="📋"
        )
        
        button_status = discord.ui.Button(
            style=discord.ButtonStyle.primary,
            label="Status",
            emoji="📊"
        )
        
        view.add_item(button_create)
        view.add_item(button_list)
        view.add_item(button_status)
        
        return view
    
    @staticmethod
    def create_confirmation_view() -> discord.ui.View:
        """Create confirm/cancel buttons"""
        view = discord.ui.View()
        
        button_confirm = discord.ui.Button(
            style=discord.ButtonStyle.green,
            label="Confirm",
            emoji="✅"
        )
        
        button_cancel = discord.ui.Button(
            style=discord.ButtonStyle.red,
            label="Cancel",
            emoji="❌"
        )
        
        view.add_item(button_confirm)
        view.add_item(button_cancel)
        
        return view
    
    @staticmethod
    def create_pagination_view() -> discord.ui.View:
        """Create pagination buttons"""
        view = discord.ui.View()
        
        button_first = discord.ui.Button(
            style=discord.ButtonStyle.gray,
            label="First",
            emoji="⏮️"
        )
        
        button_prev = discord.ui.Button(
            style=discord.ButtonStyle.gray,
            label="Previous",
            emoji="⏪"
        )
        
        button_next = discord.ui.Button(
            style=discord.ButtonStyle.gray,
            label="Next",
            emoji="⏩"
        )
        
        button_last = discord.ui.Button(
            style=discord.ButtonStyle.gray,
            label="Last",
            emoji="⏭️"
        )
        
        view.add_item(button_first)
        view.add_item(button_prev)
        view.add_item(button_next)
        view.add_item(button_last)
        
        return view
    
    @staticmethod
    def create_role_select() -> discord.ui.View:
        """Create role selection dropdown"""
        view = discord.ui.View()
        
        select = discord.ui.Select(
            placeholder="Choose an agent role",
            min_values=1,
            max_values=1,
            options=[
                discord.SelectOption(label="Analyst", value="analyst", emoji="📊"),
                discord.SelectOption(label="Executor", value="executor", emoji="⚡"),
                discord.SelectOption(label="Creator", value="creator", emoji="🎨"),
                discord.SelectOption(label="Coordinator", value="coordinator", emoji="🎯"),
                discord.SelectOption(label="Monitor", value="monitor", emoji="👁️"),
                discord.SelectOption(label="Researcher", value="researcher", emoji="🔬"),
            ]
        )
        
        view.add_item(select)
        return view
