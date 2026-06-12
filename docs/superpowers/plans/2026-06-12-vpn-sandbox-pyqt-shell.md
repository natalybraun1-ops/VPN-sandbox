# PyQt6 Application Shell Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build Stage 1 of "Песочница VPN": a real PyQt6 desktop application shell that lets the user choose the first-run scenario, view and edit zone/profile/app settings, read the event journal, use tray actions, and show a compact mini-indicator while still relying on the local `ServiceSimulator`.

**Architecture:** Keep the existing foundation as the source of truth and add a thin application/controller layer between SQLite and PyQt6 widgets. PyQt widgets should not talk to SQLite directly; they call an `AppController` that owns repository operations, event loading, and simulator-backed status evaluation. This sprint deliberately does not implement Windows service, WFP, real process interception, real VPN detection, or installer behavior.

**Tech Stack:** Python 3.13-compatible code, PyQt6, stdlib `sqlite3`, stdlib `pathlib`, existing `vpn_sandbox` domain/storage/events/ipc foundation, `pytest`, Qt offscreen smoke tests.

---

## Scope Check

Source roadmap: `docs/handoff/global-roadmap.md`.

The next global step after `Этап 0. Python Foundation` is `Этап 1. PyQt6 Application Shell`.

This sprint includes:

- PyQt6 dependency and GUI entry point;
- persistent first-run scenario selection;
- main window with dashboard, zones, profiles, managed apps, journal, and diagnostics tabs;
- zone settings editing through the existing `ZoneSettings` model;
- manual profile CRUD sufficient for UI work before real calibration exists;
- managed app list/add/remove through repository methods;
- event journal view backed by `EventJournal`;
- tray menu and mini-indicator;
- controller/view-model tests plus basic offscreen Qt smoke tests.

This sprint does not include:

- Windows service;
- WFP/native networking;
- process launch interception;
- automatic VPN/protocol detection;
- geo-IP endpoint;
- installer;
- real update/report submission.

## File Structure

Modify these existing files:

```text
pyproject.toml
README.md
src/vpn_sandbox/__main__.py
src/vpn_sandbox/storage/schema.py
src/vpn_sandbox/storage/repository.py
tests/storage/test_repository.py
```

Create these new files:

```text
src/vpn_sandbox/app/
  __init__.py
  bootstrap.py
  controller.py
  ids.py
  paths.py

src/vpn_sandbox/ui/
  __init__.py
  app.py
  first_run.py
  main_window.py
  mini_indicator.py
  text.py
  tray.py
  view_models.py
  widgets.py

tests/app/
  test_bootstrap.py
  test_controller.py

tests/ui/
  test_view_models.py
  test_qt_smoke.py
```

Responsibilities:

- `app/paths.py`: app data path resolution, using `VPN_SANDBOX_DATA_DIR` for tests and `%ProgramData%\VPN Sandbox` on Windows.
- `app/bootstrap.py`: open SQLite, initialize schema, create event journal, return an `AppContext`.
- `app/controller.py`: pure application operations used by PyQt: first-run mode, zone settings, profiles, managed apps, dashboard state, journal events, simulator status.
- `app/ids.py`: small deterministic ID factory abstraction for tests.
- `ui/text.py`: Russian labels for enum values and user-facing status text.
- `ui/view_models.py`: pure formatting from controller/domain objects into UI-friendly cards, rows, and event lines.
- `ui/widgets.py`: reusable Qt widgets for status badges, form rows, profile/app tables.
- `ui/first_run.py`: first-run scenario dialog.
- `ui/main_window.py`: main application window and tabs.
- `ui/tray.py`: tray icon/menu controller.
- `ui/mini_indicator.py`: always-on-top compact status window.
- `ui/app.py`: PyQt application entry point.

## Task 1: Prepare GUI Dependency And Entry Points

**Files:**
- Modify: `pyproject.toml`
- Modify: `src/vpn_sandbox/__main__.py`
- Create: `src/vpn_sandbox/ui/__init__.py`
- Create: `src/vpn_sandbox/ui/app.py`
- Test: `tests/ui/test_qt_smoke.py`

- [ ] **Step 1: Add PyQt6 dependency and scripts**

Update `pyproject.toml` so `[project]` has a runtime dependency and scripts:

```toml
dependencies = [
  "PyQt6>=6.7",
]

[project.scripts]
vpn-sandbox = "vpn_sandbox.__main__:main"
vpn-sandbox-ui = "vpn_sandbox.ui.app:main"
```

Keep the existing `[project.optional-dependencies]` `dev` section with `pytest`.

- [ ] **Step 2: Create a failing Qt smoke test**

Create `tests/ui/test_qt_smoke.py`:

```python
import os

import pytest

pytest.importorskip("PyQt6")

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


def test_create_qapplication_returns_single_instance():
    from PyQt6.QtWidgets import QApplication
    from vpn_sandbox.ui.app import create_qapplication

    app = create_qapplication([])

    assert app is QApplication.instance()
    assert app.applicationName() == "Песочница VPN"
```

- [ ] **Step 3: Run the focused failing test**

Run:

```powershell
python -m pytest tests/ui/test_qt_smoke.py -q
```

Expected: FAIL with `ModuleNotFoundError: No module named 'vpn_sandbox.ui'`.

- [ ] **Step 4: Implement the GUI entry point**

Create `src/vpn_sandbox/ui/__init__.py`:

```python
"""PyQt6 user interface for VPN Sandbox."""
```

Create `src/vpn_sandbox/ui/app.py`:

