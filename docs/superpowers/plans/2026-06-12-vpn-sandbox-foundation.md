# VPN Sandbox Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the first testable foundation for `vpn-sandbox`: project scaffold, domain model, policy evaluation, SQLite storage, event journal, IPC DTOs, and a service simulator that can be used by later UI/service/WFP work.

**Architecture:** This plan creates a Python core package with no PyQt or WFP dependency yet. The core models and policy engine become the contract shared by the PyQt UI, Windows service, and native network component. System-level networking, installer work, real process interception, and endpoints are split into later implementation plans.

**Tech Stack:** Python 3.13-compatible code, stdlib `sqlite3`, stdlib `dataclasses`, JSON, `pytest`, src-layout package.

---

## Scope Check

The approved design covers multiple independent subsystems: PyQt6 desktop UI, Windows service, native WFP component, installer, update/report endpoints, and diagnostics. A single implementation plan for all of that would be too large to execute safely.

This first plan covers only the foundation that every subsystem needs:

- project structure;
- domain models;
- rule evaluation;
- SQLite persistence;
- event journal;
- IPC message contracts;
- local service simulator;
- a small CLI smoke check.

Separate plans should follow for:

- PyQt6 UI and tray/minimized indicator;
- Windows service and process monitor;
- native WFP/network component;
- installer and Start Menu integration;
- update/report/geo-IP endpoints;
- VPN protocol recognition adapters.

## File Structure

Create this structure:

```text
pyproject.toml
README.md
src/
  vpn_sandbox/
    __init__.py
    __main__.py
    core/
      __init__.py
      models.py
      policy.py
    storage/
      __init__.py
      repository.py
      schema.py
    events/
      __init__.py
      journal.py
    ipc/
      __init__.py
      messages.py
      service_simulator.py
tests/
  core/
    test_models.py
    test_policy.py
  storage/
    test_repository.py
  events/
    test_journal.py
  ipc/
    test_messages.py
    test_service_simulator.py
  test_cli.py
```

Responsibilities:

- `core/models.py`: pure dataclasses and enums used by every subsystem.
- `core/policy.py`: pure decision logic for zone status, start blocking, and runtime violation reactions.
- `storage/schema.py`: SQLite DDL and schema version.
- `storage/repository.py`: persistence API for profiles, zone settings, and managed apps.
- `events/journal.py`: structured JSONL event log with basic privacy masking.
- `ipc/messages.py`: JSON-serializable command/status DTOs for UI-service communication.
- `ipc/service_simulator.py`: in-process fake service for tests and early UI development.
- `__main__.py`: CLI smoke entry point for `python -m vpn_sandbox doctor`.

## Task 1: Project Scaffold

**Files:**
- Create: `pyproject.toml`
- Create: `README.md`
- Create: `src/vpn_sandbox/__init__.py`
- Create: `src/vpn_sandbox/core/__init__.py`
- Create: `src/vpn_sandbox/storage/__init__.py`
- Create: `src/vpn_sandbox/events/__init__.py`
- Create: `src/vpn_sandbox/ipc/__init__.py`

- [ ] **Step 1: Create packaging and pytest configuration**

Write `pyproject.toml`:

```toml
[build-system]
requires = ["hatchling>=1.25"]
build-backend = "hatchling.build"

[project]
name = "vpn-sandbox"
version = "0.1.0"
description = "VPN sandbox foundation for controlled application networking"
readme = "README.md"
requires-python = ">=3.11"
dependencies = []

[project.optional-dependencies]
dev = [
  "pytest>=8.2",
]

[tool.hatch.build.targets.wheel]
packages = ["src/vpn_sandbox"]

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["src"]
addopts = "-q"
```

- [ ] **Step 2: Create README**

Write `README.md`:

````markdown
# Песочница VPN

`vpn-sandbox` is the technical project name for a Windows VPN control application.

The first implementation slice contains the Python foundation:

- domain models for VPN and direct zones;
- policy evaluation;
- SQLite persistence;
- structured event journal;
- IPC message contracts;
- a local service simulator for tests and early UI development.

The approved product design lives in `docs/superpowers/specs/2026-06-12-vpn-sandbox-design.md`.
```

- [ ] **Step 3: Create package markers**

Write `src/vpn_sandbox/__init__.py`:

```python
"""VPN Sandbox Python foundation package."""

