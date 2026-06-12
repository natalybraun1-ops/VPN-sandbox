from pathlib import Path

from vpn_sandbox.core.models import (
    Confidence,
    DirectProfile,
    ManagedApp,
    ViolationAction,
    VpnProfile,
    ZoneKind,
    ZoneSettings,
    ZoneStatus,
)
from vpn_sandbox.core.policy import NetworkSnapshot
from vpn_sandbox.ipc.service_simulator import ServiceSimulator
from vpn_sandbox.storage.repository import Repository


def make_repo(tmp_path: Path) -> Repository:
    repo = Repository.connect(tmp_path / "settings.sqlite3")
    repo.initialize()
    repo.save_vpn_profile(
        VpnProfile(
            id="vpn-1",
            country_code="DE",
            country_name="Германия",
            city="Frankfurt",
            external_ip="203.0.113.10",
            protocol="WireGuard",
            client_name="Amnezia",
            confidence=Confidence.CERTAIN,
        )
    )
    repo.save_zone_settings(
        ZoneSettings(
            zone=ZoneKind.VPN,
            enabled=True,
            violation_action=ViolationAction.CLOSE_AFTER_20,
            warn_only_acknowledged=False,
            active_profile_id="vpn-1",
        )
    )
    repo.add_managed_app(
        ManagedApp(
            id="app-1",
            zone=ZoneKind.VPN,
            exe_path="C:/Apps/browser.exe",
            display_name="Browser",
        )
    )
    repo.save_direct_profile(
        DirectProfile(
            id="direct-1",
            interface_name="Ethernet",
            gateway="192.0.2.1",
            dns_servers=("1.1.1.1",),
        )
    )
    repo.save_zone_settings(
        ZoneSettings(
            zone=ZoneKind.DIRECT,
            enabled=True,
            violation_action=ViolationAction.CLOSE_AFTER_20,
            warn_only_acknowledged=False,
            active_profile_id="direct-1",
        )
    )
    repo.add_managed_app(
        ManagedApp(
            id="app-2",
            zone=ZoneKind.DIRECT,
            exe_path="C:/Apps/editor.exe",
            display_name="Editor",
        )
    )
    return repo


def test_simulator_allows_unmanaged_apps(tmp_path: Path):
    simulator = ServiceSimulator(make_repo(tmp_path))
    snapshot = NetworkSnapshot(
        control_available=True,
        vpn_detected=False,
        country_code=None,
        direct_route_confirmed=True,
        geo_ip_available=True,
    )

    decision = simulator.evaluate_start("C:/Other/tool.exe", snapshot)

    assert decision.can_start is True
    assert decision.status == ZoneStatus.OK
    assert decision.reason == "Application is not managed"


def test_simulator_blocks_managed_vpn_app_on_wrong_country(tmp_path: Path):
    simulator = ServiceSimulator(make_repo(tmp_path))
    snapshot = NetworkSnapshot(
        control_available=True,
        vpn_detected=True,
        country_code="NL",
        direct_route_confirmed=False,
        geo_ip_available=True,
    )

    decision = simulator.evaluate_start("c:\\apps\\browser.exe", snapshot)

    assert decision.can_start is False
    assert decision.status == ZoneStatus.BLOCKED
    assert decision.reason == "VPN country mismatch"


def test_simulator_allows_managed_direct_app_when_direct_route_confirmed(
    tmp_path: Path,
):
    simulator = ServiceSimulator(make_repo(tmp_path))
    snapshot = NetworkSnapshot(
        control_available=True,
        vpn_detected=False,
        country_code=None,
        direct_route_confirmed=True,
        geo_ip_available=True,
    )

    decision = simulator.evaluate_start("c:\\apps\\editor.exe", snapshot)

    assert decision.can_start is True
    assert decision.status == ZoneStatus.OK
    assert decision.reason == "Direct route confirmed"
