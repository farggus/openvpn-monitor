import importlib
import json
import sys
from datetime import datetime as RealDateTime
from pathlib import Path
import uuid

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


@pytest.fixture
def parser_module(tmp_path, monkeypatch):
    status_path = tmp_path / "status.log"
    history_path = tmp_path / "history.log"
    active_path = tmp_path / "active_sessions.json"

    monkeypatch.setenv("OPENVPN_STATUS_LOG", str(status_path))
    monkeypatch.setenv("OPENVPN_HISTORY_LOG", str(history_path))
    monkeypatch.setenv("OPENVPN_ACTIVE_SESSIONS", str(active_path))

    from app import config

    importlib.reload(config)

    from app import parser

    importlib.reload(parser)

    return parser, status_path, history_path, active_path


def _freeze_time(monkeypatch, parser, year=2024, month=1, day=1, hour=12, minute=0, second=0):
    class FixedDateTime(RealDateTime):
        @classmethod
        def now(cls, tz=None):
            return cls(year, month, day, hour, minute, second, tzinfo=tz)

    monkeypatch.setattr(parser.datetime, "datetime", FixedDateTime)
    return FixedDateTime


def test_parse_status_log_handles_ipv6(parser_module, monkeypatch):
    parser, status_path, history_path, active_path = parser_module

    status_path.write_text(
        """
Common Name,Real Address,Bytes Received,Bytes Sent,Connected Since
client1,[2001:db8::1]:443,1024,2048,2024-01-01 12:00:00

ROUTING TABLE
10.8.0.2,client1
""".strip()
    )

    _freeze_time(monkeypatch, parser, hour=12, minute=10)

    fixed_uuid = uuid.UUID("12345678-1234-5678-1234-567812345678")
    monkeypatch.setattr(parser.uuid, "uuid4", lambda: fixed_uuid)

    clients = parser.parse_status_log(str(status_path))
    assert len(clients) == 1
    client = clients[0]

    assert client["common_name"] == "client1"
    assert client["real_ip"] == "2001:db8::1"
    assert client["port"] == "443"
    assert client["bytes_received"] == 1024
    assert client["bytes_sent"] == 2048
    assert client["connected_since"] == "2024-01-01 12:00:00"
    assert client["vpn_ip"] == "10.8.0.2"
    assert client["time_online"].startswith("0:")

    with active_path.open() as fh:
        data = json.load(fh)

    assert data["client1"]["port"] == "443"
    assert data["client1"]["vpn_ip"] == "10.8.0.2"

    history_entries = history_path.read_text().strip().split(",")
    assert history_entries == [
        "2024-01-01 12:00:00",
        "client1",
        "2001:db8::1",
        str(fixed_uuid),
        "",
        "",
        "",
        "10.8.0.2",
        "443",
    ]


def test_parse_status_log_records_disconnect(parser_module, monkeypatch):
    parser, status_path, history_path, active_path = parser_module

    parser.save_active_sessions(
        {
            "alice": {
                "ip": "198.51.100.10",
                "vpn_ip": "10.8.0.5",
                "connected_at": "2024-01-01 09:00:00",
                "bytes_received": 1048576,
                "bytes_sent": 2097152,
                "session_id": "existing-session",
                "port": "443",
            }
        },
        str(active_path),
    )

    status_path.write_text(
        """
Common Name,Real Address,Bytes Received,Bytes Sent,Connected Since

ROUTING TABLE
""".strip()
    )

    _freeze_time(monkeypatch, parser, hour=13)

    clients = parser.parse_status_log(str(status_path))
    assert clients == []

    with active_path.open() as fh:
        data = json.load(fh)
    assert data == {}

    history_line = history_path.read_text().strip()
    assert history_line == (
        "2024-01-01 09:00:00,alice,198.51.100.10,existing-session,1.0,2.0,10.8.0.5,443,"
        "2024-01-01 13:00:00"
    )


def test_parse_status_log_recovers_from_corrupted_state(parser_module, monkeypatch):
    parser, status_path, history_path, active_path = parser_module

    active_path.write_text("{")


    status_path.write_text(
        """
Common Name,Real Address,Bytes Received,Bytes Sent,Connected Since
alice,198.51.100.20:51820,2048,1024,2024-01-01 11:45:00

ROUTING TABLE
10.8.0.6,alice
""".strip()
    )

    _freeze_time(monkeypatch, parser, hour=12)

    fixed_uuid = uuid.UUID("87654321-4321-6789-4321-678943216789")
    monkeypatch.setattr(parser.uuid, "uuid4", lambda: fixed_uuid)

    clients = parser.parse_status_log(str(status_path))

    assert clients[0]["common_name"] == "alice"
    assert clients[0]["vpn_ip"] == "10.8.0.6"
    assert clients[0]["real_ip"] == "198.51.100.20"
    assert clients[0]["port"] == "51820"

    with active_path.open() as fh:
        data = json.load(fh)

    assert data == {
        "alice": {
            "ip": "198.51.100.20",
            "vpn_ip": "10.8.0.6",
            "connected_at": "2024-01-01 11:45:00",
            "bytes_received": 2048,
            "bytes_sent": 1024,
            "port": "51820",
            "session_id": str(fixed_uuid),
        }
    }

    history_entries = history_path.read_text().strip().split(",")
    assert history_entries[0:4] == [
        "2024-01-01 11:45:00",
        "alice",
        "198.51.100.20",
        str(fixed_uuid),
    ]