__all__ = ["__version__"]

__version__ = "0.1.0"
```

Write these empty package marker files:

```python
```

- `src/vpn_sandbox/core/__init__.py`
- `src/vpn_sandbox/storage/__init__.py`
- `src/vpn_sandbox/events/__init__.py`
- `src/vpn_sandbox/ipc/__init__.py`

- [ ] **Step 4: Verify import works**

Run:

```powershell
$env:PYTHONPATH = "src"
python -c "import vpn_sandbox; print(vpn_sandbox.__version__)"
```

Expected:

```text
0.1.0
```

- [ ] **Step 5: Commit scaffold**

```powershell
git add pyproject.toml README.md src/vpn_sandbox
git commit -m "chore: scaffold Python foundation package"
```

## Task 2: Domain Models

**Files:**
- Create: `tests/core/test_models.py`
- Create: `src/vpn_sandbox/core/models.py`

- [ ] **Step 1: Write failing tests for profile names and zone settings**

Write `tests/core/test_models.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```powershell
python -m pytest tests/core/test_models.py -q
```

Expected: FAIL with `ModuleNotFoundError: No module named 'vpn_sandbox.core.models'`.

- [ ] **Step 3: Implement domain models**

Write `src/vpn_sandbox/core/models.py`:

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run:

```powershell
python -m pytest tests/core/test_models.py -q
```

Expected:

```text
5 passed
```

- [ ] **Step 5: Commit domain models**

```powershell
git add src/vpn_sandbox/core/models.py tests/core/test_models.py
git commit -m "feat: add VPN sandbox domain models"
```

## Task 3: Policy Evaluation

**Files:**
- Create: `tests/core/test_policy.py`
- Create: `src/vpn_sandbox/core/policy.py`

- [ ] **Step 1: Write failing policy tests**

Write `tests/core/test_policy.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```powershell
python -m pytest tests/core/test_policy.py -q
```

Expected: FAIL with `ModuleNotFoundError: No module named 'vpn_sandbox.core.policy'`.

- [ ] **Step 3: Implement policy engine**

Write `src/vpn_sandbox/core/policy.py`:

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run:

```powershell
python -m pytest tests/core/test_policy.py -q
```

Expected:

```text
6 passed
```

- [ ] **Step 5: Commit policy engine**

```powershell
git add src/vpn_sandbox/core/policy.py tests/core/test_policy.py
git commit -m "feat: add zone policy evaluation"
```

## Task 4: SQLite Repository

**Files:**
- Create: `tests/storage/test_repository.py`
- Create: `src/vpn_sandbox/storage/schema.py`
- Create: `src/vpn_sandbox/storage/repository.py`

- [ ] **Step 1: Write failing repository tests**

Write `tests/storage/test_repository.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```powershell
python -m pytest tests/storage/test_repository.py -q
```

Expected: FAIL with `ModuleNotFoundError: No module named 'vpn_sandbox.storage.repository'`.

- [ ] **Step 3: Implement SQLite schema**

Write `src/vpn_sandbox/storage/schema.py`:

```python
SCHEMA_VERSION = 1

DDL = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS meta (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS vpn_profiles (
    id TEXT PRIMARY KEY,
    country_code TEXT NOT NULL,
    country_name TEXT NOT NULL,
    city TEXT,
    external_ip TEXT NOT NULL,
    protocol TEXT,
    client_name TEXT,
    confidence TEXT NOT NULL,
    custom_name TEXT
);

CREATE TABLE IF NOT EXISTS zone_settings (
    zone TEXT PRIMARY KEY,
    enabled INTEGER NOT NULL,
    violation_action TEXT NOT NULL,
    warn_only_acknowledged INTEGER NOT NULL,
    active_profile_id TEXT
);

CREATE TABLE IF NOT EXISTS managed_apps (
    id TEXT PRIMARY KEY,
    zone TEXT NOT NULL,
    exe_path TEXT NOT NULL,
    match_key TEXT NOT NULL UNIQUE,
    display_name TEXT NOT NULL
);
"""
```

- [ ] **Step 4: Implement repository**

Write `src/vpn_sandbox/storage/repository.py`:

