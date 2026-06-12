from __future__ import annotations

from vpn_sandbox.core.models import ViolationAction, ZoneKind, ZoneStatus
from vpn_sandbox.core.policy import (
    NetworkSnapshot,
    PolicyDecision,
    evaluate_direct_zone,
    evaluate_vpn_zone,
)
from vpn_sandbox.storage.repository import Repository


class ServiceSimulator:
    def __init__(self, repository: Repository):
        self._repository = repository

    def evaluate_start(
        self,
        exe_path: str,
        snapshot: NetworkSnapshot,
    ) -> PolicyDecision:
        app = self._repository.find_managed_app(exe_path)
        if app is None:
            return PolicyDecision(
                status=ZoneStatus.OK,
                can_start=True,
                reason="Application is not managed",
                action=ViolationAction.CLOSE_AFTER_20,
            )

        settings = self._repository.get_zone_settings(app.zone)
        if settings is None:
            return PolicyDecision(
                status=ZoneStatus.DISABLED,
                can_start=True,
                reason="Zone settings missing",
                action=ViolationAction.CLOSE_AFTER_20,
            )

        if app.zone == ZoneKind.VPN:
            profile = self._repository.get_vpn_profile(settings.active_profile_id)
            return evaluate_vpn_zone(settings, profile, snapshot)

        profile = self._repository.get_direct_profile(settings.active_profile_id)
        return evaluate_direct_zone(settings, profile, snapshot)
