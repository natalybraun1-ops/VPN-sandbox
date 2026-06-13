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
    subparsers.add_parser("ui")
    args = parser.parse_args(argv)

    if args.command == "ui":
        from vpn_sandbox.ui.app import main as ui_main

        return ui_main([])

    if args.command == "doctor":
        print(json.dumps(build_doctor_payload(), ensure_ascii=False, sort_keys=True))
        return 0

    return 2


if __name__ == "__main__":
    raise SystemExit(main())
