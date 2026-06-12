from pathlib import Path

from vpn_sandbox.app.controller import AppController
from vpn_sandbox.core.models import (
    Confidence,
    OperatingMode,
    ViolationAction,
    VpnProfile,
    ZoneKind,
    ZoneSettings,
    ZoneStatus,
)
from vpn_sandbox.core.policy import NetworkSnapshot
from vpn_sandbox.events.journal import EventJournal, EventRecord
from vpn_sandbox.storage.repository import Repository


class SequentialIds:
    def __init__(self):
        self.count = 0

    def new_id(self, prefix: str) -> str:
        self.count += 1
        return f"{prefix}-{self.count}"


def make_controller(tmp_path: Path) -> AppController:
    repo = Repository.connect(tmp_path / "settings.sqlite3")
    repo.initialize()
    return AppController(
        repository=repo,
        journal=EventJournal(tmp_path / "events.jsonl"),
        ids=SequentialIds(),
    )


def make_snapshot() -> NetworkSnapshot:
    return NetworkSnapshot(
        control_available=True,
        vpn_detected=True,
        country_code="DE",
        direct_route_confirmed=True,
        geo_ip_available=True,
    )


def test_configure_vpn_only_mode_enables_only_vpn_zone(tmp_path: Path):
    controller = make_controller(tmp_path)

    controller.configure_mode(OperatingMode.VPN_ONLY)

    assert controller.get_operating_mode() == OperatingMode.VPN_ONLY
    assert controller.repository.get_zone_settings(ZoneKind.VPN).enabled is True
    assert controller.repository.get_zone_settings(ZoneKind.DIRECT).enabled is False


def test_configure_mode_preserves_existing_zone_settings_fields(tmp_path: Path):
    controller = make_controller(tmp_path)
    controller.repository.save_zone_settings(
        ZoneSettings(
            zone=ZoneKind.VPN,
            enabled=True,
            violation_action=ViolationAction.WARN_ONLY,
            warn_only_acknowledged=True,
            active_profile_id="vpn-active",
        )
    )
    controller.repository.save_zone_settings(
        ZoneSettings(
            zone=ZoneKind.DIRECT,
            enabled=False,
            violation_action=ViolationAction.CLOSE_IMMEDIATELY,
            warn_only_acknowledged=False,
            active_profile_id="direct-active",
        )
    )

    controller.configure_mode(OperatingMode.DIRECT_ONLY)

    assert controller.repository.get_zone_settings(ZoneKind.VPN) == ZoneSettings(
        zone=ZoneKind.VPN,
        enabled=False,
        violation_action=ViolationAction.WARN_ONLY,
        warn_only_acknowledged=True,
        active_profile_id="vpn-active",
    )
    assert controller.repository.get_zone_settings(ZoneKind.DIRECT) == ZoneSettings(
        zone=ZoneKind.DIRECT,
        enabled=True,
        violation_action=ViolationAction.CLOSE_IMMEDIATELY,
        warn_only_acknowledged=False,
        active_profile_id="direct-active",
    )


def test_add_manual_app_persists_in_selected_zone(tmp_path: Path):
    controller = make_controller(tmp_path)
    controller.configure_mode(OperatingMode.DUAL_ZONE)

    app = controller.add_manual_app(
        zone=ZoneKind.VPN,
        exe_path="C:/Apps/browser.exe",
        display_name="Browser",
    )

    assert app.id == "app-1"
    assert controller.repository.list_managed_apps(ZoneKind.VPN) == [app]


def test_remove_managed_app_deletes_it_from_repository(tmp_path: Path):
    controller = make_controller(tmp_path)
    controller.configure_mode(OperatingMode.DUAL_ZONE)
    app = controller.add_manual_app(
        zone=ZoneKind.DIRECT,
        exe_path="C:/Apps/editor.exe",
        display_name="Editor",
    )

    controller.remove_managed_app(app.id)

    assert controller.repository.list_managed_apps(ZoneKind.DIRECT) == []
    assert controller.repository.find_managed_app(app.exe_path) is None


def test_save_vpn_profile_sets_active_profile_when_requested(tmp_path: Path):
    controller = make_controller(tmp_path)
    controller.configure_mode(OperatingMode.VPN_ONLY)

    profile = controller.save_vpn_profile(
        country_code="DE",
        country_name="Германия",
        city="Frankfurt",
        external_ip="203.0.113.10",
        protocol="WireGuard",
        client_name="Amnezia",
        confidence=Confidence.CERTAIN,
        custom_name="Основной VPN",
        make_active=True,
    )

    settings = controller.repository.get_zone_settings(ZoneKind.VPN)
    assert profile.id == "vpn-1"
    assert settings.active_profile_id == profile.id


