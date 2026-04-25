"""
Test Suite for Discord Integration - Complete coverage of all components

Tests:
- Command parsing and routing
- Embed building and formatting
- Interaction handling
- Permission checking
- Server management
- Error scenarios
"""

import unittest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
import discord
from datetime import datetime
from typing import Optional

# Import modules to test
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from integrations.discord_handlers import DiscordHandlers
from integrations.discord_embeds import DiscordEmbeds, DiscordComponents
from integrations.discord_server_mgmt import (
    ServerManager, ServerConfig, PermissionLevel, GuildPermissionManager
)


class TestDiscordHandlers(unittest.TestCase):
    """Test cases for Discord command handlers"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.handlers = DiscordHandlers()
        
        # Mock context
        self.mock_ctx = AsyncMock(spec=discord.ext.commands.Context)
        self.mock_ctx.author = Mock(spec=discord.Member)
        self.mock_ctx.author.name = "TestUser"
        self.mock_ctx.guild = Mock(spec=discord.Guild)
        self.mock_ctx.guild.name = "TestGuild"
    
    def test_handler_initialization(self):
        """Test handler initialization"""
        self.assertIsNotNone(self.handlers)
        self.assertEqual(len(self.handlers.command_history), 0)
        self.assertEqual(self.handlers.active_agents, 0)
    
    def test_command_validation_agent_name(self):
        """Test agent name validation"""
        # Valid names
        self.assertTrue(self.handlers._validate_agent_name("Agent1"))
        self.assertTrue(self.handlers._validate_agent_name("test-agent"))
        self.assertTrue(self.handlers._validate_agent_name("agent_123"))
        
        # Invalid names
        self.assertFalse(self.handlers._validate_agent_name("ab"))  # Too short
        self.assertFalse(self.handlers._validate_agent_name("a" * 40))  # Too long
        self.assertFalse(self.handlers._validate_agent_name("agent@test"))  # Invalid char
    
    def test_command_logging(self):
        """Test command logging"""
        self.handlers._log_command("agent", "create", self.mock_ctx)
        
        self.assertEqual(len(self.handlers.command_history), 1)
        entry = self.handlers.command_history[0]
        self.assertEqual(entry["command"], "agent")
        self.assertEqual(entry["subcommand"], "create")
        self.assertIn("timestamp", entry)
    
    def test_command_history_limit(self):
        """Test command history is accessible"""
        for i in range(10):
            self.handlers._log_command("agent", f"cmd{i}", self.mock_ctx)
        
        history = self.handlers.get_command_history(limit=5)
        self.assertEqual(len(history), 5)
    
    def test_active_agents_tracking(self):
        """Test active agents counter"""
        initial = self.handlers.get_active_agents_count()
        self.handlers.active_agents += 1
        self.assertEqual(self.handlers.get_active_agents_count(), initial + 1)


class TestDiscordEmbeds(unittest.TestCase):
    """Test cases for Discord embed creation"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.embeds = DiscordEmbeds()
        
        # Mock guild
        self.mock_guild = Mock(spec=discord.Guild)
        self.mock_guild.name = "TestGuild"
        self.mock_guild.icon = Mock()
        self.mock_guild.icon.url = "https://example.com/icon.png"
    
    def test_welcome_embed_creation(self):
        """Test welcome embed creation"""
        embed = self.embeds.create_welcome_embed(self.mock_guild)
        
        self.assertIsInstance(embed, discord.Embed)
        self.assertIn("Welcome", embed.title)
        self.assertGreater(len(embed.fields), 0)
    
    def test_error_embed_creation(self):
        """Test error embed creation"""
        embed = self.embeds.create_error_embed(
            title="Test Error",
            description="This is a test error",
            error_type="ValueError"
        )
        
        self.assertIsInstance(embed, discord.Embed)
        self.assertIn("❌", embed.title)
        self.assertEqual(embed.color, self.embeds.COLOR_ERROR)
    
    def test_success_embed_creation(self):
        """Test success embed creation"""
        embed = self.embeds.create_success_embed(
            title="Test Success",
            description="Operation completed",
            fields={"Status": "OK"}
        )
        
        self.assertIsInstance(embed, discord.Embed)
        self.assertIn("✅", embed.title)
        self.assertEqual(embed.color, self.embeds.COLOR_SUCCESS)
    
    def test_info_embed_creation(self):
        """Test info embed creation"""
        embed = self.embeds.create_info_embed(
            title="Test Info",
            description="Information message"
        )
        
        self.assertIsInstance(embed, discord.Embed)
        self.assertEqual(embed.color, self.embeds.COLOR_INFO)
    
    def test_warning_embed_creation(self):
        """Test warning embed creation"""
        embed = self.embeds.create_warning_embed(
            title="Test Warning",
            description="Warning message"
        )
        
        self.assertIsInstance(embed, discord.Embed)
        self.assertEqual(embed.color, self.embeds.COLOR_WARNING)
    
    def test_progress_embed_creation(self):
        """Test progress embed with progress bar"""
        embed = self.embeds.create_progress_embed(
            title="Processing",
            progress=50,
            total=100
        )
        
        self.assertIsInstance(embed, discord.Embed)
        self.assertIn("50%", embed.description)
        self.assertIn("▓", embed.description)
    
    def test_progress_bar_accuracy(self):
        """Test progress bar calculation accuracy"""
        # Test various progress levels
        for progress in [0, 25, 50, 75, 100]:
            embed = self.embeds.create_progress_embed(
                title="Test",
                progress=progress,
                total=100
            )
            self.assertIn(f"{progress}%", embed.description)
    
    def test_status_embed_creation(self):
        """Test status embed creation"""
        embed = self.embeds.create_status_embed(
            bot_status="Connected",
            uptime="1h 30m 45s",
            agents_active=5
        )
        
        self.assertIsInstance(embed, discord.Embed)
        self.assertGreater(len(embed.fields), 0)
    
    def test_help_embed_creation(self):
        """Test help embed creation"""
        embed = self.embeds.create_help_embed()
        
        self.assertIsInstance(embed, discord.Embed)
        self.assertGreater(len(embed.fields), 0)
        
        # Check that help mentions main commands
        help_text = "\n".join([f.value for f in embed.fields])
        self.assertIn("agent", help_text.lower())
        self.assertIn("swarm", help_text.lower())
        self.assertIn("skill", help_text.lower())
    
    def test_agent_card_creation(self):
        """Test agent profile card creation"""
        embed = self.embeds.create_agent_card(
            agent_name="TestAgent",
            role="analyst",
            status="active",
            tasks_completed=42,
            success_rate=98.5
        )
        
        self.assertIsInstance(embed, discord.Embed)
        self.assertIn("TestAgent", embed.title)
    
    def test_swarm_card_creation(self):
        """Test swarm profile card creation"""
        embed = self.embeds.create_swarm_card(
            swarm_name="TestSwarm",
            agent_count=5,
            status="active",
            total_tasks=127
        )
        
        self.assertIsInstance(embed, discord.Embed)
        self.assertIn("TestSwarm", embed.title)
    
    def test_leaderboard_embed_creation(self):
        """Test leaderboard embed creation"""
        entries = [("Agent1", 100), ("Agent2", 90), ("Agent3", 80)]
        embed = self.embeds.create_leaderboard_embed(
            title="Top Agents",
            entries=entries
        )
        
        self.assertIsInstance(embed, discord.Embed)
        self.assertIn("Agent1", embed.description)
        self.assertIn("100", embed.description)