```python
from __future__ import annotations

import sys
from collections.abc import Sequence

from PyQt6.QtWidgets import QApplication


def create_qapplication(argv: Sequence[str] | None = None) -> QApplication:
    existing = QApplication.instance()
    if existing is not None:
        return existing
    app = QApplication(list(argv or []))
    app.setApplicationName("Песочница VPN")
    app.setOrganizationName("VPN Sandbox")
    return app


def main(argv: Sequence[str] | None = None) -> int:
    app = create_qapplication(sys.argv[:1] if argv is None else argv)
    from vpn_sandbox.app.bootstrap import open_app_context
    from vpn_sandbox.ui.first_run import FirstRunDialog
    from vpn_sandbox.ui.main_window import MainWindow
    from vpn_sandbox.ui.tray import TrayController

    context = open_app_context()
    if context.controller.get_operating_mode() is None:
        dialog = FirstRunDialog()
        if dialog.exec() != dialog.DialogCode.Accepted:
            context.close()
            return 0
        context.controller.configure_mode(dialog.selected_mode())

    window = MainWindow(context.controller)
    tray = TrayController(window)
    tray.show()
    window.show()
    exit_code = app.exec()
    context.close()
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 5: Update CLI to expose GUI launch**

Modify `src/vpn_sandbox/__main__.py` so it keeps the existing `doctor` command and adds:

```python
subparsers.add_parser("ui")
```

Then handle it:

```python
if args.command == "ui":
    from vpn_sandbox.ui.app import main as ui_main

    return ui_main([])
```

- [ ] **Step 6: Verify focused test**

Run:

```powershell
python -m pytest tests/ui/test_qt_smoke.py -q
```

Expected:

```text
1 passed
```

- [ ] **Step 7: Commit dependency and entry point**

```powershell
git add pyproject.toml src/vpn_sandbox/__main__.py src/vpn_sandbox/ui tests/ui/test_qt_smoke.py
git commit -m "feat: add PyQt6 application entry point"
```

## Task 2: Extend Storage For UI Shell State

**Files:**
- Modify: `src/vpn_sandbox/storage/schema.py`
- Modify: `src/vpn_sandbox/storage/repository.py`
- Modify: `tests/storage/test_repository.py`

- [ ] **Step 1: Write failing repository tests**

Append these tests to `tests/storage/test_repository.py`:

```python
from vpn_sandbox.core.models import OperatingMode


def test_repository_round_trips_operating_mode(tmp_path: Path):
    repo = Repository.connect(tmp_path / "settings.sqlite3")
    repo.initialize()

    assert repo.get_operating_mode() is None

    repo.save_operating_mode(OperatingMode.DUAL_ZONE)

    assert repo.get_operating_mode() == OperatingMode.DUAL_ZONE


def test_repository_lists_managed_apps_by_zone(tmp_path: Path):
    repo = Repository.connect(tmp_path / "settings.sqlite3")
    repo.initialize()
    vpn_app = ManagedApp(
        id="app-vpn",
        zone=ZoneKind.VPN,
        exe_path="C:/Apps/browser.exe",
        display_name="Browser",
    )
    direct_app = ManagedApp(
        id="app-direct",
        zone=ZoneKind.DIRECT,
        exe_path="C:/Apps/editor.exe",
        display_name="Editor",
    )

    repo.add_managed_app(vpn_app)
    repo.add_managed_app(direct_app)

    assert repo.list_managed_apps() == [direct_app, vpn_app]
    assert repo.list_managed_apps(ZoneKind.VPN) == [vpn_app]
    assert repo.list_managed_apps(ZoneKind.DIRECT) == [direct_app]


def test_repository_deletes_managed_app(tmp_path: Path):
    repo = Repository.connect(tmp_path / "settings.sqlite3")
    repo.initialize()
    app = ManagedApp(
        id="app-1",
        zone=ZoneKind.VPN,
        exe_path="C:/Apps/browser.exe",
        display_name="Browser",
    )
    repo.add_managed_app(app)

    repo.delete_managed_app(app.id)

    assert repo.list_managed_apps() == []
    assert repo.find_managed_app(app.exe_path) is None


def test_repository_deletes_profiles(tmp_path: Path):
    repo = Repository.connect(tmp_path / "settings.sqlite3")
    repo.initialize()
    vpn_profile = VpnProfile(
        id="vpn-1",
        country_code="DE",
        country_name="Германия",
        city="Frankfurt",
        external_ip="203.0.113.10",
        protocol="WireGuard",
        client_name="Amnezia",
        confidence=Confidence.CERTAIN,
    )
    direct_profile = DirectProfile(
        id="direct-1",
        interface_name="Ethernet",
        gateway=None,
        dns_servers=("1.1.1.1",),
    )
    repo.save_vpn_profile(vpn_profile)
    repo.save_direct_profile(direct_profile)

    repo.delete_vpn_profile(vpn_profile.id)
    repo.delete_direct_profile(direct_profile.id)

    assert repo.list_vpn_profiles() == []
    assert repo.list_direct_profiles() == []
```

- [ ] **Step 2: Run the focused failing tests**

Run:

```powershell
python -m pytest tests/storage/test_repository.py -q
```

Expected: FAIL because `get_operating_mode`, `save_operating_mode`, `list_managed_apps`, `delete_managed_app`, `delete_vpn_profile`, and `delete_direct_profile` are not defined.

- [ ] **Step 3: Add schema table for app settings**

Modify `src/vpn_sandbox/storage/schema.py`:

```python
SCHEMA_VERSION = 2
```

Add this table to `DDL` before `vpn_profiles`:

```sql
CREATE TABLE IF NOT EXISTS app_settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
```

- [ ] **Step 4: Add repository methods**

Modify imports in `src/vpn_sandbox/storage/repository.py` to include `OperatingMode`.

Add these methods to `Repository`:

```python
    def save_operating_mode(self, mode: OperatingMode) -> None:
        self._connection.execute(
            "INSERT OR REPLACE INTO app_settings(key, value) VALUES('operating_mode', ?)",
            (mode.value,),
        )
        self._connection.commit()

    def get_operating_mode(self) -> OperatingMode | None:
        try:
            row = self._connection.execute(
                "SELECT value FROM app_settings WHERE key = 'operating_mode'"
            ).fetchone()
        except sqlite3.OperationalError as exc:
            if str(exc) != "no such table: app_settings":
                raise
            return None
        if row is None:
            return None
        return OperatingMode(row["value"])

    def list_managed_apps(self, zone: ZoneKind | None = None) -> list[ManagedApp]:
        if zone is None:
            rows = self._connection.execute(
                """
                SELECT id, zone, exe_path, display_name
                FROM managed_apps
                ORDER BY display_name, id
                """
            ).fetchall()
        else:
            rows = self._connection.execute(
                """
                SELECT id, zone, exe_path, display_name
                FROM managed_apps
                WHERE zone = ?
                ORDER BY display_name, id
                """,
                (zone.value,),
            ).fetchall()
        return [
            ManagedApp(
                id=row["id"],
                zone=ZoneKind(row["zone"]),
                exe_path=row["exe_path"],
                display_name=row["display_name"],
            )
            for row in rows
        ]

    def delete_managed_app(self, app_id: str) -> None:
        self._connection.execute("DELETE FROM managed_apps WHERE id = ?", (app_id,))
        self._connection.commit()

    def delete_vpn_profile(self, profile_id: str) -> None:
        self._connection.execute("DELETE FROM vpn_profiles WHERE id = ?", (profile_id,))
        self._connection.commit()

    def delete_direct_profile(self, profile_id: str) -> None:
        self._connection.execute(
            "DELETE FROM direct_profiles WHERE id = ?",
            (profile_id,),
        )
        self._connection.commit()
