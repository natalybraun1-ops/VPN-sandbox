from vpn_sandbox.app.controller import ZoneDashboard
from vpn_sandbox.core.models import ZoneKind, ZoneStatus
from vpn_sandbox.ui.text import status_label, zone_label
from vpn_sandbox.ui.view_models import build_zone_card


def test_text_labels_are_russian_and_user_facing():
    assert zone_label(ZoneKind.VPN) == "VPN-зона"
    assert zone_label(ZoneKind.DIRECT) == "Прямая зона"
    assert status_label(ZoneStatus.OK) == "Работает штатно"
    assert status_label(ZoneStatus.ATTENTION) == "Требует внимания"


def test_build_zone_card_formats_counts_and_profile_name():
    dashboard = ZoneDashboard(
        zone=ZoneKind.VPN,
        enabled=True,
        status=ZoneStatus.OK,
        reason="VPN profile matched",
        apps=(),
        active_profile_name="Германия · WireGuard",
    )

    card = build_zone_card(dashboard)

    assert card.title == "VPN-зона"
    assert card.status == "Работает штатно"
    assert card.profile == "Германия · WireGuard"
    assert card.app_count == "0 приложений"
