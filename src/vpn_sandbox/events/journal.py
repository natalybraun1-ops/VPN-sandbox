from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


def mask_ip(value: str) -> str:
    parts = value.split(".")
    if len(parts) == 4 and all(part.isdigit() for part in parts):
        return ".".join(parts[:3] + ["x"])
    return value


def _mask_details(details: dict[str, Any]) -> dict[str, Any]:
    def mask_value(key: str | None, value: Any) -> Any:
        if isinstance(value, dict):
            return {
                child_key: mask_value(child_key, child_value)
                for child_key, child_value in value.items()
            }
        if isinstance(value, list):
            return [mask_value(None, item) for item in value]
        if (
            key is not None
            and (key == "ip" or key.endswith("_ip"))
            and isinstance(value, str)
        ):
            return mask_ip(value)
        return value

    masked: dict[str, Any] = {}
    for key, value in details.items():
        masked[key] = mask_value(key, value)
    return masked


@dataclass(frozen=True)
class EventRecord:
    timestamp: str
    level: str
    zone: str | None
    app: str | None
    reason: str
    details: dict[str, Any]

    def to_json_line(self) -> str:
        payload = {
            "timestamp": self.timestamp,
            "level": self.level,
            "zone": self.zone,
            "app": self.app,
            "reason": self.reason,
            "details": _mask_details(self.details),
        }
        return json.dumps(payload, ensure_ascii=False, sort_keys=True)

    @classmethod
    def from_json_line(cls, line: str) -> EventRecord:
        payload = json.loads(line)
        return cls(
            timestamp=payload["timestamp"],
            level=payload["level"],
            zone=payload["zone"],
            app=payload["app"],
            reason=payload["reason"],
            details=payload["details"],
        )


class EventJournal:
    def __init__(self, path: Path):
        self._path = path

    def append(self, record: EventRecord) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with self._path.open("a", encoding="utf-8") as handle:
            handle.write(record.to_json_line() + "\n")

    def read_recent(self, limit: int) -> list[EventRecord]:
        if limit <= 0:
            return []
        if not self._path.exists():
            return []
        lines = self._path.read_text(encoding="utf-8").splitlines()
        selected = lines[-limit:]
        return [EventRecord.from_json_line(line) for line in selected if line.strip()]