```

- [ ] **Step 5: Verify repository tests**

Run:

```powershell
python -m pytest tests/storage/test_repository.py -q
```

Expected: all repository tests pass.

- [ ] **Step 6: Commit storage UI support**

```powershell
git add src/vpn_sandbox/storage tests/storage/test_repository.py
git commit -m "feat: extend repository for application shell"
```

## Task 3: Add Application Bootstrap And Paths

**Files:**
- Create: `src/vpn_sandbox/app/__init__.py`
- Create: `src/vpn_sandbox/app/paths.py`
- Create: `src/vpn_sandbox/app/bootstrap.py`
- Test: `tests/app/test_bootstrap.py`

- [ ] **Step 1: Write failing bootstrap tests**

Create `tests/app/test_bootstrap.py`:

```python
from pathlib import Path

from vpn_sandbox.app.bootstrap import open_app_context
from vpn_sandbox.app.paths import default_data_dir


def test_default_data_dir_uses_override(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("VPN_SANDBOX_DATA_DIR", str(tmp_path / "data"))

    assert default_data_dir() == tmp_path / "data"


def test_open_app_context_initializes_repository_and_journal(tmp_path: Path):
    context = open_app_context(tmp_path)

    assert context.repository.schema_version() == 2
    assert context.journal.read_recent(10) == []

    context.close()
```

- [ ] **Step 2: Run focused failing tests**

Run:

```powershell
python -m pytest tests/app/test_bootstrap.py -q
```

Expected: FAIL with `ModuleNotFoundError: No module named 'vpn_sandbox.app'`.

- [ ] **Step 3: Implement app package marker and path resolution**

Create `src/vpn_sandbox/app/__init__.py`:

```python
"""Application orchestration layer for VPN Sandbox."""
```

Create `src/vpn_sandbox/app/paths.py`:

```python
from __future__ import annotations

import os
from pathlib import Path


def default_data_dir() -> Path:
    override = os.environ.get("VPN_SANDBOX_DATA_DIR")
    if override:
        return Path(override)
    program_data = os.environ.get("PROGRAMDATA")
    if program_data:
        return Path(program_data) / "VPN Sandbox"
    return Path.home() / ".vpn-sandbox"
```

- [ ] **Step 4: Implement bootstrap context**

Create `src/vpn_sandbox/app/bootstrap.py`:

```python
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from vpn_sandbox.app.controller import AppController
from vpn_sandbox.app.paths import default_data_dir
from vpn_sandbox.events.journal import EventJournal
from vpn_sandbox.storage.repository import Repository


@dataclass
class AppContext:
    repository: Repository
    journal: EventJournal
    controller: AppController

    def close(self) -> None:
        self.repository.close()


def open_app_context(data_dir: Path | None = None) -> AppContext:
    root = data_dir or default_data_dir()
    repository = Repository.connect(root / "settings.sqlite3")
    repository.initialize()
    journal = EventJournal(root / "events.jsonl")
    controller = AppController(repository=repository, journal=journal)
    return AppContext(
        repository=repository,
        journal=journal,
        controller=controller,
    )
```

This imports `AppController` before it exists; the test still fails until Task 4 implements it.

- [ ] **Step 5: Commit bootstrap after Task 4 passes**

Do not commit this task until Task 4 also passes because `bootstrap.py` depends on `controller.py`.

## Task 4: Add Pure App Controller

**Files:**
- Create: `src/vpn_sandbox/app/ids.py`
- Create: `src/vpn_sandbox/app/controller.py`
- Test: `tests/app/test_controller.py`
- Test: `tests/app/test_bootstrap.py`

- [ ] **Step 1: Write failing controller tests**

Create `tests/app/test_controller.py`:

```python
from pathlib import Path

from vpn_sandbox.app.controller import AppController
from vpn_sandbox.core.models import (
    Confidence,
    OperatingMode,
    ViolationAction,
    VpnProfile,
    ZoneKind,
    ZoneStatus,
)
from vpn_sandbox.core.policy import NetworkSnapshot
from vpn_sandbox.events.journal import EventJournal
from vpn_sandbox.storage.repository import Repository


class SequentialIds:
    def __init__(self):
        self.count = 0

    def new_id(self, prefix: str) -> str:
        self.count += 1
        return f"{prefix}-{self.count}"


def make_controller(tmp_path: Path) -> AppController:
    repo = Repository.connect(tmp_path / "settings.sqlite3")
    repo.initialize()
    return AppController(
        repository=repo,
        journal=EventJournal(tmp_path / "events.jsonl"),
        ids=SequentialIds(),
    )


def test_configure_vpn_only_mode_enables_only_vpn_zone(tmp_path: Path):
    controller = make_controller(tmp_path)

    controller.configure_mode(OperatingMode.VPN_ONLY)

    assert controller.get_operating_mode() == OperatingMode.VPN_ONLY
    assert controller.repository.get_zone_settings(ZoneKind.VPN).enabled is True
    assert controller.repository.get_zone_settings(ZoneKind.DIRECT).enabled is False


def test_add_manual_app_persists_in_selected_zone(tmp_path: Path):
    controller = make_controller(tmp_path)
    controller.configure_mode(OperatingMode.DUAL_ZONE)

    app = controller.add_manual_app(
        zone=ZoneKind.VPN,
        exe_path="C:/Apps/browser.exe",
        display_name="Browser",
    )

    assert app.id == "app-1"
    assert controller.repository.list_managed_apps(ZoneKind.VPN) == [app]


def test_save_vpn_profile_sets_active_profile_when_requested(tmp_path: Path):
    controller = make_controller(tmp_path)
    controller.configure_mode(OperatingMode.VPN_ONLY)

    profile = controller.save_vpn_profile(
        country_code="DE",
        country_name="Германия",
        city="Frankfurt",
        external_ip="203.0.113.10",
        protocol="WireGuard",
        client_name="Amnezia",
        confidence=Confidence.CERTAIN,
        custom_name="Основной VPN",
        make_active=True,
    )

    settings = controller.repository.get_zone_settings(ZoneKind.VPN)
    assert profile.id == "vpn-1"
    assert settings.active_profile_id == profile.id


def test_dashboard_uses_service_simulator_for_zone_status(tmp_path: Path):
    controller = make_controller(tmp_path)
    controller.configure_mode(OperatingMode.VPN_ONLY)
    profile = VpnProfile(
        id="vpn-existing",
        country_code="DE",
        country_name="Германия",
        city=None,
        external_ip="203.0.113.10",
        protocol="WireGuard",
        client_name=None,
        confidence=Confidence.CERTAIN,
    )
    controller.repository.save_vpn_profile(profile)
    controller.repository.save_zone_settings(
        controller.repository.get_zone_settings(ZoneKind.VPN).__class__(
            zone=ZoneKind.VPN,
            enabled=True,
            violation_action=ViolationAction.CLOSE_AFTER_20,
            warn_only_acknowledged=False,
            active_profile_id=profile.id,
        )
    )
    controller.add_manual_app(
        zone=ZoneKind.VPN,
        exe_path="C:/Apps/browser.exe",
        display_name="Browser",
    )

    dashboard = controller.load_dashboard(
        NetworkSnapshot(
            control_available=True,
            vpn_detected=True,
            country_code="NL",
            direct_route_confirmed=False,
            geo_ip_available=True,
        )
    )

    assert dashboard.zones[ZoneKind.VPN].status == ZoneStatus.BLOCKED
    assert dashboard.zones[ZoneKind.VPN].reason == "VPN country mismatch"
```

- [ ] **Step 2: Run focused failing tests**

Run:

```powershell
python -m pytest tests/app -q
```

Expected: FAIL with missing `AppController`.

- [ ] **Step 3: Implement deterministic ID factory**

Create `src/vpn_sandbox/app/ids.py`:

```python
from __future__ import annotations

from uuid import uuid4


class UuidFactory:
    def new_id(self, prefix: str) -> str:
        return f"{prefix}-{uuid4().hex}"
```

- [ ] **Step 4: Implement controller models and operations**

Create `src/vpn_sandbox/app/controller.py`:

```python
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
            ZoneKind.DIRECT: mode in {OperatingMode.DIRECT_ONLY, OperatingMode.DUAL_ZONE},
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
        if settings is None or not settings.enabled:
            return PolicyDecision(
                status=ZoneStatus.DISABLED,
                can_start=True,
                reason="Zone disabled",
                action=ViolationAction.CLOSE_AFTER_20,
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
```

- [ ] **Step 5: Verify app tests**

Run:

```powershell
python -m pytest tests/app -q
```

Expected:

```text
6 passed
```

- [ ] **Step 6: Commit app controller and bootstrap**

```powershell
git add src/vpn_sandbox/app tests/app
git commit -m "feat: add application controller for UI shell"
```

## Task 5: Add Pure UI View Models And Text

**Files:**
- Create: `src/vpn_sandbox/ui/text.py`
- Create: `src/vpn_sandbox/ui/view_models.py`
- Test: `tests/ui/test_view_models.py`

- [ ] **Step 1: Write failing view-model tests**

Create `tests/ui/test_view_models.py`:

```python
from vpn_sandbox.app.controller import ZoneDashboard
from vpn_sandbox.core.models import ZoneKind, ZoneStatus
from vpn_sandbox.ui.text import status_label, zone_label
from vpn_sandbox.ui.view_models import build_zone_card


def test_text_labels_are_russian_and_user_facing():
    assert zone_label(ZoneKind.VPN) == "VPN-зона"
    assert zone_label(ZoneKind.DIRECT) == "Прямая зона"
    assert status_label(ZoneStatus.OK) == "Работает штатно"
    assert status_label(ZoneStatus.ATTENTION) == "Требует внимания"


def test_build_zone_card_formats_counts_and_profile_name():
    dashboard = ZoneDashboard(
        zone=ZoneKind.VPN,
        enabled=True,
        status=ZoneStatus.OK,
        reason="VPN profile matched",
        apps=(),
        active_profile_name="Германия · WireGuard",
    )

    card = build_zone_card(dashboard)

    assert card.title == "VPN-зона"
    assert card.status == "Работает штатно"
    assert card.profile == "Германия · WireGuard"
    assert card.app_count == "0 приложений"
```

- [ ] **Step 2: Run focused failing tests**

Run:

```powershell
python -m pytest tests/ui/test_view_models.py -q
```

Expected: FAIL with missing `vpn_sandbox.ui.text` or `vpn_sandbox.ui.view_models`.

- [ ] **Step 3: Implement labels**

Create `src/vpn_sandbox/ui/text.py`:

```python
from __future__ import annotations

from vpn_sandbox.core.models import ViolationAction, ZoneKind, ZoneStatus


def zone_label(zone: ZoneKind) -> str:
    return {
        ZoneKind.VPN: "VPN-зона",
        ZoneKind.DIRECT: "Прямая зона",
    }[zone]


def status_label(status: ZoneStatus) -> str:
    return {
        ZoneStatus.OK: "Работает штатно",
        ZoneStatus.ATTENTION: "Требует внимания",
        ZoneStatus.BLOCKED: "Заблокировано",
        ZoneStatus.DISABLED: "Отключено",
    }[status]


def violation_action_label(action: ViolationAction) -> str:
    return {
        ViolationAction.CLOSE_IMMEDIATELY: "Закрыть сразу",
        ViolationAction.CLOSE_AFTER_10: "Закрыть через 10 секунд",
        ViolationAction.CLOSE_AFTER_20: "Закрыть через 20 секунд",
        ViolationAction.CLOSE_AFTER_30: "Закрыть через 30 секунд",
        ViolationAction.WARN_ONLY: "Только предупреждать",
    }[action]
```

- [ ] **Step 4: Implement view models**

Create `src/vpn_sandbox/ui/view_models.py`:

```python
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
```

- [ ] **Step 5: Verify view-model tests**

Run:

```powershell
python -m pytest tests/ui/test_view_models.py -q
```

Expected:

```text
2 passed
```

- [ ] **Step 6: Commit view models**

```powershell
git add src/vpn_sandbox/ui/text.py src/vpn_sandbox/ui/view_models.py tests/ui/test_view_models.py
git commit -m "feat: add UI view models"
```

## Task 6: Implement First-Run Wizard

**Files:**
- Create: `src/vpn_sandbox/ui/first_run.py`
- Modify: `tests/ui/test_qt_smoke.py`

- [ ] **Step 1: Add failing wizard smoke test**

Append to `tests/ui/test_qt_smoke.py`:

```python
def test_first_run_dialog_defaults_to_dual_zone_mode():
    from vpn_sandbox.core.models import OperatingMode
    from vpn_sandbox.ui.first_run import FirstRunDialog

    dialog = FirstRunDialog()

    assert dialog.windowTitle() == "Первый запуск"
    assert dialog.selected_mode() == OperatingMode.DUAL_ZONE
```

- [ ] **Step 2: Run focused failing test**

Run:

```powershell
python -m pytest tests/ui/test_qt_smoke.py::test_first_run_dialog_defaults_to_dual_zone_mode -q
```

Expected: FAIL with missing `vpn_sandbox.ui.first_run`.

- [ ] **Step 3: Implement first-run dialog**

Create `src/vpn_sandbox/ui/first_run.py`:

```python
from __future__ import annotations

from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QRadioButton,
    QVBoxLayout,
)

from vpn_sandbox.core.models import OperatingMode


class FirstRunDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Первый запуск")
        self._vpn_only = QRadioButton("Только VPN-контроль")
        self._direct_only = QRadioButton("Только прямой обход VPN")
        self._dual_zone = QRadioButton("Две зоны")
        self._dual_zone.setChecked(True)

        form = QFormLayout()
        form.addRow(self._dual_zone)
        form.addRow(self._vpn_only)
        form.addRow(self._direct_only)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout()
        layout.addLayout(form)
        layout.addWidget(buttons)
        self.setLayout(layout)

    def selected_mode(self) -> OperatingMode:
        if self._vpn_only.isChecked():
            return OperatingMode.VPN_ONLY
        if self._direct_only.isChecked():
            return OperatingMode.DIRECT_ONLY
        return OperatingMode.DUAL_ZONE
```

- [ ] **Step 4: Verify wizard smoke test**

Run:

```powershell
python -m pytest tests/ui/test_qt_smoke.py -q
```

Expected: Qt smoke tests pass.

- [ ] **Step 5: Commit first-run wizard**

```powershell
git add src/vpn_sandbox/ui/first_run.py tests/ui/test_qt_smoke.py
git commit -m "feat: add first-run scenario dialog"
```

## Task 7: Implement Main Window Tabs

**Files:**
- Create: `src/vpn_sandbox/ui/widgets.py`
- Create: `src/vpn_sandbox/ui/main_window.py`
- Modify: `tests/ui/test_qt_smoke.py`

- [ ] **Step 1: Add failing main-window smoke test**

Append to `tests/ui/test_qt_smoke.py`:

```python
from pathlib import Path


def test_main_window_contains_expected_tabs(tmp_path: Path):
    from vpn_sandbox.app.bootstrap import open_app_context
    from vpn_sandbox.core.models import OperatingMode
    from vpn_sandbox.ui.main_window import MainWindow

    context = open_app_context(tmp_path)
    context.controller.configure_mode(OperatingMode.DUAL_ZONE)

    window = MainWindow(context.controller)

    assert window.windowTitle() == "Песочница VPN"
    assert [window.tabs.tabText(index) for index in range(window.tabs.count())] == [
        "Обзор",
        "Зоны",
        "Профили",
        "Приложения",
        "Журнал",
        "Диагностика",
    ]
    context.close()
```

- [ ] **Step 2: Run focused failing test**

Run:

```powershell
python -m pytest tests/ui/test_qt_smoke.py::test_main_window_contains_expected_tabs -q
```

Expected: FAIL with missing `vpn_sandbox.ui.main_window`.

- [ ] **Step 3: Implement reusable widgets**

Create `src/vpn_sandbox/ui/widgets.py`:

```python
from __future__ import annotations

from PyQt6.QtWidgets import QLabel, QTableWidget, QTableWidgetItem


class StatusBadge(QLabel):
    def __init__(self, text: str):
        super().__init__(text)
        self.setMinimumWidth(120)
        self.setStyleSheet(
            "QLabel { padding: 4px 8px; border: 1px solid #8a8a8a; border-radius: 4px; }"
        )


def set_table_rows(table: QTableWidget, rows: list[list[str]]) -> None:
    table.setRowCount(len(rows))
    for row_index, row in enumerate(rows):
        for column_index, value in enumerate(row):
            table.setItem(row_index, column_index, QTableWidgetItem(value))
```

- [ ] **Step 4: Implement main window**

Create `src/vpn_sandbox/ui/main_window.py` with these required elements:

```python
from __future__ import annotations

from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QTabWidget,
    QTableWidget,
    QVBoxLayout,
    QWidget,
)

