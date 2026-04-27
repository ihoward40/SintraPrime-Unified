"""Phase 17D — Windows Deployment Tests (65 tests)."""
import os
import pytest
import tempfile
from phase17.windows_deploy.win_deployer import (
    InstallerType, DeploymentTarget, AppConfig,
    DeploymentArtifact, DeploymentBundle,
    PowerShellSetupGenerator, PyInstallerSpecGenerator,
    NSISInstallerGenerator, AutoUpdaterConfigGenerator,
    SystemTrayConfigGenerator, RegistryManifestGenerator,
    WindowsDeployer,
)


# ─────────────────────────────────────────────────────────────────────────────
# AppConfig (8 tests)
# ─────────────────────────────────────────────────────────────────────────────
class TestAppConfig:
    def test_default_name(self):
        cfg = AppConfig()
        assert cfg.name == "SintraPrime"

    def test_default_version(self):
        cfg = AppConfig()
        assert cfg.version == "1.0.0"

    def test_default_target(self):
        cfg = AppConfig()
        assert cfg.target == DeploymentTarget.ALL_USERS

    def test_default_installer_type(self):
        cfg = AppConfig()
        assert cfg.installer_type == InstallerType.NSIS

    def test_auto_update_default_true(self):
        cfg = AppConfig()
        assert cfg.enable_auto_update is True

    def test_system_tray_default_true(self):
        cfg = AppConfig()
        assert cfg.enable_system_tray is True

    def test_custom_version(self):
        cfg = AppConfig(version="2.5.1")
        assert cfg.version == "2.5.1"

    def test_custom_author(self):
        cfg = AppConfig(author="Test Corp")
        assert cfg.author == "Test Corp"


# ─────────────────────────────────────────────────────────────────────────────
# DeploymentArtifact (7 tests)
# ─────────────────────────────────────────────────────────────────────────────
class TestDeploymentArtifact:
    def _make(self, content="Hello World"):
        return DeploymentArtifact(
            artifact_id="art_001",
            artifact_type="test_type",
            filename="test.txt",
            content=content,
            description="Test artifact",
        )

    def test_artifact_id(self):
        a = self._make()
        assert a.artifact_id == "art_001"

    def test_artifact_type(self):
        a = self._make()
        assert a.artifact_type == "test_type"

    def test_filename(self):
        a = self._make()
        assert a.filename == "test.txt"

    def test_content(self):
        a = self._make("Test content")
        assert a.content == "Test content"

    def test_size_bytes_auto(self):
        a = self._make("Hello")
        assert a.size_bytes == len("Hello".encode("utf-8"))

    def test_size_bytes_empty(self):
        a = self._make("")
        assert a.size_bytes == 0

    def test_description(self):
        a = self._make()
        assert a.description == "Test artifact"


