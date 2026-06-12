from vpn_sandbox.core.models import (
    Confidence,
    DirectProfile,
    ViolationAction,
    VpnProfile,
    ZoneKind,
    ZoneSettings,
    ZoneStatus,
)
from vpn_sandbox.core.policy import NetworkSnapshot, evaluate_direct_zone, evaluate_vpn_zone


def make_vpn_profile() -> VpnProfile:
    return VpnProfile(
        id="vpn-1",
        country_code="DE",
        country_name="Германия",
        city="Frankfurt",
        external_ip="203.0.113.10",
        protocol="WireGuard",
        client_name="Amnezia",
        confidence=Confidence.CERTAIN,
    )


def make_direct_profile() -> DirectProfile:
    return DirectProfile(
        id="direct-1",
        interface_name="Wi-Fi",
        gateway="192.168.1.1",
        dns_servers=("1.1.1.1",),
    )


def test_disabled_vpn_zone_does_not_block():
    settings = ZoneSettings(
        zone=ZoneKind.VPN,
        enabled=False,
        violation_action=ViolationAction.CLOSE_AFTER_20,
        warn_only_acknowledged=False,
        active_profile_id="vpn-1",
    )
    snapshot = NetworkSnapshot(
        control_available=True,
        vpn_detected=False,
        country_code=None,
        direct_route_confirmed=True,
        geo_ip_available=True,
    )

    decision = evaluate_vpn_zone(settings, make_vpn_profile(), snapshot)

    assert decision.status == ZoneStatus.DISABLED
    assert decision.can_start is True


def test_vpn_zone_allows_matching_country_with_control():
    settings = ZoneSettings(
        zone=ZoneKind.VPN,
        enabled=True,
        violation_action=ViolationAction.CLOSE_AFTER_20,
        warn_only_acknowledged=False,
        active_profile_id="vpn-1",
    )
    snapshot = NetworkSnapshot(
        control_available=True,
        vpn_detected=True,
        country_code="DE",
        direct_route_confirmed=False,
        geo_ip_available=True,
    )

    decision = evaluate_vpn_zone(settings, make_vpn_profile(), snapshot)

    assert decision.status == ZoneStatus.OK
    assert decision.can_start is True
    assert decision.reason == "VPN profile matched"


def test_vpn_zone_blocks_when_country_differs():
    settings = ZoneSettings(
        zone=ZoneKind.VPN,
        enabled=True,
        violation_action=ViolationAction.CLOSE_AFTER_10,
        warn_only_acknowledged=False,
        active_profile_id="vpn-1",
    )
    snapshot = NetworkSnapshot(
        control_available=True,
        vpn_detected=True,
        country_code="NL",
        direct_route_confirmed=False,
        geo_ip_available=True,
    )

    decision = evaluate_vpn_zone(settings, make_vpn_profile(), snapshot)

    assert decision.status == ZoneStatus.BLOCKED
    assert decision.can_start is False
    assert decision.reason == "VPN country mismatch"


def test_vpn_zone_blocks_when_control_is_unavailable():
    settings = ZoneSettings(
        zone=ZoneKind.VPN,
        enabled=True,
        violation_action=ViolationAction.CLOSE_AFTER_20,
        warn_only_acknowledged=False,
        active_profile_id="vpn-1",
    )
    snapshot = NetworkSnapshot(
        control_available=False,
        vpn_detected=True,
        country_code="DE",
        direct_route_confirmed=False,
        geo_ip_available=True,
    )

    decision = evaluate_vpn_zone(settings, make_vpn_profile(), snapshot)

    assert decision.status == ZoneStatus.BLOCKED
    assert decision.can_start is False
    assert decision.reason == "Network control unavailable"


def test_direct_zone_allows_confirmed_direct_route():
    settings = ZoneSettings(
        zone=ZoneKind.DIRECT,
        enabled=True,
        violation_action=ViolationAction.CLOSE_AFTER_20,
        warn_only_acknowledged=False,
        active_profile_id="direct-1",
    )
    snapshot = NetworkSnapshot(
        control_available=True,
        vpn_detected=True,
        country_code="DE",
        direct_route_confirmed=True,
        geo_ip_available=True,
    )

    decision = evaluate_direct_zone(settings, make_direct_profile(), snapshot)

    assert decision.status == ZoneStatus.OK
    assert decision.can_start is True
    assert decision.reason == "Direct route confirmed"


def test_direct_zone_warn_only_allows_start_with_attention():
    settings = ZoneSettings(
        zone=ZoneKind.DIRECT,
        enabled=True,
        violation_action=ViolationAction.WARN_ONLY,
        warn_only_acknowledged=True,
        active_profile_id="direct-1",
    )
    snapshot = NetworkSnapshot(
        control_available=False,
        vpn_detected=True,
        country_code="DE",
        direct_route_confirmed=False,
        geo_ip_available=True,
    )

    decision = evaluate_direct_zone(settings, make_direct_profile(), snapshot)

    assert decision.status == ZoneStatus.ATTENTION
    assert decision.can_start is True
    assert decision.reason == "Direct route not guaranteed"