from vpn_sandbox.app.controller import AppController
from vpn_sandbox.core.policy import NetworkSnapshot
from vpn_sandbox.ui.view_models import build_zone_card
from vpn_sandbox.ui.widgets import StatusBadge, set_table_rows


class MainWindow(QMainWindow):
    def __init__(self, controller: AppController):
        super().__init__()
        self.controller = controller
        self.setWindowTitle("Песочница VPN")
        self.resize(980, 640)
        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)
        self._dashboard_labels: list[QLabel] = []
        self._apps_table = QTableWidget(0, 3)
        self._journal_table = QTableWidget(0, 4)
        self._build_tabs()
        self.refresh()

    def _build_tabs(self) -> None:
        self.tabs.addTab(self._overview_tab(), "Обзор")
        self.tabs.addTab(self._zones_tab(), "Зоны")
        self.tabs.addTab(self._profiles_tab(), "Профили")
        self.tabs.addTab(self._apps_tab(), "Приложения")
        self.tabs.addTab(self._journal_tab(), "Журнал")
        self.tabs.addTab(self._diagnostics_tab(), "Диагностика")

    def _overview_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout()
        for _ in range(2):
            label = QLabel()
            label.setMinimumHeight(64)
            self._dashboard_labels.append(label)
            layout.addWidget(label)
        refresh = QPushButton("Обновить")
        refresh.clicked.connect(self.refresh)
        layout.addWidget(refresh)
        layout.addStretch()
        page.setLayout(layout)
        return page

    def _zones_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout()
        layout.addWidget(StatusBadge("Настройки зон"))
        layout.addWidget(QLabel("Реакции на нарушения и включение зон"))
        layout.addStretch()
        page.setLayout(layout)
        return page

    def _profiles_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout()
        layout.addWidget(QLabel("VPN-профили и прямые профили"))
        layout.addStretch()
        page.setLayout(layout)
        return page

    def _apps_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout()
        self._apps_table.setHorizontalHeaderLabels(["Зона", "Приложение", "Путь"])
        layout.addWidget(self._apps_table)
        page.setLayout(layout)
        return page

    def _journal_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout()
        self._journal_table.setHorizontalHeaderLabels(["Время", "Уровень", "Зона", "Причина"])
        layout.addWidget(self._journal_table)
        page.setLayout(layout)
        return page

    def _diagnostics_tab(self) -> QWidget:
        page = QWidget()
        layout = QHBoxLayout()
        layout.addWidget(QLabel("Локальный режим: активен"))
        layout.addWidget(QLabel("Сетевой контроль: не подключен"))
        layout.addWidget(QLabel("Служба Windows: не подключена"))
        page.setLayout(layout)
        return page

    def refresh(self) -> None:
        snapshot = NetworkSnapshot(
            control_available=True,
            vpn_detected=False,
            country_code=None,
            direct_route_confirmed=False,
            geo_ip_available=True,
        )
        dashboard = self.controller.load_dashboard(snapshot)
        for label, zone in zip(self._dashboard_labels, dashboard.zones.values()):
            card = build_zone_card(zone)
            label.setText(
                f"{card.title}: {card.status}\n"
                f"{card.profile}\n"
                f"{card.app_count} · {card.reason}"
            )
        app_rows = [
            [app.zone.value, app.display_name, app.exe_path]
            for zone in dashboard.zones.values()
            for app in zone.apps
        ]
        set_table_rows(self._apps_table, app_rows)
        event_rows = [
            [
                event.timestamp,
                event.level,
                event.zone or "",
                event.reason,
            ]
            for event in dashboard.events
        ]
        set_table_rows(self._journal_table, event_rows)
