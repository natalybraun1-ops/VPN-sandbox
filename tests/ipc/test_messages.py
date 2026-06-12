from vpn_sandbox.core.models import ZoneStatus
from vpn_sandbox.ipc.messages import ServiceCommand, ServiceStatus, ZoneRuntimeStatus


def test_service_command_round_trips_json():
    command = ServiceCommand(
        name="evaluate_start",
        payload={"exe_path": "C:/Apps/browser.exe"},
    )

    assert ServiceCommand.from_json(command.to_json()) == command


def test_service_status_round_trips_json():
    status = ServiceStatus(
        control_available=True,
        service_running=True,
        zones={
            "vpn": ZoneRuntimeStatus(
                status=ZoneStatus.OK,
                reason="VPN profile matched",
            )
        },
    )

    loaded = ServiceStatus.from_json(status.to_json())

    assert loaded == status
    assert loaded.zones["vpn"].status == ZoneStatus.OK
