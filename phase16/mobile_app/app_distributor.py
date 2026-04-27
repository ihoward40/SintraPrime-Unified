"""Phase 16E — Mobile App Distribution & Build Manager."""
from __future__ import annotations
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class Platform(str, Enum):
    IOS = "ios"
    ANDROID = "android"
    BOTH = "both"


class BuildStatus(str, Enum):
    PENDING = "pending"
    BUILDING = "building"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"


class DistributionChannel(str, Enum):
    APP_STORE = "app_store"
    PLAY_STORE = "play_store"
    TESTFLIGHT = "testflight"
    INTERNAL = "internal"
    ENTERPRISE = "enterprise"


@dataclass
class AppBuild:
    build_id: str
    version: str
    build_number: int
    platform: Platform
    status: BuildStatus = BuildStatus.PENDING
    channel: DistributionChannel = DistributionChannel.INTERNAL
    artifact_url: Optional[str] = None
    error_message: str = ""
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def duration_seconds(self) -> Optional[float]:
        if self.started_at and self.completed_at:
            return self.completed_at - self.started_at
        return None

    @property
    def is_complete(self) -> bool:
        return self.status in (BuildStatus.SUCCESS, BuildStatus.FAILED, BuildStatus.CANCELLED)


@dataclass
class AppRelease:
    release_id: str
    version: str
    platform: Platform
    channel: DistributionChannel
    build_id: str
    release_notes: str = ""
    downloads: int = 0
    active_installs: int = 0
    released_at: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PushNotification:
    notification_id: str
    title: str
    body: str
    target_platform: Platform
    target_users: List[str] = field(default_factory=list)
    sent_count: int = 0
    delivered_count: int = 0
    opened_count: int = 0
    sent_at: Optional[float] = None

    @property
    def delivery_rate(self) -> float:
        if self.sent_count == 0:
            return 0.0
        return self.delivered_count / self.sent_count

    @property
    def open_rate(self) -> float:
        if self.delivered_count == 0:
            return 0.0
        return self.opened_count / self.delivered_count


class BuildPipeline:
    """Manages app build lifecycle."""

    def __init__(self):
        self._builds: Dict[str, AppBuild] = {}
        self._build_number = 0

    def create_build(self, version: str, platform: Platform,
                     channel: DistributionChannel = DistributionChannel.INTERNAL) -> AppBuild:
        self._build_number += 1
        build = AppBuild(
            build_id=f"bld_{uuid.uuid4().hex[:8]}",
            version=version,
            build_number=self._build_number,
            platform=platform,
            channel=channel,
        )
        self._builds[build.build_id] = build
        return build

    def start_build(self, build_id: str) -> AppBuild:
        build = self._get_build(build_id)
        if build.status != BuildStatus.PENDING:
            raise ValueError(f"Build {build_id} is not in PENDING state")
        build.status = BuildStatus.BUILDING
        build.started_at = time.time()
        return build

    def complete_build(self, build_id: str, success: bool = True,
                       artifact_url: Optional[str] = None,
                       error_message: str = "") -> AppBuild:
        build = self._get_build(build_id)
        build.status = BuildStatus.SUCCESS if success else BuildStatus.FAILED
        build.completed_at = time.time()
        if artifact_url:
            build.artifact_url = artifact_url
        if error_message:
            build.error_message = error_message
        return build

    def cancel_build(self, build_id: str) -> AppBuild:
        build = self._get_build(build_id)
        if build.is_complete:
            raise ValueError(f"Build {build_id} is already complete")
        build.status = BuildStatus.CANCELLED
        build.completed_at = time.time()
        return build

    def get_build(self, build_id: str) -> Optional[AppBuild]:
        return self._builds.get(build_id)

    def list_builds(self, status: Optional[BuildStatus] = None) -> List[AppBuild]:
        builds = list(self._builds.values())
        if status:
            builds = [b for b in builds if b.status == status]
        return builds

    def _get_build(self, build_id: str) -> AppBuild:
        build = self._builds.get(build_id)
        if not build:
            raise KeyError(f"Build {build_id} not found")
        return build


