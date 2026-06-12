from vpn_sandbox.core.models import (
    Confidence,
    DirectProfile,
    ManagedApp,
    OperatingMode,
    ViolationAction,
    VpnProfile,
    ZoneKind,
    ZoneSettings,
)


def test_vpn_profile_effective_name_uses_country_and_protocol():
    profile = VpnProfile(
        id="vpn-1",
        country_code="DE",
        country_name="Германия",
        city="Frankfurt",
        external_ip="203.0.113.10",
        protocol="WireGuard",
        client_name="Amnezia",
        confidence=Confidence.CERTAIN,
    )

    assert profile.effective_name == "Германия · WireGuard"


def test_vpn_profile_keeps_custom_name():
    profile = VpnProfile(
        id="vpn-1",
        country_code="NL",
        country_name="Нидерланды",
        city=None,
        external_ip="203.0.113.20",
        protocol="OpenVPN",
        client_name=None,
        confidence=Confidence.LIKELY,
        custom_name="Рабочий VPN",
    )

    assert profile.effective_name == "Рабочий VPN"


def test_direct_profile_default_names_are_human_readable():
    assert DirectProfile.default_name(0) == "Прямое подключение"
    assert DirectProfile.default_name(1) == "Прямое подключение 2"
    assert DirectProfile.default_name(2) == "Прямое подключение 3"


def test_zone_settings_warn_only_requires_acknowledgement():
    settings = ZoneSettings(
        zone=ZoneKind.VPN,
        enabled=True,
        violation_action=ViolationAction.WARN_ONLY,
        warn_only_acknowledged=False,
        active_profile_id="vpn-1",
    )

    assert settings.is_warn_only_allowed is False

    acknowledged = ZoneSettings(
        zone=ZoneKind.VPN,
        enabled=True,
        violation_action=ViolationAction.WARN_ONLY,
        warn_only_acknowledged=True,
        active_profile_id="vpn-1",
    )

    assert acknowledged.is_warn_only_allowed is True


def test_managed_app_normalizes_exe_path_for_matching():
    app = ManagedApp(
        id="app-1",
        zone=ZoneKind.DIRECT,
        exe_path="C:/Program Files/Browser/browser.exe",
        display_name="Browser",
    )

    assert app.match_key == "c:\\program files\\browser\\browser.exe"
