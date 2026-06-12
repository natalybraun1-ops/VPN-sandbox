from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from vpn_sandbox.core.models import ZoneStatus


@dataclass(frozen=True)
class ServiceCommand:
    name: str
    payload: dict[str, Any]

    def to_json(self) -> str:
        return json.dumps(
            {"name": self.name, "payload": self.payload},
            ensure_ascii=False,
            sort_keys=True,
        )

    @classmethod
    def from_json(cls, raw: str) -> "ServiceCommand":
        payload = json.loads(raw)
        return cls(name=payload["name"], payload=payload["payload"])


@dataclass(frozen=True)
class ZoneRuntimeStatus:
    status: ZoneStatus
    reason: str

    def to_dict(self) -> dict[str, str]:
        return {"status": self.status.value, "reason": self.reason}

    @classmethod
    def from_dict(cls, payload: dict[str, str]) -> "ZoneRuntimeStatus":
        return cls(status=ZoneStatus(payload["status"]), reason=payload["reason"])


@dataclass(frozen=True)
class ServiceStatus:
    control_available: bool
    service_running: bool
    zones: dict[str, ZoneRuntimeStatus]

    def to_json(self) -> str:
        return json.dumps(
            {
                "control_available": self.control_available,
                "service_running": self.service_running,
                "zones": {
                    key: value.to_dict()
                    for key, value in sorted(self.zones.items())
                },
            },
            ensure_ascii=False,
            sort_keys=True,
        )

    @classmethod
    def from_json(cls, raw: str) -> "ServiceStatus":
        payload = json.loads(raw)
        return cls(
            control_available=payload["control_available"],
            service_running=payload["service_running"],
            zones={
                key: ZoneRuntimeStatus.from_dict(value)
                for key, value in payload["zones"].items()
            },
        )