class ReleaseManager:
    """Manages app releases and distribution."""

    def __init__(self):
        self._releases: Dict[str, AppRelease] = {}

    def create_release(self, version: str, platform: Platform,
                       channel: DistributionChannel, build_id: str,
                       release_notes: str = "") -> AppRelease:
        release = AppRelease(
            release_id=f"rel_{uuid.uuid4().hex[:8]}",
            version=version,
            platform=platform,
            channel=channel,
            build_id=build_id,
            release_notes=release_notes,
            released_at=time.time(),
        )
        self._releases[release.release_id] = release
        return release

    def record_download(self, release_id: str, count: int = 1) -> AppRelease:
        release = self._get_release(release_id)
        release.downloads += count
        return release

    def record_install(self, release_id: str, count: int = 1) -> AppRelease:
        release = self._get_release(release_id)
        release.active_installs += count
        return release

    def get_release(self, release_id: str) -> Optional[AppRelease]:
        return self._releases.get(release_id)

    def list_releases(self, platform: Optional[Platform] = None,
                      channel: Optional[DistributionChannel] = None) -> List[AppRelease]:
        releases = list(self._releases.values())
        if platform:
            releases = [r for r in releases if r.platform in (platform, Platform.BOTH)]
        if channel:
            releases = [r for r in releases if r.channel == channel]
        return releases

    def get_latest_release(self, platform: Platform,
                           channel: DistributionChannel) -> Optional[AppRelease]:
        releases = self.list_releases(platform, channel)
        if not releases:
            return None
        return max(releases, key=lambda r: r.released_at)

    def _get_release(self, release_id: str) -> AppRelease:
        release = self._releases.get(release_id)
        if not release:
            raise KeyError(f"Release {release_id} not found")
        return release


class PushNotificationService:
    """Manages push notifications to mobile users."""

    def __init__(self):
        self._notifications: Dict[str, PushNotification] = {}

    def send(self, title: str, body: str, platform: Platform,
             target_users: Optional[List[str]] = None) -> PushNotification:
        notif = PushNotification(
            notification_id=f"pn_{uuid.uuid4().hex[:8]}",
            title=title,
            body=body,
            target_platform=platform,
            target_users=target_users or [],
            sent_count=len(target_users) if target_users else 0,
            sent_at=time.time(),
        )
        self._notifications[notif.notification_id] = notif
        return notif

    def record_delivery(self, notification_id: str, delivered: int, opened: int = 0) -> PushNotification:
        notif = self._get_notification(notification_id)
        notif.delivered_count = delivered
        notif.opened_count = opened
        return notif

    def get_notification(self, notification_id: str) -> Optional[PushNotification]:
        return self._notifications.get(notification_id)

    def list_notifications(self) -> List[PushNotification]:
        return list(self._notifications.values())

    def get_stats(self) -> Dict[str, Any]:
        notifs = list(self._notifications.values())
        total_sent = sum(n.sent_count for n in notifs)
        total_delivered = sum(n.delivered_count for n in notifs)
        total_opened = sum(n.opened_count for n in notifs)
        return {
            "total_notifications": len(notifs),
            "total_sent": total_sent,
            "total_delivered": total_delivered,
            "total_opened": total_opened,
            "avg_delivery_rate": total_delivered / total_sent if total_sent > 0 else 0.0,
            "avg_open_rate": total_opened / total_delivered if total_delivered > 0 else 0.0,
        }

    def _get_notification(self, notification_id: str) -> PushNotification:
        notif = self._notifications.get(notification_id)
        if not notif:
            raise KeyError(f"Notification {notification_id} not found")
        return notif


class MobileAppDistributor:
    """Top-level mobile app distribution manager."""

    def __init__(self):
        self.pipeline = BuildPipeline()
        self.releases = ReleaseManager()
        self.push = PushNotificationService()

    def full_release_cycle(self, version: str, platform: Platform,
                           channel: DistributionChannel,
                           release_notes: str = "") -> AppRelease:
        """Create build → start → complete → release in one call (for testing)."""
        build = self.pipeline.create_build(version, platform, channel)
        self.pipeline.start_build(build.build_id)
        artifact_url = f"https://builds.sintra.prime/{platform.value}/{version}/{build.build_id}.ipa"
        self.pipeline.complete_build(build.build_id, success=True, artifact_url=artifact_url)
        release = self.releases.create_release(version, platform, channel,
                                                build.build_id, release_notes)
        return release

    def get_stats(self) -> Dict[str, Any]:
        builds = self.pipeline.list_builds()
        releases = self.releases.list_releases()
        return {
            "total_builds": len(builds),
            "successful_builds": sum(1 for b in builds if b.status == BuildStatus.SUCCESS),
            "failed_builds": sum(1 for b in builds if b.status == BuildStatus.FAILED),
            "total_releases": len(releases),
            "total_downloads": sum(r.downloads for r in releases),
            "total_installs": sum(r.active_installs for r in releases),
        }
