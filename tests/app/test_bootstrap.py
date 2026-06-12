from pathlib import Path

from vpn_sandbox.app.bootstrap import open_app_context
from vpn_sandbox.app.paths import default_data_dir
from vpn_sandbox.storage.schema import SCHEMA_VERSION


def test_default_data_dir_uses_override(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("VPN_SANDBOX_DATA_DIR", str(tmp_path / "data"))

    assert default_data_dir() == tmp_path / "data"


def test_open_app_context_initializes_repository_and_journal(tmp_path: Path):
    context = open_app_context(tmp_path)

    assert context.repository.schema_version() == SCHEMA_VERSION
    assert context.journal.read_recent(10) == []

    context.close()