```python
from __future__ import annotations

import sqlite3
from pathlib import Path

from vpn_sandbox.core.models import (
    Confidence,
    ManagedApp,
    ViolationAction,
    VpnProfile,
    ZoneKind,
    ZoneSettings,
)
from vpn_sandbox.storage.schema import DDL, SCHEMA_VERSION


class Repository:
    def __init__(self, connection: sqlite3.Connection):
        self._connection = connection
        self._connection.row_factory = sqlite3.Row

    @classmethod
    def connect(cls, path: Path) -> "Repository":
        path.parent.mkdir(parents=True, exist_ok=True)
        return cls(sqlite3.connect(path))

    def initialize(self) -> None:
        self._connection.executescript(DDL)
        self._connection.execute(
            "INSERT OR REPLACE INTO meta(key, value) VALUES('schema_version', ?)",
            (str(SCHEMA_VERSION),),
        )
        self._connection.commit()

    def schema_version(self) -> int:
        row = self._connection.execute(
            "SELECT value FROM meta WHERE key = 'schema_version'"
        ).fetchone()
        if row is None:
            return 0
        return int(row["value"])

    def save_vpn_profile(self, profile: VpnProfile) -> None:
        self._connection.execute(
            """
            INSERT OR REPLACE INTO vpn_profiles(
                id, country_code, country_name, city, external_ip,
                protocol, client_name, confidence, custom_name
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                profile.id,
                profile.country_code,
                profile.country_name,
                profile.city,
                profile.external_ip,
                profile.protocol,
                profile.client_name,
                profile.confidence.value,
                profile.custom_name,
            ),
        )
        self._connection.commit()

    def list_vpn_profiles(self) -> list[VpnProfile]:
        rows = self._connection.execute(
            """
            SELECT id, country_code, country_name, city, external_ip,
                   protocol, client_name, confidence, custom_name
            FROM vpn_profiles
            ORDER BY id
            """
        ).fetchall()
        return [
            VpnProfile(
                id=row["id"],
                country_code=row["country_code"],
                country_name=row["country_name"],
                city=row["city"],
                external_ip=row["external_ip"],
                protocol=row["protocol"],
                client_name=row["client_name"],
                confidence=Confidence(row["confidence"]),
                custom_name=row["custom_name"],
            )
            for row in rows
        ]

    def get_vpn_profile(self, profile_id: str | None) -> VpnProfile | None:
        if profile_id is None:
            return None
        for profile in self.list_vpn_profiles():
            if profile.id == profile_id:
                return profile
        return None

    def save_zone_settings(self, settings: ZoneSettings) -> None:
        self._connection.execute(
            """
            INSERT OR REPLACE INTO zone_settings(
                zone, enabled, violation_action,
                warn_only_acknowledged, active_profile_id
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                settings.zone.value,
                int(settings.enabled),
                settings.violation_action.value,
                int(settings.warn_only_acknowledged),
                settings.active_profile_id,
            ),
        )
        self._connection.commit()

    def get_zone_settings(self, zone: ZoneKind) -> ZoneSettings | None:
        row = self._connection.execute(
            """
            SELECT zone, enabled, violation_action,
                   warn_only_acknowledged, active_profile_id
            FROM zone_settings
            WHERE zone = ?
            """,
            (zone.value,),
        ).fetchone()
        if row is None:
            return None
        return ZoneSettings(
            zone=ZoneKind(row["zone"]),
            enabled=bool(row["enabled"]),
            violation_action=ViolationAction(row["violation_action"]),
            warn_only_acknowledged=bool(row["warn_only_acknowledged"]),
            active_profile_id=row["active_profile_id"],
        )

    def add_managed_app(self, app: ManagedApp) -> None:
        try:
            self._connection.execute(
                """
                INSERT INTO managed_apps(id, zone, exe_path, match_key, display_name)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    app.id,
                    app.zone.value,
                    app.exe_path,
                    app.match_key,
                    app.display_name,
                ),
            )
            self._connection.commit()
        except sqlite3.IntegrityError as exc:
            raise ValueError("application is already managed") from exc

    def find_managed_app(self, exe_path: str) -> ManagedApp | None:
        match_key = ManagedApp(
            id="match",
            zone=ZoneKind.VPN,
            exe_path=exe_path,
            display_name="match",
        ).match_key
        row = self._connection.execute(
            """
            SELECT id, zone, exe_path, display_name
            FROM managed_apps
            WHERE match_key = ?
            """,
            (match_key,),
        ).fetchone()
        if row is None:
            return None
        return ManagedApp(
            id=row["id"],
            zone=ZoneKind(row["zone"]),
            exe_path=row["exe_path"],
            display_name=row["display_name"],
        )
```