```

This is a functional shell. Rich profile/app editing is added in Tasks 8 and 9.

- [ ] **Step 5: Verify main-window smoke test**

Run:

```powershell
python -m pytest tests/ui/test_qt_smoke.py -q
```

Expected: all Qt smoke tests pass.

- [ ] **Step 6: Commit main window shell**

```powershell
git add src/vpn_sandbox/ui/main_window.py src/vpn_sandbox/ui/widgets.py tests/ui/test_qt_smoke.py
git commit -m "feat: add PyQt main window shell"
```

## Task 8: Wire Zone, Profile, And Managed App Actions

**Files:**
- Modify: `src/vpn_sandbox/ui/main_window.py`
- Modify: `src/vpn_sandbox/ui/widgets.py`
- Modify: `tests/ui/test_qt_smoke.py`

- [ ] **Step 1: Add smoke tests for action methods**

Append to `tests/ui/test_qt_smoke.py`:

```python
def test_main_window_adds_manual_app_from_action(tmp_path: Path):
    from vpn_sandbox.app.bootstrap import open_app_context
    from vpn_sandbox.core.models import OperatingMode, ZoneKind
    from vpn_sandbox.ui.main_window import MainWindow

    context = open_app_context(tmp_path)
    context.controller.configure_mode(OperatingMode.DUAL_ZONE)
    window = MainWindow(context.controller)

    window.add_manual_app_for_test(
        zone=ZoneKind.VPN,
        exe_path="C:/Apps/browser.exe",
        display_name="Browser",
    )

    assert context.repository.list_managed_apps(ZoneKind.VPN)[0].display_name == "Browser"
    context.close()
