"""
SintraPrime Platform Detector
==============================
Detects the current platform (Windows/Mac/Linux/iOS/Android/Web)
and auto-configures optimal settings and feature flags.
"""

from __future__ import annotations

import os
import platform
import sys
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Dict, Optional, Set


# ─── Platform Enum ─────────────────────────────────────────────────────────────
class Platform(str, Enum):
    WINDOWS = "windows"
    MACOS = "macos"
    LINUX = "linux"
    IOS = "ios"
    ANDROID = "android"
    WEB = "web"
    UNKNOWN = "unknown"


class RuntimeEnvironment(str, Enum):
    SSH = "ssh"
    TERMINAL = "terminal"
    BROWSER = "browser"
    DOCKER = "docker"
    CI = "ci"
    JUPYTER = "jupyter"
    UNKNOWN = "unknown"


# ─── Feature Flags ─────────────────────────────────────────────────────────────
class Feature(str, Enum):
    PUSH_NOTIFICATIONS = "push_notifications"
    OFFLINE_MODE = "offline_mode"
    BIOMETRIC_AUTH = "biometric_auth"
    FILE_SYSTEM = "file_system"
    BACKGROUND_SYNC = "background_sync"
    VOICE_INPUT = "voice_input"
    HAPTIC_FEEDBACK = "haptic_feedback"
    SYSTEM_TRAY = "system_tray"
    NATIVE_NOTIFICATIONS = "native_notifications"
    GPU_ACCELERATION = "gpu_acceleration"
    MULTI_WINDOW = "multi_window"
    DRAG_AND_DROP = "drag_and_drop"
    KEYBOARD_SHORTCUTS = "keyboard_shortcuts"
    MOUSE_SUPPORT = "mouse_support"
    COLOR_TERMINAL = "color_terminal"
    UNICODE_SUPPORT = "unicode_support"
    TLS_PINNING = "tls_pinning"
    LOCAL_LLM = "local_llm"


# ─── Platform Config ───────────────────────────────────────────────────────────
@dataclass
class PlatformConfig:
    platform: Platform
    runtime: RuntimeEnvironment
    features: Set[Feature] = field(default_factory=set)
    terminal_width: int = 80
    terminal_height: int = 24
    is_mobile: bool = False
    is_headless: bool = False
    color_support: int = 0  # 0=none, 8=basic, 256=256color, 16777216=truecolor
    encoding: str = "utf-8"
    path_separator: str = "/"
    home_dir: str = ""
    config_dir: str = ""
    cache_dir: str = ""
    temp_dir: str = "/tmp"
    cpu_count: int = 1
    arch: str = "unknown"
    python_version: str = ""
    extra: Dict = field(default_factory=dict)

    def has(self, feature: Feature) -> bool:
        return feature in self.features

    def to_dict(self) -> Dict:
        return {
            "platform": self.platform.value,
            "runtime": self.runtime.value,
            "features": [f.value for f in self.features],
            "terminal_width": self.terminal_width,
            "terminal_height": self.terminal_height,
            "is_mobile": self.is_mobile,
            "is_headless": self.is_headless,
            "color_support": self.color_support,
            "encoding": self.encoding,
            "arch": self.arch,
            "python_version": self.python_version,
            "home_dir": self.home_dir,
            "config_dir": self.config_dir,
        }


