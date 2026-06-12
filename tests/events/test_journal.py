from pathlib import Path

from vpn_sandbox.events.journal import EventJournal, EventRecord, mask_ip


def test_mask_ip_hides_last_octet():
    assert mask_ip("203.0.113.10") == "203.0.113.x"
    assert mask_ip("not-an-ip") == "not-an-ip"


def test_event_journal_appends_and_reads_recent_events(tmp_path: Path):
    journal = EventJournal(tmp_path / "events.jsonl")
    journal.append(
        EventRecord(
            timestamp="2026-06-12T10:00:00Z",
            level="warning",
            zone="vpn",
            app="Chrome",
            reason="VPN country mismatch",
            details={"external_ip": "203.0.113.10"},
        )
    )

    events = journal.read_recent(limit=10)

    assert len(events) == 1
    assert events[0].details["external_ip"] == "203.0.113.x"