# ─────────────────────────────────────────────────────────────────────────────
# DeploymentBundle (10 tests)
# ─────────────────────────────────────────────────────────────────────────────
class TestDeploymentBundle:
    def _make_bundle(self):
        cfg = AppConfig()
        bundle = DeploymentBundle(bundle_id="b_001", app_config=cfg)
        bundle.artifacts.append(DeploymentArtifact("a1", "powershell_setup", "setup.ps1", "# ps1", "PS1"))
        bundle.artifacts.append(DeploymentArtifact("a2", "pyinstaller_spec", "app.spec", "# spec", "Spec"))
        return bundle

    def test_bundle_id(self):
        b = self._make_bundle()
        assert b.bundle_id == "b_001"

    def test_artifact_count(self):
        b = self._make_bundle()
        assert len(b.artifacts) == 2

    def test_get_artifact_found(self):
        b = self._make_bundle()
        a = b.get_artifact("powershell_setup")
        assert a is not None
        assert a.artifact_type == "powershell_setup"

    def test_get_artifact_not_found(self):
        b = self._make_bundle()
        assert b.get_artifact("nonexistent") is None

    def test_artifact_types(self):
        b = self._make_bundle()
        types = b.artifact_types()
        assert "powershell_setup" in types
        assert "pyinstaller_spec" in types

    def test_total_size_bytes(self):
        b = self._make_bundle()
        assert b.total_size_bytes() > 0

    def test_created_at_set(self):
        b = self._make_bundle()
        assert b.created_at > 0

    def test_save_all(self):
        b = self._make_bundle()
        with tempfile.TemporaryDirectory() as tmpdir:
            paths = b.save_all(tmpdir)
            assert len(paths) == 2
            for p in paths:
                assert os.path.exists(p)

    def test_save_all_content(self):
        b = self._make_bundle()
        with tempfile.TemporaryDirectory() as tmpdir:
            paths = b.save_all(tmpdir)
            for p in paths:
                with open(p) as f:
                    assert len(f.read()) > 0

    def test_save_all_creates_dir(self):
        b = self._make_bundle()
        with tempfile.TemporaryDirectory() as tmpdir:
            new_dir = os.path.join(tmpdir, "deploy_output")
            paths = b.save_all(new_dir)
            assert os.path.isdir(new_dir)


# ─────────────────────────────────────────────────────────────────────────────
# PowerShellSetupGenerator (6 tests)
# ─────────────────────────────────────────────────────────────────────────────
class TestPowerShellSetupGenerator:
    @pytest.fixture
    def artifact(self):
        return PowerShellSetupGenerator().generate(AppConfig())

    def test_returns_artifact(self, artifact):
        assert isinstance(artifact, DeploymentArtifact)

    def test_artifact_type(self, artifact):
        assert artifact.artifact_type == "powershell_setup"

    def test_filename_ps1(self, artifact):
        assert artifact.filename.endswith(".ps1")

    def test_content_has_requires(self, artifact):
        assert "#Requires -RunAsAdministrator" in artifact.content

    def test_content_has_app_name(self, artifact):
        assert "SintraPrime" in artifact.content

    def test_content_has_install_dir(self, artifact):
        assert "InstallDir" in artifact.content


# ─────────────────────────────────────────────────────────────────────────────
# PyInstallerSpecGenerator (5 tests)
# ─────────────────────────────────────────────────────────────────────────────
class TestPyInstallerSpecGenerator:
    @pytest.fixture
    def artifact(self):
        return PyInstallerSpecGenerator().generate(AppConfig())

    def test_artifact_type(self, artifact):
        assert artifact.artifact_type == "pyinstaller_spec"

    def test_filename_spec(self, artifact):
        assert artifact.filename.endswith(".spec")

    def test_content_has_analysis(self, artifact):
        assert "Analysis(" in artifact.content

    def test_content_has_exe(self, artifact):
        assert "EXE(" in artifact.content

    def test_content_has_hidden_imports(self, artifact):
        assert "hiddenimports" in artifact.content


# ─────────────────────────────────────────────────────────────────────────────
# NSISInstallerGenerator (5 tests)
# ─────────────────────────────────────────────────────────────────────────────
class TestNSISInstallerGenerator:
    @pytest.fixture
    def artifact(self):
        return NSISInstallerGenerator().generate(AppConfig())

    def test_artifact_type(self, artifact):
        assert artifact.artifact_type == "nsis_installer"

    def test_filename_nsi(self, artifact):
        assert artifact.filename.endswith(".nsi")

    def test_content_has_name(self, artifact):
        assert 'Name "SintraPrime"' in artifact.content

    def test_content_has_uninstall(self, artifact):
        assert "Uninstall" in artifact.content

    def test_content_has_mui(self, artifact):
        assert "MUI2.nsh" in artifact.content


