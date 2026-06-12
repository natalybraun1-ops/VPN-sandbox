# Песочница VPN

`vpn-sandbox` is the technical project name for a Windows VPN control application.

The first implementation slice contains the Python foundation:

- domain models for VPN and direct zones;
- policy evaluation;
- SQLite persistence;
- structured event journal;
- IPC message contracts;
- a local service simulator for tests and early UI development.

The approved product design lives in
[docs/superpowers/specs/2026-06-12-vpn-sandbox-design.md](docs/superpowers/specs/2026-06-12-vpn-sandbox-design.md).

## Foundation Checks

Run the test suite:

```powershell
python -m pytest
```

If Windows temp-directory permissions interfere in the local sandbox, run the same
suite with an explicit project-local temp directory:

```powershell
python -m pytest -p no:cacheprovider --basetemp .pytest-tmp -q
```

Run the smoke check:

```powershell
$env:PYTHONPATH = "src"
python -m vpn_sandbox doctor
```

Expected smoke output contains:

```json
{"app": "vpn-sandbox", "core": "ok", "storage_schema": 1, "version": "0.1.0"}
```