- [ ] **Step 5: Run tests to verify they pass**

Run:

```powershell
python -m pytest tests/storage/test_repository.py -q
```

Expected:

```text
4 passed
```

- [ ] **Step 6: Commit repository**

```powershell
git add src/vpn_sandbox/storage tests/storage/test_repository.py
git commit -m "feat: add SQLite settings repository"
```

## Task 5: Structured Event Journal

**Files:**
- Create: `tests/events/test_journal.py`
- Create: `src/vpn_sandbox/events/journal.py`

- [ ] **Step 1: Write failing journal tests**

Write `tests/events/test_journal.py`:

```python
from pathlib import Path

from vpn_sandbox.events.journal import EventJournal, EventRecord, mask_ip


def test_mask_ip_hides_last_octet():
    assert mask_ip("203.0.113.10") == "203.0.113.x"
    assert mask_ip("not-an-ip") == "not-an-ip"


def test_event_journal_appends_and_reads_recent_events(tmp_path: Path):
    journal = EventJournal(tmp_path / "events.jsonl")
    journal.append(
        EventRecord(
            timestamp="2026-06-12T10:00:00Z",
            level="warning",
            zone="vpn",
            app="Chrome",
            reason="VPN country mismatch",
            details={"external_ip": "203.0.113.10"},
        )
    )

    events = journal.read_recent(limit=10)

    assert len(events) == 1
    assert events[0].details["external_ip"] == "203.0.113.x"
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```powershell
python -m pytest tests/events/test_journal.py -q
```

Expected: FAIL with `ModuleNotFoundError: No module named 'vpn_sandbox.events.journal'`.

- [ ] **Step 3: Implement event journal**

Write `src/vpn_sandbox/events/journal.py`:

```python
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
    masked: dict[str, Any] = {}
    for key, value in details.items():
        if key.endswith("_ip") and isinstance(value, str):
            masked[key] = mask_ip(value)
        else:
            masked[key] = value
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
    def from_json_line(cls, line: str) -> "EventRecord":
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
        if not self._path.exists():
            return []
        lines = self._path.read_text(encoding="utf-8").splitlines()
        selected = lines[-limit:]
        return [EventRecord.from_json_line(line) for line in selected if line.strip()]
```

- [ ] **Step 4: Run tests to verify they pass**

Run:

```powershell
python -m pytest tests/events/test_journal.py -q
```

Expected:

```text
2 passed
```

- [ ] **Step 5: Commit journal**

```powershell
git add src/vpn_sandbox/events/journal.py tests/events/test_journal.py
git commit -m "feat: add structured event journal"
```

## Task 6: IPC Message Contracts

**Files:**
- Create: `tests/ipc/test_messages.py`
- Create: `src/vpn_sandbox/ipc/messages.py`

- [ ] **Step 1: Write failing IPC serialization tests**

Write `tests/ipc/test_messages.py`:

```python
from vpn_sandbox.core.models import ZoneStatus
from vpn_sandbox.ipc.messages import ServiceCommand, ServiceStatus, ZoneRuntimeStatus


def test_service_command_round_trips_json():
    command = ServiceCommand(
        name="evaluate_start",
        payload={"exe_path": "C:/Apps/browser.exe"},
    )

    assert ServiceCommand.from_json(command.to_json()) == command


def test_service_status_round_trips_json():
    status = ServiceStatus(
        control_available=True,
        service_running=True,
        zones={
            "vpn": ZoneRuntimeStatus(
                status=ZoneStatus.OK,
                reason="VPN profile matched",
            )
        },
    )

    loaded = ServiceStatus.from_json(status.to_json())

    assert loaded == status
    assert loaded.zones["vpn"].status == ZoneStatus.OK
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```powershell
python -m pytest tests/ipc/test_messages.py -q
```

Expected: FAIL with `ModuleNotFoundError: No module named 'vpn_sandbox.ipc.messages'`.

- [ ] **Step 3: Implement IPC messages**

Write `src/vpn_sandbox/ipc/messages.py`:

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run:

```powershell
python -m pytest tests/ipc/test_messages.py -q
```

Expected:

```text
2 passed
```

- [ ] **Step 5: Commit IPC messages**

```powershell
git add src/vpn_sandbox/ipc/messages.py tests/ipc/test_messages.py
git commit -m "feat: add service IPC message contracts"
```

## Task 7: Service Simulator

**Files:**
- Create: `tests/ipc/test_service_simulator.py`
- Create: `src/vpn_sandbox/ipc/service_simulator.py`

- [ ] **Step 1: Write failing service simulator tests**

Write `tests/ipc/test_service_simulator.py`:

```python
from pathlib import Path

from vpn_sandbox.core.models import (
    Confidence,
    ManagedApp,
    ViolationAction,
    VpnProfile,
    ZoneKind,
    ZoneSettings,
    ZoneStatus,
)
from vpn_sandbox.core.policy import NetworkSnapshot
from vpn_sandbox.ipc.service_simulator import ServiceSimulator
from vpn_sandbox.storage.repository import Repository


def make_repo(tmp_path: Path) -> Repository:
    repo = Repository.connect(tmp_path / "settings.sqlite3")
    repo.initialize()
    repo.save_vpn_profile(
        VpnProfile(
            id="vpn-1",
            country_code="DE",
            country_name="Германия",
            city="Frankfurt",
            external_ip="203.0.113.10",
            protocol="WireGuard",
            client_name="Amnezia",
            confidence=Confidence.CERTAIN,
        )
    )
    repo.save_zone_settings(
        ZoneSettings(
            zone=ZoneKind.VPN,
            enabled=True,
            violation_action=ViolationAction.CLOSE_AFTER_20,
            warn_only_acknowledged=False,
            active_profile_id="vpn-1",
        )
    )
    repo.add_managed_app(
        ManagedApp(
            id="app-1",
            zone=ZoneKind.VPN,
            exe_path="C:/Apps/browser.exe",
            display_name="Browser",
        )
    )
    return repo


def test_simulator_allows_unmanaged_apps(tmp_path: Path):
    simulator = ServiceSimulator(make_repo(tmp_path))
    snapshot = NetworkSnapshot(
        control_available=True,
        vpn_detected=False,
        country_code=None,
        direct_route_confirmed=True,
        geo_ip_available=True,
    )

    decision = simulator.evaluate_start("C:/Other/tool.exe", snapshot)

    assert decision.can_start is True
    assert decision.status == ZoneStatus.OK
    assert decision.reason == "Application is not managed"


def test_simulator_blocks_managed_vpn_app_on_wrong_country(tmp_path: Path):
    simulator = ServiceSimulator(make_repo(tmp_path))
    snapshot = NetworkSnapshot(
        control_available=True,
        vpn_detected=True,
        country_code="NL",
        direct_route_confirmed=False,
        geo_ip_available=True,
    )

    decision = simulator.evaluate_start("c:\\apps\\browser.exe", snapshot)

    assert decision.can_start is False
    assert decision.status == ZoneStatus.BLOCKED
    assert decision.reason == "VPN country mismatch"
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```powershell
python -m pytest tests/ipc/test_service_simulator.py -q
```

Expected: FAIL with `ModuleNotFoundError: No module named 'vpn_sandbox.ipc.service_simulator'`.

- [ ] **Step 3: Implement service simulator**

Write `src/vpn_sandbox/ipc/service_simulator.py`:

```python
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

        return evaluate_direct_zone(settings, None, snapshot)
```

- [ ] **Step 4: Run tests to verify they pass**

Run:

```powershell
python -m pytest tests/ipc/test_service_simulator.py -q
```

Expected:

```text
2 passed
```

- [ ] **Step 5: Commit service simulator**

```powershell
git add src/vpn_sandbox/ipc/service_simulator.py tests/ipc/test_service_simulator.py
git commit -m "feat: add local service simulator"
```

## Task 8: CLI Doctor Smoke Check

**Files:**
- Create: `tests/test_cli.py`
- Create: `src/vpn_sandbox/__main__.py`

- [ ] **Step 1: Write failing CLI tests**

Write `tests/test_cli.py`:

```python
from vpn_sandbox.__main__ import build_doctor_payload, main