# ─────────────────────────────────────────────────────────────────────────────
# AutoUpdaterConfigGenerator (4 tests)
# ─────────────────────────────────────────────────────────────────────────────
class TestAutoUpdaterConfigGenerator:
    @pytest.fixture
    def artifact(self):
        return AutoUpdaterConfigGenerator().generate(AppConfig())

    def test_artifact_type(self, artifact):
        assert artifact.artifact_type == "autoupdater_config"

    def test_filename_json(self, artifact):
        assert artifact.filename.endswith(".json")

    def test_content_has_version(self, artifact):
        assert "1.0.0" in artifact.content

    def test_content_valid_json(self, artifact):
        import json
        data = json.loads(artifact.content)
        assert "currentVersion" in data


# ─────────────────────────────────────────────────────────────────────────────
# SystemTrayConfigGenerator (4 tests)
# ─────────────────────────────────────────────────────────────────────────────
class TestSystemTrayConfigGenerator:
    @pytest.fixture
    def artifact(self):
        return SystemTrayConfigGenerator().generate(AppConfig())

    def test_artifact_type(self, artifact):
        assert artifact.artifact_type == "system_tray_config"

    def test_filename_ini(self, artifact):
        assert artifact.filename.endswith(".ini")

    def test_content_has_app_section(self, artifact):
        assert "[app]" in artifact.content

    def test_content_has_menu(self, artifact):
        assert "[menu]" in artifact.content


# ─────────────────────────────────────────────────────────────────────────────
# RegistryManifestGenerator (4 tests)
# ─────────────────────────────────────────────────────────────────────────────
class TestRegistryManifestGenerator:
    @pytest.fixture
    def artifact(self):
        return RegistryManifestGenerator().generate(AppConfig())

    def test_artifact_type(self, artifact):
        assert artifact.artifact_type == "registry_manifest"

    def test_filename_reg(self, artifact):
        assert artifact.filename.endswith(".reg")

    def test_content_has_hklm(self, artifact):
        assert "HKEY_LOCAL_MACHINE" in artifact.content

    def test_content_has_version(self, artifact):
        assert "1.0.0" in artifact.content


# ─────────────────────────────────────────────────────────────────────────────
# WindowsDeployer (12 tests)
# ─────────────────────────────────────────────────────────────────────────────
class TestWindowsDeployer:
    @pytest.fixture(scope="class")
    def deployer(self):
        return WindowsDeployer(AppConfig())

    @pytest.fixture(scope="class")
    def bundle(self, deployer):
        return deployer.generate_bundle()

    def test_generate_bundle_returns_bundle(self, bundle):
        assert isinstance(bundle, DeploymentBundle)

    def test_bundle_has_artifacts(self, bundle):
        assert len(bundle.artifacts) > 0

    def test_bundle_has_powershell(self, bundle):
        assert bundle.get_artifact("powershell_setup") is not None

    def test_bundle_has_spec(self, bundle):
        assert bundle.get_artifact("pyinstaller_spec") is not None

    def test_bundle_has_nsis(self, bundle):
        assert bundle.get_artifact("nsis_installer") is not None

    def test_bundle_has_updater(self, bundle):
        assert bundle.get_artifact("autoupdater_config") is not None

    def test_bundle_has_tray(self, bundle):
        assert bundle.get_artifact("system_tray_config") is not None

    def test_bundle_has_registry(self, bundle):
        assert bundle.get_artifact("registry_manifest") is not None

    def test_validate_bundle_valid(self, deployer, bundle):
        result = deployer.validate_bundle(bundle)
        assert result["valid"] is True

    def test_validate_bundle_no_missing(self, deployer, bundle):
        result = deployer.validate_bundle(bundle)
        assert result["missing_artifacts"] == []

    def test_generate_single_artifact(self, deployer):
        a = deployer.generate_artifact("powershell_setup")
        assert a is not None
        assert a.artifact_type == "powershell_setup"

    def test_generate_unknown_artifact(self, deployer):
        a = deployer.generate_artifact("nonexistent_type")
        assert a is None