# ─── Detector ──────────────────────────────────────────────────────────────────
class PlatformDetector:
    """Detects platform and configures optimal settings."""

    def __init__(self, user_agent: Optional[str] = None):
        self._user_agent = user_agent or os.environ.get("HTTP_USER_AGENT", "")
        self._config: Optional[PlatformConfig] = None

    def detect(self) -> PlatformConfig:
        if self._config is not None:
            return self._config

        plat = self._detect_platform()
        runtime = self._detect_runtime()
        config = PlatformConfig(
            platform=plat,
            runtime=runtime,
            arch=platform.machine().lower(),
            python_version=sys.version.split()[0],
            encoding=sys.getfilesystemencoding() or "utf-8",
            home_dir=os.path.expanduser("~"),
        )

        self._detect_terminal(config)
        self._detect_colors(config)
        self._detect_dirs(config)
        self._detect_features(config)
        self._apply_platform_settings(config)

        self._config = config
        return config

    def _detect_platform(self) -> Platform:
        # Web browser check via user agent
        if self._user_agent:
            ua = self._user_agent.lower()
            if "iphone" in ua or "ipad" in ua or "ipod" in ua:
                return Platform.IOS
            if "android" in ua:
                return Platform.ANDROID

        # OS detection
        system = platform.system().lower()
        if system == "windows":
            return Platform.WINDOWS
        elif system == "darwin":
            return Platform.MACOS
        elif system == "linux":
            # Check for Android via environment
            if os.path.exists("/system/build.prop") or "android" in os.environ.get("SHELL", "").lower():
                return Platform.ANDROID
            return Platform.LINUX
        elif "java" in system:
            return Platform.UNKNOWN
        return Platform.UNKNOWN

    def _detect_runtime(self) -> RuntimeEnvironment:
        # CI/CD takes priority over Docker since CI runners often run inside containers
        if any(os.environ.get(v) for v in ("CI", "GITHUB_ACTIONS", "JENKINS_URL", "GITLAB_CI")):
            return RuntimeEnvironment.CI


        # Docker
        if os.path.exists("/.dockerenv") or os.environ.get("container"):
            return RuntimeEnvironment.DOCKER

        # Jupyter
        try:
            if "ipykernel" in sys.modules or "jupyter" in sys.modules:
                return RuntimeEnvironment.JUPYTER
        except Exception:
            pass

        # SSH session
        if os.environ.get("SSH_CLIENT") or os.environ.get("SSH_TTY") or os.environ.get("SSH_CONNECTION"):
            return RuntimeEnvironment.SSH

        # Terminal
        if sys.stdin.isatty():
            return RuntimeEnvironment.TERMINAL

        return RuntimeEnvironment.UNKNOWN

    def _detect_terminal(self, config: PlatformConfig):
        try:
            size = os.get_terminal_size()
            config.terminal_width = size.columns
            config.terminal_height = size.lines
        except OSError:
            config.terminal_width = int(os.environ.get("COLUMNS", 80))
            config.terminal_height = int(os.environ.get("LINES", 24))

        config.is_mobile = config.terminal_width <= 50
        config.is_headless = not sys.stdin.isatty()

    def _detect_colors(self, config: PlatformConfig):
        term = os.environ.get("TERM", "")
        colorterm = os.environ.get("COLORTERM", "").lower()
        no_color = os.environ.get("NO_COLOR", "")

        if no_color:
            config.color_support = 0
            return

        if colorterm in ("truecolor", "24bit"):
            config.color_support = 16777216
        elif "256color" in term or "256" in colorterm:
            config.color_support = 256
        elif term in ("xterm", "screen", "tmux", "rxvt") or "color" in term:
            config.color_support = 8
        elif config.platform == Platform.WINDOWS:
            # Windows Terminal supports truecolor
            if os.environ.get("WT_SESSION"):
                config.color_support = 16777216
            elif os.environ.get("ANSICON"):
                config.color_support = 8
            else:
                config.color_support = 0
        else:
            config.color_support = 8 if sys.stdout.isatty() else 0

    def _detect_dirs(self, config: PlatformConfig):
        plat = config.platform
        home = config.home_dir

        if plat == Platform.WINDOWS:
            config.path_separator = "\\"
            appdata = os.environ.get("APPDATA", os.path.join(home, "AppData", "Roaming"))
            config.config_dir = os.path.join(appdata, "SintraPrime")
            localappdata = os.environ.get("LOCALAPPDATA", os.path.join(home, "AppData", "Local"))
            config.cache_dir = os.path.join(localappdata, "SintraPrime", "Cache")
            config.temp_dir = os.environ.get("TEMP", "C:\\Temp")
        elif plat == Platform.MACOS:
            config.config_dir = os.path.join(home, "Library", "Application Support", "SintraPrime")
            config.cache_dir = os.path.join(home, "Library", "Caches", "SintraPrime")
            config.temp_dir = "/tmp"
        elif plat in (Platform.IOS, Platform.ANDROID):
            config.config_dir = os.path.join(home, ".sintra")
            config.cache_dir = os.path.join(home, ".sintra", "cache")
            config.temp_dir = "/tmp"
        else:
            # Linux and others: XDG
            xdg_config = os.environ.get("XDG_CONFIG_HOME", os.path.join(home, ".config"))
            xdg_cache = os.environ.get("XDG_CACHE_HOME", os.path.join(home, ".cache"))
            config.config_dir = os.path.join(xdg_config, "sintra-prime")
            config.cache_dir = os.path.join(xdg_cache, "sintra-prime")
            config.temp_dir = "/tmp"

        try:
            config.cpu_count = os.cpu_count() or 1
        except Exception:
            config.cpu_count = 1

    def _detect_features(self, config: PlatformConfig):
        features = set()
        plat = config.platform

        # Universal features
        features.add(Feature.UNICODE_SUPPORT)
        features.add(Feature.FILE_SYSTEM)
        features.add(Feature.KEYBOARD_SHORTCUTS)

        # Color terminal
        if config.color_support > 0:
            features.add(Feature.COLOR_TERMINAL)

        # Mouse support (common terminals)
        if config.runtime in (RuntimeEnvironment.TERMINAL, RuntimeEnvironment.SSH):
            features.add(Feature.MOUSE_SUPPORT)

        # Platform-specific features
        if plat == Platform.WINDOWS:
            features.add(Feature.SYSTEM_TRAY)
            features.add(Feature.NATIVE_NOTIFICATIONS)
            features.add(Feature.MULTI_WINDOW)
            features.add(Feature.DRAG_AND_DROP)
            if config.cpu_count >= 4:
                features.add(Feature.GPU_ACCELERATION)
                features.add(Feature.LOCAL_LLM)

        elif plat == Platform.MACOS:
            features.add(Feature.SYSTEM_TRAY)
            features.add(Feature.NATIVE_NOTIFICATIONS)
            features.add(Feature.BIOMETRIC_AUTH)
            features.add(Feature.MULTI_WINDOW)
            features.add(Feature.DRAG_AND_DROP)
            features.add(Feature.VOICE_INPUT)
            if config.cpu_count >= 4:
                features.add(Feature.GPU_ACCELERATION)
                features.add(Feature.LOCAL_LLM)

        elif plat == Platform.LINUX:
            features.add(Feature.SYSTEM_TRAY)
            features.add(Feature.MULTI_WINDOW)
            features.add(Feature.DRAG_AND_DROP)
            if config.cpu_count >= 8:
                features.add(Feature.LOCAL_LLM)

        elif plat in (Platform.IOS, Platform.ANDROID):
            config.is_mobile = True
            features.add(Feature.PUSH_NOTIFICATIONS)
            features.add(Feature.OFFLINE_MODE)
            features.add(Feature.BACKGROUND_SYNC)
            features.add(Feature.HAPTIC_FEEDBACK)
            features.add(Feature.BIOMETRIC_AUTH)
            features.add(Feature.VOICE_INPUT)
            features.discard(Feature.KEYBOARD_SHORTCUTS)
            features.discard(Feature.MOUSE_SUPPORT)

        # SSH runtime
        if config.runtime == RuntimeEnvironment.SSH:
            features.add(Feature.UNICODE_SUPPORT)
            features.discard(Feature.DRAG_AND_DROP)

        # Docker / CI
        if config.runtime in (RuntimeEnvironment.DOCKER, RuntimeEnvironment.CI):
            features.discard(Feature.NATIVE_NOTIFICATIONS)
            features.discard(Feature.SYSTEM_TRAY)
            features.discard(Feature.GPU_ACCELERATION)
            features.discard(Feature.BIOMETRIC_AUTH)

        # TLS pinning always available
        features.add(Feature.TLS_PINNING)

        config.features = features

    def _apply_platform_settings(self, config: PlatformConfig):
        """Apply platform-specific optimizations."""
        if config.is_mobile or config.runtime == RuntimeEnvironment.SSH:
            # Reduce default terminal width for mobile
            if config.terminal_width > 50:
                config.extra["recommended_width"] = 40
            else:
                config.extra["recommended_width"] = config.terminal_width

        config.extra["tui_mode"] = "mobile" if config.is_mobile else "desktop"
        config.extra["api_timeout"] = 10 if config.is_mobile else 30
        config.extra["cache_strategy"] = (
            "aggressive" if config.is_mobile else "standard"
        )


# ─── Global Detector ───────────────────────────────────────────────────────────
_detector = PlatformDetector()


def get_platform_config(user_agent: Optional[str] = None) -> PlatformConfig:
    """Get the current platform configuration."""
    if user_agent:
        return PlatformDetector(user_agent=user_agent).detect()
    return _detector.detect()


def supports(feature: Feature, user_agent: Optional[str] = None) -> bool:
    """Check if a specific feature is supported on this platform."""
    config = get_platform_config(user_agent)
    return config.has(feature)


def get_optimal_tui_width() -> int:
    """Get the optimal TUI width for the current terminal."""
    config = get_platform_config()
    return config.extra.get("recommended_width", config.terminal_width)


# ─── Entry Point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    config = get_platform_config()
    print(f"Platform: {config.platform.value}")
    print(f"Runtime: {config.runtime.value}")
    print(f"Mobile: {config.is_mobile}")
    print(f"Terminal: {config.terminal_width}x{config.terminal_height}")
    print(f"Colors: {config.color_support}")
    print(f"Features ({len(config.features)}):")
    for f in sorted(config.features, key=lambda x: x.value):
        print(f"  ✓ {f.value}")
