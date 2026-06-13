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
