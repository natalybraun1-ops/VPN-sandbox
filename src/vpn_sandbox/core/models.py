from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import PureWindowsPath


class OperatingMode(StrEnum):
    VPN_ONLY = "vpn_only"
    DIRECT_ONLY = "direct_only"
    DUAL_ZONE = "dual_zone"


class ZoneKind(StrEnum):
    VPN = "vpn"
    DIRECT = "direct"


class ZoneStatus(StrEnum):
    OK = "ok"
    ATTENTION = "attention"
    BLOCKED = "blocked"
    DISABLED = "disabled"


class ViolationAction(StrEnum):
    CLOSE_IMMEDIATELY = "close_immediately"
    CLOSE_AFTER_10 = "close_after_10"
    CLOSE_AFTER_20 = "close_after_20"
    CLOSE_AFTER_30 = "close_after_30"
    WARN_ONLY = "warn_only"


class Confidence(StrEnum):
    CERTAIN = "certain"
    LIKELY = "likely"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class VpnProfile:
    id: str
    country_code: str
    country_name: str
    city: str | None
    external_ip: str
    protocol: str | None
    client_name: str | None
    confidence: Confidence
    custom_name: str | None = None

    @property
    def effective_name(self) -> str:
        if self.custom_name:
            return self.custom_name
        if self.country_name and self.protocol:
            return f"{self.country_name} · {self.protocol}"
        if self.country_name:
            return f"{self.country_name} · неизвестный протокол"
        return "VPN-профиль"


@dataclass(frozen=True)
class DirectProfile:
    id: str
    interface_name: str
    gateway: str | None
    dns_servers: tuple[str, ...]
    custom_name: str | None = None
    ordinal: int = 0

    @staticmethod
    def default_name(existing_count: int) -> str:
        if existing_count <= 0:
            return "Прямое подключение"
        return f"Прямое подключение {existing_count + 1}"

    @property
    def effective_name(self) -> str:
        if self.custom_name:
            return self.custom_name
        return self.default_name(self.ordinal)


@dataclass(frozen=True)
class ZoneSettings:
    zone: ZoneKind
    enabled: bool
    violation_action: ViolationAction
    warn_only_acknowledged: bool
    active_profile_id: str | None

    @property
    def is_warn_only_allowed(self) -> bool:
        return (
            self.violation_action == ViolationAction.WARN_ONLY
            and self.warn_only_acknowledged
        )


@dataclass(frozen=True)
class ManagedApp:
    id: str
    zone: ZoneKind
    exe_path: str
    display_name: str

    @property
    def match_key(self) -> str:
        return str(PureWindowsPath(self.exe_path)).lower()