class TestDiscordComponents(unittest.TestCase):
    """Test cases for Discord UI components"""
    
    def test_agent_buttons_creation(self):
        """Test agent action buttons creation"""
        view = DiscordComponents.create_agent_buttons()
        
        self.assertIsNotNone(view)
        self.assertGreater(len(view.children), 0)
    
    def test_confirmation_view_creation(self):
        """Test confirmation buttons creation"""
        view = DiscordComponents.create_confirmation_view()
        
        self.assertIsNotNone(view)
        self.assertEqual(len(view.children), 2)  # Confirm and Cancel
    
    def test_pagination_view_creation(self):
        """Test pagination buttons creation"""
        view = DiscordComponents.create_pagination_view()
        
        self.assertIsNotNone(view)
        self.assertEqual(len(view.children), 4)  # First, Prev, Next, Last
    
    def test_role_select_creation(self):
        """Test role selection dropdown creation"""
        view = DiscordComponents.create_role_select()
        
        self.assertIsNotNone(view)
        self.assertGreater(len(view.children), 0)


class TestServerConfig(unittest.TestCase):
    """Test cases for ServerConfig class"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.config = ServerConfig("123456789", "TestGuild")
    
    def test_config_initialization(self):
        """Test server config initialization"""
        self.assertEqual(self.config.guild_id, "123456789")
        self.assertEqual(self.config.guild_name, "TestGuild")
        self.assertEqual(self.config.prefix, "!")
        self.assertGreater(len(self.config.enabled_features), 0)
    
    def test_config_to_dict(self):
        """Test config serialization"""
        data = self.config.to_dict()
        
        self.assertIsInstance(data, dict)
        self.assertEqual(data["guild_id"], "123456789")
        self.assertEqual(data["guild_name"], "TestGuild")
        self.assertIn("channels", data)
        self.assertIn("stats", data)
    
    def test_config_from_dict(self):
        """Test config deserialization"""
        original = self.config.to_dict()
        restored = ServerConfig.from_dict(original)
        
        self.assertEqual(restored.guild_id, original["guild_id"])
        self.assertEqual(restored.guild_name, original["guild_name"])
        self.assertEqual(restored.prefix, original["prefix"])


class TestServerManager(unittest.TestCase):
    """Test cases for ServerManager"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.manager = ServerManager()
    
    def test_manager_initialization(self):
        """Test server manager initialization"""
        self.assertIsNotNone(self.manager)
        self.assertEqual(len(self.manager.configs), 0)
    
    def test_config_creation(self):
        """Test creating guild configuration"""
        config = ServerConfig("123456789", "TestGuild")
        self.manager.configs["123456789"] = config
        
        retrieved = self.manager.get_config("123456789")
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.guild_name, "TestGuild")
    
    def test_prefix_management(self):
        """Test prefix management"""
        config = ServerConfig("123456789", "TestGuild")
        self.manager.configs["123456789"] = config
        
        self.assertTrue(self.manager.set_prefix("123456789", "?"))
        self.assertEqual(self.manager.get_config("123456789").prefix, "?")
    
    def test_invalid_prefix(self):
        """Test invalid prefix rejection"""
        config = ServerConfig("123456789", "TestGuild")
        self.manager.configs["123456789"] = config
        
        # Too long prefix
        self.assertFalse(self.manager.set_prefix("123456789", "!!!!!!!!"))
    
    def test_mod_role_assignment(self):
        """Test moderator role assignment"""
        config = ServerConfig("123456789", "TestGuild")
        self.manager.configs["123456789"] = config
        
        self.assertTrue(self.manager.assign_mod_role("123456789", 987654321))
        self.assertIn(987654321, self.manager.get_config("123456789").mod_roles)
    
    def test_admin_role_assignment(self):
        """Test admin role assignment"""
        config = ServerConfig("123456789", "TestGuild")
        self.manager.configs["123456789"] = config
        
        self.assertTrue(self.manager.assign_admin_role("123456789", 987654321))
        self.assertIn(987654321, self.manager.get_config("123456789").admin_roles)
    
    def test_feature_management(self):
        """Test feature enable/disable"""
        config = ServerConfig("123456789", "TestGuild")
        self.manager.configs["123456789"] = config
        
        self.assertTrue(self.manager.disable_feature("123456789", "prefix_commands"))
        self.assertFalse(self.manager.is_feature_enabled("123456789", "prefix_commands"))
        
        self.assertTrue(self.manager.enable_feature("123456789", "prefix_commands"))
        self.assertTrue(self.manager.is_feature_enabled("123456789", "prefix_commands"))
    
    def test_stats_recording(self):
        """Test statistics recording"""
        config = ServerConfig("123456789", "TestGuild")
        self.manager.configs["123456789"] = config
        
        self.manager.record_stat("123456789", "commands_executed")
        self.manager.record_stat("123456789", "commands_executed", 5)
        
        stats = self.manager.get_stats("123456789")
        self.assertEqual(stats["commands_executed"], 6)
    
    def test_config_export_import(self):
        """Test configuration export and import"""
        config = ServerConfig("123456789", "TestGuild")
        self.manager.configs["123456789"] = config
        
        exported = self.manager.export_configs()
        self.assertGreater(len(exported), 0)
        
        # Create new manager and import
        new_manager = ServerManager()
        new_manager.import_configs(exported)
        
        imported_config = new_manager.get_config("123456789")
        self.assertIsNotNone(imported_config)


