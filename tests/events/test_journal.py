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


def test_event_journal_masks_exact_ip_key(tmp_path: Path):
    journal = EventJournal(tmp_path / "events.jsonl")
    journal.append(
        EventRecord(
            timestamp="2026-06-12T10:00:00Z",
            level="warning",
            zone="vpn",
            app="Chrome",
            reason="IP check",
            details={"ip": "203.0.113.10"},
        )
    )

    events = journal.read_recent(limit=10)

    assert events[0].details["ip"] == "203.0.113.x"


def test_event_journal_masks_nested_ip_details(tmp_path: Path):
    journal = EventJournal(tmp_path / "events.jsonl")
    details = {
        "network": {"external_ip": "198.51.100.7"},
        "routes": [{"gateway_ip": "192.0.2.1"}],
        "label": "keep-me",
    }
    journal.append(
        EventRecord(
            timestamp="2026-06-12T10:00:00Z",
            level="warning",
            zone="direct",
            app="Editor",
            reason="Route check",
            details=details,
        )
    )

    events = journal.read_recent(limit=10)

    assert events[0].details == {
        "network": {"external_ip": "198.51.100.x"},
        "routes": [{"gateway_ip": "192.0.2.x"}],
        "label": "keep-me",
    }
    assert details == {
        "network": {"external_ip": "198.51.100.7"},
        "routes": [{"gateway_ip": "192.0.2.1"}],
        "label": "keep-me",
    }


def test_event_journal_returns_no_events_for_non_positive_limit(tmp_path: Path):
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

    assert journal.read_recent(limit=0) == []
    assert journal.read_recent(limit=-1) == []


def test_event_journal_missing_file_has_no_recent_events(tmp_path: Path):
    journal = EventJournal(tmp_path / "missing.jsonl")

    assert journal.read_recent(limit=10) == []


def test_event_journal_skips_blank_lines(tmp_path: Path):
    journal_path = tmp_path / "events.jsonl"
    record = EventRecord(
        timestamp="2026-06-12T10:00:00Z",
        level="warning",
        zone="vpn",
        app="Chrome",
        reason="VPN country mismatch",
        details={"external_ip": "203.0.113.10"},
    )
    journal_path.write_text(f"\n{record.to_json_line()}\n\n", encoding="utf-8")

    events = EventJournal(journal_path).read_recent(limit=10)

    assert events == [
        EventRecord(
            timestamp="2026-06-12T10:00:00Z",
            level="warning",
            zone="vpn",
            app="Chrome",
            reason="VPN country mismatch",
            details={"external_ip": "203.0.113.x"},
        )
    ]
