"""
Phase 18B — React Native Mobile App Scaffold (Expo)
=====================================================
Provides a Python-side scaffold generator and configuration manager for the
SintraPrime mobile app. This module:

  - Generates a complete Expo + React Native + TypeScript project structure
  - Configures app.json, tsconfig.json, package.json, and navigation
  - Produces screen templates (Home, Cases, Chat, Profile, Auth)
  - Manages build variants (development, staging, production)
  - Generates EAS (Expo Application Services) build configuration
  - Provides OTA update manifest management
  - Tracks app version and build numbers

The actual React Native code is generated as template strings and written to
the target directory. Tests validate the scaffold logic in pure Python.
"""

from __future__ import annotations

import json
import os
import re
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Enums & Models
# ---------------------------------------------------------------------------

class BuildVariant(str, Enum):
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


class Platform(str, Enum):
    IOS = "ios"
    ANDROID = "android"
    ALL = "all"


class NavigationStyle(str, Enum):
    STACK = "stack"
    TABS = "tabs"
    DRAWER = "drawer"


@dataclass
class AppConfig:
    name: str
    slug: str
    version: str = "1.0.0"
    build_number: int = 1
    bundle_id: str = ""
    package_name: str = ""
    description: str = ""
    primary_color: str = "#1a1a2e"
    accent_color: str = "#e94560"
    navigation: NavigationStyle = NavigationStyle.TABS
    platforms: List[Platform] = field(default_factory=lambda: [Platform.IOS, Platform.ANDROID])
    features: List[str] = field(default_factory=list)
    api_base_url: str = "https://api.sintraprime.com"
    enable_push_notifications: bool = True
    enable_biometrics: bool = True
    enable_offline_mode: bool = True

    def __post_init__(self):
        if not self.bundle_id:
            self.bundle_id = f"com.sintraprime.{self.slug}"
        if not self.package_name:
            self.package_name = f"com.sintraprime.{self.slug}"


@dataclass
class Screen:
    name: str
    route: str
    title: str
    icon: str
    requires_auth: bool = True
    tab_visible: bool = True
    component_template: str = ""


@dataclass
class BuildArtifact:
    id: str
    variant: BuildVariant
    platform: Platform
    version: str
    build_number: int
    created_at: float = field(default_factory=time.time)
    eas_build_id: Optional[str] = None
    download_url: Optional[str] = None
    status: str = "pending"
    size_bytes: int = 0

    @property
    def filename(self) -> str:
        ext = "ipa" if self.platform == Platform.IOS else "apk"
        return f"sintraprime-{self.variant.value}-{self.version}-{self.build_number}.{ext}"


