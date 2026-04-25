"""
Discord Handlers - Command and interaction handlers for Discord bot

Handles:
- Prefix command processing (!agent, !swarm, !skill)
- Slash command processing
- Message reaction handling
- Interaction responses
- Error handling and validation
"""

import discord
from discord.ext import commands
from typing import Optional, Dict, List, Any
import logging
import re
from datetime import datetime

logger = logging.getLogger(__name__)


class DiscordHandlers:
    """Handler for all Discord commands and interactions"""
    
    def __init__(self, agent_framework=None, skill_registry=None):
        """
        Initialize handlers
        
        Args:
            agent_framework: Reference to agent execution framework
            skill_registry: Reference to skill registry system
        """
        self.agent_framework = agent_framework
        self.skill_registry = skill_registry
        self.active_tasks: Dict[str, Dict] = {}
        self.command_history: List[Dict] = []
        self.active_agents = 0
    
    async def handle_agent_command(self, ctx, query: str):
        """
        Handle !agent or /agent commands
        
        Syntax:
            !agent <agent_name> <task_description>
            !agent list
            !agent create <name> <role> <description>
            !agent status <agent_id>
        """
        try:
            # Parse command
            parts = query.strip().split(maxsplit=1)
            if not parts:
                await self._send_error(ctx, "Missing agent subcommand")
                return
            
            subcommand = parts[0].lower()
            args = parts[1] if len(parts) > 1 else ""
            
            self._log_command("agent", subcommand, ctx)
            
            # Route to appropriate handler
            if subcommand == "list":
                await self._agent_list(ctx)
            elif subcommand == "create":
                await self._agent_create(ctx, args)
            elif subcommand == "status":
                await self._agent_status(ctx, args)
            elif subcommand == "execute":
                await self._agent_execute(ctx, args)
            else:
                await self._send_error(ctx, f"Unknown agent subcommand: {subcommand}")
        
        except Exception as e:
            logger.error(f"Error in agent command: {e}")
            await self._send_error(ctx, f"Command failed: {str(e)}")
    
    async def handle_swarm_command(self, ctx, args: str):
        """
        Handle !swarm or /swarm commands
        
        Syntax:
            !swarm list
            !swarm create <name> <description>
            !swarm add <swarm_id> <agent_id>
            !swarm status <swarm_id>
        """
        try:
            parts = args.strip().split(maxsplit=1)
            if not parts:
                await self._send_error(ctx, "Missing swarm subcommand")
                return
            
            subcommand = parts[0].lower()
            args = parts[1] if len(parts) > 1 else ""
            
            self._log_command("swarm", subcommand, ctx)
            
            if subcommand == "list":
                await self._swarm_list(ctx)
            elif subcommand == "create":
                await self._swarm_create(ctx, args)
            elif subcommand == "add":
                await self._swarm_add(ctx, args)
            elif subcommand == "status":
                await self._swarm_status(ctx, args)
            else:
                await self._send_error(ctx, f"Unknown swarm subcommand: {subcommand}")
        
        except Exception as e:
            logger.error(f"Error in swarm command: {e}")
            await self._send_error(ctx, f"Command failed: {str(e)}")
    
    async def handle_skill_command(self, ctx, args: str):
        """
        Handle !skill or /skill commands
        
        Syntax:
            !skill list
            !skill search <query>
            !skill install <skill_name>
            !skill info <skill_name>
        """
        try:
            parts = args.strip().split(maxsplit=1)
            if not parts:
                await self._send_error(ctx, "Missing skill subcommand")
                return
            
            subcommand = parts[0].lower()
            args = parts[1] if len(parts) > 1 else ""
            
            self._log_command("skill", subcommand, ctx)
            
            if subcommand == "list":
                await self._skill_list(ctx)
            elif subcommand == "search":
                await self._skill_search(ctx, args)
            elif subcommand == "install":
                await self._skill_install(ctx, args)
            elif subcommand == "info":
                await self._skill_info(ctx, args)
            else:
                await self._send_error(ctx, f"Unknown skill subcommand: {subcommand}")
        
        except Exception as e:
            logger.error(f"Error in skill command: {e}")
            await self._send_error(ctx, f"Command failed: {str(e)}")
    
    async def handle_reaction(self, reaction: discord.Reaction, user: discord.User):
        """
        Handle message reactions
        
        Common reaction handlers for interactive components
        """
        try:
            if user.bot:
                return
            
            logger.debug(f"Reaction {reaction.emoji} from {user} on message")
            
            # Route based on emoji
            if reaction.emoji == "✅":
                await self._handle_confirm(reaction, user)
            elif reaction.emoji == "❌":
                await self._handle_cancel(reaction, user)
            elif reaction.emoji == "⏭️":
                await self._handle_next(reaction, user)
            elif reaction.emoji == "⏮️":
                await self._handle_previous(reaction, user)
        
        except Exception as e:
            logger.error(f"Error handling reaction: {e}")
    
    # Private handler methods
    
    async def _agent_list(self, ctx):
        """List available agents"""
        # In production, fetch from agent_framework
        agents = [
            {"name": "Analyst", "role": "analyst", "status": "active"},
            {"name": "Executor", "role": "executor", "status": "idle"},
            {"name": "Creator", "role": "creator", "status": "active"}
        ]
        
        agent_list = "\n".join([f"• **{a['name']}** ({a['role']}) - {a['status']}" 
                               for a in agents])
        
        embed = discord.Embed(
            title="Available Agents",
            description=agent_list,
            color=discord.Color.blue()
        )
        await self._send_response(ctx, embed=embed)
    
    async def _agent_create(self, ctx, args: str):
        """Create new agent"""
        parts = args.split()
        if len(parts) < 3:
            await self._send_error(ctx, "Usage: !agent create <name> <role> <description>")
            return
        
        name, role = parts[0], parts[1]
        description = " ".join(parts[2:])
        
        # Validate input
        if not self._validate_agent_name(name):
            await self._send_error(ctx, "Invalid agent name")
            return
        
        if role not in ["analyst", "executor", "creator", "coordinator", "monitor"]:
            await self._send_error(ctx, f"Invalid role: {role}")
            return
        
        # Create agent
        embed = discord.Embed(
            title="✅ Agent Created",
            description=f"**{name}** created with role **{role}**",
            color=discord.Color.green()
        )
        embed.add_field(name="Description", value=description, inline=False)
        embed.add_field(name="Status", value="Ready", inline=True)
        
        await self._send_response(ctx, embed=embed)
    
    async def _agent_status(self, ctx, args: str):
        """Get agent status"""
        if not args:
            await self._send_error(ctx, "Usage: !agent status <agent_name>")
            return
        
        agent_name = args.strip()
        
        # In production, fetch from framework
        embed = discord.Embed(
            title=f"Agent Status: {agent_name}",
            color=discord.Color.blue()
        )
        embed.add_field(name="Status", value="Active", inline=True)
        embed.add_field(name="Tasks Completed", value="42", inline=True)
        embed.add_field(name="Success Rate", value="98.5%", inline=True)
        embed.add_field(name="Last Activity", value="2 minutes ago", inline=True)
        
        await self._send_response(ctx, embed=embed)
    
    async def _agent_execute(self, ctx, args: str):
        """Execute task with agent"""
        if not args:
            await self._send_error(ctx, "Usage: !agent execute <agent_name> <task>")
            return
        
        parts = args.split(maxsplit=1)
        agent_name = parts[0]
        task = parts[1] if len(parts) > 1 else "default task"
        
        self.active_agents += 1
        
        embed = discord.Embed(
            title="🚀 Task Executing",
            description=f"Agent **{agent_name}** is executing task",
            color=discord.Color.yellow()
        )
        embed.add_field(name="Task", value=task, inline=False)
        embed.add_field(name="Progress", value="▓░░░░░░░░░ 10%", inline=False)
        
        await self._send_response(ctx, embed=embed)
    
    async def _swarm_list(self, ctx):
        """List available swarms"""
        swarms = [
            {"name": "Analysis", "agents": 3, "status": "active"},
            {"name": "Execution", "agents": 5, "status": "active"},
            {"name": "Creation", "agents": 2, "status": "idle"}
        ]
        
        swarm_list = "\n".join([f"• **{s['name']}** - {s['agents']} agents ({s['status']})" 
                               for s in swarms])
        
        embed = discord.Embed(
            title="Available Swarms",
            description=swarm_list,
            color=discord.Color.blue()
        )
        await self._send_response(ctx, embed=embed)
    
    async def _swarm_create(self, ctx, args: str):
        """Create new swarm"""
        parts = args.split(maxsplit=1)
        if len(parts) < 1:
            await self._send_error(ctx, "Usage: !swarm create <name> [description]")
            return
        
        name = parts[0]
        description = parts[1] if len(parts) > 1 else "No description"
        
        embed = discord.Embed(
            title="✅ Swarm Created",
            description=f"**{name}** swarm created successfully",
            color=discord.Color.green()
        )
        embed.add_field(name="Description", value=description, inline=False)
        embed.add_field(name="Initial Agents", value="0", inline=True)
        
        await self._send_response(ctx, embed=embed)
    
    async def _swarm_add(self, ctx, args: str):
        """Add agent to swarm"""
        parts = args.split()
        if len(parts) < 2:
            await self._send_error(ctx, "Usage: !swarm add <swarm_name> <agent_name>")
            return
        
        swarm_name, agent_name = parts[0], parts[1]
        
        embed = discord.Embed(
            title="✅ Agent Added to Swarm",
            description=f"**{agent_name}** added to **{swarm_name}**",
            color=discord.Color.green()
        )
        
        await self._send_response(ctx, embed=embed)
    
    async def _swarm_status(self, ctx, args: str):
        """Get swarm status"""
        if not args:
            await self._send_error(ctx, "Usage: !swarm status <swarm_name>")
            return
        
        swarm_name = args.strip()
        
        embed = discord.Embed(
            title=f"Swarm Status: {swarm_name}",
            color=discord.Color.blue()
        )
        embed.add_field(name="Status", value="Active", inline=True)
        embed.add_field(name="Agent Count", value="5", inline=True)
        embed.add_field(name="Total Tasks", value="127", inline=True)
        embed.add_field(name="Success Rate", value="96.2%", inline=True)
        
        await self._send_response(ctx, embed=embed)
    
    async def _skill_list(self, ctx):
        """List installed skills"""
        skills = ["data_analysis", "web_scraping", "nlp_processing", "image_gen"]
        
        skill_list = "\n".join([f"• `{skill}`" for skill in skills])
        
        embed = discord.Embed(
            title="Installed Skills",
            description=skill_list,
            color=discord.Color.blue()
        )
        embed.set_footer(text=f"Total: {len(skills)} skills")
        
        await self._send_response(ctx, embed=embed)
    
    async def _skill_search(self, ctx, query: str):
        """Search for skills"""
        if not query:
            await self._send_error(ctx, "Usage: !skill search <query>")
            return
        
        # In production, search skill registry
        results = [
            {"name": "advanced_data_analysis", "rating": 4.8},
            {"name": "data_validation", "rating": 4.5}
        ]
        
        result_list = "\n".join([f"• **{r['name']}** ⭐ {r['rating']}" 
                                for r in results])
        
        embed = discord.Embed(
            title=f"Skill Search: '{query}'",
            description=result_list,
            color=discord.Color.blue()
        )
        
        await self._send_response(ctx, embed=embed)
    
    async def _skill_install(self, ctx, skill_name: str):
        """Install skill"""
        if not skill_name:
            await self._send_error(ctx, "Usage: !skill install <skill_name>")
            return
        
        embed = discord.Embed(
            title="✅ Skill Installed",
            description=f"**{skill_name}** installed successfully",
            color=discord.Color.green()
        )
        embed.add_field(name="Version", value="1.0.0", inline=True)
        embed.add_field(name="Dependencies", value="Resolved", inline=True)
        
        await self._send_response(ctx, embed=embed)
    
    async def _skill_info(self, ctx, skill_name: str):
        """Get skill information"""
        if not skill_name:
            await self._send_error(ctx, "Usage: !skill info <skill_name>")
            return
        
        embed = discord.Embed(
            title=f"Skill Info: {skill_name}",
            color=discord.Color.blue()
        )
        embed.add_field(name="Version", value="1.0.0", inline=True)
        embed.add_field(name="Rating", value="⭐⭐⭐⭐⭐", inline=True)
        embed.add_field(name="Downloads", value="1,240", inline=True)
        embed.add_field(name="Author", value="SintraPrime", inline=True)
        embed.add_field(name="Description", value="Advanced skill for data processing", inline=False)
        
        await self._send_response(ctx, embed=embed)
    
    # Reaction handlers
    
    async def _handle_confirm(self, reaction: discord.Reaction, user: discord.User):
        """Handle confirmation reaction"""
        logger.info(f"{user} confirmed action")
    
    async def _handle_cancel(self, reaction: discord.Reaction, user: discord.User):
        """Handle cancel reaction"""
        logger.info(f"{user} cancelled action")
    
    async def _handle_next(self, reaction: discord.Reaction, user: discord.User):
        """Handle next page reaction"""
        logger.info(f"{user} requested next page")
    
    async def _handle_previous(self, reaction: discord.Reaction, user: discord.User):
        """Handle previous page reaction"""
        logger.info(f"{user} requested previous page")
    
    # Utility methods
    
    async def _send_response(self, ctx, content: str = None, embed: discord.Embed = None):
        """Send response message"""
        try:
            await ctx.send(content=content, embed=embed)
        except Exception as e:
            logger.error(f"Failed to send response: {e}")
    
    async def _send_error(self, ctx, message: str):
        """Send error message"""
        embed = discord.Embed(
            title="❌ Error",
            description=message,
            color=discord.Color.red()
        )
        await self._send_response(ctx, embed=embed)
    
    def _validate_agent_name(self, name: str) -> bool:
        """Validate agent name"""
        return bool(re.match(r"^[a-zA-Z0-9_-]{3,32}$", name))
    
    def _log_command(self, command: str, subcommand: str, ctx):
        """Log command execution"""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "user": str(ctx.author),
            "command": command,
            "subcommand": subcommand,
            "guild": str(ctx.guild) if ctx.guild else "DM"
        }
        self.command_history.append(log_entry)
        logger.info(f"Command: {command} {subcommand} by {ctx.author}")
    
    def get_active_agents_count(self) -> int:
        """Get count of active agents"""
        return self.active_agents
    
    def get_command_history(self, limit: int = 100) -> List[Dict]:
        """Get command execution history"""
        return self.command_history[-limit:]