```

- [ ] **Step 2: Run focused failing test**

Run:

```powershell
python -m pytest tests/ui/test_qt_smoke.py::test_main_window_adds_manual_app_from_action -q
```

Expected: FAIL because `add_manual_app_for_test` does not exist.

- [ ] **Step 3: Add window action methods**

In `MainWindow`, add public action methods that the UI buttons and tests can call:

```python
    def add_manual_app_for_test(
        self,
        zone,
        exe_path: str,
        display_name: str,
    ) -> None:
        self.controller.add_manual_app(
            zone=zone,
            exe_path=exe_path,
            display_name=display_name,
        )
        self.refresh()
```

Add real button handlers in `_apps_tab()`:

```python
        add_button = QPushButton("Добавить вручную")
        add_button.clicked.connect(self._show_add_app_dialog)
        layout.addWidget(add_button)
```

Add the required imports:

```python
from pathlib import Path

from PyQt6.QtWidgets import QFileDialog, QInputDialog, QMessageBox
from vpn_sandbox.core.models import ZoneKind
```

Add `_show_add_app_dialog()` with `QFileDialog.getOpenFileName`, `QInputDialog.getItem` for zone, and display name from the selected `.exe` stem:

```python
    def _show_add_app_dialog(self) -> None:
        file_name, _ = QFileDialog.getOpenFileName(
            self,
            "Выберите приложение",
            "",
            "Windows applications (*.exe)",
        )
        if not file_name:
            return
        zone_label, accepted = QInputDialog.getItem(
            self,
            "Зона",
            "Куда добавить приложение",
            ["VPN-зона", "Прямая зона"],
            0,
            False,
        )
        if not accepted:
            return
        zone = ZoneKind.VPN if zone_label == "VPN-зона" else ZoneKind.DIRECT
        try:
            self.add_manual_app_for_test(
                zone=zone,
                exe_path=file_name,
                display_name=Path(file_name).stem,
            )
        except ValueError:
            QMessageBox.warning(
                self,
                "Приложение уже добавлено",
                "Это приложение уже добавлено в одну из зон. "
                "Удалите его из текущей зоны, чтобы добавить в другую.",
            )
