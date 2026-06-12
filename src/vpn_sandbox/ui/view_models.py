from __future__ import annotations

from dataclasses import dataclass

from vpn_sandbox.app.controller import ZoneDashboard
from vpn_sandbox.ui.text import status_label, zone_label


@dataclass(frozen=True)
class ZoneCardViewModel:
    title: str
    status: str
    reason: str
    profile: str
    app_count: str
    enabled: bool


def _plural_apps(count: int) -> str:
    if count % 10 == 1 and count % 100 != 11:
        return f"{count} приложение"
    if count % 10 in {2, 3, 4} and count % 100 not in {12, 13, 14}:
        return f"{count} приложения"
    return f"{count} приложений"


def build_zone_card(zone: ZoneDashboard) -> ZoneCardViewModel:
    return ZoneCardViewModel(
        title=zone_label(zone.zone),
        status=status_label(zone.status),
        reason=zone.reason,
        profile=zone.active_profile_name or "Профиль не выбран",
        app_count=_plural_apps(len(zone.apps)),
        enabled=zone.enabled,
    )
