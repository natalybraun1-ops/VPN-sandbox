import ast
from dataclasses import FrozenInstanceError
import importlib
import inspect

import pytest

from vpn_sandbox.app.controller import ZoneDashboard
from vpn_sandbox.core.models import ManagedApp, ViolationAction, ZoneKind, ZoneStatus
from vpn_sandbox.ui.text import (
    status_label,
    violation_action_label,
    zone_label,
)
from vpn_sandbox.ui.view_models import build_zone_card


ZONE_LABEL_CASES = (
    (ZoneKind.VPN, "VPN-зона"),
    (ZoneKind.DIRECT, "Прямая зона"),
)

STATUS_LABEL_CASES = (
    (ZoneStatus.OK, "Работает штатно"),
    (ZoneStatus.ATTENTION, "Требует внимания"),
    (ZoneStatus.BLOCKED, "Заблокировано"),
    (ZoneStatus.DISABLED, "Отключено"),
)

VIOLATION_ACTION_LABEL_CASES = (
    (ViolationAction.CLOSE_IMMEDIATELY, "Закрыть сразу"),
    (ViolationAction.CLOSE_AFTER_10, "Закрыть через 10 секунд"),
    (ViolationAction.CLOSE_AFTER_20, "Закрыть через 20 секунд"),
    (ViolationAction.CLOSE_AFTER_30, "Закрыть через 30 секунд"),
    (ViolationAction.WARN_ONLY, "Только предупреждать"),
)


def _apps(count: int) -> tuple[ManagedApp, ...]:
    return tuple(
        ManagedApp(
            id=f"app-{index}",
            zone=ZoneKind.VPN,
            exe_path=rf"C:\Apps\app-{index}.exe",
            display_name=f"App {index}",
        )
        for index in range(count)
    )


def _dashboard(
    *,
    apps: tuple[ManagedApp, ...] = (),
    enabled: bool = True,
    active_profile_name: str | None = "Германия · WireGuard",
    reason: str = "VPN profile matched",
    status: ZoneStatus = ZoneStatus.OK,
    zone: ZoneKind = ZoneKind.VPN,
) -> ZoneDashboard:
    return ZoneDashboard(
        zone=zone,
        enabled=enabled,
        status=status,
        reason=reason,
        apps=apps,
        active_profile_name=active_profile_name,
    )


def test_zone_label_table_covers_every_zone_kind():
    assert {zone for zone, _ in ZONE_LABEL_CASES} == set(ZoneKind)


@pytest.mark.parametrize(("zone", "expected"), ZONE_LABEL_CASES)
def test_zone_labels_are_russian_and_user_facing(zone, expected):
    assert zone_label(zone) == expected


def test_status_label_table_covers_every_zone_status():
    assert {status for status, _ in STATUS_LABEL_CASES} == set(ZoneStatus)


@pytest.mark.parametrize(("status", "expected"), STATUS_LABEL_CASES)
def test_status_labels_are_russian_and_user_facing(status, expected):
    assert status_label(status) == expected


def test_violation_action_label_table_covers_every_action():
    assert {action for action, _ in VIOLATION_ACTION_LABEL_CASES} == set(
        ViolationAction
    )


@pytest.mark.parametrize(("action", "expected"), VIOLATION_ACTION_LABEL_CASES)
def test_violation_action_labels_are_russian_and_user_facing(action, expected):
    assert violation_action_label(action) == expected


def test_build_zone_card_formats_active_profile_name_and_zero_apps():
    card = build_zone_card(_dashboard())

    assert card.title == "VPN-зона"
    assert card.status == "Работает штатно"
    assert card.profile == "Германия · WireGuard"
    assert card.app_count == "0 приложений"


def test_build_zone_card_uses_profile_fallback_and_propagates_state():
    card = build_zone_card(
        _dashboard(
            enabled=False,
            status=ZoneStatus.ATTENTION,
            reason="No managed applications",
            active_profile_name=None,
        )
    )

    assert card.reason == "No managed applications"
    assert card.enabled is False
    assert card.profile == "Профиль не выбран"


@pytest.mark.parametrize(
    ("count", "expected"),
    (
        (1, "1 приложение"),
        (2, "2 приложения"),
        (5, "5 приложений"),
        (11, "11 приложений"),
        (21, "21 приложение"),
        (22, "22 приложения"),
    ),
)
def test_build_zone_card_formats_russian_app_count_plurals(count, expected):
    assert build_zone_card(_dashboard(apps=_apps(count))).app_count == expected


def test_zone_card_view_model_is_frozen():
    card = build_zone_card(_dashboard())

    with pytest.raises(FrozenInstanceError):
        card.title = "Прямая зона"


@pytest.mark.parametrize(
    "module_name",
    (
        "vpn_sandbox.ui.text",
        "vpn_sandbox.ui.view_models",
    ),
)
def test_ui_view_model_modules_do_not_import_qt(module_name):
    module = importlib.import_module(module_name)
    tree = ast.parse(inspect.getsource(module))
    imported_roots = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_roots.update(
                alias.name.split(".", maxsplit=1)[0] for alias in node.names
            )
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported_roots.add(node.module.split(".", maxsplit=1)[0])

    assert not any(
        root.startswith(("PyQt", "PySide", "Qt")) for root in imported_roots
    )