@dataclass
class OTAUpdate:
    id: str
    version: str
    channel: str
    message: str
    created_at: float = field(default_factory=time.time)
    mandatory: bool = False
    min_app_version: str = "1.0.0"
    assets: List[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Screen Registry
# ---------------------------------------------------------------------------

DEFAULT_SCREENS: List[Screen] = [
    Screen(
        name="Home",
        route="/(tabs)/index",
        title="Dashboard",
        icon="home",
        requires_auth=True,
        tab_visible=True,
    ),
    Screen(
        name="Cases",
        route="/(tabs)/cases",
        title="My Cases",
        icon="briefcase",
        requires_auth=True,
        tab_visible=True,
    ),
    Screen(
        name="Chat",
        route="/(tabs)/chat",
        title="AI Assistant",
        icon="message-circle",
        requires_auth=True,
        tab_visible=True,
    ),
    Screen(
        name="Documents",
        route="/(tabs)/documents",
        title="Documents",
        icon="file-text",
        requires_auth=True,
        tab_visible=True,
    ),
    Screen(
        name="Profile",
        route="/(tabs)/profile",
        title="Profile",
        icon="user",
        requires_auth=True,
        tab_visible=True,
    ),
    Screen(
        name="Login",
        route="/auth/login",
        title="Sign In",
        icon="log-in",
        requires_auth=False,
        tab_visible=False,
    ),
    Screen(
        name="Register",
        route="/auth/register",
        title="Create Account",
        icon="user-plus",
        requires_auth=False,
        tab_visible=False,
    ),
    Screen(
        name="CaseDetail",
        route="/cases/[id]",
        title="Case Detail",
        icon="file",
        requires_auth=True,
        tab_visible=False,
    ),
]


# ---------------------------------------------------------------------------
# Template Generator
# ---------------------------------------------------------------------------

class TemplateGenerator:
    """Generates React Native / Expo file templates."""

    @staticmethod
    def app_json(config: AppConfig) -> Dict[str, Any]:
        return {
            "expo": {
                "name": config.name,
                "slug": config.slug,
                "version": config.version,
                "orientation": "portrait",
                "icon": "./assets/images/icon.png",
                "scheme": config.slug,
                "userInterfaceStyle": "automatic",
                "splash": {
                    "image": "./assets/images/splash.png",
                    "resizeMode": "contain",
                    "backgroundColor": config.primary_color,
                },
                "ios": {
                    "supportsTablet": True,
                    "bundleIdentifier": config.bundle_id,
                    "buildNumber": str(config.build_number),
                    "infoPlist": {
                        "NSFaceIDUsageDescription": "Use Face ID to authenticate",
                        "NSCameraUsageDescription": "Required for document scanning",
                    },
                },
                "android": {
                    "adaptiveIcon": {
                        "foregroundImage": "./assets/images/adaptive-icon.png",
                        "backgroundColor": config.primary_color,
                    },
                    "package": config.package_name,
                    "versionCode": config.build_number,
                    "permissions": [
                        "CAMERA",
                        "READ_EXTERNAL_STORAGE",
                        "WRITE_EXTERNAL_STORAGE",
                        "USE_BIOMETRIC",
                        "USE_FINGERPRINT",
                    ],
                },
                "plugins": [
                    "expo-router",
                    "expo-secure-store",
                    "expo-local-authentication",
                    ["expo-notifications", {"icon": "./assets/images/notification-icon.png"}],
                ],
                "experiments": {"typedRoutes": True},
            }
        }

    @staticmethod
    def package_json(config: AppConfig) -> Dict[str, Any]:
        return {
            "name": config.slug,
            "main": "expo-router/entry",
            "version": config.version,
            "scripts": {
                "start": "expo start",
                "android": "expo start --android",
                "ios": "expo start --ios",
                "web": "expo start --web",
                "test": "jest --watchAll",
                "lint": "eslint .",
                "build:dev": "eas build --profile development",
                "build:staging": "eas build --profile staging",
                "build:prod": "eas build --profile production",
                "submit:ios": "eas submit --platform ios",
                "submit:android": "eas submit --platform android",
                "update": "eas update",
            },
            "dependencies": {
                "expo": "~51.0.0",
                "expo-router": "~3.5.0",
                "expo-status-bar": "~1.12.1",
                "expo-secure-store": "~13.0.1",
                "expo-local-authentication": "~14.0.1",
                "expo-notifications": "~0.28.0",
                "expo-file-system": "~17.0.1",
                "expo-document-picker": "~12.0.1",
                "react": "18.2.0",
                "react-native": "0.74.1",
                "@react-navigation/native": "^6.1.17",
                "@react-navigation/bottom-tabs": "^6.5.20",
                "react-native-safe-area-context": "4.10.1",
                "react-native-screens": "3.31.1",
                "react-native-reanimated": "~3.10.1",
                "react-native-gesture-handler": "~2.16.1",
                "@tanstack/react-query": "^5.40.0",
                "axios": "^1.7.2",
                "zustand": "^4.5.2",
                "react-hook-form": "^7.52.0",
                "zod": "^3.23.8",
            },
            "devDependencies": {
                "@babel/core": "^7.24.0",
                "@types/react": "~18.2.79",
                "typescript": "^5.3.3",
                "jest": "^29.7.0",
                "jest-expo": "~51.0.0",
                "@testing-library/react-native": "^12.5.0",
                "eslint": "^8.57.0",
                "eslint-config-expo": "~7.0.0",
            },
        }

    @staticmethod
    def tsconfig_json() -> Dict[str, Any]:
        return {
            "extends": "expo/tsconfig.base",
            "compilerOptions": {
                "strict": True,
                "paths": {
                    "@/*": ["./*"],
                    "@components/*": ["./components/*"],
                    "@screens/*": ["./app/*"],
                    "@hooks/*": ["./hooks/*"],
                    "@services/*": ["./services/*"],
                    "@store/*": ["./store/*"],
                    "@types/*": ["./types/*"],
                },
            },
        }

    @staticmethod
    def eas_json(config: AppConfig) -> Dict[str, Any]:
        return {
            "cli": {"version": ">= 10.0.0"},
            "build": {
                "development": {
                    "developmentClient": True,
                    "distribution": "internal",
                    "ios": {"simulator": True},
                    "env": {
                        "APP_ENV": "development",
                        "API_BASE_URL": "http://localhost:3000",
                    },
                },
                "staging": {
                    "distribution": "internal",
                    "env": {
                        "APP_ENV": "staging",
                        "API_BASE_URL": "https://staging-api.sintraprime.com",
                    },
                    "channel": "staging",
                },
                "production": {
                    "autoIncrement": True,
                    "env": {
                        "APP_ENV": "production",
                        "API_BASE_URL": config.api_base_url,
                    },
                    "channel": "production",
                },
            },
            "submit": {
                "production": {
                    "ios": {
                        "appleId": "developer@sintraprime.com",
                        "ascAppId": "PLACEHOLDER_ASC_APP_ID",
                        "appleTeamId": "PLACEHOLDER_TEAM_ID",
                    },
                    "android": {
                        "serviceAccountKeyPath": "./google-services-key.json",
                        "track": "production",
                    },
                }
            },
        }

    @staticmethod
    def screen_component(screen: Screen, config: AppConfig) -> str:
        return f"""import React from 'react';
import {{ View, Text, StyleSheet, ScrollView }} from 'react-native';
import {{ SafeAreaView }} from 'react-native-safe-area-context';

export default function {screen.name}Screen() {{
  return (
    <SafeAreaView style={{styles.container}}>
      <ScrollView contentContainerStyle={{styles.content}}>
        <Text style={{styles.title}}>{screen.title}</Text>
        <Text style={{styles.subtitle}}>SintraPrime — {screen.title}</Text>
      </ScrollView>
    </SafeAreaView>
  );
}}

const styles = StyleSheet.create({{
  container: {{
    flex: 1,
    backgroundColor: '{config.primary_color}',
  }},
  content: {{
    padding: 24,
  }},
  title: {{
    fontSize: 28,
    fontWeight: '700',
    color: '#ffffff',
    marginBottom: 8,
  }},
  subtitle: {{
    fontSize: 16,
    color: 'rgba(255,255,255,0.7)',
  }},
}});
"""

    @staticmethod
    def api_service(config: AppConfig) -> str:
        return f"""import axios from 'axios';
import * as SecureStore from 'expo-secure-store';

const BASE_URL = process.env.API_BASE_URL || '{config.api_base_url}';

const api = axios.create({{
  baseURL: BASE_URL,
  timeout: 30000,
  headers: {{
    'Content-Type': 'application/json',
    'X-App-Version': '{config.version}',
  }},
}});

api.interceptors.request.use(async (config) => {{
  const token = await SecureStore.getItemAsync('auth_token');
  if (token) {{
    config.headers.Authorization = `Bearer ${{token}}`;
  }}
  return config;
}});

api.interceptors.response.use(
  (response) => response,
  async (error) => {{
    if (error.response?.status === 401) {{
      await SecureStore.deleteItemAsync('auth_token');
    }}
    return Promise.reject(error);
  }}
);

export default api;
"""


# ---------------------------------------------------------------------------
# Scaffold Generator
# ---------------------------------------------------------------------------

class ScaffoldGenerator:
    """Generates the complete Expo project scaffold."""

    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self._generator = TemplateGenerator()

    def generate_manifest(self) -> Dict[str, Any]:
        """Return a manifest of all files to be generated (without writing to disk)."""
        screens = DEFAULT_SCREENS
        manifest = {
            "app.json": json.dumps(self._generator.app_json(self.config), indent=2),
            "package.json": json.dumps(self._generator.package_json(self.config), indent=2),
            "tsconfig.json": json.dumps(self._generator.tsconfig_json(), indent=2),
            "eas.json": json.dumps(self._generator.eas_json(self.config), indent=2),
            "services/api.ts": self._generator.api_service(self.config),
        }
        for screen in screens:
            path = f"app/{screen.route.lstrip('/')}.tsx"
            manifest[path] = self._generator.screen_component(screen, self.config)
        return manifest

    def write_to_disk(self, output_dir: str) -> List[str]:
        """Write all scaffold files to the given directory. Returns list of written paths."""
        manifest = self.generate_manifest()
        written = []
        for rel_path, content in manifest.items():
            full_path = Path(output_dir) / rel_path
            full_path.parent.mkdir(parents=True, exist_ok=True)
            full_path.write_text(content, encoding="utf-8")
            written.append(str(full_path))
        return written

    def file_count(self) -> int:
        return len(self.generate_manifest())

    def validate_config(self) -> List[str]:
        """Return a list of validation errors (empty = valid)."""
        errors = []
        if not re.match(r"^[a-z0-9-]+$", self.config.slug):
            errors.append("slug must be lowercase alphanumeric with hyphens only")
        if not re.match(r"^\d+\.\d+\.\d+$", self.config.version):
            errors.append("version must be semver (e.g., 1.0.0)")
        if self.config.build_number < 1:
            errors.append("build_number must be >= 1")
        if not self.config.api_base_url.startswith(("http://", "https://")):
            errors.append("api_base_url must start with http:// or https://")
        return errors


# ---------------------------------------------------------------------------
# Build Manager
# ---------------------------------------------------------------------------

class BuildManager:
    """Manages build artifacts and OTA updates."""

    def __init__(self) -> None:
        self._artifacts: List[BuildArtifact] = []
        self._ota_updates: List[OTAUpdate] = []

    def create_build(
        self,
        config: AppConfig,
        variant: BuildVariant,
        platform: Platform = Platform.ALL,
    ) -> List[BuildArtifact]:
        """Create build artifact records for the given variant and platform."""
        platforms = (
            [Platform.IOS, Platform.ANDROID]
            if platform == Platform.ALL
            else [platform]
        )
        created = []
        for p in platforms:
            artifact = BuildArtifact(
                id=str(uuid.uuid4()),
                variant=variant,
                platform=p,
                version=config.version,
                build_number=config.build_number,
                eas_build_id=f"eas_{uuid.uuid4().hex[:8]}",
            )
            self._artifacts.append(artifact)
            created.append(artifact)
        return created

    def complete_build(self, build_id: str, download_url: str, size_bytes: int) -> bool:
        for artifact in self._artifacts:
            if artifact.id == build_id:
                artifact.status = "completed"
                artifact.download_url = download_url
                artifact.size_bytes = size_bytes
                return True
        return False

    def fail_build(self, build_id: str, reason: str) -> bool:
        for artifact in self._artifacts:
            if artifact.id == build_id:
                artifact.status = f"failed: {reason}"
                return True
        return False

    def create_ota_update(
        self,
        version: str,
        channel: str,
        message: str,
        mandatory: bool = False,
        min_app_version: str = "1.0.0",
    ) -> OTAUpdate:
        update = OTAUpdate(
            id=str(uuid.uuid4()),
            version=version,
            channel=channel,
            message=message,
            mandatory=mandatory,
            min_app_version=min_app_version,
        )
        self._ota_updates.append(update)
        return update

    def get_latest_ota(self, channel: str) -> Optional[OTAUpdate]:
        channel_updates = [u for u in self._ota_updates if u.channel == channel]
        if not channel_updates:
            return None
        return max(channel_updates, key=lambda u: u.created_at)

    def builds_by_variant(self, variant: BuildVariant) -> List[BuildArtifact]:
        return [a for a in self._artifacts if a.variant == variant]

    def completed_builds(self) -> List[BuildArtifact]:
        return [a for a in self._artifacts if a.status == "completed"]

    @property
    def total_builds(self) -> int:
        return len(self._artifacts)

    @property
    def total_ota_updates(self) -> int:
        return len(self._ota_updates)