def test_save_direct_profile_sets_active_profile_when_requested(tmp_path: Path):
    controller = make_controller(tmp_path)
    controller.configure_mode(OperatingMode.DIRECT_ONLY)

    profile = controller.save_direct_profile(
        interface_name="Ethernet",
        gateway="192.0.2.1",
        dns_servers=("1.1.1.1",),
        custom_name="Home ISP",
        make_active=True,
    )

    settings = controller.repository.get_zone_settings(ZoneKind.DIRECT)
    assert profile.id == "direct-1"
    assert settings.active_profile_id == profile.id


def test_dashboard_uses_service_simulator_for_zone_status(tmp_path: Path):
    controller = make_controller(tmp_path)
    controller.configure_mode(OperatingMode.VPN_ONLY)
    profile = VpnProfile(
        id="vpn-existing",
        country_code="DE",
        country_name="Германия",
        city=None,
        external_ip="203.0.113.10",
        protocol="WireGuard",
        client_name=None,
        confidence=Confidence.CERTAIN,
    )
    controller.repository.save_vpn_profile(profile)
    controller.repository.save_zone_settings(
        controller.repository.get_zone_settings(ZoneKind.VPN).__class__(
            zone=ZoneKind.VPN,
            enabled=True,
            violation_action=ViolationAction.CLOSE_AFTER_20,
            warn_only_acknowledged=False,
            active_profile_id=profile.id,
        )
    )
    controller.add_manual_app(
        zone=ZoneKind.VPN,
        exe_path="C:/Apps/browser.exe",
        display_name="Browser",
    )

    dashboard = controller.load_dashboard(
        NetworkSnapshot(
            control_available=True,
            vpn_detected=True,
            country_code="NL",
            direct_route_confirmed=False,
            geo_ip_available=True,
        )
    )

    assert dashboard.zones[ZoneKind.VPN].status == ZoneStatus.BLOCKED
    assert dashboard.zones[ZoneKind.VPN].reason == "VPN country mismatch"


def test_dashboard_includes_active_profile_names(tmp_path: Path):
    controller = make_controller(tmp_path)
    controller.configure_mode(OperatingMode.DUAL_ZONE)
    controller.save_vpn_profile(
        country_code="DE",
        country_name="Germany",
        city="Frankfurt",
        external_ip="203.0.113.10",
        protocol="WireGuard",
        client_name="Amnezia",
        confidence=Confidence.CERTAIN,
        custom_name="Primary VPN",
        make_active=True,
    )
    controller.save_direct_profile(
        interface_name="Ethernet",
        gateway="192.0.2.1",
        dns_servers=("1.1.1.1",),
        custom_name="Home ISP",
        make_active=True,
    )

    dashboard = controller.load_dashboard(make_snapshot())

    assert dashboard.zones[ZoneKind.VPN].active_profile_name == "Primary VPN"
    assert dashboard.zones[ZoneKind.DIRECT].active_profile_name == "Home ISP"


def test_dashboard_reads_only_recent_50_events(tmp_path: Path):
    controller = make_controller(tmp_path)
    for index in range(55):
        controller.journal.append(
            EventRecord(
                timestamp=f"2026-06-12T00:{index:02d}:00Z",
                level="info",
                zone=None,
                app=None,
                reason=f"event-{index}",
                details={},
            )
        )

    dashboard = controller.load_dashboard(make_snapshot())

    assert len(dashboard.events) == 50
    assert dashboard.events[0].reason == "event-5"
    assert dashboard.events[-1].reason == "event-54"


def test_dashboard_reports_missing_zone_settings(tmp_path: Path):
    controller = make_controller(tmp_path)

    dashboard = controller.load_dashboard(make_snapshot())

    assert dashboard.zones[ZoneKind.VPN].status == ZoneStatus.DISABLED
    assert dashboard.zones[ZoneKind.VPN].reason == "Zone settings missing"


def test_dashboard_reports_disabled_zone(tmp_path: Path):
    controller = make_controller(tmp_path)
    controller.configure_mode(OperatingMode.VPN_ONLY)

    dashboard = controller.load_dashboard(make_snapshot())

    assert dashboard.zones[ZoneKind.DIRECT].status == ZoneStatus.DISABLED
    assert dashboard.zones[ZoneKind.DIRECT].reason == "Zone disabled"


def test_dashboard_reports_enabled_zone_with_no_apps(tmp_path: Path):
    controller = make_controller(tmp_path)
    controller.configure_mode(OperatingMode.VPN_ONLY)

    dashboard = controller.load_dashboard(make_snapshot())

    assert dashboard.zones[ZoneKind.VPN].status == ZoneStatus.ATTENTION
    assert dashboard.zones[ZoneKind.VPN].reason == "No managed applications"
