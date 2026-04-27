"""Phase 16E — Mobile App Distribution tests (96 tests)."""
import time
import pytest
from phase16.mobile_app.app_distributor import (
    Platform, BuildStatus, DistributionChannel,
    BuildPipeline, ReleaseManager, PushNotificationService, MobileAppDistributor,
)


@pytest.fixture
def pipeline():
    return BuildPipeline()


@pytest.fixture
def release_mgr():
    return ReleaseManager()


@pytest.fixture
def push_svc():
    return PushNotificationService()


@pytest.fixture
def distributor():
    return MobileAppDistributor()


@pytest.fixture
def pending_build(pipeline):
    return pipeline.create_build("1.0.0", Platform.IOS)


@pytest.fixture
def started_build(pipeline, pending_build):
    pipeline.start_build(pending_build.build_id)
    return pending_build


@pytest.fixture
def successful_build(pipeline, started_build):
    pipeline.complete_build(started_build.build_id, success=True,
                             artifact_url="https://builds.sintra.prime/ios/1.0.0/build.ipa")
    return started_build


# ─────────────────────────────────────────────────────────────
# Build pipeline tests (30)
# ─────────────────────────────────────────────────────────────
class TestBuildPipeline:
    def test_create_build(self, pipeline):
        b = pipeline.create_build("1.0.0", Platform.IOS)
        assert b.build_id.startswith("bld_")

    def test_build_pending_by_default(self, pipeline):
        b = pipeline.create_build("1.0.0", Platform.IOS)
        assert b.status == BuildStatus.PENDING

    def test_build_version_stored(self, pipeline):
        b = pipeline.create_build("2.3.1", Platform.ANDROID)
        assert b.version == "2.3.1"

    def test_build_platform_stored(self, pipeline):
        b = pipeline.create_build("1.0.0", Platform.ANDROID)
        assert b.platform == Platform.ANDROID

    def test_build_number_increments(self, pipeline):
        b1 = pipeline.create_build("1.0.0", Platform.IOS)
        b2 = pipeline.create_build("1.0.1", Platform.IOS)
        assert b2.build_number == b1.build_number + 1

    def test_start_build(self, pipeline, pending_build):
        pipeline.start_build(pending_build.build_id)
        assert pipeline.get_build(pending_build.build_id).status == BuildStatus.BUILDING

    def test_start_build_sets_started_at(self, pipeline, pending_build):
        pipeline.start_build(pending_build.build_id)
        assert pipeline.get_build(pending_build.build_id).started_at is not None

    def test_start_non_pending_raises(self, pipeline, started_build):
        with pytest.raises(ValueError):
            pipeline.start_build(started_build.build_id)

    def test_complete_build_success(self, pipeline, started_build):
        pipeline.complete_build(started_build.build_id, success=True)
        assert pipeline.get_build(started_build.build_id).status == BuildStatus.SUCCESS

    def test_complete_build_failure(self, pipeline, started_build):
        pipeline.complete_build(started_build.build_id, success=False, error_message="Compile error")
        b = pipeline.get_build(started_build.build_id)
        assert b.status == BuildStatus.FAILED
        assert b.error_message == "Compile error"

    def test_complete_build_sets_artifact_url(self, pipeline, started_build):
        pipeline.complete_build(started_build.build_id, success=True,
                                 artifact_url="https://builds.sintra.prime/build.ipa")
        assert pipeline.get_build(started_build.build_id).artifact_url is not None

    def test_complete_build_sets_completed_at(self, pipeline, started_build):
        pipeline.complete_build(started_build.build_id, success=True)
        assert pipeline.get_build(started_build.build_id).completed_at is not None

    def test_cancel_pending_build(self, pipeline, pending_build):
        pipeline.cancel_build(pending_build.build_id)
        assert pipeline.get_build(pending_build.build_id).status == BuildStatus.CANCELLED

    def test_cancel_building_build(self, pipeline, started_build):
        pipeline.cancel_build(started_build.build_id)
        assert pipeline.get_build(started_build.build_id).status == BuildStatus.CANCELLED

    def test_cancel_complete_build_raises(self, pipeline, successful_build):
        with pytest.raises(ValueError):
            pipeline.cancel_build(successful_build.build_id)

    def test_get_build(self, pipeline, pending_build):
        retrieved = pipeline.get_build(pending_build.build_id)
        assert retrieved.build_id == pending_build.build_id

    def test_get_nonexistent_build(self, pipeline):
        assert pipeline.get_build("nonexistent") is None

    def test_list_builds_all(self, pipeline):
        pipeline.create_build("1.0.0", Platform.IOS)
        pipeline.create_build("1.0.1", Platform.ANDROID)
        assert len(pipeline.list_builds()) >= 2

    def test_list_builds_by_status(self, pipeline, pending_build, started_build):
        building = pipeline.list_builds(status=BuildStatus.BUILDING)
        assert any(b.build_id == started_build.build_id for b in building)

    def test_build_is_complete_property(self, pipeline, successful_build):
        assert successful_build.is_complete is True

    def test_build_not_complete_when_pending(self, pipeline, pending_build):
        assert pending_build.is_complete is False

    def test_build_duration_seconds(self, pipeline, started_build):
        time.sleep(0.01)
        pipeline.complete_build(started_build.build_id, success=True)
        b = pipeline.get_build(started_build.build_id)
        assert b.duration_seconds is not None
        assert b.duration_seconds >= 0

    def test_build_duration_none_when_not_started(self, pipeline, pending_build):
        assert pending_build.duration_seconds is None

    def test_start_nonexistent_build_raises(self, pipeline):
        with pytest.raises(KeyError):
            pipeline.start_build("nonexistent")

    def test_complete_nonexistent_build_raises(self, pipeline):
        with pytest.raises(KeyError):
            pipeline.complete_build("nonexistent")

    def test_cancel_nonexistent_build_raises(self, pipeline):
        with pytest.raises(KeyError):
            pipeline.cancel_build("nonexistent")

    def test_build_channel_stored(self, pipeline):
        b = pipeline.create_build("1.0.0", Platform.IOS, DistributionChannel.APP_STORE)
        assert b.channel == DistributionChannel.APP_STORE

    def test_build_unique_ids(self, pipeline):
        ids = {pipeline.create_build("1.0.0", Platform.IOS).build_id for _ in range(10)}
        assert len(ids) == 10

    def test_both_platform_build(self, pipeline):
        b = pipeline.create_build("1.0.0", Platform.BOTH)
        assert b.platform == Platform.BOTH

    def test_list_builds_empty_initially(self, pipeline):
        assert pipeline.list_builds() == []


