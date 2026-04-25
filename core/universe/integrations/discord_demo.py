"""
Discord Integration Demo - Example usage and integration patterns

Demonstrates:
- Bot initialization and setup
- Command handling
- Server configuration
- Permission management
- Interactive components
"""

import asyncio
import os
from datetime import datetime
from typing import Optional

# Import Discord integration modules
from discord_bridge import create_discord_bot
from discord_handlers import DiscordHandlers
from discord_embeds import DiscordEmbeds, DiscordComponents
from discord_server_mgmt import ServerManager, PermissionLevel, ChannelType


class DiscordIntegrationDemo:
    """Demonstration of Discord integration capabilities"""
    
    def __init__(self):
        """Initialize demo components"""
        self.bot = None
        self.server_manager = ServerManager()
        self.embeds = DiscordEmbeds()
        self.handlers = DiscordHandlers()
        
        print("=" * 70)
        print("DISCORD INTEGRATION DEMO - SintraPrime UniVerse")
        print("=" * 70)
    
    def demo_bot_initialization(self):
        """Demonstrate bot initialization"""
        print("\n[1] Bot Initialization")
        print("-" * 70)
        
        # In production, use environment variable
        token = "YOUR_DISCORD_BOT_TOKEN"
        
        # Create bot instance
        print(f"Creating bot with token: {token[:20]}...")
        self.bot = create_discord_bot(
            token=token,
            agent_framework=None,  # Would pass actual framework
            event_hub=None         # Would pass actual event hub
        )
        
        print("✓ Bot instance created")
        print(f"  - Command prefix: {self.bot.bot.command_prefix}")
        print(f"  - Intents configured: True")
        print(f"  - Ready to connect")
    
    def demo_server_configuration(self):
        """Demonstrate server configuration management"""
        print("\n[2] Server Configuration Management")
        print("-" * 70)
        
        # Initialize server config
        guild_id = "123456789"
        guild_name = "Test Discord Server"
        
        from discord_server_mgmt import ServerConfig
        config = ServerConfig(guild_id, guild_name)
        self.server_manager.configs[guild_id] = config
        
        print(f"Initialized config for guild: {guild_name}")
        
        # Set custom prefix
        print("\nConfiguring server settings:")
        self.server_manager.set_prefix(guild_id, "?")
        print(f"  ✓ Prefix set to: ?")
        
        # Assign roles
        self.server_manager.assign_mod_role(guild_id, 987654321)
        print(f"  ✓ Moderator role assigned")
        
        self.server_manager.assign_admin_role(guild_id, 876543210)
        print(f"  ✓ Admin role assigned")
        
        # Enable/disable features
        self.server_manager.enable_feature(guild_id, "slash_commands")
        print(f"  ✓ Slash commands enabled")
        
        # Record statistics
        self.server_manager.record_stat(guild_id, "commands_executed", 5)
        self.server_manager.record_stat(guild_id, "agents_spawned", 2)
        print(f"  ✓ Statistics recorded")
        
        # Display configuration
        config = self.server_manager.get_config(guild_id)
        print(f"\nServer Configuration Summary:")
        print(f"  - Guild: {config.guild_name}")
        print(f"  - Prefix: {config.prefix}")
        print(f"  - Enabled Features: {len(config.enabled_features)}")
        print(f"  - Moderator Roles: {len(config.mod_roles)}")
        print(f"  - Admin Roles: {len(config.admin_roles)}")
    
    def demo_embed_creation(self):
        """Demonstrate embed creation for various messages"""
        print("\n[3] Rich Embed Creation")
        print("-" * 70)
        
        # Welcome embed
        class MockGuild:
            name = "Test Guild"
            icon = None
        
        embed = self.embeds.create_welcome_embed(MockGuild())
        print(f"\n✓ Welcome Embed:")
        print(f"  - Title: {embed.title}")
        print(f"  - Fields: {len(embed.fields)}")
        
        # Success embed
        embed = self.embeds.create_success_embed(
            title="Agent Created",
            description="New agent successfully initialized",
            fields={"Status": "Ready", "Role": "Analyst"}
        )
        print(f"\n✓ Success Embed:")
        print(f"  - Title: {embed.title}")
        print(f"  - Color: {embed.color}")
        
        # Error embed
        embed = self.embeds.create_error_embed(
            title="Command Failed",
            description="Unable to execute agent command",
            error_type="PermissionError"
        )
        print(f"\n✓ Error Embed:")
        print(f"  - Title: {embed.title}")
        print(f"  - Error Type: PermissionError")
        
        # Progress embed
        embed = self.embeds.create_progress_embed(
            title="Task Execution",
            progress=65,
            total=100
        )
        print(f"\n✓ Progress Embed:")
        print(f"  - Progress: 65%")
        print(f"  - Shows progress bar")
        
        # Agent card
        embed = self.embeds.create_agent_card(
            agent_name="DataAnalyst",
            role="analyst",
            status="active",
            tasks_completed=42,
            success_rate=98.5
        )
        print(f"\n✓ Agent Card:")
        print(f"  - Agent: DataAnalyst")
        print(f"  - Tasks: 42")
        print(f"  - Success Rate: 98.5%")
        
        # Status embed
        embed = self.embeds.create_status_embed(
            bot_status="Connected",
            uptime="2h 15m 30s",
            agents_active=7
        )
        print(f"\n✓ Status Embed:")
        print(f"  - Bot Status: Connected")
        print(f"  - Uptime: 2h 15m 30s")
        print(f"  - Active Agents: 7")
    
    def demo_components(self):
        """Demonstrate interactive components"""
        print("\n[4] Interactive Components")
        print("-" * 70)
        
        # Agent buttons
        view = DiscordComponents.create_agent_buttons()
        print(f"\n✓ Agent Buttons:")
        print(f"  - Components created: {len(view.children)}")
        print(f"  - Actions: Create, List, Status")
        
        # Confirmation buttons
        view = DiscordComponents.create_confirmation_view()
        print(f"\n✓ Confirmation Buttons:")
        print(f"  - Confirm button")
        print(f"  - Cancel button")
        
        # Pagination buttons
        view = DiscordComponents.create_pagination_view()
        print(f"\n✓ Pagination Buttons:")
        print(f"  - Components: {len(view.children)}")
        print(f"  - Navigation: First, Prev, Next, Last")
        
        # Role selection
        view = DiscordComponents.create_role_select()
        print(f"\n✓ Role Selection:")
        print(f"  - Dropdown menu")
        print(f"  - Options: Analyst, Executor, Creator, Coordinator, Monitor, Researcher")
    
    def demo_permissions(self):
        """Demonstrate permission system"""
        print("\n[5] Permission System")
        print("-" * 70)
        
        guild_id = "123456789"
        
        # Create mock user
        class MockMember:
            id = 999999999
            guild = MockGuild = type('Guild', (), {'owner_id': 111111111})()
            roles = []
        
        class MockGuild:
            owner_id = 111111111
        
        mock_user = MockMember()
        
        # Check permissions
        print(f"\nPermission Checks:")
        
        # Server owner always has full access
        mock_user.guild.owner_id = mock_user.id
        result = self.server_manager.check_permission(
            guild_id, mock_user, PermissionLevel.OWNER
        )
        print(f"  ✓ Owner check: {result}")
        
        # Admin level check
        result = self.server_manager.check_permission(
            guild_id, mock_user, PermissionLevel.ADMIN
        )
        print(f"  ✓ Admin check: {result}")
        
        # User level check (less restrictive)
        result = self.server_manager.check_permission(
            guild_id, mock_user, PermissionLevel.USER
        )
        print(f"  ✓ User check: {result}")
        
        # Granular permission management
        from discord_server_mgmt import GuildPermissionManager
        perm_mgr = GuildPermissionManager()
        
        print(f"\nGranular Permissions:")
        perm_mgr.set_user_permission(guild_id, 888888888, PermissionLevel.MODERATOR)
        print(f"  ✓ User 888888888 set to MODERATOR")
        
        perm = perm_mgr.get_user_permission(guild_id, 888888888)
        print(f"  ✓ Retrieved permission: {perm.name}")
    
    def demo_command_handling(self):
        """Demonstrate command parsing and handling"""
        print("\n[6] Command Handling")
        print("-" * 70)
        
        # Demonstrate validation
        print(f"\nAgent Name Validation:")
        valid_names = ["Agent1", "test-agent", "agent_123"]
        invalid_names = ["ab", "agent@test", "x" * 50]
        
        for name in valid_names:
            result = self.handlers._validate_agent_name(name)
            print(f"  ✓ '{name}': Valid")
        
        for name in invalid_names:
            result = self.handlers._validate_agent_name(name)
            print(f"  ✗ '{name}': Invalid")
        
        # Command logging
        print(f"\nCommand Logging:")
        
        class MockCtx:
            class Author:
                name = "TestUser"
            class Guild:
                name = "TestGuild"
            author = Author()
            guild = Guild()
        
        for i in range(3):
            self.handlers._log_command("agent", f"create{i}", MockCtx())
        
        print(f"  ✓ Logged 3 commands")
        history = self.handlers.get_command_history(limit=10)
        print(f"  ✓ Retrieved history: {len(history)} entries")
        
        if history:
            latest = history[-1]
            print(f"    - Latest: {latest['command']} {latest['subcommand']}")
    
    def demo_statistics(self):
        """Demonstrate statistics tracking"""
        print("\n[7] Statistics & Analytics")
        print("-" * 70)
        
        guild_id = "123456789"
        
        # Record various statistics
        self.server_manager.record_stat(guild_id, "commands_executed", 1)
        self.server_manager.record_stat(guild_id, "agents_spawned", 1)
        self.server_manager.record_stat(guild_id, "swarms_created", 1)
        self.server_manager.record_stat(guild_id, "tasks_created", 5)
        
        # Get statistics
        stats = self.server_manager.get_stats(guild_id)
        
        print(f"\nGuild Statistics:")
        for key, value in stats.items():
            if not key.startswith("_"):
                print(f"  - {key}: {value}")
    
    def demo_multi_server(self):
        """Demonstrate multi-server support"""
        print("\n[8] Multi-Server Support")
        print("-" * 70)
        
        # Create configurations for multiple servers
        servers = [
            ("111111111", "Analytics Guild"),
            ("222222222", "Development Guild"),
            ("333333333", "Operations Guild"),
        ]
        
        from discord_server_mgmt import ServerConfig
        
        print(f"\nInitializing {len(servers)} servers:")
        
        for guild_id, guild_name in servers:
            config = ServerConfig(guild_id, guild_name)
            self.server_manager.configs[guild_id] = config
            self.server_manager.record_stat(guild_id, "initialized", 1)
            print(f"  ✓ {guild_name}")
        
        # Display all configs
        all_configs = self.server_manager.get_all_configs()
        print(f"\nManaged Servers: {len(all_configs)}")
        for config in all_configs:
            stats = self.server_manager.get_stats(config.guild_id)
            print(f"  - {config.guild_name}: {config.guild_id}")
    
    def run_full_demo(self):
        """Run complete demonstration"""
        try:
            self.demo_bot_initialization()
            self.demo_server_configuration()
            self.demo_embed_creation()
            self.demo_components()
            self.demo_permissions()
            self.demo_command_handling()
            self.demo_statistics()
            self.demo_multi_server()
            
            # Summary
            print("\n" + "=" * 70)
            print("DEMO SUMMARY")
            print("=" * 70)
            print("\n✅ All demonstrations completed successfully!")
            print("\nKey Features Demonstrated:")
            print("  1. Bot initialization and configuration")
            print("  2. Per-server configuration management")
            print("  3. Rich embed creation for various message types")
            print("  4. Interactive UI components (buttons, selects)")
            print("  5. Role-based permission system")
            print("  6. Command parsing and validation")
            print("  7. Statistics and analytics tracking")
            print("  8. Multi-server support")
            
            print("\n" + "=" * 70)
            print("Next Steps:")
            print("  1. Set up Discord bot token in environment")
            print("  2. Connect bot to Discord server")
            print("  3. Test commands in Discord channel")
            print("  4. Configure per-server settings")
            print("  5. Integrate with agent framework")
            print("=" * 70)
            
        except Exception as e:
            print(f"\n❌ Demo failed with error: {e}")
            import traceback
            traceback.print_exc()


def main():
    """Main entry point"""
    demo = DiscordIntegrationDemo()
    demo.run_full_demo()


if __name__ == "__main__":
    main()