def test_build_doctor_payload_reports_core_status():
    payload = build_doctor_payload()

    assert payload["app"] == "vpn-sandbox"
    assert payload["core"] == "ok"
    assert payload["storage_schema"] == 1


def test_main_doctor_prints_json(capsys):
    exit_code = main(["doctor"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert '"app": "vpn-sandbox"' in captured.out
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```powershell
python -m pytest tests/test_cli.py -q
```

Expected: FAIL with `ModuleNotFoundError: No module named 'vpn_sandbox.__main__'`.

- [ ] **Step 3: Implement CLI doctor command**

Write `src/vpn_sandbox/__main__.py`:

```python
from __future__ import annotations

import argparse
import json
from collections.abc import Sequence

from vpn_sandbox import __version__
from vpn_sandbox.storage.schema import SCHEMA_VERSION


def build_doctor_payload() -> dict[str, str | int]:
    return {
        "app": "vpn-sandbox",
        "version": __version__,
        "core": "ok",
        "storage_schema": SCHEMA_VERSION,
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="vpn-sandbox")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("doctor")
    args = parser.parse_args(argv)

    if args.command == "doctor":
        print(json.dumps(build_doctor_payload(), ensure_ascii=False, sort_keys=True))
        return 0

    return 2


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run CLI tests**

Run:

```powershell
python -m pytest tests/test_cli.py -q
```

Expected:

```text
2 passed
```

- [ ] **Step 5: Run full test suite**

Run:

```powershell
python -m pytest
```

Expected:

```text
23 passed
```

- [ ] **Step 6: Run CLI manually**

Run:

```powershell
$env:PYTHONPATH = "src"
python -m vpn_sandbox doctor
```

Expected output contains:

```json
{"app": "vpn-sandbox", "core": "ok", "storage_schema": 1, "version": "0.1.0"}
```

- [ ] **Step 7: Commit CLI doctor**

```powershell
git add src/vpn_sandbox/__main__.py tests/test_cli.py
git commit -m "feat: add foundation doctor command"
```

## Task 9: Foundation Verification

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Add foundation verification commands to README**

Replace `README.md` with:

```markdown
# Песочница VPN

`vpn-sandbox` is the technical project name for a Windows VPN control application.

The first implementation slice contains the Python foundation:

- domain models for VPN and direct zones;
- policy evaluation;
- SQLite persistence;
- structured event journal;
- IPC message contracts;
- a local service simulator for tests and early UI development.

The approved product design lives in `docs/superpowers/specs/2026-06-12-vpn-sandbox-design.md`.

## Foundation Checks

Run the test suite:

```powershell
python -m pytest
```

Run the smoke check:

```powershell
$env:PYTHONPATH = "src"
python -m vpn_sandbox doctor
```
````

- [ ] **Step 2: Run full verification**

Run:

```powershell
python -m pytest
$env:PYTHONPATH = "src"
python -m vpn_sandbox doctor
git status --short
```

Expected:

```text
23 passed
{"app": "vpn-sandbox", "core": "ok", "storage_schema": 1, "version": "0.1.0"}
```

`git status --short` should show only the README change before the commit.

- [ ] **Step 3: Commit README verification notes**

```powershell
git add README.md
git commit -m "docs: document foundation verification"
```

## Plan Self-Review Notes

Spec coverage in this foundation plan:

- Product modes and zone concepts: covered by `OperatingMode`, `ZoneKind`, `ZoneSettings`, and policy tests.
- VPN country as strict condition: covered by `VpnProfile.country_code` and VPN policy tests.
- City as informational marker: covered by `VpnProfile.city`; no policy logic uses city.
- Warn-only risk acknowledgement: covered by `ZoneSettings.is_warn_only_allowed`.
- One `.exe` in one zone: covered by repository unique `match_key`.
- SQLite settings foundation: covered by repository and schema.
- Event visibility: covered by JSONL event journal.
- IPC contract: covered by DTO serialization tests.
- Service source of truth: represented by the service simulator.

Requirements intentionally outside this plan:

- Real WFP/network enforcement.
- Real Windows service process.
- PyQt6 UI.
- Tray and mini-indicator.
- Installer and Start Menu integration.
- Real geo-IP/update/report endpoints.
- VPN protocol detection adapters.

Those items need their own plans because they are independent, risk-heavy subsystems.
