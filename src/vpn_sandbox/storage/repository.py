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
        try:
            row = self._connection.execute(
                "SELECT value FROM meta WHERE key = 'schema_version'"
            ).fetchone()
        except sqlite3.OperationalError as exc:
            if str(exc) != "no such table: meta":
                raise
            return 0
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