# ─────────────────────────────────────────────────────────────
# Release manager tests (25)
# ─────────────────────────────────────────────────────────────
class TestReleaseManager:
    def test_create_release(self, release_mgr):
        r = release_mgr.create_release("1.0.0", Platform.IOS, DistributionChannel.APP_STORE, "bld_001")
        assert r.release_id.startswith("rel_")

    def test_release_version_stored(self, release_mgr):
        r = release_mgr.create_release("2.1.0", Platform.ANDROID, DistributionChannel.PLAY_STORE, "bld_001")
        assert r.version == "2.1.0"

    def test_release_platform_stored(self, release_mgr):
        r = release_mgr.create_release("1.0.0", Platform.IOS, DistributionChannel.TESTFLIGHT, "bld_001")
        assert r.platform == Platform.IOS

    def test_release_channel_stored(self, release_mgr):
        r = release_mgr.create_release("1.0.0", Platform.IOS, DistributionChannel.TESTFLIGHT, "bld_001")
        assert r.channel == DistributionChannel.TESTFLIGHT

    def test_release_notes_stored(self, release_mgr):
        r = release_mgr.create_release("1.0.0", Platform.IOS, DistributionChannel.APP_STORE, "bld_001",
                                        release_notes="Bug fixes and performance improvements")
        assert r.release_notes == "Bug fixes and performance improvements"

    def test_release_released_at(self, release_mgr):
        r = release_mgr.create_release("1.0.0", Platform.IOS, DistributionChannel.APP_STORE, "bld_001")
        assert r.released_at > 0

    def test_get_release(self, release_mgr):
        r = release_mgr.create_release("1.0.0", Platform.IOS, DistributionChannel.APP_STORE, "bld_001")
        assert release_mgr.get_release(r.release_id) is not None

    def test_get_nonexistent_release(self, release_mgr):
        assert release_mgr.get_release("nonexistent") is None

    def test_record_download(self, release_mgr):
        r = release_mgr.create_release("1.0.0", Platform.IOS, DistributionChannel.APP_STORE, "bld_001")
        release_mgr.record_download(r.release_id, 50)
        assert release_mgr.get_release(r.release_id).downloads == 50

    def test_record_install(self, release_mgr):
        r = release_mgr.create_release("1.0.0", Platform.IOS, DistributionChannel.APP_STORE, "bld_001")
        release_mgr.record_install(r.release_id, 30)
        assert release_mgr.get_release(r.release_id).active_installs == 30

    def test_downloads_accumulate(self, release_mgr):
        r = release_mgr.create_release("1.0.0", Platform.IOS, DistributionChannel.APP_STORE, "bld_001")
        release_mgr.record_download(r.release_id, 10)
        release_mgr.record_download(r.release_id, 20)
        assert release_mgr.get_release(r.release_id).downloads == 30

    def test_list_releases_all(self, release_mgr):
        release_mgr.create_release("1.0.0", Platform.IOS, DistributionChannel.APP_STORE, "b1")
        release_mgr.create_release("1.0.0", Platform.ANDROID, DistributionChannel.PLAY_STORE, "b2")
        assert len(release_mgr.list_releases()) == 2

    def test_list_releases_by_platform(self, release_mgr):
        release_mgr.create_release("1.0.0", Platform.IOS, DistributionChannel.APP_STORE, "b1")
        release_mgr.create_release("1.0.0", Platform.ANDROID, DistributionChannel.PLAY_STORE, "b2")
        ios = release_mgr.list_releases(platform=Platform.IOS)
        assert len(ios) == 1

    def test_list_releases_by_channel(self, release_mgr):
        release_mgr.create_release("1.0.0", Platform.IOS, DistributionChannel.APP_STORE, "b1")
        release_mgr.create_release("1.0.1", Platform.IOS, DistributionChannel.TESTFLIGHT, "b2")
        testflight = release_mgr.list_releases(channel=DistributionChannel.TESTFLIGHT)
        assert len(testflight) == 1

    def test_get_latest_release(self, release_mgr):
        release_mgr.create_release("1.0.0", Platform.IOS, DistributionChannel.APP_STORE, "b1")
        time.sleep(0.01)
        r2 = release_mgr.create_release("1.0.1", Platform.IOS, DistributionChannel.APP_STORE, "b2")
        latest = release_mgr.get_latest_release(Platform.IOS, DistributionChannel.APP_STORE)
        assert latest.release_id == r2.release_id

    def test_get_latest_release_none(self, release_mgr):
        assert release_mgr.get_latest_release(Platform.IOS, DistributionChannel.APP_STORE) is None

    def test_record_download_nonexistent_raises(self, release_mgr):
        with pytest.raises(KeyError):
            release_mgr.record_download("nonexistent", 10)

    def test_record_install_nonexistent_raises(self, release_mgr):
        with pytest.raises(KeyError):
            release_mgr.record_install("nonexistent", 10)

    def test_release_unique_ids(self, release_mgr):
        ids = {release_mgr.create_release("1.0.0", Platform.IOS, DistributionChannel.APP_STORE, "b").release_id
               for _ in range(10)}
        assert len(ids) == 10

    def test_release_downloads_zero_initially(self, release_mgr):
        r = release_mgr.create_release("1.0.0", Platform.IOS, DistributionChannel.APP_STORE, "b1")
        assert r.downloads == 0

    def test_release_installs_zero_initially(self, release_mgr):
        r = release_mgr.create_release("1.0.0", Platform.IOS, DistributionChannel.APP_STORE, "b1")
        assert r.active_installs == 0

    def test_both_platform_release(self, release_mgr):
        r = release_mgr.create_release("1.0.0", Platform.BOTH, DistributionChannel.ENTERPRISE, "b1")
        assert r.platform == Platform.BOTH

    def test_enterprise_channel(self, release_mgr):
        r = release_mgr.create_release("1.0.0", Platform.BOTH, DistributionChannel.ENTERPRISE, "b1")
        assert r.channel == DistributionChannel.ENTERPRISE

    def test_internal_channel(self, release_mgr):
        r = release_mgr.create_release("1.0.0", Platform.ANDROID, DistributionChannel.INTERNAL, "b1")
        assert r.channel == DistributionChannel.INTERNAL

    def test_list_releases_empty_initially(self, release_mgr):
        assert release_mgr.list_releases() == []


