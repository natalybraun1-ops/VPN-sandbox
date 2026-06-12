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
