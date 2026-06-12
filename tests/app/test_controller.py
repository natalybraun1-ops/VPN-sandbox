from pathlib import Path

from vpn_sandbox.app.controller import AppController
from vpn_sandbox.core.models import (
    Confidence,
    OperatingMode,
    ViolationAction,
    VpnProfile,
    ZoneKind,
    ZoneStatus,
)
from vpn_sandbox.core.policy import NetworkSnapshot
from vpn_sandbox.events.journal import EventJournal
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


def test_configure_vpn_only_mode_enables_only_vpn_zone(tmp_path: Path):
    controller = make_controller(tmp_path)

    controller.configure_mode(OperatingMode.VPN_ONLY)

    assert controller.get_operating_mode() == OperatingMode.VPN_ONLY
    assert controller.repository.get_zone_settings(ZoneKind.VPN).enabled is True
    assert controller.repository.get_zone_settings(ZoneKind.DIRECT).enabled is False


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