# ─────────────────────────────────────────────────────────────
# Push notification tests (20)
# ─────────────────────────────────────────────────────────────
class TestPushNotifications:
    def test_send_notification(self, push_svc):
        n = push_svc.send("Hello", "World", Platform.IOS)
        assert n.notification_id.startswith("pn_")

    def test_notification_title_stored(self, push_svc):
        n = push_svc.send("New Case Update", "Your case has been updated", Platform.IOS)
        assert n.title == "New Case Update"

    def test_notification_body_stored(self, push_svc):
        n = push_svc.send("Title", "Body text here", Platform.ANDROID)
        assert n.body == "Body text here"

    def test_notification_platform_stored(self, push_svc):
        n = push_svc.send("T", "B", Platform.ANDROID)
        assert n.target_platform == Platform.ANDROID

    def test_notification_target_users(self, push_svc):
        users = ["u1", "u2", "u3"]
        n = push_svc.send("T", "B", Platform.IOS, target_users=users)
        assert n.sent_count == 3

    def test_notification_sent_at(self, push_svc):
        n = push_svc.send("T", "B", Platform.IOS)
        assert n.sent_at is not None

    def test_record_delivery(self, push_svc):
        n = push_svc.send("T", "B", Platform.IOS, target_users=["u1", "u2", "u3"])
        push_svc.record_delivery(n.notification_id, delivered=3, opened=1)
        updated = push_svc.get_notification(n.notification_id)
        assert updated.delivered_count == 3
        assert updated.opened_count == 1

    def test_delivery_rate(self, push_svc):
        n = push_svc.send("T", "B", Platform.IOS, target_users=["u1", "u2"])
        push_svc.record_delivery(n.notification_id, delivered=2)
        assert push_svc.get_notification(n.notification_id).delivery_rate == 1.0

    def test_open_rate(self, push_svc):
        n = push_svc.send("T", "B", Platform.IOS, target_users=["u1", "u2", "u3", "u4"])
        push_svc.record_delivery(n.notification_id, delivered=4, opened=2)
        assert push_svc.get_notification(n.notification_id).open_rate == 0.5

    def test_delivery_rate_zero_when_no_sent(self, push_svc):
        n = push_svc.send("T", "B", Platform.IOS)
        assert n.delivery_rate == 0.0

    def test_open_rate_zero_when_no_delivered(self, push_svc):
        n = push_svc.send("T", "B", Platform.IOS)
        assert n.open_rate == 0.0

    def test_get_notification(self, push_svc):
        n = push_svc.send("T", "B", Platform.IOS)
        assert push_svc.get_notification(n.notification_id) is not None

    def test_get_nonexistent_notification(self, push_svc):
        assert push_svc.get_notification("nonexistent") is None

    def test_list_notifications(self, push_svc):
        push_svc.send("T1", "B1", Platform.IOS)
        push_svc.send("T2", "B2", Platform.ANDROID)
        assert len(push_svc.list_notifications()) == 2

    def test_stats(self, push_svc):
        n = push_svc.send("T", "B", Platform.IOS, target_users=["u1", "u2"])
        push_svc.record_delivery(n.notification_id, delivered=2, opened=1)
        stats = push_svc.get_stats()
        assert stats["total_sent"] == 2
        assert stats["total_delivered"] == 2
        assert stats["total_opened"] == 1

    def test_stats_avg_delivery_rate(self, push_svc):
        n = push_svc.send("T", "B", Platform.IOS, target_users=["u1", "u2"])
        push_svc.record_delivery(n.notification_id, delivered=2)
        stats = push_svc.get_stats()
        assert stats["avg_delivery_rate"] == 1.0

    def test_record_delivery_nonexistent_raises(self, push_svc):
        with pytest.raises(KeyError):
            push_svc.record_delivery("nonexistent", 1)

    def test_notification_unique_ids(self, push_svc):
        ids = {push_svc.send("T", "B", Platform.IOS).notification_id for _ in range(10)}
        assert len(ids) == 10

    def test_stats_empty(self, push_svc):
        stats = push_svc.get_stats()
        assert stats["total_notifications"] == 0
        assert stats["avg_delivery_rate"] == 0.0

    def test_both_platform_notification(self, push_svc):
        n = push_svc.send("T", "B", Platform.BOTH)
        assert n.target_platform == Platform.BOTH


