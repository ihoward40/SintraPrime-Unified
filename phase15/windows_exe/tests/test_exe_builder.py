"""Tests for Phase 15B — Windows Desktop Executable Builder."""
import sys, os, json, tempfile

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from phase15.windows_exe.exe_builder import (
    ExeConfig, SpecGenerator, NSISGenerator, TrayIconGenerator,
    BuildScriptGenerator, ExeBuilder,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def default_config():
    return ExeConfig()


@pytest.fixture
def custom_config():
    return ExeConfig(
        app_name="MyApp",
        app_version="2.1.3",
        app_description="My Custom App",
        company_name="Acme Corp",
        main_script="app.py",
        icon_path="assets/app.ico",
        one_file=True,
        windowed=True,
        tray_enabled=True,
        auto_start=True,
        port=9000,
        hidden_imports=["pkg_resources", "six"],
        exclude_modules=["tkinter", "test"],
    )


@pytest.fixture
def builder(default_config):
    return ExeBuilder(default_config)


@pytest.fixture
def custom_builder(custom_config):
    return ExeBuilder(custom_config)


# ---------------------------------------------------------------------------
# ExeConfig tests
# ---------------------------------------------------------------------------

class TestExeConfig:
    def test_default_values(self, default_config):
        assert default_config.app_name == "SintraPrime"
        assert default_config.app_version == "1.0.0"
        assert default_config.one_file is True
        assert default_config.windowed is True
        assert default_config.tray_enabled is True
        assert default_config.port == 8765

    def test_to_dict_contains_required_keys(self, default_config):
        d = default_config.to_dict()
        assert "app_name" in d
        assert "app_version" in d
        assert "tray_enabled" in d
        assert "port" in d

    def test_custom_config_values(self, custom_config):
        assert custom_config.app_name == "MyApp"
        assert custom_config.app_version == "2.1.3"
        assert custom_config.port == 9000
        assert custom_config.auto_start is True


# ---------------------------------------------------------------------------
# SpecGenerator tests
# ---------------------------------------------------------------------------

class TestSpecGenerator:
    def test_generates_spec_string(self, default_config):
        gen = SpecGenerator(default_config)
        spec = gen.generate()
        assert isinstance(spec, str)
        assert len(spec) > 100

    def test_spec_contains_app_name(self, default_config):
        gen = SpecGenerator(default_config)
        spec = gen.generate()
        assert "SintraPrime" in spec

    def test_spec_contains_main_script(self, default_config):
        gen = SpecGenerator(default_config)
        spec = gen.generate()
        assert default_config.main_script in spec

    def test_spec_contains_icon_path(self, default_config):
        gen = SpecGenerator(default_config)
        spec = gen.generate()
        assert default_config.icon_path in spec

    def test_spec_windowed_mode(self, default_config):
        gen = SpecGenerator(default_config)
        spec = gen.generate()
        assert "console=False" in spec

    def test_spec_console_mode(self):
        config = ExeConfig(windowed=False)
        gen = SpecGenerator(config)
        spec = gen.generate()
        assert "console=True" in spec

    def test_spec_hidden_imports(self, custom_config):
        gen = SpecGenerator(custom_config)
        spec = gen.generate()
        assert "pkg_resources" in spec
        assert "six" in spec

    def test_spec_exclude_modules(self, custom_config):
        gen = SpecGenerator(custom_config)
        spec = gen.generate()
        assert "tkinter" in spec

    def test_spec_uac_admin_false(self, default_config):
        gen = SpecGenerator(default_config)
        spec = gen.generate()
        assert "uac_admin=False" in spec

    def test_spec_uac_admin_true(self):
        config = ExeConfig(uac_admin=True)
        gen = SpecGenerator(config)
        spec = gen.generate()
        assert "uac_admin=True" in spec

    def test_spec_collect_section_for_multi_file(self):
        config = ExeConfig(one_file=False)
        gen = SpecGenerator(config)
        spec = gen.generate()
        assert "COLLECT" in spec

    def test_version_info_contains_company(self, default_config):
        gen = SpecGenerator(default_config)
        vi = gen.generate_version_info()
        assert "SintraPrime Inc." in vi

    def test_version_info_contains_version(self, default_config):
        gen = SpecGenerator(default_config)
        vi = gen.generate_version_info()
        assert "1, 0, 0" in vi

    def test_version_info_custom_version(self, custom_config):
        gen = SpecGenerator(custom_config)
        vi = gen.generate_version_info()
        assert "2, 1, 3" in vi


# ---------------------------------------------------------------------------
# NSISGenerator tests
# ---------------------------------------------------------------------------

class TestNSISGenerator:
    def test_generates_nsi_string(self, default_config):
        gen = NSISGenerator(default_config)
        nsi = gen.generate()
        assert isinstance(nsi, str)
        assert len(nsi) > 200

    def test_nsi_contains_app_name(self, default_config):
        gen = NSISGenerator(default_config)
        nsi = gen.generate()
        assert "SintraPrime" in nsi

    def test_nsi_contains_version(self, default_config):
        gen = NSISGenerator(default_config)
        nsi = gen.generate()
        assert "1.0.0" in nsi

    def test_nsi_contains_company(self, default_config):
        gen = NSISGenerator(default_config)
        nsi = gen.generate()
        assert "SintraPrime Inc." in nsi

    def test_nsi_contains_uninstall_section(self, default_config):
        gen = NSISGenerator(default_config)
        nsi = gen.generate()
        assert "Uninstall" in nsi

    def test_nsi_auto_start_section_present(self, custom_config):
        gen = NSISGenerator(custom_config)
        nsi = gen.generate()
        assert "Auto-start on login" in nsi

    def test_nsi_no_auto_start_by_default(self, default_config):
        gen = NSISGenerator(default_config)
        nsi = gen.generate()
        assert "Auto-start on login" not in nsi

    def test_nsi_contains_desktop_shortcut(self, default_config):
        gen = NSISGenerator(default_config)
        nsi = gen.generate()
        assert "DESKTOP" in nsi

    def test_nsi_contains_registry_entries(self, default_config):
        gen = NSISGenerator(default_config)
        nsi = gen.generate()
        assert "WriteRegStr" in nsi


# ---------------------------------------------------------------------------
# TrayIconGenerator tests
# ---------------------------------------------------------------------------

class TestTrayIconGenerator:
    def test_generates_tray_script(self, default_config):
        gen = TrayIconGenerator(default_config)
        script = gen.generate()
        assert isinstance(script, str)
        assert len(script) > 100

    def test_tray_script_contains_port(self, default_config):
        gen = TrayIconGenerator(default_config)
        script = gen.generate()
        assert "8765" in script

    def test_tray_script_contains_app_name(self, default_config):
        gen = TrayIconGenerator(default_config)
        script = gen.generate()
        assert "SintraPrime" in script

    def test_tray_script_has_quit_function(self, default_config):
        gen = TrayIconGenerator(default_config)
        script = gen.generate()
        assert "_quit_app" in script

    def test_tray_script_has_open_dashboard(self, default_config):
        gen = TrayIconGenerator(default_config)
        script = gen.generate()
        assert "_open_dashboard" in script

    def test_tray_script_custom_port(self, custom_config):
        gen = TrayIconGenerator(custom_config)
        script = gen.generate()
        assert "9000" in script

    def test_tray_script_has_pystray_import(self, default_config):
        gen = TrayIconGenerator(default_config)
        script = gen.generate()
        assert "pystray" in script

    def test_tray_script_has_background_thread(self, default_config):
        gen = TrayIconGenerator(default_config)
        script = gen.generate()
        assert "start_tray_in_background" in script


# ---------------------------------------------------------------------------
# BuildScriptGenerator tests
# ---------------------------------------------------------------------------

class TestBuildScriptGenerator:
    def test_generates_bat_script(self, default_config):
        gen = BuildScriptGenerator(default_config)
        bat = gen.generate_bat()
        assert isinstance(bat, str)
        assert "@echo off" in bat

    def test_bat_contains_pyinstaller(self, default_config):
        gen = BuildScriptGenerator(default_config)
        bat = gen.generate_bat()
        assert "pyinstaller" in bat.lower()

    def test_bat_contains_app_name(self, default_config):
        gen = BuildScriptGenerator(default_config)
        bat = gen.generate_bat()
        assert "SintraPrime" in bat

    def test_bat_contains_nsis_check(self, default_config):
        gen = BuildScriptGenerator(default_config)
        bat = gen.generate_bat()
        assert "makensis" in bat

    def test_generates_sh_script(self, default_config):
        gen = BuildScriptGenerator(default_config)
        sh = gen.generate_sh()
        assert "#!/bin/bash" in sh

    def test_sh_contains_pyinstaller(self, default_config):
        gen = BuildScriptGenerator(default_config)
        sh = gen.generate_sh()
        assert "pyinstaller" in sh.lower()


# ---------------------------------------------------------------------------
# ExeBuilder tests
# ---------------------------------------------------------------------------

class TestExeBuilder:
    def test_default_builder_creates(self, builder):
        assert builder.config.app_name == "SintraPrime"

    def test_validate_config_clean(self, builder):
        warnings = builder.validate_config()
        assert isinstance(warnings, list)
        # Default config should have no warnings
        assert len(warnings) == 0

    def test_validate_config_bad_script(self):
        config = ExeConfig(main_script="main")  # missing .py
        b = ExeBuilder(config)
        warnings = b.validate_config()
        assert any("main_script" in w for w in warnings)

    def test_validate_config_bad_port(self):
        config = ExeConfig(port=80)
        b = ExeBuilder(config)
        warnings = b.validate_config()
        assert any("port" in w for w in warnings)

    def test_validate_config_bad_version(self):
        config = ExeConfig(app_version="1.0")
        b = ExeBuilder(config)
        warnings = b.validate_config()
        assert any("version" in w for w in warnings)

    def test_generate_all_creates_files(self, builder):
        with tempfile.TemporaryDirectory() as tmpdir:
            artifacts = builder.generate_all(base_dir=tmpdir)
            assert len(artifacts) == 7
            for filename in artifacts:
                assert (Path(tmpdir) / filename).exists()

    def test_generate_all_spec_file(self, builder):
        with tempfile.TemporaryDirectory() as tmpdir:
            artifacts = builder.generate_all(base_dir=tmpdir)
            assert "SintraPrime.spec" in artifacts

    def test_generate_all_nsi_file(self, builder):
        with tempfile.TemporaryDirectory() as tmpdir:
            artifacts = builder.generate_all(base_dir=tmpdir)
            assert "SintraPrime_installer.nsi" in artifacts

    def test_generate_all_tray_script(self, builder):
        with tempfile.TemporaryDirectory() as tmpdir:
            artifacts = builder.generate_all(base_dir=tmpdir)
            assert "tray_icon.py" in artifacts

    def test_generate_all_build_scripts(self, builder):
        with tempfile.TemporaryDirectory() as tmpdir:
            artifacts = builder.generate_all(base_dir=tmpdir)
            assert "build.bat" in artifacts
            assert "build.sh" in artifacts

    def test_generate_all_config_json(self, builder):
        with tempfile.TemporaryDirectory() as tmpdir:
            artifacts = builder.generate_all(base_dir=tmpdir)
            assert "build_config.json" in artifacts
            config_data = json.loads(artifacts["build_config.json"])
            assert config_data["app_name"] == "SintraPrime"

    def test_get_generated_files_after_generate(self, builder):
        with tempfile.TemporaryDirectory() as tmpdir:
            builder.generate_all(base_dir=tmpdir)
            files = builder.get_generated_files()
            assert len(files) == 7

    def test_from_json_roundtrip(self, builder):
        with tempfile.TemporaryDirectory() as tmpdir:
            artifacts = builder.generate_all(base_dir=tmpdir)
            config_path = str(Path(tmpdir) / "build_config.json")
            restored = ExeBuilder.from_json(config_path)
            assert restored.config.app_name == builder.config.app_name
            assert restored.config.app_version == builder.config.app_version

    def test_custom_config_generate(self, custom_builder):
        with tempfile.TemporaryDirectory() as tmpdir:
            artifacts = custom_builder.generate_all(base_dir=tmpdir)
            spec = artifacts["MyApp.spec"]
            assert "MyApp" in spec
            assert "2.1.3" in spec

    def test_build_calls_pyinstaller(self, builder):
        with tempfile.TemporaryDirectory() as tmpdir:
            builder.generate_all(base_dir=tmpdir)
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
                result = builder.build(cwd=tmpdir)
                mock_run.assert_called_once()
                cmd = mock_run.call_args[0][0]
                assert "PyInstaller" in cmd or "pyinstaller" in " ".join(cmd).lower()

    def test_output_dir_override(self):
        b = ExeBuilder(output_dir="/tmp/custom_dist")
        assert b.config.output_dir == "/tmp/custom_dist"
