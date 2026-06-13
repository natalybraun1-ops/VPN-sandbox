from __future__ import annotations

from vpn_sandbox.core.models import ViolationAction, ZoneKind, ZoneStatus


def zone_label(zone: ZoneKind) -> str:
    return {
        ZoneKind.VPN: "VPN-зона",
        ZoneKind.DIRECT: "Прямая зона",
    }[zone]


def status_label(status: ZoneStatus) -> str:
    return {
        ZoneStatus.OK: "Работает штатно",
        ZoneStatus.ATTENTION: "Требует внимания",
        ZoneStatus.BLOCKED: "Заблокировано",
        ZoneStatus.DISABLED: "Отключено",
    }[status]


def violation_action_label(action: ViolationAction) -> str:
    return {
        ViolationAction.CLOSE_IMMEDIATELY: "Закрыть сразу",
        ViolationAction.CLOSE_AFTER_10: "Закрыть через 10 секунд",
        ViolationAction.CLOSE_AFTER_20: "Закрыть через 20 секунд",
        ViolationAction.CLOSE_AFTER_30: "Закрыть через 30 секунд",
        ViolationAction.WARN_ONLY: "Только предупреждать",
    }[action]
