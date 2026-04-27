"""
Phase 18B — React Native Mobile App Scaffold Tests
"""
import json
import os
import sys
import tempfile
import uuid

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

from phase18.mobile_app.app_scaffold import (
    AppConfig,
    BuildArtifact,
    BuildManager,
    BuildVariant,
    NavigationStyle,
    OTAUpdate,
    Platform,
    ScaffoldGenerator,
    Screen,
    TemplateGenerator,
    DEFAULT_SCREENS,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def config():
    return AppConfig(
        name="SintraPrime",
        slug="sintraprime",
        version="1.0.0",
        build_number=1,
        description="AI-powered legal assistant",
        api_base_url="https://api.sintraprime.com",
    )


@pytest.fixture
def generator(config):
    return ScaffoldGenerator(config)


@pytest.fixture
def build_manager():
    return BuildManager()


@pytest.fixture
def template_gen():
    return TemplateGenerator()


# ---------------------------------------------------------------------------
# AppConfig tests
# ---------------------------------------------------------------------------

class TestAppConfig:
    def test_default_bundle_id(self):
        cfg = AppConfig(name="Test", slug="test-app")
        assert cfg.bundle_id == "com.sintraprime.test-app"

    def test_default_package_name(self):
        cfg = AppConfig(name="Test", slug="test-app")
        assert cfg.package_name == "com.sintraprime.test-app"

    def test_custom_bundle_id(self):
        cfg = AppConfig(name="Test", slug="test-app", bundle_id="com.custom.app")
        assert cfg.bundle_id == "com.custom.app"

    def test_default_platforms(self, config):
        assert Platform.IOS in config.platforms
        assert Platform.ANDROID in config.platforms

    def test_default_navigation(self, config):
        assert config.navigation == NavigationStyle.TABS

    def test_default_features_empty(self, config):
        assert config.features == []

    def test_primary_color_default(self, config):
        assert config.primary_color == "#1a1a2e"

    def test_accent_color_default(self, config):
        assert config.accent_color == "#e94560"


# ---------------------------------------------------------------------------
# TemplateGenerator tests
# ---------------------------------------------------------------------------

class TestTemplateGenerator:
    def test_app_json_has_expo_key(self, template_gen, config):
        result = template_gen.app_json(config)
        assert "expo" in result

    def test_app_json_name(self, template_gen, config):
        result = template_gen.app_json(config)
        assert result["expo"]["name"] == "SintraPrime"

    def test_app_json_slug(self, template_gen, config):
        result = template_gen.app_json(config)
        assert result["expo"]["slug"] == "sintraprime"

    def test_app_json_version(self, template_gen, config):
        result = template_gen.app_json(config)
        assert result["expo"]["version"] == "1.0.0"

    def test_app_json_ios_bundle_id(self, template_gen, config):
        result = template_gen.app_json(config)
        assert result["expo"]["ios"]["bundleIdentifier"] == "com.sintraprime.sintraprime"

    def test_app_json_android_package(self, template_gen, config):
        result = template_gen.app_json(config)
        assert result["expo"]["android"]["package"] == "com.sintraprime.sintraprime"

    def test_app_json_has_plugins(self, template_gen, config):
        result = template_gen.app_json(config)
        assert "expo-router" in result["expo"]["plugins"]

    def test_package_json_has_scripts(self, template_gen, config):
        result = template_gen.package_json(config)
        assert "start" in result["scripts"]
        assert "build:prod" in result["scripts"]

    def test_package_json_has_expo_dependency(self, template_gen, config):
        result = template_gen.package_json(config)
        assert "expo" in result["dependencies"]

    def test_package_json_has_react_native(self, template_gen, config):
        result = template_gen.package_json(config)
        assert "react-native" in result["dependencies"]

    def test_package_json_version(self, template_gen, config):
        result = template_gen.package_json(config)
        assert result["version"] == "1.0.0"

    def test_tsconfig_extends_expo(self, template_gen):
        result = template_gen.tsconfig_json()
        assert "expo/tsconfig.base" in result["extends"]

    def test_tsconfig_strict_mode(self, template_gen):
        result = template_gen.tsconfig_json()
        assert result["compilerOptions"]["strict"] is True

    def test_tsconfig_has_path_aliases(self, template_gen):
        result = template_gen.tsconfig_json()
        assert "@/*" in result["compilerOptions"]["paths"]

    def test_eas_json_has_build_profiles(self, template_gen, config):
        result = template_gen.eas_json(config)
        assert "development" in result["build"]
        assert "staging" in result["build"]
        assert "production" in result["build"]

    def test_eas_json_production_api_url(self, template_gen, config):
        result = template_gen.eas_json(config)
        assert result["build"]["production"]["env"]["API_BASE_URL"] == config.api_base_url

    def test_eas_json_development_simulator(self, template_gen, config):
        result = template_gen.eas_json(config)
        assert result["build"]["development"]["ios"]["simulator"] is True

    def test_screen_component_contains_screen_name(self, template_gen, config):
        screen = DEFAULT_SCREENS[0]  # Home
        code = template_gen.screen_component(screen, config)
        assert "HomeScreen" in code

    def test_screen_component_contains_title(self, template_gen, config):
        screen = DEFAULT_SCREENS[0]
        code = template_gen.screen_component(screen, config)
        assert screen.title in code

    def test_api_service_contains_base_url(self, template_gen, config):
        code = template_gen.api_service(config)
        assert config.api_base_url in code

    def test_api_service_has_auth_interceptor(self, template_gen, config):
        code = template_gen.api_service(config)
        assert "interceptors.request" in code

    def test_api_service_has_401_handler(self, template_gen, config):
        code = template_gen.api_service(config)
        assert "401" in code


# ---------------------------------------------------------------------------
# ScaffoldGenerator tests
# ---------------------------------------------------------------------------

class TestScaffoldGenerator:
    def test_generate_manifest_has_app_json(self, generator):
        manifest = generator.generate_manifest()
        assert "app.json" in manifest

    def test_generate_manifest_has_package_json(self, generator):
        manifest = generator.generate_manifest()
        assert "package.json" in manifest

    def test_generate_manifest_has_tsconfig(self, generator):
        manifest = generator.generate_manifest()
        assert "tsconfig.json" in manifest

    def test_generate_manifest_has_eas_json(self, generator):
        manifest = generator.generate_manifest()
        assert "eas.json" in manifest

    def test_generate_manifest_has_api_service(self, generator):
        manifest = generator.generate_manifest()
        assert "services/api.ts" in manifest

    def test_generate_manifest_has_screen_files(self, generator):
        manifest = generator.generate_manifest()
        # At least the tab screens should be present
        screen_files = [k for k in manifest.keys() if k.endswith(".tsx")]
        assert len(screen_files) >= 5

    def test_file_count(self, generator):
        assert generator.file_count() >= 10  # app.json + package.json + tsconfig + eas + api + screens

    def test_write_to_disk(self, generator):
        with tempfile.TemporaryDirectory() as tmpdir:
            written = generator.write_to_disk(tmpdir)
            assert len(written) >= 10
            for path in written:
                assert os.path.exists(path)

    def test_write_to_disk_app_json_valid(self, generator):
        with tempfile.TemporaryDirectory() as tmpdir:
            generator.write_to_disk(tmpdir)
            app_json_path = os.path.join(tmpdir, "app.json")
            with open(app_json_path) as f:
                data = json.load(f)
            assert "expo" in data

    def test_validate_config_valid(self, generator):
        errors = generator.validate_config()
        assert errors == []

    def test_validate_config_invalid_slug(self, config):
        config.slug = "Invalid Slug!"
        gen = ScaffoldGenerator(config)
        errors = gen.validate_config()
        assert any("slug" in e for e in errors)

    def test_validate_config_invalid_version(self, config):
        config.version = "not-semver"
        gen = ScaffoldGenerator(config)
        errors = gen.validate_config()
        assert any("version" in e for e in errors)

    def test_validate_config_invalid_build_number(self, config):
        config.build_number = 0
        gen = ScaffoldGenerator(config)
        errors = gen.validate_config()
        assert any("build_number" in e for e in errors)

    def test_validate_config_invalid_api_url(self, config):
        config.api_base_url = "not-a-url"
        gen = ScaffoldGenerator(config)
        errors = gen.validate_config()
        assert any("api_base_url" in e for e in errors)


# ---------------------------------------------------------------------------
# BuildManager tests
# ---------------------------------------------------------------------------

class TestBuildManager:
    def test_create_build_all_platforms(self, build_manager, config):
        artifacts = build_manager.create_build(config, BuildVariant.PRODUCTION, Platform.ALL)
        assert len(artifacts) == 2
        platforms = {a.platform for a in artifacts}
        assert Platform.IOS in platforms
        assert Platform.ANDROID in platforms

    def test_create_build_single_platform(self, build_manager, config):
        artifacts = build_manager.create_build(config, BuildVariant.STAGING, Platform.IOS)
        assert len(artifacts) == 1
        assert artifacts[0].platform == Platform.IOS

    def test_build_artifact_filename_ios(self, build_manager, config):
        artifacts = build_manager.create_build(config, BuildVariant.PRODUCTION, Platform.IOS)
        assert artifacts[0].filename.endswith(".ipa")

    def test_build_artifact_filename_android(self, build_manager, config):
        artifacts = build_manager.create_build(config, BuildVariant.PRODUCTION, Platform.ANDROID)
        assert artifacts[0].filename.endswith(".apk")

    def test_complete_build(self, build_manager, config):
        artifacts = build_manager.create_build(config, BuildVariant.PRODUCTION, Platform.IOS)
        build_id = artifacts[0].id
        result = build_manager.complete_build(build_id, "https://cdn.example.com/app.ipa", 50_000_000)
        assert result is True
        assert artifacts[0].status == "completed"
        assert artifacts[0].download_url == "https://cdn.example.com/app.ipa"
        assert artifacts[0].size_bytes == 50_000_000

    def test_fail_build(self, build_manager, config):
        artifacts = build_manager.create_build(config, BuildVariant.STAGING, Platform.ANDROID)
        build_id = artifacts[0].id
        result = build_manager.fail_build(build_id, "Compilation error")
        assert result is True
        assert "failed" in artifacts[0].status

    def test_complete_build_unknown_id(self, build_manager):
        result = build_manager.complete_build("unknown-id", "https://example.com", 0)
        assert result is False

    def test_create_ota_update(self, build_manager):
        update = build_manager.create_ota_update(
            version="1.0.1",
            channel="production",
            message="Bug fixes and performance improvements",
        )
        assert update.id is not None
        assert update.version == "1.0.1"
        assert update.channel == "production"
        assert update.mandatory is False

    def test_create_mandatory_ota_update(self, build_manager):
        update = build_manager.create_ota_update(
            version="1.0.2",
            channel="production",
            message="Critical security patch",
            mandatory=True,
        )
        assert update.mandatory is True

    def test_get_latest_ota(self, build_manager):
        build_manager.create_ota_update("1.0.0", "production", "v1")
        build_manager.create_ota_update("1.0.1", "production", "v2")
        latest = build_manager.get_latest_ota("production")
        assert latest.version == "1.0.1"

    def test_get_latest_ota_no_updates(self, build_manager):
        result = build_manager.get_latest_ota("production")
        assert result is None

    def test_get_latest_ota_channel_isolation(self, build_manager):
        build_manager.create_ota_update("1.0.0", "staging", "staging update")
        result = build_manager.get_latest_ota("production")
        assert result is None

    def test_builds_by_variant(self, build_manager, config):
        build_manager.create_build(config, BuildVariant.PRODUCTION, Platform.ALL)
        build_manager.create_build(config, BuildVariant.STAGING, Platform.IOS)
        prod_builds = build_manager.builds_by_variant(BuildVariant.PRODUCTION)
        assert len(prod_builds) == 2

    def test_completed_builds(self, build_manager, config):
        artifacts = build_manager.create_build(config, BuildVariant.PRODUCTION, Platform.IOS)
        build_manager.complete_build(artifacts[0].id, "https://example.com", 1000)
        completed = build_manager.completed_builds()
        assert len(completed) == 1

    def test_total_builds(self, build_manager, config):
        build_manager.create_build(config, BuildVariant.PRODUCTION, Platform.ALL)
        assert build_manager.total_builds == 2

    def test_total_ota_updates(self, build_manager):
        build_manager.create_ota_update("1.0.0", "production", "v1")
        build_manager.create_ota_update("1.0.1", "staging", "v2")
        assert build_manager.total_ota_updates == 2


# ---------------------------------------------------------------------------
# Default Screens tests
# ---------------------------------------------------------------------------

class TestDefaultScreens:
    def test_has_home_screen(self):
        names = [s.name for s in DEFAULT_SCREENS]
        assert "Home" in names

    def test_has_chat_screen(self):
        names = [s.name for s in DEFAULT_SCREENS]
        assert "Chat" in names

    def test_has_auth_screens(self):
        names = [s.name for s in DEFAULT_SCREENS]
        assert "Login" in names
        assert "Register" in names

    def test_auth_screens_not_in_tabs(self):
        auth_screens = [s for s in DEFAULT_SCREENS if not s.requires_auth]
        assert all(not s.tab_visible for s in auth_screens)

    def test_tab_screens_count(self):
        tab_screens = [s for s in DEFAULT_SCREENS if s.tab_visible]
        assert len(tab_screens) >= 5

    def test_all_screens_have_routes(self):
        for screen in DEFAULT_SCREENS:
            assert screen.route.startswith("/")
