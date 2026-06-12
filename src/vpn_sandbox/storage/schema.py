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
