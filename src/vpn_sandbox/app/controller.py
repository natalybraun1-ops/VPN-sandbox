from __future__ import annotations

from dataclasses import dataclass

from vpn_sandbox.app.ids import UuidFactory
from vpn_sandbox.core.models import (
    Confidence,
    DirectProfile,
    ManagedApp,
    OperatingMode,
    ViolationAction,
    VpnProfile,
    ZoneKind,
    ZoneSettings,
    ZoneStatus,
)
from vpn_sandbox.core.policy import NetworkSnapshot, PolicyDecision
from vpn_sandbox.events.journal import EventJournal, EventRecord
from vpn_sandbox.ipc.service_simulator import ServiceSimulator
from vpn_sandbox.storage.repository import Repository


@dataclass(frozen=True)
class ZoneDashboard:
    zone: ZoneKind
    enabled: bool
    status: ZoneStatus
    reason: str
    apps: tuple[ManagedApp, ...]
    active_profile_name: str | None


@dataclass(frozen=True)
class DashboardState:
    operating_mode: OperatingMode | None
    zones: dict[ZoneKind, ZoneDashboard]
    events: tuple[EventRecord, ...]


class AppController:
    def __init__(
        self,
        repository: Repository,
        journal: EventJournal,
        ids: UuidFactory | None = None,
    ):
        self.repository = repository
        self.journal = journal
        self._ids = ids or UuidFactory()

    def get_operating_mode(self) -> OperatingMode | None:
        return self.repository.get_operating_mode()

    def configure_mode(self, mode: OperatingMode) -> None:
        self.repository.save_operating_mode(mode)
        enabled = {
            ZoneKind.VPN: mode in {OperatingMode.VPN_ONLY, OperatingMode.DUAL_ZONE},
            ZoneKind.DIRECT: mode in {
                OperatingMode.DIRECT_ONLY,
                OperatingMode.DUAL_ZONE,
            },
        }
        for zone in (ZoneKind.VPN, ZoneKind.DIRECT):
            existing = self.repository.get_zone_settings(zone)
            self.repository.save_zone_settings(
                ZoneSettings(
                    zone=zone,
                    enabled=enabled[zone],
                    violation_action=(
                        existing.violation_action
                        if existing is not None
                        else ViolationAction.CLOSE_AFTER_20
                    ),
                    warn_only_acknowledged=(
                        existing.warn_only_acknowledged if existing is not None else False
                    ),
                    active_profile_id=existing.active_profile_id if existing else None,
                )
            )

    def save_zone_settings(self, settings: ZoneSettings) -> None:
        self.repository.save_zone_settings(settings)

    def add_manual_app(
        self,
        zone: ZoneKind,
        exe_path: str,
        display_name: str,
    ) -> ManagedApp:
        app = ManagedApp(
            id=self._ids.new_id("app"),
            zone=zone,
            exe_path=exe_path,
            display_name=display_name,
        )
        self.repository.add_managed_app(app)
        return app

    def remove_managed_app(self, app_id: str) -> None:
        self.repository.delete_managed_app(app_id)

    def save_vpn_profile(
        self,
        country_code: str,
        country_name: str,
        city: str | None,
        external_ip: str,
        protocol: str | None,
        client_name: str | None,
        confidence: Confidence,
        custom_name: str | None,
        make_active: bool,
    ) -> VpnProfile:
        profile = VpnProfile(
            id=self._ids.new_id("vpn"),
            country_code=country_code,
            country_name=country_name,
            city=city,
            external_ip=external_ip,
            protocol=protocol,
            client_name=client_name,
            confidence=confidence,
            custom_name=custom_name,
        )
        self.repository.save_vpn_profile(profile)
        if make_active:
            self._set_active_profile(ZoneKind.VPN, profile.id)
        return profile

    def save_direct_profile(
        self,
        interface_name: str,
        gateway: str | None,
        dns_servers: tuple[str, ...],
        custom_name: str | None,
        make_active: bool,
    ) -> DirectProfile:
        profile = DirectProfile(
            id=self._ids.new_id("direct"),
            interface_name=interface_name,
            gateway=gateway,
            dns_servers=dns_servers,
            custom_name=custom_name,
            ordinal=len(self.repository.list_direct_profiles()),
        )
        self.repository.save_direct_profile(profile)
        if make_active:
            self._set_active_profile(ZoneKind.DIRECT, profile.id)
        return profile

    def _set_active_profile(self, zone: ZoneKind, profile_id: str) -> None:
        existing = self.repository.get_zone_settings(zone)
        if existing is None:
            existing = ZoneSettings(
                zone=zone,
                enabled=True,
                violation_action=ViolationAction.CLOSE_AFTER_20,
                warn_only_acknowledged=False,
                active_profile_id=None,
            )
        self.repository.save_zone_settings(
            ZoneSettings(
                zone=zone,
                enabled=existing.enabled,
                violation_action=existing.violation_action,
                warn_only_acknowledged=existing.warn_only_acknowledged,
                active_profile_id=profile_id,
            )
        )

    def load_dashboard(self, snapshot: NetworkSnapshot) -> DashboardState:
        simulator = ServiceSimulator(self.repository)
        zones = {
            zone: self._load_zone_dashboard(zone, snapshot, simulator)
            for zone in (ZoneKind.VPN, ZoneKind.DIRECT)
        }
        return DashboardState(
            operating_mode=self.get_operating_mode(),
            zones=zones,
            events=tuple(self.journal.read_recent(50)),
        )

    def _load_zone_dashboard(
        self,
        zone: ZoneKind,
        snapshot: NetworkSnapshot,
        simulator: ServiceSimulator,
    ) -> ZoneDashboard:
        settings = self.repository.get_zone_settings(zone)
        apps = tuple(self.repository.list_managed_apps(zone))
        decision = self._zone_decision(zone, apps, snapshot, simulator, settings)
        return ZoneDashboard(
            zone=zone,
            enabled=settings.enabled if settings else False,
            status=decision.status,
            reason=decision.reason,
            apps=apps,
            active_profile_name=self._active_profile_name(zone, settings),
        )

    def _zone_decision(
        self,
        zone: ZoneKind,
        apps: tuple[ManagedApp, ...],
        snapshot: NetworkSnapshot,
        simulator: ServiceSimulator,
        settings: ZoneSettings | None,
    ) -> PolicyDecision:
        if settings is None:
            return PolicyDecision(
                status=ZoneStatus.DISABLED,
                can_start=True,
                reason="Zone settings missing",
                action=ViolationAction.CLOSE_AFTER_20,
            )
        if not settings.enabled:
            return PolicyDecision(
                status=ZoneStatus.DISABLED,
                can_start=True,
                reason="Zone disabled",
                action=settings.violation_action,
            )
        if not apps:
            return PolicyDecision(
                status=ZoneStatus.ATTENTION,
                can_start=True,
                reason="No managed applications",
                action=settings.violation_action,
            )
        return simulator.evaluate_start(apps[0].exe_path, snapshot)

    def _active_profile_name(
        self,
        zone: ZoneKind,
        settings: ZoneSettings | None,
    ) -> str | None:
        if settings is None:
            return None
        if zone == ZoneKind.VPN:
            profile = self.repository.get_vpn_profile(settings.active_profile_id)
        else:
            profile = self.repository.get_direct_profile(settings.active_profile_id)
        return profile.effective_name if profile else None