class TestGuildPermissionManager(unittest.TestCase):
    """Test cases for GuildPermissionManager"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.perm_manager = GuildPermissionManager()
    
    def test_permission_manager_initialization(self):
        """Test permission manager initialization"""
        self.assertIsNotNone(self.perm_manager)
        self.assertEqual(len(self.perm_manager.user_permissions), 0)
    
    def test_set_user_permission(self):
        """Test setting user permission"""
        self.perm_manager.set_user_permission(
            "123456789",
            987654321,
            PermissionLevel.ADMIN
        )
        
        perm = self.perm_manager.get_user_permission("123456789", 987654321)
        self.assertEqual(perm, PermissionLevel.ADMIN)
    
    def test_remove_user_permission(self):
        """Test removing user permission"""
        self.perm_manager.set_user_permission(
            "123456789",
            987654321,
            PermissionLevel.MODERATOR
        )
        
        self.assertTrue(
            self.perm_manager.remove_user_permission("123456789", 987654321)
        )
        
        perm = self.perm_manager.get_user_permission("123456789", 987654321)
        self.assertIsNone(perm)


class TestPermissionLevels(unittest.TestCase):
    """Test cases for permission level enumeration"""
    
    def test_permission_level_values(self):
        """Test permission level values"""
        self.assertGreater(PermissionLevel.OWNER.value, PermissionLevel.ADMIN.value)
        self.assertGreater(PermissionLevel.ADMIN.value, PermissionLevel.MODERATOR.value)
        self.assertGreater(PermissionLevel.MODERATOR.value, PermissionLevel.USER.value)
        self.assertGreater(PermissionLevel.USER.value, PermissionLevel.GUEST.value)


def run_tests():
    """Run all tests"""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    suite.addTests(loader.loadTestsFromTestCase(TestDiscordHandlers))
    suite.addTests(loader.loadTestsFromTestCase(TestDiscordEmbeds))
    suite.addTests(loader.loadTestsFromTestCase(TestDiscordComponents))
    suite.addTests(loader.loadTestsFromTestCase(TestServerConfig))
    suite.addTests(loader.loadTestsFromTestCase(TestServerManager))
    suite.addTests(loader.loadTestsFromTestCase(TestGuildPermissionManager))
    suite.addTests(loader.loadTestsFromTestCase(TestPermissionLevels))
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result


if __name__ == "__main__":
    result = run_tests()
    exit(0 if result.wasSuccessful() else 1)