```

On duplicate app, the user sees:

```text
Это приложение уже добавлено в одну из зон. Удалите его из текущей зоны, чтобы добавить в другую.
```

- [ ] **Step 4: Add profile action methods**

Add these methods to `MainWindow`:

```python
    def save_vpn_profile_for_test(
        self,
        country_code: str,
        country_name: str,
        city: str | None,
        external_ip: str,
        protocol: str | None,
        client_name: str | None,
        custom_name: str | None,
        make_active: bool = True,
    ) -> None:
        from vpn_sandbox.core.models import Confidence

        self.controller.save_vpn_profile(
            country_code=country_code,
            country_name=country_name,
            city=city,
            external_ip=external_ip,
            protocol=protocol,
            client_name=client_name,
            confidence=Confidence.CERTAIN,
            custom_name=custom_name,
            make_active=make_active,
        )
        self.refresh()

    def save_direct_profile_for_test(
        self,
        interface_name: str,
        gateway: str | None,
        dns_servers: tuple[str, ...],
        custom_name: str | None,
        make_active: bool = True,
    ) -> None:
        self.controller.save_direct_profile(
            interface_name=interface_name,
            gateway=gateway,
            dns_servers=dns_servers,
            custom_name=custom_name,
            make_active=make_active,
        )
        self.refresh()
```

The GUI buttons in the profiles tab should collect the same values with `QInputDialog` and call these methods.

- [ ] **Step 5: Verify Qt smoke tests**

Run:

```powershell
python -m pytest tests/ui/test_qt_smoke.py -q
```

Expected: all Qt smoke tests pass.

- [ ] **Step 6: Commit UI actions**

```powershell
git add src/vpn_sandbox/ui tests/ui/test_qt_smoke.py
git commit -m "feat: wire UI actions to application controller"
```

## Task 9: Add Tray And Mini Indicator

**Files:**
- Create: `src/vpn_sandbox/ui/tray.py`
- Create: `src/vpn_sandbox/ui/mini_indicator.py`
- Modify: `tests/ui/test_qt_smoke.py`

- [ ] **Step 1: Add failing smoke tests**

Append to `tests/ui/test_qt_smoke.py`:

```python
def test_mini_indicator_can_update_status_text():
    from vpn_sandbox.core.models import ZoneStatus
    from vpn_sandbox.ui.mini_indicator import MiniIndicator

    indicator = MiniIndicator()
    indicator.update_status(ZoneStatus.ATTENTION, "Требует внимания")

    assert "Требует внимания" in indicator.status_text()


def test_tray_controller_builds_menu(tmp_path: Path):
    from vpn_sandbox.app.bootstrap import open_app_context
    from vpn_sandbox.core.models import OperatingMode
    from vpn_sandbox.ui.main_window import MainWindow
    from vpn_sandbox.ui.tray import TrayController

    context = open_app_context(tmp_path)
    context.controller.configure_mode(OperatingMode.DUAL_ZONE)
    window = MainWindow(context.controller)
    tray = TrayController(window)

    assert tray.menu_action_texts() == [
        "Открыть",
        "Показать мини-индикатор",
        "Открыть журнал",
        "Выход",
    ]
    context.close()
```

- [ ] **Step 2: Run focused failing tests**

Run:

```powershell
python -m pytest tests/ui/test_qt_smoke.py::test_mini_indicator_can_update_status_text tests/ui/test_qt_smoke.py::test_tray_controller_builds_menu -q
```

Expected: FAIL with missing modules.

- [ ] **Step 3: Implement mini indicator**

Create `src/vpn_sandbox/ui/mini_indicator.py`:

```python
from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QLabel, QVBoxLayout, QWidget

from vpn_sandbox.core.models import ZoneStatus