# ─────────────────────────────────────────────────────────────
# Distributor integration tests (21)
# ─────────────────────────────────────────────────────────────
class TestMobileAppDistributor:
    def test_full_release_cycle(self, distributor):
        release = distributor.full_release_cycle("1.0.0", Platform.IOS, DistributionChannel.APP_STORE)
        assert release.release_id.startswith("rel_")

    def test_full_release_cycle_android(self, distributor):
        release = distributor.full_release_cycle("1.0.0", Platform.ANDROID, DistributionChannel.PLAY_STORE)
        assert release.platform == Platform.ANDROID

    def test_full_release_cycle_build_successful(self, distributor):
        release = distributor.full_release_cycle("1.0.0", Platform.IOS, DistributionChannel.APP_STORE)
        build = distributor.pipeline.get_build(release.build_id)
        assert build.status == BuildStatus.SUCCESS

    def test_full_release_cycle_artifact_url(self, distributor):
        release = distributor.full_release_cycle("1.0.0", Platform.IOS, DistributionChannel.APP_STORE)
        build = distributor.pipeline.get_build(release.build_id)
        assert build.artifact_url is not None

    def test_full_release_cycle_release_notes(self, distributor):
        release = distributor.full_release_cycle("1.0.0", Platform.IOS, DistributionChannel.APP_STORE,
                                                  release_notes="Initial release")
        assert release.release_notes == "Initial release"

    def test_stats_after_release(self, distributor):
        distributor.full_release_cycle("1.0.0", Platform.IOS, DistributionChannel.APP_STORE)
        stats = distributor.get_stats()
        assert stats["total_builds"] == 1
        assert stats["successful_builds"] == 1
        assert stats["total_releases"] == 1

    def test_stats_initial(self, distributor):
        stats = distributor.get_stats()
        assert stats["total_builds"] == 0
        assert stats["total_releases"] == 0

    def test_multiple_releases(self, distributor):
        distributor.full_release_cycle("1.0.0", Platform.IOS, DistributionChannel.APP_STORE)
        distributor.full_release_cycle("1.0.1", Platform.IOS, DistributionChannel.APP_STORE)
        stats = distributor.get_stats()
        assert stats["total_releases"] == 2

    def test_download_tracking(self, distributor):
        release = distributor.full_release_cycle("1.0.0", Platform.IOS, DistributionChannel.APP_STORE)
        distributor.releases.record_download(release.release_id, 100)
        stats = distributor.get_stats()
        assert stats["total_downloads"] == 100

    def test_install_tracking(self, distributor):
        release = distributor.full_release_cycle("1.0.0", Platform.IOS, DistributionChannel.APP_STORE)
        distributor.releases.record_install(release.release_id, 75)
        stats = distributor.get_stats()
        assert stats["total_installs"] == 75

    def test_push_notification_after_release(self, distributor):
        distributor.full_release_cycle("1.0.0", Platform.IOS, DistributionChannel.APP_STORE)
        n = distributor.push.send("New Version Available", "Update to 1.0.0 now!", Platform.IOS,
                                   target_users=["u1", "u2", "u3"])
        assert n.sent_count == 3

    def test_failed_build_count(self, distributor):
        b = distributor.pipeline.create_build("1.0.0", Platform.IOS)
        distributor.pipeline.start_build(b.build_id)
        distributor.pipeline.complete_build(b.build_id, success=False, error_message="Error")
        stats = distributor.get_stats()
        assert stats["failed_builds"] == 1

    def test_ios_and_android_releases(self, distributor):
        distributor.full_release_cycle("1.0.0", Platform.IOS, DistributionChannel.APP_STORE)
        distributor.full_release_cycle("1.0.0", Platform.ANDROID, DistributionChannel.PLAY_STORE)
        ios = distributor.releases.list_releases(platform=Platform.IOS)
        android = distributor.releases.list_releases(platform=Platform.ANDROID)
        assert len(ios) == 1
        assert len(android) == 1

    def test_testflight_release(self, distributor):
        release = distributor.full_release_cycle("1.0.0-beta", Platform.IOS, DistributionChannel.TESTFLIGHT)
        assert release.channel == DistributionChannel.TESTFLIGHT

    def test_enterprise_release(self, distributor):
        release = distributor.full_release_cycle("1.0.0", Platform.BOTH, DistributionChannel.ENTERPRISE)
        assert release.channel == DistributionChannel.ENTERPRISE

    def test_latest_release_after_two_versions(self, distributor):
        distributor.full_release_cycle("1.0.0", Platform.IOS, DistributionChannel.APP_STORE)
        time.sleep(0.01)
        r2 = distributor.full_release_cycle("1.0.1", Platform.IOS, DistributionChannel.APP_STORE)
        latest = distributor.releases.get_latest_release(Platform.IOS, DistributionChannel.APP_STORE)
        assert latest.release_id == r2.release_id

    def test_push_stats_after_notifications(self, distributor):
        n = distributor.push.send("T", "B", Platform.IOS, target_users=["u1"])
        distributor.push.record_delivery(n.notification_id, delivered=1, opened=1)
        push_stats = distributor.push.get_stats()
        assert push_stats["total_sent"] == 1
        assert push_stats["avg_open_rate"] == 1.0

    def test_build_pipeline_accessible(self, distributor):
        assert distributor.pipeline is not None

    def test_release_manager_accessible(self, distributor):
        assert distributor.releases is not None

    def test_push_service_accessible(self, distributor):
        assert distributor.push is not None

    def test_stats_total_downloads_multiple_releases(self, distributor):
        r1 = distributor.full_release_cycle("1.0.0", Platform.IOS, DistributionChannel.APP_STORE)
        r2 = distributor.full_release_cycle("1.0.1", Platform.IOS, DistributionChannel.APP_STORE)
        distributor.releases.record_download(r1.release_id, 100)
        distributor.releases.record_download(r2.release_id, 200)
        stats = distributor.get_stats()
        assert stats["total_downloads"] == 300
