from pathlib import Path

import pytest

from vpn_sandbox.core.models import (
    Confidence,
    ManagedApp,
    ViolationAction,
    VpnProfile,
    ZoneKind,
    ZoneSettings,
)
from vpn_sandbox.storage.repository import Repository
from vpn_sandbox.storage.schema import SCHEMA_VERSION


def test_repository_initializes_schema(tmp_path: Path):
    db_path = tmp_path / "settings.sqlite3"

    repo = Repository.connect(db_path)
    repo.initialize()

    assert repo.schema_version() == SCHEMA_VERSION


def test_repository_round_trips_vpn_profile(tmp_path: Path):
    repo = Repository.connect(tmp_path / "settings.sqlite3")
    repo.initialize()
    profile = VpnProfile(
        id="vpn-1",
        country_code="DE",
        country_name="Германия",
        city="Frankfurt",
        external_ip="203.0.113.10",
        protocol="WireGuard",
        client_name="Amnezia",
        confidence=Confidence.CERTAIN,
        custom_name="Основной VPN",
    )

    repo.save_vpn_profile(profile)

    assert repo.list_vpn_profiles() == [profile]


def test_repository_keeps_one_active_profile_per_zone(tmp_path: Path):
    repo = Repository.connect(tmp_path / "settings.sqlite3")
    repo.initialize()

    repo.save_zone_settings(
        ZoneSettings(
            zone=ZoneKind.VPN,
            enabled=True,
            violation_action=ViolationAction.CLOSE_AFTER_20,
            warn_only_acknowledged=False,
            active_profile_id="vpn-1",
        )
    )

    loaded = repo.get_zone_settings(ZoneKind.VPN)

    assert loaded == ZoneSettings(
        zone=ZoneKind.VPN,
        enabled=True,
        violation_action=ViolationAction.CLOSE_AFTER_20,
        warn_only_acknowledged=False,
        active_profile_id="vpn-1",
    )


def test_repository_rejects_same_exe_in_two_zones(tmp_path: Path):
    repo = Repository.connect(tmp_path / "settings.sqlite3")
    repo.initialize()
    repo.add_managed_app(
        ManagedApp(
            id="app-1",
            zone=ZoneKind.VPN,
            exe_path="C:/Apps/browser.exe",
            display_name="Browser",
        )
    )

    with pytest.raises(ValueError, match="already managed"):
        repo.add_managed_app(
            ManagedApp(
                id="app-2",
                zone=ZoneKind.DIRECT,
                exe_path="c:\\apps\\browser.exe",
                display_name="Browser",
            )
        )
