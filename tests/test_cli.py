from vpn_sandbox.__main__ import build_doctor_payload, main
from vpn_sandbox.storage.schema import SCHEMA_VERSION


def test_build_doctor_payload_reports_core_status():
    payload = build_doctor_payload()

    assert payload["app"] == "vpn-sandbox"
    assert payload["core"] == "ok"
    assert payload["storage_schema"] == SCHEMA_VERSION


def test_main_doctor_prints_json(capsys):
    exit_code = main(["doctor"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert '"app": "vpn-sandbox"' in captured.out
