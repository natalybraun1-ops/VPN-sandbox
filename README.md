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
