from __future__ import annotations

from dataclasses import dataclass

from vpn_sandbox.core.models import (
    DirectProfile,
    ViolationAction,
    VpnProfile,
    ZoneSettings,
    ZoneStatus,
)


@dataclass(frozen=True)
class NetworkSnapshot:
    control_available: bool
    vpn_detected: bool
    country_code: str | None
    direct_route_confirmed: bool
    geo_ip_available: bool


@dataclass(frozen=True)
class PolicyDecision:
    status: ZoneStatus
    can_start: bool
    reason: str
    action: ViolationAction


def _attention_or_block(
    settings: ZoneSettings,
    reason: str,
    status_when_blocked: ZoneStatus = ZoneStatus.BLOCKED,
) -> PolicyDecision:
    if settings.is_warn_only_allowed:
        return PolicyDecision(
            status=ZoneStatus.ATTENTION,
            can_start=True,
            reason=reason,
            action=settings.violation_action,
        )
    return PolicyDecision(
        status=status_when_blocked,
        can_start=False,
        reason=reason,
        action=settings.violation_action,
    )


def evaluate_vpn_zone(
    settings: ZoneSettings,
    profile: VpnProfile | None,
    snapshot: NetworkSnapshot,
) -> PolicyDecision:
    if not settings.enabled:
        return PolicyDecision(
            status=ZoneStatus.DISABLED,
            can_start=True,
            reason="Zone disabled",
            action=settings.violation_action,
        )
    if not snapshot.control_available:
        return PolicyDecision(
            status=ZoneStatus.BLOCKED,
            can_start=False,
            reason="Network control unavailable",
            action=settings.violation_action,
        )
    if profile is None:
        return PolicyDecision(
            status=ZoneStatus.BLOCKED,
            can_start=False,
            reason="Active VPN profile missing",
            action=settings.violation_action,
        )
    if not snapshot.vpn_detected:
        return _attention_or_block(settings, "VPN is not detected")
    if not snapshot.geo_ip_available:
        return _attention_or_block(settings, "Geo-IP unavailable")
    if snapshot.country_code != profile.country_code:
        return _attention_or_block(settings, "VPN country mismatch")
    return PolicyDecision(
        status=ZoneStatus.OK,
        can_start=True,
        reason="VPN profile matched",
        action=settings.violation_action,
    )


def evaluate_direct_zone(
    settings: ZoneSettings,
    profile: DirectProfile | None,
    snapshot: NetworkSnapshot,
) -> PolicyDecision:
    if not settings.enabled:
        return PolicyDecision(
            status=ZoneStatus.DISABLED,
            can_start=True,
            reason="Zone disabled",
            action=settings.violation_action,
        )
    if profile is None:
        return _attention_or_block(settings, "Active direct profile missing")
    if snapshot.direct_route_confirmed:
        return PolicyDecision(
            status=ZoneStatus.OK,
            can_start=True,
            reason="Direct route confirmed",
            action=settings.violation_action,
        )
    return _attention_or_block(
        settings,
        "Direct route not guaranteed",
        status_when_blocked=ZoneStatus.ATTENTION,
    )
