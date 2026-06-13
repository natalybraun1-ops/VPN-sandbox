# Песочница VPN

`vpn-sandbox` is the technical project name for a Windows VPN control application.

Current branch status: Stage 0 foundation and Stage 1 PyQt6 application shell
are implemented. The app is still a local prototype: it uses SQLite,
JSONL event logs and a local `ServiceSimulator`; it does not yet include real
VPN calibration/detection, Windows service, WFP/native networking, installer or
process enforcement.

Implemented foundation:

- domain models for VPN and direct zones;
- policy evaluation;
- SQLite persistence;
- structured event journal;
- IPC message contracts;
- a local service simulator for tests and early UI development.

Implemented PyQt6 shell:

- first-run scenario dialog;
- main window with Overview, Zones, Profiles, Apps, Journal and Diagnostics tabs;
- editable zone settings;
- manual VPN/direct profile add, activate and delete actions;
- manual managed app add and delete actions;
- tray menu and mini-indicator;
- UI/controller layer that keeps PyQt widgets away from SQLite internals.

The approved product design lives in
[docs/superpowers/specs/2026-06-12-vpn-sandbox-design.md](docs/superpowers/specs/2026-06-12-vpn-sandbox-design.md).

For continuation in new branches, start with
[docs/handoff/README.md](docs/handoff/README.md).

## Setup

From a fresh checkout:

```powershell
python -m pip install -e ".[dev]"
```

If the package is not installed in editable mode, set source import path before
running CLI commands directly from the checkout:

```powershell
$env:PYTHONPATH = "src"
```

## Verification

Run the test suite:

```powershell
$env:QT_QPA_PLATFORM = "offscreen"
python -m pytest -q
```

If Windows temp-directory permissions interfere in the local sandbox, run the same
suite with an explicit project-local temp directory:

```powershell
$env:QT_QPA_PLATFORM = "offscreen"
python -m pytest -p no:cacheprovider --basetemp .pytest-tmp -q
```

Run the smoke check:

```powershell
$env:PYTHONPATH = "src"
python -m vpn_sandbox doctor
```

Expected smoke output contains:

```json
{"app": "vpn-sandbox", "core": "ok", "storage_schema": 2, "version": "0.1.0"}
```

## UI Shell

Run the PyQt6 application:

```powershell
$env:PYTHONPATH = "src"
python -m vpn_sandbox ui
```

For a local sandbox data directory:

```powershell
$env:PYTHONPATH = "src"
$env:VPN_SANDBOX_DATA_DIR = "$PWD\.local-data"
python -m vpn_sandbox ui
```

Run headless UI smoke tests:

```powershell
$env:QT_QPA_PLATFORM = "offscreen"
python -m pytest tests/ui -q
```

## Next Stage

The next roadmap stage is **Stage 2. Calibration And Detection**. It should add
real calibration flows for VPN and direct profiles, collect external IP and local
network/process signals, and save the detected profile data through the existing
controller/repository architecture. It should not introduce Windows service,
WFP/native networking, installer work or process enforcement yet.