class MiniIndicator(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Песочница VPN")
        self.setWindowFlags(
            Qt.WindowType.Tool
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.WindowCloseButtonHint
        )
        self._label = QLabel("Статус зон")
        layout = QVBoxLayout()
        layout.addWidget(self._label)
        self.setLayout(layout)
        self.resize(220, 80)

    def update_status(self, status: ZoneStatus, text: str) -> None:
        self._label.setText(f"{text} · {status.value}")

    def status_text(self) -> str:
        return self._label.text()
```

- [ ] **Step 4: Implement tray controller**

Create `src/vpn_sandbox/ui/tray.py`:

```python
from __future__ import annotations

from PyQt6.QtGui import QAction, QIcon
from PyQt6.QtWidgets import QMenu, QSystemTrayIcon

from vpn_sandbox.ui.main_window import MainWindow
from vpn_sandbox.ui.mini_indicator import MiniIndicator


class TrayController:
    def __init__(self, window: MainWindow):
        self.window = window
        self.indicator = MiniIndicator()
        self.menu = QMenu()
        self._open = QAction("Открыть")
        self._mini = QAction("Показать мини-индикатор")
        self._journal = QAction("Открыть журнал")
        self._quit = QAction("Выход")
        self._open.triggered.connect(self.window.show)
        self._mini.triggered.connect(self.indicator.show)
        self._journal.triggered.connect(lambda: self.window.tabs.setCurrentIndex(4))
        self._quit.triggered.connect(self.window.close)
        for action in (self._open, self._mini, self._journal, self._quit):
            self.menu.addAction(action)
        self.tray = QSystemTrayIcon(QIcon(), self.window)
        self.tray.setToolTip("Песочница VPN")
        self.tray.setContextMenu(self.menu)

    def show(self) -> None:
        if QSystemTrayIcon.isSystemTrayAvailable():
            self.tray.show()

    def menu_action_texts(self) -> list[str]:
        return [action.text() for action in self.menu.actions()]
```

- [ ] **Step 5: Verify tray and mini indicator tests**

Run:

```powershell
python -m pytest tests/ui/test_qt_smoke.py -q
```

Expected: all Qt smoke tests pass.

- [ ] **Step 6: Commit tray and mini indicator**

```powershell
git add src/vpn_sandbox/ui/tray.py src/vpn_sandbox/ui/mini_indicator.py tests/ui/test_qt_smoke.py
git commit -m "feat: add tray and mini indicator"
```

## Task 10: Documentation And Manual Smoke

**Files:**
- Modify: `README.md`
- Modify: `docs/handoff/global-roadmap.md`

- [ ] **Step 1: Update README with UI commands**

Add this section to `README.md` after `Foundation Checks`:

````markdown
## UI Shell Checks

Run the PyQt6 application:

```powershell
python -m vpn_sandbox ui
```

For a local sandbox data directory:

```powershell
$env:VPN_SANDBOX_DATA_DIR = "$PWD\.local-data"
python -m vpn_sandbox ui
```

Run headless UI smoke tests:

```powershell
$env:QT_QPA_PLATFORM = "offscreen"
python -m pytest tests/ui -q
```
````

- [ ] **Step 2: Update roadmap status**

In `docs/handoff/global-roadmap.md`, change `Этап 1. PyQt6 Application Shell` after implementation to include:

```markdown
Статус: готово в ветке `codex/pyqt-shell`.
```

Do this only after the sprint implementation is finished and verified.

- [ ] **Step 3: Run full automated verification**

Run:

```powershell
$env:QT_QPA_PLATFORM = "offscreen"
python -m pytest -p no:cacheprovider --basetemp .pytest-tmp -q
$env:PYTHONPATH = "src"
python -m vpn_sandbox doctor
```

Expected:

```text
all tests pass
{"app": "vpn-sandbox", "core": "ok", "storage_schema": 2, "version": "0.1.0"}
```

- [ ] **Step 4: Run manual UI smoke**

Run:

```powershell
$env:VPN_SANDBOX_DATA_DIR = "$PWD\.local-data"
python -m vpn_sandbox ui
```

Manual acceptance:

- first-run dialog appears when no mode is stored;
- choosing "Две зоны" opens the main window;
- main window has tabs: `Обзор`, `Зоны`, `Профили`, `Приложения`, `Журнал`, `Диагностика`;
- adding a manual app shows it in `Приложения`;
- duplicate `.exe` shows the duplicate warning;
- tray menu is available when Windows exposes a system tray;
- mini-indicator opens and can be hidden;
- closing the app does not change unrelated user network settings.

- [ ] **Step 5: Commit docs**

```powershell
git add README.md docs/handoff/global-roadmap.md
git commit -m "docs: document PyQt application shell"
```

## Final Verification Checklist

- [ ] `python -m pytest -p no:cacheprovider --basetemp .pytest-tmp -q` passes.
- [ ] `$env:PYTHONPATH = "src"; python -m vpn_sandbox doctor` reports `storage_schema` as `2`.
- [ ] `$env:QT_QPA_PLATFORM = "offscreen"; python -m pytest tests/ui -q` passes.
- [ ] `$env:VPN_SANDBOX_DATA_DIR = "$PWD\.local-data"; python -m vpn_sandbox ui` opens the UI.
- [ ] `git status --short` shows only intended files before each commit.
- [ ] No Windows service, WFP, process interception, or geo-IP code is introduced in this sprint.

## Plan Self-Review Notes

Spec and roadmap coverage:

- First-run scenario selection: Task 6.
- Main window: Task 7.
- Zone settings surface: Tasks 4, 7, 8.
- Profile screens and manual profile state: Tasks 4, 8.
- Managed application list/add/remove: Tasks 2, 4, 8.
- Event journal view: Tasks 4, 7.
- Tray: Task 9.
- Mini-indicator: Task 9.
- UI uses local `ServiceSimulator`: Task 4.
- No Windows service/WFP dependency: enforced in Scope Check and Final Verification Checklist.

Deliberate sprint boundary:

- Calibration and detection remain for `Этап 2. Calibration And Detection`.
- Local IPC/background agent remains for `Этап 3. Local IPC And Background Agent`.
- Real process control remains for `Этап 4. Process Control`.
- Native network control remains for `Этап 5. Native Network Control`.
